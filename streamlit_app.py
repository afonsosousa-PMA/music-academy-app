import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Park Music Academy Management Portal",
    page_icon="🎵",
    layout="wide"
)

st.title("🎵 PARK MUSIC ACADEMY — MANAGEMENT PORTAL")

# -----------------------------------------------------------------------------
# 1. DATA LAYER (Decoupled & Prepared for Standalone Migration)
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data():
    """
    Loads raw data from the master DATABASE tab.
    Cleanly formatted to decouple UI logic from Google Sheets.
    """
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        if "/d/" in sheet_url:
            sheet_id = sheet_url.split("/d/")[1].split("/")[0]
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=DATABASE"
            df = pd.read_csv(csv_url)
        else:
            df = conn.read(worksheet="DATABASE", ttl=5)
            
        df = df.fillna("")
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading master database: {e}")
        return pd.DataFrame()

df = load_data()

# Ensure standard schema columns exist
expected_cols = [
    "Campus", "Teacher", "Day", "Start Time", "End Time", 
    "Student", "Grade", "Instrument", "Inst. Year", "Level", 
    "Room", "Lesson Duration", "Notes", "Parent Name", "Parent Phone", "Parent Email", "Teacher Email"
]

for col in expected_cols:
    if col not in df.columns:
        df[col] = ""

valid_df = df[df["Student"] != ""].copy() if not df.empty and "Student" in df.columns else pd.DataFrame()

# -----------------------------------------------------------------------------
# 2. STANDALONE METRIC CALCULATIONS
# -----------------------------------------------------------------------------
def calculate_enrollments(data):
    """
    Calculates enrollments by grouping (Student + Campus + Instrument).
    Automatically counts 30+30 split lessons as 1 enrollment.
    """
    if data.empty:
        return 0
    if "Instrument" in data.columns and "Campus" in data.columns:
        return data.groupby(["Student", "Campus", "Instrument"]).ngroups
    return len(data)

def calculate_unique_students(data):
    """Calculates unique students (students with multiple instruments count as 1)."""
    if data.empty or "Student" not in data.columns:
        return 0
    return data["Student"].nunique()

# -----------------------------------------------------------------------------
# 3. AUTHENTICATION & ROLE-BASED ACCESS (Sidebar)
# -----------------------------------------------------------------------------
st.sidebar.title("🔐 Portal Login")

user_role = st.sidebar.selectbox(
    "Select Role",
    ["Academy Coordinator", "School Coordinator", "Academy Teacher"]
)

user_email = st.sidebar.text_input("Enter School Email", value="").strip().lower()
st.sidebar.markdown("---")

