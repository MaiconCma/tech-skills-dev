# 🚀 TechSkills.dev (Motor de Inteligência de Vagas)

Um pipeline de **Engenharia de Dados ponta a ponta** que consome vagas de TI, utiliza Inteligência Artificial (LLM) para extrair dados estruturados e exibe insights em um dashboard analítico.

## 🏗️ Arquitetura do Projeto

1. **Extract:** Consumo de vagas remotas via API (Remotive).
2. **Transform (AI-Powered):** Processamento do texto não-estruturado usando o modelo **Google Gemini 3.5 Flash** para inferência de tecnologias, senioridade e modelo de trabalho. Validação estrita (Data Contract) utilizando **Pydantic**.
3. **Load:** Ingestão de dados (*Upsert*) em um banco de dados relacional na nuvem (**Supabase / PostgreSQL**).
4. **Orchestration & Resiliência:** 
   - `Tenacity` para *Exponential Backoff* e tratamento de Rate Limits.
   - Automação em nuvem via **GitHub Actions** (Pipeline ETL diário).
5. **Data Visualization:** Dashboard analítico construído com **Streamlit** e **Pandas**.

## 🚀 Como rodar o projeto localmente

1. Clone este repositório.
2. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
   ```env
   GEMINI_API_KEY=sua_chave_aqui
   SUPABASE_URL=sua_url_aqui
   SUPABASE_SERVICE_KEY=sua_chave_secreta_aqui
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Para rodar o motor de IA e popular o banco (ETL):
   ```bash
   python extract_and_enrich.py
   ```
5. Para abrir o Dashboard de Análise:
   ```bash
   streamlit run dashboard.py
   ```
