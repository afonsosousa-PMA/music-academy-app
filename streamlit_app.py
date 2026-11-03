import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Music Academy Portal",
    page_icon="🎵",
    layout="wide"
)

st.title("🎵 Music Academy Management Portal")
st.write("Painel de gestão da Academia de Música.")

# Menu Lateral
st.sidebar.header("Navegação")
menu_choice = st.sidebar.radio(
    "Selecione a vista",
    ["Dados Globais (DATABASE)", "Horários", "Inscrições", "Contactos dos Pais", "Salas"]
)

try:
    # Obtém o link configurado nos Secrets
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # Extrai o ID da folha de cálculo para ler a aba DATABASE diretamente
    if "/d/" in sheet_url:
        sheet_id = sheet_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=DATABASE"
    else:
        csv_url = sheet_url

    # Carrega os dados da aba DATABASE
    df = pd.read_csv(csv_url)

    if menu_choice == "Dados Globais (DATABASE)":
        st.header("📊 Master Database View")
        st.dataframe(df, use_container_width=True)

    elif menu_choice == "Horários":
        st.header("📅 Horários de Aulas e Professores")
        st.dataframe(df, use_container_width=True)

    elif menu_choice == "Inscrições":
        st.header("🎓 Alunos e Inscrições")
        st.dataframe(df, use_container_width=True)

    elif menu_choice == "Contactos dos Pais":
        st.header("📞 Diretório de Contactos dos Encarregados de Educação")
        st.dataframe(df, use_container_width=True)

    elif menu_choice == "Salas":
        st.header("🚪 Ocupação de Salas e Estúdios")
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Não foi possível carregar os dados. Verifique a ligação nos Secrets. Detalhes: {e}")
