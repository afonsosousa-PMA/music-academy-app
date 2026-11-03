import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Browser tab configuration
st.set_page_config(
    page_title="Music Academy Portal",
    page_icon="🎵",
    layout="wide"
)

# App Header
st.title("🎵 Music Academy Management Portal")
st.write("Welcome to your custom administration dashboard.")

# Establish Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Sidebar Navigation
st.sidebar.header("Navigation")
menu_choice = st.sidebar.radio(
    "Select View",
    [
        "📊 Master Database View",
        "➕ Add New Student",
        "📞 Parent Contacts",
        "🚪 Studio Availability"
    ]
)

# Helper function to load data from DATABASE tab
def load_data():
    try:
        return conn.read(worksheet="DATABASE", ttl=0)
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
        st.info("No data found or worksheet is empty.")

# OPTION 2: New Student / Lesson Form with Direct Write
elif menu_choice == "➕ Add New Booking / Student":
    st.header("📝 Register New Student & Lesson")
    st.write("Fill out the form below to add a new registration directly to your Google Sheet.")

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

        submitted = st.form_submit_button("💾 Save & Update Google Sheet")

        if submitted:
            if not student_name or not teacher:
                st.warning("Please enter at least the Student Name and Teacher Name.")
            else:
                # Double-booking conflict check
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
                    # Prepare new record row matching Google Sheet structure
                    new_data = pd.DataFrame([{
                        "Student Name": student_name,
                        "Instrument": instrument,
                        "Teacher": teacher,
                        "Room": room,
                        "Day": day_of_week,
                        "Time": str(time_slot),
                        "Parent Name": parent_parent_name if 'parent_parent_name' in locals() else parent_name,
                        "Parent Contact": parent_contact
                    }])

                    # Append to existing dataframe and write back to Google Sheets
                    updated_df = pd.concat([df, new_data], ignore_index=True)
                    try:
                        conn.update(worksheet="DATABASE", data=updated_df)
                        st.success(f"✅ Record for {student_name} saved directly to Google Sheets!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Could not save to Google Sheets. Verify permissions. Details: {e}")

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
