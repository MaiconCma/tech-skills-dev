import os
import time
import requests
from pydantic import BaseModel, ValidationError
from typing import List, Optional
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from google import genai
from google.genai import types
from supabase import create_client, Client

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

if not api_key or not supabase_url or not supabase_key:
    raise ValueError("Chaves faltando no arquivo .env.")

client = genai.Client(api_key=api_key)
supabase: Client = create_client(supabase_url, supabase_key)

class JobInsights(BaseModel):
    tecnologias: List[str]
    senioridade: str  
    remoto: bool
    salario_mencionado: Optional[str]

def fetch_jobs_from_remotive(limit=3):
    print(f"📥 Buscando {limit} vagas na API da Remotive...")
    response = requests.get(f"https://remotive.com/api/remote-jobs?category=software-dev&limit={limit}")
    response.raise_for_status()
    jobs = response.json().get("jobs", [])
    print(f"✅ {len(jobs)} vagas encontradas!\n")
    return jobs

@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=4, max=20))
def enrich_job_with_ai(job_description: str) -> Optional[JobInsights]:
    prompt = f"""
    Você é um Engenheiro de Dados especialista. Leia a descrição da vaga abaixo e extraia as informações pedidas.
    Retorne EXATAMENTE um JSON válido.
    
    Vaga:
    {job_description}
    """
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JobInsights,
            ),
        )
        return JobInsights.model_validate_json(response.text)
    except Exception as e:
        print(f"⚠️ Erro na IA: {e}")
        raise 

if __name__ == "__main__":
    print("🚀 Iniciando Pipeline ETL -> Conectado ao Supabase!\n")
    
    # Pegamos 3 vagas
    raw_jobs = fetch_jobs_from_remotive(limit=3)[:3]
    
    for i, job in enumerate(raw_jobs, 1):
        print("-" * 50)
        print(f"🏢 Processando Vaga {i}: {job['title']}")
        
        insights = enrich_job_with_ai(job["description"])
        
        if insights:
            print(f"✨ Tecnologias extraídas: {insights.tecnologias}")
            
            # PREPARANDO DADOS PARA O BANCO (Camada Gold)
            job_data = {
                "id_original": str(job["id"]),
                "titulo": job["title"],
                "nome_empresa": job["company_name"],
                "url": job["url"],
                "senioridade": insights.senioridade,
                "remoto": insights.remoto,
                "salario_mencionado": insights.salario_mencionado
            }
            
            try:
                # 1. UPSERT (Faz o INSERT. Se o id_original já existir, ele só atualiza. Isso garante que nunca teremos vagas duplicadas!)
                result = supabase.table("vagas").upsert(job_data, on_conflict="id_original").execute()
                
                if result.data:
                    vaga_id = result.data[0]['id']
                    
                    # 2. Deleta as tecnologias antigas dessa vaga (caso seja atualização)
                    supabase.table("vagas_tecnologias").delete().eq("vaga_id", vaga_id).execute()
                    
                    # 3. Insere as tecnologias novas extraídas pela IA
                    techs_to_insert = [{"vaga_id": vaga_id, "tecnologia": tech} for tech in insights.tecnologias]
                    if techs_to_insert:
                        supabase.table("vagas_tecnologias").insert(techs_to_insert).execute()
                        
                    print("💾 Salvo com sucesso no Supabase!")
            except Exception as e:
                print(f"❌ Erro ao salvar no banco de dados: {e}")
        
        # Rate Limiting do Gemini Grátis
        if i < len(raw_jobs):
            print("⏳ Pausa de 12 segundos (Rate Limit)...")
            time.sleep(12)
            
    print("\n🏁 Pipeline finalizado! Vá olhar a aba 'Table Editor' no Supabase!")
