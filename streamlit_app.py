import streamlit as st
import pandas as pd

# Browser tab configuration
st.set_page_config(
    page_title="Music Academy Portal",
    page_icon="🎵",
    layout="wide"
)

# App Header
st.title("🎵 Music Academy Management Portal")
st.write("Welcome to your custom administration dashboard.")

# Sidebar Navigation
st.sidebar.header("Navigation")
menu_choice = st.sidebar.radio(
    "Select View",
    [
        "📊 Master Database View",
        "➕ Add New Booking / Student",
        "📞 Parent Contacts",
        "🚪 Studio Availability"
    ]
)

# Function to load Google Sheets data
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
        st.error(f"Error loading database: {e}")
        return pd.DataFrame()

# Load current data
df = load_data()

# OPTION 1: Master Database View
if menu_choice == "📊 Master Database View":
    st.header("📋 Master Data (DATABASE)")
    if not df.empty:
        search_query = st.text_input("🔍 Search by Student, Teacher, or Instrument:")
        if search_query:
            filtered_df = df[df.astype(str).apply(lambda row: row.str.contains(search_query, case=False).any(), axis=1)]
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No data found or loading...")

# OPTION 2: New Student / Lesson Form
elif menu_choice == "➕ Add New Booking / Student":
    st.header("📝 Register New Student & Lesson")
    st.write("Fill out the form below to add a new registration to your database.")

    with st.form("new_student_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            student_name = st.text_input("Student Name *")
            instrument = st.selectbox("Instrument", ["Piano", "Guitar", "Violin", "Vocals", "Drums", "Flute", "Other"])
            teacher = st.text_input("Teacher Name *")
            room = st.selectbox("Room / Studio", ["Room 1", "Room 2", "Room 3", "Studio A", "Studio B"])

        with col2:
            day_of_week = st.selectbox("Day of Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
            time_slot = st.time_input("Lesson Time")
            parent_name = st.text_input("Parent / Guardian Name")
            parent_contact = st.text_input("Contact Phone / Email")

        submitted = st.form_submit_button("💾 Save Record")

        if submitted:
            if not student_name or not teacher:
                st.warning("Please enter at least the Student Name and Teacher Name.")
            else:
                # Double-booking prevention check
                conflict = False
                if not df.empty and "Room" in df.columns and "Day" in df.columns and "Time" in df.columns:
                    check_conflict = df[
                        (df["Room"] == room) & 
                        (df["Day"] == day_of_week) & 
                        (df["Time"] == str(time_slot))
                    ]
                    if not check_conflict.empty:
                        conflict = True

                if conflict:
                    st.error(f"⚠️ Schedule Conflict Alert! {room} is already booked on {day_of_week} at {time_slot}.")
                else:
                    st.success(f"✅ Record for {student_name} successfully validated!")
                    st.info("Note: To write changes directly back to Google Sheets from the app, we will set up direct write access in the next step.")

# OPTION 3: Parent Directory
elif menu_choice == "📞 Parent Contacts":
    st.header("📞 Parent & Guardian Contact Directory")
    if not df.empty:
        st.dataframe(df, use_container_width=True)

# OPTION 4: Studio Availability
elif menu_choice == "🚪 Studio Availability":
    st.header("🚪 Studio & Room Assignments")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
