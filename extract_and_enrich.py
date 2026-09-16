import os
import json
import time
import requests
from pydantic import BaseModel, ValidationError
from typing import List, Optional
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Chave da API não encontrada. Verifique o arquivo .env.")

client = genai.Client(api_key=api_key)

class JobInsights(BaseModel):
    tecnologias: List[str]
    senioridade: str  
    remoto: bool
    salario_mencionado: Optional[str]

def fetch_jobs_from_remotive(limit=3):
    print(f"📥 Buscando {limit} vagas na API da Remotive...")
    url = f"https://remotive.com/api/remote-jobs?category=software-dev&limit={limit}"
    
    response = requests.get(url)
    response.raise_for_status()
    
    jobs = response.json().get("jobs", [])
    print(f"✅ {len(jobs)} vagas encontradas!\n")
    return jobs

# Tenacity: Se der erro (ex: 429), ele espera e tenta de novo automaticamente até 4 vezes!
@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=4, max=20))
def enrich_job_with_ai(job_description: str) -> Optional[JobInsights]:
    prompt = f"""
    Você é um Engenheiro de Dados especialista em análise de vagas de TI.
    Leia a descrição da vaga abaixo (que pode conter HTML) e extraia as informações solicitadas.
    Retorne EXATAMENTE um JSON válido.
    
    Descrição da Vaga:
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
        job_data = JobInsights.model_validate_json(response.text)
        return job_data
    
    except ValidationError as e:
        print(f"⚠️ Erro de validação do Pydantic: {e}")
        return None
    except Exception as e:
        print(f"⚠️ Erro na IA (será tentado novamente se for Rate Limit): {e}")
        raise # Levanta o erro para o Tenacity capturar e fazer o Retry

if __name__ == "__main__":
    print("🚀 Iniciando Pipeline ETL - Fase 1.5 (Resiliência)\n")
    
    # Vamos pegar só 3 para o teste ser mais rápido, mas agora a API não vai bloquear!
    raw_jobs = fetch_jobs_from_remotive(limit=3)[:3]
    
    for i, job in enumerate(raw_jobs, 1):
        print("-" * 50)
        print(f"🏢 Vaga {i}: {job['title']} na {job['company_name']}")
        
        insights = enrich_job_with_ai(job["description"])
        
        if insights:
            print(f"✨ Tecnologias extraídas: {insights.tecnologias}")
            print(f"✨ Senioridade: {insights.senioridade}")
        else:
            print("❌ Falha ao processar essa vaga.")
            
        # O Pulo do Gato para a API Gratuita (5 requisições por minuto = 1 a cada 12 seg)
        if i < len(raw_jobs):
            print("⏳ Pausa de 12 segundos (Rate Limit)...")
            time.sleep(12)
            
    print("\n🏁 Fase 1.5 concluída com sucesso! Nenhuma vaga perdida.")
