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
    nome_empresa: Optional[str] # Adicionamos para o Gemini tentar achar a empresa caso não venha clara na API

def fetch_jobs_from_remotive(limit=2):
    print(f"📥 Buscando {limit} vagas na API da Remotive (Gringa)...")
    response = requests.get(f"https://remotive.com/api/remote-jobs?category=software-dev&limit={limit}")
    response.raise_for_status()
    raw_jobs = response.json().get("jobs", [])
    
    jobs = []
    for j in raw_jobs:
        jobs.append({
            "id": str(j["id"]),
            "title": j["title"],
            "company_name": j["company_name"],
            "url": j["url"],
            "description": j["description"],
            "origem": "Remotive"
        })
    print(f"✅ {len(jobs)} vagas gringas encontradas!\n")
    return jobs

def fetch_jobs_from_github_br(limit=2):
    print(f"📥 Buscando {limit} vagas BR no GitHub (backend-br/vagas)...")
    url = f"https://api.github.com/repos/backend-br/vagas/issues?state=open&per_page={limit}"
    response = requests.get(url)
    response.raise_for_status()
    issues = response.json()
    
    jobs = []
    for issue in issues:
        if "pull_request" in issue:
            continue
        jobs.append({
            "id": f"gh-br-{issue['number']}",
            "title": issue["title"],
            "company_name": "Buscar no texto", 
            "url": issue["html_url"],
            "description": issue.get("body", "") or issue["title"],
            "origem": "GitHub BR"
        })
    print(f"✅ {len(jobs)} vagas BR encontradas!\n")
    return jobs

@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=4, max=20))
def enrich_job_with_ai(job_description: str) -> Optional[JobInsights]:
    prompt = f"""
    Você é um Engenheiro de Dados. Leia a vaga abaixo e extraia as informações pedidas.
    Preste atenção especial para encontrar o Nome da Empresa no texto, caso exista.
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
    print("🚀 Iniciando Pipeline ETL V2 (Brasil + Mundo)\n")
    
    # Junta as vagas do Brasil e da Gringa
    jobs_gringa = fetch_jobs_from_remotive(limit=2)[:2]
    jobs_brasil = fetch_jobs_from_github_br(limit=2)[:2]
    all_jobs = jobs_gringa + jobs_brasil
    
    for i, job in enumerate(all_jobs, 1):
        print("-" * 50)
        print(f"🏢 Processando Vaga {i} ({job['origem']}): {job['title']}")
        
        insights = enrich_job_with_ai(job["description"])
        
        if insights:
            print(f"✨ Tecnologias extraídas: {insights.tecnologias}")
            
            # Decide o nome da empresa (usa a da API se existir, senão usa a que a IA achou)
            empresa_final = job["company_name"]
            if empresa_final == "Buscar no texto" and insights.nome_empresa:
                empresa_final = insights.nome_empresa
            elif empresa_final == "Buscar no texto":
                empresa_final = "Não informada"
                
            job_data = {
                "id_original": job["id"],
                "titulo": job["title"],
                "nome_empresa": empresa_final,
                "url": job["url"],
                "senioridade": insights.senioridade,
                "remoto": insights.remoto,
                "salario_mencionado": insights.salario_mencionado,
                "origem": job["origem"]
            }
            
            try:
                result = supabase.table("vagas").upsert(job_data, on_conflict="id_original").execute()
                
                if result.data:
                    vaga_id = result.data[0]['id']
                    supabase.table("vagas_tecnologias").delete().eq("vaga_id", vaga_id).execute()
                    
                    techs_to_insert = [{"vaga_id": vaga_id, "tecnologia": tech} for tech in insights.tecnologias]
                    if techs_to_insert:
                        supabase.table("vagas_tecnologias").insert(techs_to_insert).execute()
                        
                    print("💾 Salvo com sucesso no Supabase!")
            except Exception as e:
                print(f"❌ Erro ao salvar no banco de dados: {e}")
        
        # Pausa para o limite da API do Google (Conta grátis)
        if i < len(all_jobs):
            print("⏳ Pausa de 12 segundos (Rate Limit)...")
            time.sleep(12)
            
    print("\n🏁 Pipeline V2 finalizado!")
