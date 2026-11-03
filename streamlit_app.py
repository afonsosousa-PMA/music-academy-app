import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="Music Academy Portal",
    page_icon="🎵",
    layout="wide"
)

st.title("🎵 Music Academy Management Portal")
st.write("Welcome to your custom administration dashboard.")

conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.header("Navigation")
menu_choice = st.sidebar.radio(
    "Select View",
    ["Schedules", "Enrollments", "Parent Contacts", "Studio Availability"]
)

if menu_choice == "Schedules":
    st.header("📅 Lesson & Teacher Schedules")
    try:
        df_schedules = conn.read(worksheet="Schedules", ttl=5)
        st.dataframe(df_schedules, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load 'Schedules' tab. Please check worksheet tab name in Google Sheets. Details: {e}")

elif menu_choice == "Enrollments":
    st.header("🎓 Student Registrations & Class Tracking")
    try:
        df_enrollments = conn.read(worksheet="Enrollments", ttl=5)
        st.dataframe(df_enrollments, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load 'Enrollments' tab. Details: {e}")

elif menu_choice == "Parent Contacts":
    st.header("📞 Parent & Guardian Directory")
    try:
        df_contacts = conn.read(worksheet="Contacts", ttl=5)
        st.dataframe(df_contacts, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load 'Contacts' tab. Details: {e}")

elif menu_choice == "Studio Availability":
    st.header("🚪 Room & Studio Assignments")
    try:
        df_rooms = conn.read(worksheet="Rooms", ttl=5)
        st.dataframe(df_rooms, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load 'Rooms' tab. Details: {e}")
