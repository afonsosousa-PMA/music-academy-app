import streamlit as st
import pandas as pd
import re
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Park Music Academy Management Portal",
    page_icon="🎵",
    layout="wide"
)

st.title("🎵 PARK MUSIC ACADEMY — MANAGEMENT PORTAL")

# -----------------------------------------------------------------------------
# 1. GESTÃO DE SESSÃO E AUTO-LOGOUT (SEGURANÇA RGPD)
# -----------------------------------------------------------------------------
INACTIVITY_TIMEOUT = 900 

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "last_activity" not in st.session_state:
    st.session_state.last_activity = time.time()

if st.session_state.authenticated:
    if time.time() - st.session_state.last_activity > INACTIVITY_TIMEOUT:
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.user_email = ""
        st.warning("⚠️ Sessão expirada por inatividade. Por favor, faça login novamente.")
    else:
        st.session_state.last_activity = time.time()

# -----------------------------------------------------------------------------
# 2. CAMADA DE DADOS
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
        st.error(f"Erro ao carregar a base de dados: {e}")
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
# 3. DICIONÁRIOS DE REGRA (SALAS, INSTRUMENTOS E EMAILS DOS PROFESSORES)
# -----------------------------------------------------------------------------
ROOM_OPTIONS = {
    "Alfragide": [
        "Studio 2", "Studio 3", "Studio 4", "Studio 5", "Studio 6", 
        "Studio 7", "Studio 8", "Studio 9", "2.01", "2.02", "2.03", "2.16", "3.13", "M1"
    ],
    "PdE": ["Studio", "Music Room", "Support"],
    "Restelo": ["Library", "Music Room", "Studio"],
    "Other": ["Studio 1", "Room A", "Room B"]
}

INSTRUMENT_OPTIONS = {
    "Restelo": ["Drums", "Guitar", "Piano", "Music Initiation", "Music Atelier"],
    "PdE": ["Guitar", "Piano", "Violin", "Music Initiation", "Music Atelier"]
}

# Mapa de emails de professores existente
teacher_email_map = {}
if not df.empty and "Teacher" in df.columns and "Teacher Email" in df.columns:
    for _, r in df.iterrows():
        t_name = r.get("Teacher", "").strip()
        t_email = r.get("Teacher Email", "").strip()
        if t_name and t_email and t_name not in teacher_email_map:
            teacher_email_map[t_name] = t_email

# -----------------------------------------------------------------------------
# 4. AUXILIARES, MÉTRICAS E FORMATADORES AUTOMÁTICOS
# -----------------------------------------------------------------------------
def calculate_end_time(start_time_str, duration_minutes):
    try:
        start_dt = datetime.strptime(start_time_str.strip(), "%H:%M")
        end_dt = start_dt + timedelta(minutes=int(duration_minutes))
        return end_dt.strftime("%H:%M")
    except Exception:
        return ""

def format_time_range(row):
    start = str(row.get("Start Time", "")).strip()
    end = str(row.get("End Time", "")).strip()
    duration = row.get("Lesson Duration", "30")
    
    if start and not end and duration:
        end = calculate_end_time(start, duration)
        
    if start and end:
        return f"{start} - {end}"
    elif start:
        return start
    return ""

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

def check_room_conflict(data, campus, day, room, start_time, exclude_idx=None):
    if data.empty:
        return False, ""
    
    query = data[
        (data["Campus"].str.lower() == campus.lower()) &
        (data["Day"].str.lower() == day.lower()) &
        (data["Room"].str.lower() == room.lower()) &
        (data["Start Time"] == start_time)
    ]
    
    if exclude_idx is not None and not query.empty:
        query = query[query.index != exclude_idx]
        
    if not query.empty:
        row = query.iloc[0]
        teacher = row.get("Teacher", "Outro Professor")
        student = row.get("Student", "Outro Aluno")
        return True, f"A sala '{room}' no campus '{campus}' ({day} às {start_time}) já está ocupada por {teacher} com o aluno {student}."
    
    return False, ""

# -----------------------------------------------------------------------------
# 5. BARRA LATERAL: LOGIN COM PIN & DEV MODE
# -----------------------------------------------------------------------------
st.sidebar.title("🔐 Portal Security Login")

dev_mode = st.sidebar.checkbox("🛠️ Developer / Easy Access Mode", value=True)

