import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Radar Tech Jobs", page_icon="🚀", layout="wide")
st.title("🚀 Radar Tech Jobs (TechSkills.dev)")
st.markdown("Monitoramento de vagas de TI usando **Python, Gemini AI e Supabase**.")

# Conexão com Supabase
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

if not url or not key:
    st.error("⚠️ Chaves do Supabase não encontradas no arquivo .env")
    st.stop()

@st.cache_resource
def init_connection():
    return create_client(url, key)

supabase = init_connection()

# Buscar dados do Supabase
@st.cache_data(ttl=600)
def load_data():
    vagas_response = supabase.table("vagas").select("*").execute()
    techs_response = supabase.table("vagas_tecnologias").select("*").execute()
    
    vagas_df = pd.DataFrame(vagas_response.data) if vagas_response.data else pd.DataFrame()
    techs_df = pd.DataFrame(techs_response.data) if techs_response.data else pd.DataFrame()
    
    return vagas_df, techs_df

vagas_df, techs_df = load_data()

if vagas_df.empty:
    st.warning("Nenhuma vaga processada ainda. Aguarde o robô puxar novos dados.")
else:
    # Transformações para visualização
    vagas_df['data_extracao'] = pd.to_datetime(vagas_df['data_extracao']).dt.strftime('%d/%m/%Y')
    
    # Métricas no topo
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Vagas Extraídas", len(vagas_df))
    col2.metric("Tecnologias Mapeadas", len(techs_df))
    col3.metric("Última Atualização", vagas_df['data_extracao'].max())
    
    st.divider()

    # Layout de 2 colunas para Gráfico e Informações
    col_grafico, col_info = st.columns([2, 1])

    with col_grafico:
        st.subheader("🔥 Tecnologias Mais Requisitadas")
        if not techs_df.empty:
            # Conta as tecnologias e pega as 10 mais populares
            top_techs = techs_df['tecnologia'].value_counts().head(10).reset_index()
            top_techs.columns = ['Tecnologia', 'Vagas']
            # O Streamlit gosta do index como o eixo X no bar_chart
            st.bar_chart(top_techs.set_index('Tecnologia'))

    with col_info:
        st.subheader("💡 Insights da IA")
        st.info("A Inteligência Artificial lê o texto bruto das vagas (que muitas vezes é só uma parede de texto), entende o contexto usando um modelo LLM (Gemini) e extrai de forma estruturada as ferramentas, nível de senioridade e modelo de trabalho.")
        st.write(f"**Empresas analisadas recentemente:** {', '.join(vagas_df['nome_empresa'].unique()[:5])}...")

    st.divider()

    # Tabela completa
    st.subheader("📋 Últimas Vagas Processadas pela IA")
    # Limpando os nomes das colunas pra ficar mais bonito
    df_exibicao = vagas_df[['titulo', 'nome_empresa', 'senioridade', 'remoto', 'salario_mencionado']].copy()
    df_exibicao.columns = ['Título da Vaga', 'Empresa', 'Senioridade', 'Remoto', 'Salário']
    
    st.dataframe(df_exibicao, use_container_width=True)