# -----------------------------------------------------------------------------
# 4. TIER 1: ACADEMY COORDINATOR (Full Management Access)
# -----------------------------------------------------------------------------
if user_role == "Academy Coordinator":
    st.header("🏛️ Academy Coordinator Portal")

    # Executive Overview Dashboard
    st.subheader("📊 EXECUTIVE DASHBOARD")
    
    t1, t2, t3, t4 = st.columns(4)
    total_lessons = len(valid_df)
    total_teachers = valid_df["Teacher"].replace("", None).nunique() if not valid_df.empty else 0
    total_rooms = valid_df["Room"].replace("", None).nunique() if not valid_df.empty else 0
    total_unique_students = calculate_unique_students(valid_df)

    t1.metric("Total Lessons", total_lessons)
    t2.metric("Total Teachers", total_teachers)
    t3.metric("Total Rooms", total_rooms)
    t4.metric("Total Unique Students", total_unique_students)

    st.markdown("---")

    # Campus Breakdown Cards
    st.subheader("📍 Campus Enrollments & Unique Students Breakdown")
    c_alfragide, c_pde, c_restelo = st.columns(3)

    df_alfragide = valid_df[valid_df["Campus"] == "Alfragide"] if not valid_df.empty else pd.DataFrame()
    with c_alfragide:
        st.info("### 🏫 Alfragide")
        st.metric("Enrollments", calculate_enrollments(df_alfragide))
        st.metric("Unique Students", calculate_unique_students(df_alfragide))

    df_pde = valid_df[valid_df["Campus"] == "PdE"] if not valid_df.empty else pd.DataFrame()
    with c_pde:
        st.success("### 🏫 PdE")
        st.metric("Enrollments", calculate_enrollments(df_pde))
        st.metric("Unique Students", calculate_unique_students(df_pde))

    df_restelo = valid_df[valid_df["Campus"] == "Restelo"] if not valid_df.empty else pd.DataFrame()
    with c_restelo:
        st.warning("### 🏫 Restelo")
        st.metric("Enrollments", calculate_enrollments(df_restelo))
        st.metric("Unique Students", calculate_unique_students(df_restelo))

    st.markdown("---")

    sum1, sum2 = st.columns(2)
    sum1.metric("📌 TOTAL ENROLLMENTS (All Campuses)", calculate_enrollments(valid_df))
    sum2.metric("👤 TOTAL UNIQUE STUDENTS (All Campuses)", total_unique_students)

    st.markdown("---")

    # Management Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📅 General Schedule & Filters", 
        "📞 Parent Contact Directory", 
        "➕ Add New Booking / Record", 
        "✏️ Edit / Update Existing Records"
    ])

    # TAB 1: General Schedule View
    with tab1:
        st.subheader("Master Schedule Overview")
        if not df.empty:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                campus_list = ["All Campuses"] + sorted([c for c in df["Campus"].unique() if c]) if "Campus" in df.columns else ["All Campuses"]
                campus_filter = st.selectbox("Filter by Campus", campus_list)
            with col_f2:
                day_filter = st.selectbox("Filter by Weekday", ["All Days", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])

            filtered_df = df.copy()
            if campus_filter != "All Campuses" and "Campus" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["Campus"] == campus_filter]
            if day_filter != "All Days" and "Day" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["Day"] == day_filter]

            st.dataframe(filtered_df, use_container_width=True)

    # TAB 2: Parent Contacts
    with tab2:
        st.subheader("Parent & Guardian Directory")
        contact_cols = [c for c in ["Student", "Grade", "Campus", "Parent Name", "Parent Phone", "Parent Email"] if c in df.columns]
        if contact_cols:
            st.dataframe(df[contact_cols], use_container_width=True)

    # TAB 3: Add New Records
    with tab3:
        st.subheader("➕ Add New Schedule / Student Record")
        with st.form("add_record_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_campus = st.selectbox("Campus *", ["Alfragide", "Restelo", "PdE", "Other"])
                new_teacher = st.text_input("Teacher Name *")
                new_teacher_email = st.text_input("Teacher Email")
                new_student = st.text_input("Student Name *")
                new_grade = st.text_input("Grade (e.g., 3B, 5D)")

            with c2:
                new_day = st.selectbox("Day *", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
                new_start = st.text_input("Start Time (HH:MM)", value="14:00")
                new_end = st.text_input("End Time (HH:MM)", value="14:30")
                new_room = st.text_input("Room / Studio *", value="Music")
                new_duration = st.selectbox("Duration (min)", [30, 45, 60])

            with c3:
                new_instrument = st.text_input("Instrument", value="Piano")
                new_inst_year = st.text_input("Instrument Year", value="1st")
                new_notes = st.text_input("Notes (e.g. 30+30)", value="")
                new_parent_name = st.text_input("Parent / Guardian Name")
                new_parent_phone = st.text_input("Parent Phone")
                new_parent_email = st.text_input("Parent Email")

            submit_add = st.form_submit_button("💾 Save Record")

            if submit_add:
                if not new_student or not new_teacher or not new_room:
                    st.warning("Please fill in all required fields marked with *.")
                else:
                    new_row = pd.DataFrame([{
                        "Campus": new_campus, "Teacher": new_teacher, "Teacher Email": new_teacher_email,
                        "Day": new_day, "Start Time": new_start, "End Time": new_end,
                        "Student": new_student, "Grade": new_grade, "Instrument": new_instrument,
                        "Inst. Year": new_inst_year, "Level": "0", "Room": new_room,
                        "Lesson Duration": str(new_duration), "Notes": new_notes,
                        "Parent Name": new_parent_name, "Parent Phone": new_parent_phone, "Parent Email": new_parent_email
                    }])
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    try:
                        conn.update(worksheet="DATABASE", data=updated_df)
                        st.success(f"✅ Record for {new_student} added successfully!")
                        st.cache_data.clear()
                    except Exception as ex:
                        st.error(f"Failed to update data source: {ex}")

    # TAB 4: Edit Existing Records
    with tab4:
        st.subheader("✏️ Edit / Modify Existing Record")
        if not df.empty and "Student" in df.columns:
            student_list = [s for s in df["Student"].unique() if s]
            if student_list:
                selected_student = st.selectbox("Select Student to Edit", student_list)
                student_rows = df[df["Student"] == selected_student]
                if not student_rows.empty:
                    idx = student_rows.index[0]
                    row_data = df.loc[idx]

                    with st.form("edit_record_form"):
                        e1, e2 = st.columns(2)
                        with e1:
                            edit_campus = st.text_input("Campus", value=str(row_data.get("Campus", "")))
                            edit_teacher = st.text_input("Teacher", value=str(row_data.get("Teacher", "")))
                            edit_day = st.text_input("Day", value=str(row_data.get("Day", "")))
                            edit_start = st.text_input("Start Time", value=str(row_data.get("Start Time", "")))
                            edit_end = st.text_input("End Time", value=str(row_data.get("End Time", "")))
                            edit_room = st.text_input("Room", value=str(row_data.get("Room", "")))

                        with e2:
                            edit_instrument = st.text_input("Instrument", value=str(row_data.get("Instrument", "")))
                            edit_grade = st.text_input("Grade", value=str(row_data.get("Grade", "")))
                            edit_notes = st.text_input("Notes", value=str(row_data.get("Notes", "")))
                            edit_parent_name = st.text_input("Parent Name", value=str(row_data.get("Parent Name", "")))
                            edit_parent_phone = st.text_input("Parent Phone", value=str(row_data.get("Parent Phone", "")))
                            edit_parent_email = st.text_input("Parent Email", value=str(row_data.get("Parent Email", "")))

                        submit_edit = st.form_submit_button("🔄 Update Record")

                        if submit_edit:
                            df.at[idx, "Campus"] = edit_campus
                            df.at[idx, "Teacher"] = edit_teacher
                            df.at[idx, "Day"] = edit_day
                            df.at[idx, "Start Time"] = edit_start
                            df.at[idx, "End Time"] = edit_end
                            df.at[idx, "Room"] = edit_room
                            df.at[idx, "Instrument"] = edit_instrument
                            df.at[idx, "Grade"] = edit_grade
                            df.at[idx, "Notes"] = edit_notes
                            df.at[idx, "Parent Name"] = edit_parent_name
                            df.at[idx, "Parent Phone"] = edit_parent_phone
                            df.at[idx, "Parent Email"] = edit_parent_email

                            try:
                                conn.update(worksheet="DATABASE", data=df)
                                st.success(f"✅ Record for {selected_student} updated!")
                                st.cache_data.clear()
                            except Exception as ex:
                                st.error(f"Failed to update data source: {ex}")

# -----------------------------------------------------------------------------
# 5. TIER 2: SCHOOL COORDINATOR PORTAL
# -----------------------------------------------------------------------------
elif user_role == "School Coordinator":
    st.header("🏫 School Coordinator Portal")
    if not df.empty and "Campus" in df.columns:
        campus_options = sorted([c for c in df["Campus"].unique() if c])
        if campus_options:
            selected_campus = st.selectbox("Select Your Campus", campus_options)
            campus_df = df[df["Campus"] == selected_campus]

            st.subheader(f"General Schedule — {selected_campus} Campus")
            disp_cols = [c for c in ["Day", "Start Time", "End Time", "Room", "Student", "Grade", "Instrument", "Teacher"] if c in campus_df.columns]
            st.dataframe(campus_df[disp_cols], use_container_width=True)

# -----------------------------------------------------------------------------
# 6. TIER 3: ACADEMY TEACHER PORTAL
# -----------------------------------------------------------------------------
elif user_role == "Academy Teacher":
    st.header("👨‍🏫 Teacher Portal")

    if not user_email:
        st.info("Please enter your registered school email address in the sidebar to load your personalized schedule.")
    else:
        if not df.empty and "Teacher" in df.columns:
            teacher_df = df[
                (df["Teacher Email"].str.lower() == user_email) | 
                (df["Teacher"].str.lower().apply(lambda x: x.replace(" ", ".")) in user_email)
            ]

            if teacher_df.empty:
                st.warning(f"No records found matching email '{user_email}'. Please verify your login email or contact your Academy Coordinator.")
            else:
                teacher_name = teacher_df["Teacher"].iloc[0]
                teacher_campus = teacher_df["Campus"].iloc[0] if "Campus" in teacher_df.columns else "Main"

                st.success(f"Welcome back, **{teacher_name}**!")

                t_tab1, t_tab2, t_tab3 = st.tabs(["📅 My Personal Schedule", "🏫 My Campus Schedule", "📞 My Students' Parent Contacts"])

                with t_tab1:
                    st.subheader(f"Personal Timetable — {teacher_name}")
                    p_cols = [c for c in ["Day", "Start Time", "End Time", "Campus", "Room", "Student", "Grade", "Instrument"] if c in teacher_df.columns]
                    st.dataframe(teacher_df[p_cols], use_container_width=True)

                with t_tab2:
                    st.subheader(f"Campus Schedule — {teacher_campus}")
                    campus_df = df[df["Campus"] == teacher_campus]
                    c_cols = [c for c in ["Day", "Start Time", "End Time", "Room", "Student", "Instrument", "Teacher"] if c in campus_df.columns]
                    st.dataframe(campus_df[c_cols], use_container_width=True)

                with t_tab3:
                    st.subheader("Assigned Student Parent Contacts")
                    cont_cols = [c for c in ["Student", "Grade", "Instrument", "Parent Name", "Parent Phone", "Parent Email"] if c in teacher_df.columns]
                    st.dataframe(teacher_df[cont_cols], use_container_width=True)