if dev_mode:
    st.sidebar.success("🔓 Dev Mode Ativo: Acesso direto como Coordenador da Academia")
    st.session_state.authenticated = True
    st.session_state.user_role = "Academy Coordinator"
    user_role = "Academy Coordinator"
    user_email = "coordinator@park-is.com"
else:
    if not st.session_state.authenticated:
        st.sidebar.subheader("Introduza as suas credenciais")
        selected_role = st.sidebar.selectbox(
            "Selecione o Perfil",
            ["Academy Coordinator", "School Coordinator", "Academy Teacher"]
        )
        input_email = st.sidebar.text_input("Email da Escola", value="").strip().lower()
        input_pin = st.sidebar.text_input("Código / PIN de Acesso", type="password")

        if st.sidebar.button("🔑 Entrar no Portal"):
            valid_login = False
            if selected_role == "Academy Coordinator" and input_pin == "9999":
                valid_login = True
            elif selected_role == "School Coordinator" and input_pin == "1234":
                valid_login = True
            elif selected_role == "Academy Teacher" and input_pin == "2026" and input_email != "":
                valid_login = True
            
            if valid_login:
                st.session_state.authenticated = True
                st.session_state.user_role = selected_role
                st.session_state.user_email = input_email
                st.session_state.last_activity = time.time()
                st.sidebar.success("Login efetuado com sucesso!")
                st.rerun()
            else:
                st.sidebar.error("⚠️ PIN ou Email incorreto. Tente novamente.")
    else:
        st.sidebar.info(f"Sessão ativa: **{st.session_state.user_role}**")
        if st.session_state.user_email:
            st.sidebar.caption(f"Email: {st.session_state.user_email}")
        if st.sidebar.button("🔒 Sair (Logout)"):
            st.session_state.authenticated = False
            st.session_state.user_role = None
            st.session_state.user_email = ""
            st.rerun()

user_role = st.session_state.user_role
user_email = st.session_state.user_email

