# 🚀 TechSkills.dev (Data Pipeline)

Este é o repositório do motor de Inteligência de Dados do **TechSkills.dev**. O objetivo deste pipeline é consumir vagas de tecnologia em texto não-estruturado, utilizar Inteligência Artificial (LLMs) para extrair as habilidades requisitadas, e armazenar esses dados estruturados em um banco de dados analítico.

## 🏗️ Arquitetura (Fase 1)

1. **Extract:** Consumo de APIs de vagas remotas (ex: Remotive).
2. **Transform (AI-Powered):** Processamento de texto não-estruturado usando o **Google Gemini 3.5 Flash**. A biblioteca `Pydantic` garante o formato estrito do JSON (Data Contract).
3. **Resiliência:** Implementação de `Tenacity` para *Exponential Backoff* e controle de *Rate Limiting*.

## 🛠️ Tecnologias Utilizadas
* Python 3.14
* Google GenAI SDK
* Pydantic
* Tenacity (Resiliência de Pipeline)
* Requests

## 🚀 Como rodar localmente
1. Clone este repositório.
2. Crie um arquivo `.env` na raiz com sua `GEMINI_API_KEY`.
3. Rode `pip install -r requirements.txt`.
4. Execute `python extract_and_enrich.py`.
