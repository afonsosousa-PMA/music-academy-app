import streamlit as st
import pandas as pd

# Configuração da página do navegador
st.set_page_config(
    page_title="Music Academy Portal",
    page_icon="🎵",
    layout="wide"
)

st.title("🎵 Music Academy Management Portal")
st.write("Painel de Gestão e Controlo da Academia de Música.")

# Menu de Navegação na Barra Lateral
st.sidebar.header("Navegação")
menu_choice = st.sidebar.radio(
    "Selecione a Opção",
    [
        "📊 Visualizar Base de Dados",
        "➕ Adicionar Novo Agendamento / Aluno",
        "📞 Contactos dos Pais",
        "🚪 Ocupação de Salas"
    ]
)

# Função para carregar os dados do Google Sheets
def load_data():
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        if "/d/" in sheet_url:
            sheet_id = sheet_url.split("/d/")[1].split("/")[0]
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=DATABASE"
        else:
            csv_url = sheet_url
        return pd.read_csv(csv_url)
    except Exception as e:
        st.error(f"Erro ao carregar a base de dados: {e}")
        return pd.DataFrame()

# Carrega os dados atuais
df = load_data()

# OPÇÃO 1: Visualização dos Dados Globais
if menu_choice == "📊 Visualizar Base de Dados":
    st.header("📋 Dados Globais (DATABASE)")
    if not df.empty:
        # Filtro de pesquisa rápido
        search_query = st.text_input("🔍 Pesquisar por Aluno, Professor ou Instrumento:")
        if search_query:
            filtered_df = df[df.astype(str).apply(lambda row: row.str.contains(search_query, case=False).any(), axis=1)]
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum dado encontrado ou a carregar...")

# OPÇÃO 2: Formulário para Inserir Novos Dados
elif menu_choice == "➕ Adicionar Novo Agendamento / Aluno":
    st.header("📝 Registar Novo Aluno & Aula")
    st.write("Preencha o formulário abaixo para adicionar uma nova inscrição à base de dados.")

    with st.form("new_student_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            student_name = st.text_input("Nome do Aluno *")
            instrument = st.selectbox("Instrumento", ["Piano", "Guitarra", "Violino", "Canto", "Bateria", "Flauta", "Outro"])
            teacher = st.text_input("Nome do Professor *")
            room = st.selectbox("Sala / Estúdio", ["Sala 1", "Sala 2", "Sala 3", "Estúdio A", "Estúdio B"])

        with col2:
            day_of_week = st.selectbox("Dia da Semana", ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"])
            time_slot = st.time_input("Horário da Aula")
            parent_name = st.text_input("Nome do Encarregado de Educação")
            parent_contact = st.text_input("Contacto Telefónico / Email")

        submitted = st.form_submit_button("💾 Guardar Registo")

        if submitted:
            if not student_name or not teacher:
                st.warning("Por favor, preencha pelo menos o Nome do Aluno e o Professor.")
            else:
                # Verificação simples de duplo agendamento de sala
                conflict = False
                if not df.empty and "Sala" in df.columns and "Dia" in df.columns and "Hora" in df.columns:
                    check_conflict = df[
                        (df["Sala"] == room) & 
                        (df["Dia"] == day_of_week) & 
                        (df["Hora"] == str(time_slot))
                    ]
                    if not check_conflict.empty:
                        conflict = True

                if conflict:
                    st.error(f"⚠️ Alerta de Sobreposição! A {room} já se encontra ocupada na {day_of_week} às {time_slot}.")
                else:
                    st.success(f"✅ Registo de {student_name} validado com sucesso!")
                    st.info("Nota: Para atualizar diretamente a folha de cálculo a partir do browser, ativaremos a escrita direta no próximo passo.")

# OPÇÃO 3: Contactos dos Enc. Educação
elif menu_choice == "📞 Contactos dos Pais":
    st.header("📞 Diretório de Contactos dos Encarregados de Educação")
    if not df.empty:
        st.dataframe(df, use_container_width=True)

# OPÇÃO 4: Ocupação de Salas
elif menu_choice == "🚪 Ocupação de Salas":
    st.header("🚪 Estado e Ocupação das Salas")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