# -----------------------------------------------------------------------------
# 6. TIER 1: ACADEMY COORDINATOR PORTAL
# -----------------------------------------------------------------------------
if st.session_state.authenticated and user_role == "Academy Coordinator":
    st.header("🏛️ Academy Coordinator Portal")

    # Executive Dashboard
    st.subheader("📊 EXECUTIVE DASHBOARD")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Total Lessons", len(valid_df))
    t2.metric("Total Teachers", valid_df["Teacher"].replace("", None).nunique() if not valid_df.empty else 0)
    t3.metric("Total Rooms", valid_df["Room"].replace("", None).nunique() if not valid_df.empty else 0)
    t4.metric("Total Unique Students", calculate_unique_students(valid_df))

    st.markdown("---")

    # Campus Breakdown
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

    # NOVO MENU ORGANIZADO CONFORME PEDIDO
    tab1, tab2, tab3, tab4 = st.tabs([
        "📅 General Schedule", 
        "📋 Student Profile",
        "➕ Add New Record",
        "✏️ Edit / Delete Record"
    ])

    # TAB 1: GENERAL SCHEDULE (VISÃO SEMANAL LADO A LADO 2ª A 6ª FEIRA ESTILO EXCEL)
    with tab1:
        st.subheader("Master Schedule Overview (Weekly Grid View)")
        if not df.empty:
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                campus_opts = ["All Campuses"] + sorted([c for c in df["Campus"].unique() if c])
                campus_filter = st.selectbox("Campus Filter:", campus_opts)
            with f_col2:
                teacher_opts = ["All Teachers"] + sorted([t for t in df["Teacher"].unique() if t])
                teacher_filter = st.selectbox("Teacher Filter:", teacher_opts)
            with f_col3:
                grade_opts = ["All Grades", "Early Learning", "Junior School", "Senior School"]
                grade_filter = st.selectbox("Grade Filter:", grade_opts)

            filtered_df = df.copy()
            if campus_filter != "All Campuses":
                filtered_df = filtered_df[filtered_df["Campus"] == campus_filter]
            if teacher_filter != "All Teachers":
                filtered_df = filtered_df[filtered_df["Teacher"] == teacher_filter]
            if grade_filter != "All Grades":
                filtered_df = filtered_df[filtered_df["Grade"].apply(get_grade_category) == grade_filter]

            if not filtered_df.empty:
                csv_data = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Schedule to CSV",
                    data=csv_data,
                    file_name="master_schedule_export.csv",
                    mime="text/csv"
                )

                teachers_in_view = filtered_df["Teacher"].unique()
                for teacher in teachers_in_view:
                    if not teacher:
                        continue
                    st.markdown(f"## 👨‍🏫 {teacher.upper()}")
                    t_df = filtered_df[filtered_df["Teacher"] == teacher]
                    
                    # Layout em colunas de 2ª a 6ª Feira lado a lado
                    col_mon, col_tue, col_wed, col_thu, col_fri = st.columns(5)
                    
                    days_map = [
                        ("Monday", col_mon), ("Tuesday", col_tue), 
                        ("Wednesday", col_wed), ("Thursday", col_thu), ("Friday", col_fri)
                    ]
                    
                    for day_name, col_obj in days_map:
                        with col_obj:
                            st.markdown(f"##### 📅 {day_name.upper()}")
                            d_df = t_df[t_df["Day"] == day_name].copy()
                            if not d_df.empty:
                                d_df["Time"] = d_df.apply(format_time_range, axis=1)
                                disp_df = d_df[["Time", "Student", "Grade", "Instrument", "Room"]].copy()
                                disp_df.columns = ["Time", "Student", "Class", "Inst.", "Room"]
                                st.dataframe(disp_df, use_container_width=True, hide_index=True)
                            else:
                                st.caption("No lessons")
                    st.markdown("---")
            else:
                st.info("No lessons found matching the selected filters.")
        else:
            st.info("No schedule data loaded.")

    # TAB 2: STUDENT PROFILE (FICHA COMPLETA DO ALUNO + CONTACTOS DOS PAIS)
    with tab2:
        st.subheader("📋 Student Profile & Contact Details")
        if not df.empty and "Student" in df.columns:
            all_students = sorted([s for s in df["Student"].unique() if s])
            selected_student_profile = st.selectbox("🔍 Select Student to View Profile:", all_students)

            if selected_student_profile:
                st_data = df[df["Student"] == selected_student_profile]
                first_row = st_data.iloc[0]

                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    st.info(f"### 👤 {selected_student_profile}")
                    st.markdown(f"**Campus:** {first_row.get('Campus', '-')}")
                    st.markdown(f"**Class / Grade:** {first_row.get('Grade', '-')}")
                    st.markdown(f"**Category:** {get_grade_category(first_row.get('Grade', ''))}")

                with p_col2:
                    st.success("### 👪 Parent & Guardian Details")
                    st.markdown(f"**Parent Name:** {first_row.get('Parent Name', '-')}")
                    st.markdown(f"**Parent Email:** {first_row.get('Parent Email', '-')}")
                    st.markdown(f"**Parent Phone:** {first_row.get('Parent Phone', '-')}")

                st.markdown("---")
                st.subheader(f"🎵 Enrolled Lessons ({len(st_data)})")
                
                st_data_copy = st_data.copy()
                st_data_copy["Time"] = st_data_copy.apply(format_time_range, axis=1)
                profile_disp = st_data_copy[["Day", "Time", "Instrument", "Inst. Year", "Teacher", "Room", "Campus", "Notes"]].copy()
                profile_disp.columns = ["Day", "Time", "Instrument", "Year", "Teacher", "Room", "Campus", "Notes"]
                st.dataframe(profile_disp, use_container_width=True, hide_index=True)

    # TAB 3: ADD NEW RECORD (DURAÇÕES REGRADAS E EMAIL DO PROFESSOR DEDICADO)
    with tab3:
        st.subheader("➕ Add New Schedule / Student Record")
        
        existing_teachers = sorted([t for t in df["Teacher"].unique() if t]) if not df.empty else []

        sc1, sc2 = st.columns(2)
        with sc1:
            new_campus = st.selectbox("Campus *", ["Alfragide", "PdE", "Restelo", "Other"], key="add_campus_select")
        with sc2:
            new_teacher = st.selectbox("Teacher Name *", existing_teachers if existing_teachers else ["Select Teacher"], key="add_teacher_select")

        # Gestão de emails de professores (Permite introduzir novo se não existir)
        auto_teacher_email = teacher_email_map.get(new_teacher, f"{new_teacher.lower().replace(' ', '.')}@park-is.com" if new_teacher else "")

        available_rooms = ROOM_OPTIONS.get(new_campus, ROOM_OPTIONS["Other"])
        
        if new_campus in INSTRUMENT_OPTIONS:
            available_instruments = INSTRUMENT_OPTIONS[new_campus]
        else:
            base_insts = sorted([i for i in df["Instrument"].unique() if i and "therapy" not in i.lower()]) if not df.empty else ["Piano", "Guitar", "Violin", "Drums", "Voice"]
            available_instruments = [i for i in base_insts if "therapy" not in i.lower()]

        with st.form("add_record_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_teacher_email = st.text_input("Teacher Email", value=auto_teacher_email)
                new_student = st.text_input("Student Name *")
                new_grade = st.text_input("Grade (e.g., 3B, 5D, 4y)")

            with c2:
                new_day = st.selectbox("Day *", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
                new_start = st.text_input("Start Time (HH:MM) *", value="14:00")
                new_room = st.selectbox("Room / Studio *", available_rooms)

            with c3:
                new_instrument = st.selectbox("Instrument *", available_instruments)
                
                # Regras Automáticas de Duração de Aula
                if new_instrument in ["Music Initiation", "Music Atelier"]:
                    duration_options = [45]
                elif new_campus in ["PdE", "Restelo"]:
                    duration_options = [30]
                else:
                    duration_options = [30, 45, 60]

                new_duration = st.selectbox("Duration (min) *", duration_options)
                new_inst_year = st.text_input("Instrument Year", value="1st")
                new_notes = st.text_input("Notes (e.g. 30+30)", value="")
                new_parent_name = st.text_input("Parent / Guardian Name")
                new_parent_phone = st.text_input("Parent Phone")
                new_parent_email = st.text_input("Parent Email")

            submit_add = st.form_submit_button("💾 Save Record")

            if submit_add:
                if not new_student or not new_teacher or not new_room or not new_start:
                    st.warning("Please fill in all required fields marked with *.")
                else:
                    computed_end_time = calculate_end_time(new_start, new_duration)
                    
                    has_conflict, msg = check_room_conflict(df, new_campus, new_day, new_room, new_start)
                    if has_conflict:
                        st.error(f"⛔ AGENDAMENTO BLOQUEADO: {msg}")
                    else:
                        new_row = pd.DataFrame([{
                            "Campus": new_campus, "Teacher": new_teacher, "Teacher Email": new_teacher_email,
                            "Day": new_day, "Start Time": new_start, "End Time": computed_end_time,
                            "Student": new_student, "Grade": new_grade, "Instrument": new_instrument,
                            "Inst. Year": new_inst_year, "Level": "0", "Room": new_room,
                            "Lesson Duration": str(new_duration), "Notes": new_notes,
                            "Parent Name": new_parent_name, "Parent Phone": new_parent_phone, "Parent Email": new_parent_email
                        }])
                        updated_df = pd.concat([df, new_row], ignore_index=True)
                        try:
                            conn.update(worksheet="DATABASE", data=updated_df)
                            st.success(f"✅ Record for {new_student} added successfully! (End Time: {computed_end_time})")
                            st.cache_data.clear()
                        except Exception as ex:
                            st.error(f"Failed to update data source: {ex}")

    # TAB 4: EDIT / DELETE RECORD (UNIFICADO E COMPACTO)
    with tab4:
        st.subheader("✏️ Edit or 🗑️ Delete Existing Record")
        if not df.empty and "Student" in df.columns:
            df["Booking_Label"] = df["Student"] + " | " + df["Instrument"] + " | " + df["Campus"] + " | " + df["Day"] + " (" + df["Start Time"] + ")"
            booking_opts = df["Booking_Label"].tolist()
            
            selected_booking = st.selectbox("Selecione a Aula para Editar ou Eliminar:", booking_opts)
            
            if selected_booking:
                idx = df[df["Booking_Label"] == selected_booking].index[0]
                row_data = df.loc[idx]

                st.markdown("---")
                action_col1, action_col2 = st.columns(2)
                
                with action_col1:
                    st.markdown("#### ✏️ Edit Details")
                    with st.form("edit_record_form"):
                        existing_teachers = sorted([t for t in df["Teacher"].unique() if t])
                        
                        edit_campus = st.selectbox("Campus", ["Alfragide", "PdE", "Restelo", "Other"], index=["Alfragide", "PdE", "Restelo", "Other"].index(row_data.get("Campus", "Alfragide")) if row_data.get("Campus") in ["Alfragide", "PdE", "Restelo", "Other"] else 0)
                        edit_teacher = st.selectbox("Teacher", existing_teachers, index=existing_teachers.index(row_data.get("Teacher")) if row_data.get("Teacher") in existing_teachers else 0)
                        edit_teacher_email = st.text_input("Teacher Email", value=str(row_data.get("Teacher Email", teacher_email_map.get(row_data.get("Teacher"), ""))))
                        edit_day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], index=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"].index(row_data.get("Day", "Monday")) if row_data.get("Day") in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"] else 0)
                        edit_start = st.text_input("Start Time (HH:MM)", value=str(row_data.get("Start Time", "")))
                        
                        current_rooms = ROOM_OPTIONS.get(edit_campus, ROOM_OPTIONS["Other"])
                        edit_room = st.selectbox("Room", current_rooms, index=current_rooms.index(row_data.get("Room")) if row_data.get("Room") in current_rooms else 0)

                        if edit_campus in INSTRUMENT_OPTIONS:
                            edit_inst_opts = INSTRUMENT_OPTIONS[edit_campus]
                        else:
                            edit_inst_opts = sorted([i for i in df["Instrument"].unique() if i and "therapy" not in i.lower()])
                        
                        current_inst = row_data.get("Instrument", "")
                        edit_instrument = st.selectbox("Instrument", edit_inst_opts, index=edit_inst_opts.index(current_inst) if current_inst in edit_inst_opts else 0)
                        
                        if edit_instrument in ["Music Initiation", "Music Atelier"]:
                            edit_dur_opts = [45]
                        elif edit_campus in ["PdE", "Restelo"]:
                            edit_dur_opts = [30]
                        else:
                            edit_dur_opts = [30, 45, 60]

                        edit_duration = st.selectbox("Duration (min)", edit_dur_opts)
                        edit_grade = st.text_input("Grade", value=str(row_data.get("Grade", "")))
                        edit_notes = st.text_input("Notes", value=str(row_data.get("Notes", "")))
                        edit_parent_name = st.text_input("Parent Name", value=str(row_data.get("Parent Name", "")))
                        edit_parent_phone = st.text_input("Parent Phone", value=str(row_data.get("Parent Phone", "")))
                        edit_parent_email = st.text_input("Parent Email", value=str(row_data.get("Parent Email", "")))

                        submit_edit = st.form_submit_button("🔄 Save Changes")

                        if submit_edit:
                            has_conflict, msg = check_room_conflict(df, edit_campus, edit_day, edit_room, edit_start, exclude_idx=idx)
                            if has_conflict:
                                st.error(f"⛔ ALTERAÇÃO BLOQUEADA: {msg}")
                            else:
                                computed_end = calculate_end_time(edit_start, edit_duration)
                                df.at[idx, "Campus"] = edit_campus
                                df.at[idx, "Teacher"] = edit_teacher
                                df.at[idx, "Teacher Email"] = edit_teacher_email
                                df.at[idx, "Day"] = edit_day
                                df.at[idx, "Start Time"] = edit_start
                                df.at[idx, "End Time"] = computed_end
                                df.at[idx, "Lesson Duration"] = str(edit_duration)
                                df.at[idx, "Room"] = edit_room
                                df.at[idx, "Instrument"] = edit_instrument
                                df.at[idx, "Grade"] = edit_grade
                                df.at[idx, "Notes"] = edit_notes
                                df.at[idx, "Parent Name"] = edit_parent_name
                                df.at[idx, "Parent Phone"] = edit_parent_phone
                                df.at[idx, "Parent Email"] = edit_parent_email

                                try:
                                    conn.update(worksheet="DATABASE", data=df.drop(columns=["Booking_Label"], errors="ignore"))
                                    st.success(f"✅ Record for {row_data.get('Student')} updated!")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"Failed to update data source: {ex}")

                with action_col2:
                    st.markdown("#### 🗑️ Delete Booking")
                    st.warning("⚠️ Esta ação irá apagar a aula permanentemente.")
                    if st.button("🔴 Delete This Booking"):
                        updated_df = df.drop(idx).drop(columns=["Booking_Label"], errors="ignore")
                        try:
                            conn.update(worksheet="DATABASE", data=updated_df)
                            st.success("✅ Aula eliminada com sucesso!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Falha ao eliminar a aula: {ex}")

