import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Radar Tech Jobs", page_icon="🚀", layout="wide")
st.title("🚀 Radar Tech Jobs (TechSkills.dev)")
st.markdown("Monitoramento de vagas no Brasil e no Mundo usando **Python, Gemini AI e Supabase**.")

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
@st.cache_data(ttl=300) # Cache de 5 min
def load_data():
    vagas_response = supabase.table("vagas").select("*").execute()
    techs_response = supabase.table("vagas_tecnologias").select("*").execute()
    
    vagas_df = pd.DataFrame(vagas_response.data) if vagas_response.data else pd.DataFrame()
    techs_df = pd.DataFrame(techs_response.data) if techs_response.data else pd.DataFrame()
    
    return vagas_df, techs_df

vagas_df_completo, techs_df_completo = load_data()

if vagas_df_completo.empty:
    st.warning("Nenhuma vaga processada ainda. Rode o extrator primeiro.")
else:
    # ------------------ FILTROS ------------------
    st.sidebar.header("🔍 Filtros")
    origens_disponiveis = vagas_df_completo['origem'].unique().tolist()
    
    # Adicionar opção 'Todas'
    origem_selecionada = st.sidebar.radio("Filtrar por Origem:", ["Todas"] + origens_disponiveis)
    
    if origem_selecionada == "Todas":
        vagas_df = vagas_df_completo
    else:
        vagas_df = vagas_df_completo[vagas_df_completo['origem'] == origem_selecionada]
        
    # Filtrar tecnologias para que batam apenas com as vagas filtradas
    techs_df = techs_df_completo[techs_df_completo['vaga_id'].isin(vagas_df['id'])]

    # ---------------------------------------------
    
    vagas_df['data_extracao'] = pd.to_datetime(vagas_df['data_extracao']).dt.strftime('%d/%m/%Y')
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Vagas Encontradas", len(vagas_df))
    col2.metric("Tecnologias Citadas", len(techs_df))
    col3.metric("Última Atualização", vagas_df['data_extracao'].max())
    
    st.divider()

    col_grafico, col_info = st.columns([2, 1])

    with col_grafico:
        st.subheader(f"🔥 Tecnologias em Alta ({origem_selecionada})")
        if not techs_df.empty:
            top_techs = techs_df['tecnologia'].value_counts().head(10).reset_index()
            top_techs.columns = ['Tecnologia', 'Vagas']
            st.bar_chart(top_techs.set_index('Tecnologia'))

    with col_info:
        st.subheader("💡 Como funciona?")
        st.info("A IA do Google Gemini lê o texto bruto das vagas do Brasil (GitHub) e Internacionais (Remotive) e tenta extrair de forma padronizada os dados mostrados na tabela abaixo.")

    st.divider()

    st.subheader("📋 Últimas Vagas")
    df_exibicao = vagas_df[['titulo', 'nome_empresa', 'senioridade', 'salario_mencionado', 'origem', 'url']].copy()
    df_exibicao.columns = ['Título', 'Empresa', 'Nível', 'Salário', 'Origem', 'Link']
    
    st.dataframe(df_exibicao, use_container_width=True)
