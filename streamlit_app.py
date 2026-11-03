import streamlit as st
import pandas as pd
import re
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
# 2. HELPER FUNCTIONS & CATEGORIZATION
# -----------------------------------------------------------------------------
def get_grade_category(grade_str):
    if not grade_str:
        return "Other"
    val = str(grade_str).upper().strip()
    if any(k in val for k in ["EARLY", "3Y", "4Y", "5Y"]):
        return "Early Learning"
    numbers = re.findall(r'\d+', val)
    if numbers:
        grade_num = int(numbers[0])
        if 1 <= grade_num <= 5:
            return "Junior School"
        elif 6 <= grade_num <= 12:
            return "Senior School"
    return "Other"

def calculate_enrollments(data):
    if data.empty:
        return 0
    if "Instrument" in data.columns and "Campus" in data.columns:
        return data.groupby(["Student", "Campus", "Instrument"]).ngroups
    return len(data)

def calculate_unique_students(data):
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
# 4. TIER 1: ACADEMY COORDINATOR PORTAL
# -----------------------------------------------------------------------------
if user_role == "Academy Coordinator":
    st.header("🏛️ Academy Coordinator Portal")

    # Executive Overview Dashboard
    st.subheader("📊 EXECUTIVE DASHBOARD")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Total Lessons", len(valid_df))
    t2.metric("Total Teachers", valid_df["Teacher"].replace("", None).nunique() if not valid_df.empty else 0)
    t3.metric("Total Rooms", valid_df["Room"].replace("", None).nunique() if not valid_df.empty else 0)
    t4.metric("Total Unique Students", calculate_unique_students(valid_df))

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
    sum2.metric("👤 TOTAL UNIQUE STUDENTS (All Campuses)", calculate_unique_students(valid_df))

    st.markdown("---")

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
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            with f_col1:
                campus_opts = ["All Campuses"] + sorted([c for c in df["Campus"].unique() if c])
                campus_filter = st.selectbox("Campus Filter:", campus_opts)
            with f_col2:
                teacher_opts = ["All Teachers"] + sorted([t for t in df["Teacher"].unique() if t])
                teacher_filter = st.selectbox("Teacher Filter:", teacher_opts)
            with f_col3:
                day_opts = ["All Days", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                day_filter = st.selectbox("Day Filter:", day_opts)
            with f_col4:
                grade_opts = ["All Grades", "Early Learning", "Junior School", "Senior School"]
                grade_filter = st.selectbox("Grade Filter:", grade_opts)

            filtered_df = df.copy()
            if campus_filter != "All Campuses":
                filtered_df = filtered_df[filtered_df["Campus"] == campus_filter]
            if teacher_filter != "All Teachers":
                filtered_df = filtered_df[filtered_df["Teacher"] == teacher_filter]
            if day_filter != "All Days":
                filtered_df = filtered_df[filtered_df["Day"] == day_filter]
            if grade_filter != "All Grades":
                filtered_df = filtered_df[filtered_df["Grade"].apply(get_grade_category) == grade_filter]

            if not filtered_df.empty:
                teachers_in_view = filtered_df["Teacher"].unique()
                for teacher in teachers_in_view:
                    if not teacher:
                        continue
                    st.markdown(f"### 👨‍🏫 {teacher}")
                    t_df = filtered_df[filtered_df["Teacher"] == teacher]
                    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                    
                    for day in days:
                        d_df = t_df[t_df["Day"] == day]
                        if not d_df.empty:
                            st.markdown(f"#### 📅 {day.upper()}")
                            d_df["Time"] = d_df["Start Time"] + " - " + d_df["End Time"]
                            disp_df = d_df[["Time", "Student", "Grade", "Instrument", "Inst. Year", "Level", "Room", "Campus"]].copy()
                            disp_df.columns = ["Time", "Student", "Class", "Instrument", "Inst. Year", "Level", "Room", "Campus"]
                            st.dataframe(disp_df, use_container_width=True, hide_index=True)
            else:
                st.info("No lessons found matching the selected filters.")
        else:
            st.info("No schedule data loaded.")

    # TAB 2: Parent Contacts
    with tab2:
        st.subheader("Parent & Guardian Directory")
        contact_cols = [c for c in ["Student", "Grade", "Campus", "Parent Name", "Parent Email", "Parent Phone"] if c in df.columns]
        if contact_cols:
            st.dataframe(df[contact_cols], use_container_width=True, hide_index=True)

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
                new_grade = st.text_input("Grade (e.g., 3B, 5D, 4y)")

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
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            for day in days:
                d_df = campus_df[campus_df["Day"] == day]
                if not d_df.empty:
                    st.markdown(f"### 📅 {day.upper()}")
                    d_df["Time"] = d_df["Start Time"] + " - " + d_df["End Time"]
                    disp_df = d_df[["Time", "Student", "Grade", "Instrument", "Room", "Teacher"]].copy()
                    disp_df.columns = ["Time", "Student", "Class", "Instrument", "Room", "Teacher"]
                    st.dataframe(disp_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# 6. TIER 3: ACADEMY TEACHER PORTAL (Cleaned Up Schedule View)
# -----------------------------------------------------------------------------
elif user_role == "Academy Teacher":
    st.header("👨‍🏫 Teacher Portal")

    if not user_email:
        st.info("Please enter your registered school email address in the sidebar to load your personalized schedule.")
    else:
        if not df.empty and "Teacher" in df.columns:
            def match_teacher(row, input_email):
                t_name = str(row.get("Teacher", "")).strip().lower()
                t_email = str(row.get("Teacher Email", "")).strip().lower()
                
                if t_email and t_email == input_email:
                    return True
                
                t_handle = t_name.replace(" ", ".")
                input_username = input_email.split("@")[0]
                
                if t_handle and (t_handle in input_username or input_username in t_handle):
                    return True
                return False

            teacher_df = df[df.apply(lambda r: match_teacher(r, user_email), axis=1)]

            if teacher_df.empty:
                st.warning(f"No records found matching email '{user_email}'. Please verify your email entry or contact your Academy Coordinator.")
            else:
                teacher_name = teacher_df["Teacher"].iloc[0]
                teacher_campus = teacher_df["Campus"].iloc[0] if "Campus" in teacher_df.columns else "Main"

                st.subheader(f"👨‍🏫 {teacher_name.upper()}")

                t_tab1, t_tab2, t_tab3 = st.tabs(["📅 My Personal Schedule", "🏫 My Campus Schedule", "📞 My Students' Parent Contacts"])

                # TAB 1: Clean Timetable (Removed Parent Email & Parent Phone to prevent duplication)
                with t_tab1:
                    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                    for day in days:
                        day_df = teacher_df[teacher_df["Day"] == day]
                        if not day_df.empty:
                            campuses = day_df["Campus"].unique()
                            for campus in campuses:
                                c_df = day_df[day_df["Campus"] == campus].copy()
                                
                                st.markdown(f"### 📘 {day.upper()} — {campus.upper()}")
                                
                                c_df["Time"] = c_df["Start Time"] + " - " + c_df["End Time"]
                                # Streamlined columns focusing purely on lesson details
                                disp_df = c_df[["Time", "Student", "Grade", "Instrument", "Room"]].copy()
                                disp_df.columns = ["Time", "Student", "Class", "Instrument", "Room"]
                                
                                st.dataframe(disp_df, use_container_width=True, hide_index=True)

                # TAB 2: Campus Overview Schedule
                with t_tab2:
                    st.subheader(f"General Schedule — {teacher_campus} Campus")
                    campus_df = df[df["Campus"] == teacher_campus]
                    for day in days:
                        d_df = campus_df[campus_df["Day"] == day]
                        if not d_df.empty:
                            st.markdown(f"#### 📅 {day.upper()}")
                            d_df["Time"] = d_df["Start Time"] + " - " + d_df["End Time"]
                            disp_df = d_df[["Time", "Student", "Grade", "Instrument", "Room", "Teacher"]].copy()
                            disp_df.columns = ["Time", "Student", "Class", "Instrument", "Room", "Teacher"]
                            st.dataframe(disp_df, use_container_width=True, hide_index=True)

                # TAB 3: Dedicated Parent Contact Directory
                with t_tab3:
                    st.subheader("Assigned Student Parent Contacts")
                    cont_df = teacher_df[["Student", "Grade", "Instrument", "Parent Name", "Parent Email", "Parent Phone"]].copy()
                    cont_df.columns = ["Student", "Class", "Instrument", "Parent Name", "Parent Email", "Parent Phone"]
                    st.dataframe(cont_df, use_container_width=True, hide_index=True)