# -----------------------------------------------------------------------------
# 7. TIER 2: SCHOOL COORDINATOR PORTAL
# -----------------------------------------------------------------------------
elif st.session_state.authenticated and user_role == "School Coordinator":
    st.header("🏫 School Coordinator Portal")
    if not df.empty and "Campus" in df.columns:
        campus_options = sorted([c for c in df["Campus"].unique() if c])
        if campus_options:
            selected_campus = st.selectbox("Select Your Campus", campus_options)
            campus_df = df[df["Campus"] == selected_campus]

            st.subheader(f"General Schedule — {selected_campus} Campus")
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            for day in days:
                d_df = campus_df[campus_df["Day"] == day].copy()
                if not d_df.empty:
                    st.markdown(f"### 📅 {day.upper()}")
                    d_df["Time"] = d_df.apply(format_time_range, axis=1)
                    disp_df = d_df[["Time", "Student", "Grade", "Instrument", "Room", "Teacher"]].copy()
                    disp_df.columns = ["Time", "Student", "Class", "Instrument", "Room", "Teacher"]
                    st.dataframe(disp_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# 8. TIER 3: ACADEMY TEACHER PORTAL
# -----------------------------------------------------------------------------
elif st.session_state.authenticated and user_role == "Academy Teacher":
    st.header("👨‍🏫 Teacher Portal")

    if not user_email:
        st.info("Por favor, introduza o seu email institucional na barra lateral para carregar o seu horário.")
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
                st.warning(f"Nenhum registo encontrado para o email '{user_email}'. Verifique o seu email ou contacte a coordenação.")
            else:
                teacher_name = teacher_df["Teacher"].iloc[0]
                teacher_campus = teacher_df["Campus"].iloc[0] if "Campus" in teacher_df.columns else "Main"

                st.subheader(f"👨‍🏫 {teacher_name.upper()}")

                t_tab1, t_tab2, t_tab3 = st.tabs(["📅 My Personal Schedule", "🏫 My Campus Schedule", "📞 My Students' Parent Contacts"])

                with t_tab1:
                    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                    for day in days:
                        day_df = teacher_df[teacher_df["Day"] == day]
                        if not day_df.empty:
                            campuses = day_df["Campus"].unique()
                            for campus in campuses:
                                c_df = day_df[day_df["Campus"] == campus].copy()
                                
                                st.markdown(f"### 📘 {day.upper()} — {campus.upper()}")
                                
                                c_df["Time"] = c_df.apply(format_time_range, axis=1)
                                disp_df = c_df[["Time", "Student", "Grade", "Instrument", "Room"]].copy()
                                disp_df.columns = ["Time", "Student", "Class", "Instrument", "Room"]
                                
                                st.dataframe(disp_df, use_container_width=True, hide_index=True)

                with t_tab2:
                    st.subheader(f"General Schedule — {teacher_campus} Campus")
                    campus_df = df[df["Campus"] == teacher_campus]
                    for day in days:
                        d_df = campus_df[campus_df["Day"] == day].copy()
                        if not d_df.empty:
                            st.markdown(f"#### 📅 {day.upper()}")
                            d_df["Time"] = d_df.apply(format_time_range, axis=1)
                            disp_df = d_df[["Time", "Student", "Grade", "Instrument", "Room", "Teacher"]].copy()
                            disp_df.columns = ["Time", "Student", "Class", "Instrument", "Room", "Teacher"]
                            st.dataframe(disp_df, use_container_width=True, hide_index=True)

                with t_tab3:
                    st.subheader("Assigned Student Parent Contacts")
                    cont_df = teacher_df[["Student", "Grade", "Instrument", "Parent Name", "Parent Email", "Parent Phone"]].copy()
                    cont_df.columns = ["Student", "Class", "Instrument", "Parent Name", "Parent Email", "Parent Phone"]
                    st.dataframe(cont_df, use_container_width=True, hide_index=True)
else:
    st.info("👈 Por favor, utilize o painel de Login na barra lateral para aceder à aplicação.")
