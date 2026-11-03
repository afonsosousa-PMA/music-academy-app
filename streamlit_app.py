import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="Music Academy Portal",
    page_icon="🎵",
    layout="wide"
)

st.title("🎵 Music Academy Management Portal")
st.write("Welcome to your custom administration dashboard.")

# Conexão ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.header("Navigation")
menu_choice = st.sidebar.radio(
    "Select View",
    ["Master Data (DATABASE)", "Schedules", "Enrollments", "Parent Contacts", "Studio Availability"]
)

try:
    # Lê os dados da aba DATABASE com atualização a cada 5 segundos
    df = conn.read(worksheet="DATABASE", ttl=5)

    if menu_choice == "Master Data (DATABASE)":
        st.header("📊 Master Database View")
        st.dataframe(df, use_container_width=True)

    elif menu_choice == "Schedules":
        st.header("📅 Lesson & Teacher Schedules")
        st.dataframe(df, use_container_width=True)

    elif menu_choice == "Enrollments":
        st.header("🎓 Student Registrations & Class Tracking")
        st.dataframe(df, use_container_width=True)

    elif menu_choice == "Parent Contacts":
        st.header("📞 Parent & Guardian Directory")
        st.dataframe(df, use_container_width=True)

    elif menu_choice == "Studio Availability":
        st.header("🚪 Room & Studio Assignments")
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Could not load data from 'DATABASE' worksheet. Please check permissions and link. Details: {e}")
