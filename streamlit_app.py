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
# 2. CAMADA DE DADOS (COM CARREGAMENTO DE Apenas LEITURA PROTEGIDO)
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
    "Room", "Lesson Duration", "Notes", "Parent Name", "Parent Phone", "Parent Email", 
    "Teacher Email", "Teacher Personal Email", "Teacher Phone", "Teacher Taught Instruments"
]

for col in expected_cols:
    if col not in df.columns:
        df[col] = ""

valid_df = df[df["Student"] != ""].copy() if not df.empty and "Student" in df.columns else pd.DataFrame()

# -----------------------------------------------------------------------------
# 3. DICIONÁRIOS DE REGRA (SALAS, INSTRUMENTOS E DADOS DOS PROFESSORES)
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

# Dicionários de professores mantidos em memória durante a sessão
if "teacher_details_map" not in st.session_state:
    st.session_state.teacher_details_map = {}

# Povoar mapa inicial com os dados existentes na folha de cálculo
if not df.empty and "Teacher" in df.columns:
    for _, r in df.iterrows():
        t_name = r.get("Teacher", "").strip()
        if t_name and t_name not in st.session_state.teacher_details_map:
            st.session_state.teacher_details_map[t_name] = {
                "school_email": r.get("Teacher Email", ""),
                "personal_email": r.get("Teacher Personal Email", ""),
                "phone": r.get("Teacher Phone", ""),
                "instruments": r.get("Teacher Taught Instruments", r.get("Instrument", ""))
            }

# Modo de Proteção: Ativar para impedir escrita na folha de cálculo
READ_ONLY_MODE = st.sidebar.checkbox("🔒 Read-Only Mode (Protege o Google Sheets)", value=True)

if READ_ONLY_MODE:
    st.sidebar.info("🛡️ MODO DE PROTEÇÃO ATIVO: As alterações feitas na app não alteram o ficheiro Google Sheets original.")

# -----------------------------------------------------------------------------
# 4. AUXILIARES E FORMATADORES
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
    st.sidebar.success("🔓 Dev Mode Ativo: Coordenador da Academia")
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
# 6. PORTAL DO COORDENADOR DA ACADEMIA
# -----------------------------------------------------------------------------
if st.session_state.authenticated and user_role == "Academy Coordinator":
    st.header("🏛️ Academy Coordinator Portal")

    # Dashboard Executivo
    st.subheader("📊 EXECUTIVE DASHBOARD")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Total Lessons", len(valid_df))
    t2.metric("Total Teachers", valid_df["Teacher"].replace("", None).nunique() if not valid_df.empty else 0)
    t3.metric("Total Rooms", valid_df["Room"].replace("", None).nunique() if not valid_df.empty else 0)
    t4.metric("Total Unique Students", calculate_unique_students(valid_df))

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs([
        "📅 General Schedules", 
        "📋 Student Profile",
        "👨‍🏫 Teacher Profile"
    ])

    # -------------------------------------------------------------------------
    # TAB 1: GENERAL SCHEDULES
    # -------------------------------------------------------------------------
    with tab1:
        st.subheader("Master Schedule Overview (Weekly View)")
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
                st.download_button(
                    label="📥 Export Schedule to CSV",
                    data=filtered_df.to_csv(index=False).encode('utf-8'),
                    file_name="master_schedule_export.csv",
                    mime="text/csv"
                )

                days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                for day_name in days_order:
                    day_data = filtered_df[filtered_df["Day"] == day_name]
                    if not day_data.empty:
                        st.markdown(f"# 📅 {day_name.upper()}")
                        teachers_in_day = day_data["Teacher"].unique()
                        
                        for teacher in teachers_in_day:
                            if not teacher:
                                continue
                            
                            t_day_df = day_data[day_data["Teacher"] == teacher].copy()
                            st.markdown(f"### 👨‍🏫 {teacher}")
                            
                            t_day_df["Time"] = t_day_df.apply(format_time_range, axis=1)
                            disp_df = t_day_df[["Time", "Student", "Grade", "Instrument", "Inst. Year", "Level", "Room", "Campus"]].copy()
                            disp_df.columns = ["Time", "Student", "Class", "Instrument", "Inst. Year", "Level", "Room", "Campus"]
                            
                            st.dataframe(
                                disp_df, 
                                use_container_width=True, 
                                hide_index=True,
                                column_config={
                                    "Time": st.column_config.TextColumn("Time", width="medium"),
                                    "Student": st.column_config.TextColumn("Student", width="large"),
                                    "Class": st.column_config.TextColumn("Class", width="small"),
                                    "Instrument": st.column_config.TextColumn("Instrument", width="medium"),
                                    "Inst. Year": st.column_config.TextColumn("Inst. Year", width="small"),
                                    "Level": st.column_config.TextColumn("Level", width="small"),
                                    "Room": st.column_config.TextColumn("Room", width="small"),
                                    "Campus": st.column_config.TextColumn("Campus", width="medium"),
                                }
                            )
                        st.markdown("---")
            else:
                st.info("No lessons found matching the selected filters.")

    # -------------------------------------------------------------------------
    # TAB 2: STUDENT PROFILE
    # -------------------------------------------------------------------------
    with tab2:
        st.subheader("📋 Student Profile & Academic Details")

        with st.expander("➕ Add New Student / Lesson Booking"):
            existing_teachers = sorted([t for t in df["Teacher"].unique() if t]) if not df.empty else []
            
            add_c1, add_c2 = st.columns(2)
            with add_c1:
                ins_campus = st.selectbox("Campus *", ["Alfragide", "PdE", "Restelo", "Other"], key="add_st_campus")
            with add_c2:
                ins_teacher = st.selectbox("Teacher *", existing_teachers if existing_teachers else ["Select"], key="add_st_teacher")

            t_info = st.session_state.teacher_details_map.get(ins_teacher, {})
            auto_t_email = t_info.get("school_email", f"{ins_teacher.lower().replace(' ', '.')}@park-is.com" if ins_teacher else "")
            avail_rooms = ROOM_OPTIONS.get(ins_campus, ROOM_OPTIONS["Other"])
            
            if ins_campus in INSTRUMENT_OPTIONS:
                avail_insts = INSTRUMENT_OPTIONS[ins_campus]
            else:
                avail_insts = sorted([i for i in df["Instrument"].unique() if i and "therapy" not in i.lower()])

            with st.form("form_add_student_top"):
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    ins_teacher_email = st.text_input("Teacher Email", value=auto_t_email)
                    ins_student = st.text_input("Student Name *")
                    ins_grade = st.text_input("Grade (e.g. 3B, 5D)")
                with fc2:
                    ins_day = st.selectbox("Day *", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
                    ins_start = st.text_input("Start Time (HH:MM) *", value="14:00")
                    ins_room = st.selectbox("Room *", avail_rooms)
                with fc3:
                    ins_inst = st.selectbox("Instrument *", avail_insts)
                    dur_opts = [45] if ins_inst in ["Music Initiation", "Music Atelier"] else ([30] if ins_campus in ["PdE", "Restelo"] else [30, 45, 60])
                    ins_dur = st.selectbox("Duration (min) *", dur_opts)
                    ins_inst_year = st.text_input("Instrument Year", value="1st")
                    ins_p_name = st.text_input("Parent Name")
                    ins_p_phone = st.text_input("Parent Phone")
                    ins_p_email = st.text_input("Parent Email")

                if st.form_submit_button("💾 Save New Student / Booking"):
                    if not ins_student or not ins_teacher or not ins_start:
                        st.warning("Preencha todos os campos obrigatórios (*).")
                    else:
                        has_conf, conf_msg = check_room_conflict(df, ins_campus, ins_day, ins_room, ins_start)
                        if has_conf:
                            st.error(f"⛔ CONFLITO: {conf_msg}")
                        else:
                            c_end = calculate_end_time(ins_start, ins_dur)
                            new_r = pd.DataFrame([{
                                "Campus": ins_campus, "Teacher": ins_teacher, "Teacher Email": ins_teacher_email,
                                "Day": ins_day, "Start Time": ins_start, "End Time": c_end,
                                "Student": ins_student, "Grade": ins_grade, "Instrument": ins_inst,
                                "Inst. Year": ins_inst_year, "Level": "0", "Room": ins_room,
                                "Lesson Duration": str(ins_dur), "Notes": "",
                                "Parent Name": ins_p_name, "Parent Phone": ins_p_phone, "Parent Email": ins_p_email
                            }])
                            if not READ_ONLY_MODE:
                                try:
                                    conn.update(worksheet="DATABASE", data=pd.concat([df, new_r], ignore_index=True))
                                    st.success(f"✅ Aluno {ins_student} adicionado ao Google Sheets!")
                                except Exception as ex:
                                    st.error(f"Erro ao salvar no Google Sheets: {ex}")
                            else:
                                st.success(f"✅ Aluno {ins_student} registado na app (Modo de Proteção Ativo).")

        st.markdown("---")

        if not df.empty and "Student" in df.columns:
            all_students = sorted([s for s in df["Student"].unique() if s])
            
            s_select_col, btn_action_col = st.columns([3, 1])
            with s_select_col:
                selected_student_profile = st.selectbox("🔍 Select Student to View Profile:", all_students)

            with btn_action_col:
                st.write("")
                btn_edit_col, btn_del_col = st.columns(2)
                with btn_edit_col:
                    toggle_edit = st.button("✏️ Edit", use_container_width=True)
                with btn_del_col:
                    toggle_delete = st.button("🗑️ Delete", use_container_width=True)

            if selected_student_profile:
                st_data = df[df["Student"] == selected_student_profile]
                first_row = st_data.iloc[0]

                if toggle_edit:
                    st.info(f"✏️ Editing details for {selected_student_profile}")
                    with st.form("form_inline_edit_student"):
                        e1, e2 = st.columns(2)
                        with e1:
                            e_grade = st.text_input("Class / Grade", value=str(first_row.get("Grade", "")))
                            e_p_name = st.text_input("Parent Name", value=str(first_row.get("Parent Name", "")))
                        with e2:
                            e_p_email = st.text_input("Parent Email", value=str(first_row.get("Parent Email", "")))
                            e_p_phone = st.text_input("Parent Phone", value=str(first_row.get("Parent Phone", "")))

                        if st.form_submit_button("🔄 Update Student Info"):
                            for row_idx in st_data.index:
                                df.at[row_idx, "Grade"] = e_grade
                                df.at[row_idx, "Parent Name"] = e_p_name
                                df.at[row_idx, "Parent Email"] = e_p_email
                                df.at[row_idx, "Parent Phone"] = e_p_phone
                            if not READ_ONLY_MODE:
                                try:
                                    conn.update(worksheet="DATABASE", data=df)
                                    st.success("✅ Dados atualizados no Google Sheets!")
                                except Exception as ex:
                                    st.error(f"Erro ao guardar: {ex}")
                            else:
                                st.success("✅ Dados do aluno atualizados na app (Modo de Proteção Ativo).")

                if toggle_delete:
                    st.warning(f"⚠️ Quer mesmo eliminar o aluno {selected_student_profile}?")
                    if st.button("🔴 Confirm Delete Student"):
                        if not READ_ONLY_MODE:
                            updated_df = df[df["Student"] != selected_student_profile]
                            try:
                                conn.update(worksheet="DATABASE", data=updated_df)
                                st.success("✅ Aluno eliminado do Google Sheets!")
                            except Exception as ex:
                                st.error(f"Erro ao eliminar: {ex}")
                        else:
                            st.success("✅ Aluno removido na app (Modo de Proteção Ativo).")

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

    # -------------------------------------------------------------------------
    # TAB 3: TEACHER PROFILE (COM INSTRUMENT, PERSONAL EMAIL E TELEPHONE)
    # -------------------------------------------------------------------------
    with tab3:
        st.subheader("👨‍🏫 Teacher Profile & Contact Details")

        # 1. ADICIONAR NOVO PROFESSOR
        with st.expander("➕ Add New Teacher"):
            with st.form("form_add_teacher_top"):
                t_c1, t_c2 = st.columns(2)
                with t_c1:
                    new_t_name = st.text_input("Teacher Full Name *")
                    new_t_school_email = st.text_input("School Email *")
                    new_t_instruments = st.text_input("Instrument(s) Taught (e.g. Piano, Guitar) *")
                with t_c2:
                    new_t_personal_email = st.text_input("Personal Email")
                    new_t_phone = st.text_input("Telephone / Phone Number")
                
                if st.form_submit_button("💾 Save Teacher"):
                    if new_t_name and new_t_school_email:
                        st.session_state.teacher_details_map[new_t_name] = {
                            "school_email": new_t_school_email,
                            "personal_email": new_t_personal_email,
                            "phone": new_t_phone,
                            "instruments": new_t_instruments
                        }
                        st.success(f"✅ Professor '{new_t_name}' registado com sucesso!")
                    else:
                        st.warning("Preencha o nome e o email do professor.")

        st.markdown("---")

        # 2. SELEÇÃO E FICHA DO PROFESSOR
        all_teachers = sorted(list(st.session_state.teacher_details_map.keys())) if st.session_state.teacher_details_map else sorted([t for t in df["Teacher"].unique() if t])
        
        if all_teachers:
            t_select_col, t_btn_col = st.columns([3, 1])
            with t_select_col:
                selected_teacher_profile = st.selectbox("🔍 Select Teacher to View Profile:", all_teachers)

            with t_btn_col:
                st.write("")
                tb_edit_col, tb_del_col = st.columns(2)
                with tb_edit_col:
                    t_toggle_edit = st.button("✏️ Edit Profile", key="btn_t_edit", use_container_width=True)
                with tb_del_col:
                    t_toggle_del = st.button("🗑️ Delete", key="btn_t_del", use_container_width=True)

            if selected_teacher_profile:
                t_data = df[df["Teacher"] == selected_teacher_profile] if not df.empty else pd.DataFrame()
                first_row = t_data.iloc[0] if not t_data.empty else {}
                
                # Obter detalhes do professor do mapa em memória
                t_info = st.session_state.teacher_details_map.get(selected_teacher_profile, {
                    "school_email": first_row.get("Teacher Email", "-") if isinstance(first_row, pd.Series) else "-",
                    "personal_email": first_row.get("Teacher Personal Email", "-") if isinstance(first_row, pd.Series) else "-",
                    "phone": first_row.get("Teacher Phone", "-") if isinstance(first_row, pd.Series) else "-",
                    "instruments": first_row.get("Teacher Taught Instruments", first_row.get("Instrument", "-") if isinstance(first_row, pd.Series) else "-")
                })

                # FORMULÁRIO DE EDIÇÃO DAS INFORMAÇÕES DO PROFESSOR
                if t_toggle_edit:
                    with st.form("form_edit_t_profile"):
                        e_t_c1, e_t_c2 = st.columns(2)
                        with e_t_c1:
                            u_school_email = st.text_input("School Email", value=t_info.get("school_email", ""))
                            u_instruments = st.text_input("Instrument(s) Taught", value=t_info.get("instruments", ""))
                        with e_t_c2:
                            u_personal_email = st.text_input("Personal Email", value=t_info.get("personal_email", ""))
                            u_phone = st.text_input("Telephone", value=t_info.get("phone", ""))
                            
                        if st.form_submit_button("🔄 Save Profile Changes"):
                            st.session_state.teacher_details_map[selected_teacher_profile] = {
                                "school_email": u_school_email,
                                "personal_email": u_personal_email,
                                "phone": u_phone,
                                "instruments": u_instruments
                            }
                            
                            # Atualiza a base de dados em memória
                            if not t_data.empty:
                                for row_idx in t_data.index:
                                    df.at[row_idx, "Teacher Email"] = u_school_email
                                    df.at[row_idx, "Teacher Personal Email"] = u_personal_email
                                    df.at[row_idx, "Teacher Phone"] = u_phone
                                    df.at[row_idx, "Teacher Taught Instruments"] = u_instruments

                            if not READ_ONLY_MODE:
                                try:
                                    conn.update(worksheet="DATABASE", data=df)
                                    st.success("✅ Ficha do professor guardada no Google Sheets!")
                                except Exception as ex:
                                    st.error(f"Erro ao salvar: {ex}")
                            else:
                                st.success("✅ Ficha do professor atualizada na app (Modo de Proteção Ativo).")

                # ELIMINAÇÃO DE PROFESSOR
                if t_toggle_del:
                    st.warning(f"⚠️ Pretende remover o professor {selected_teacher_profile}?")
                    if st.button("🔴 Confirm Delete Teacher"):
                        if selected_teacher_profile in st.session_state.teacher_details_map:
                            del st.session_state.teacher_details_map[selected_teacher_profile]
                        st.success(f"✅ Professor {selected_teacher_profile} removido da app!")

                # EXIBIÇÃO DA FICHA DO PROFESSOR COM NOVOS CAMPOS
                tp_col1, tp_col2 = st.columns(2)
                with tp_col1:
                    st.info(f"### 👨‍🏫 {selected_teacher_profile}")
                    st.markdown(f"🎸 **Instrument(s) Taught:** {t_info.get('instruments', '-')}")
                    st.markdown(f"🏫 **Primary Campus:** {first_row.get('Campus', '-') if isinstance(first_row, pd.Series) else '-'}")

                with tp_col2:
                    st.success("### 📞 Contact Details")
                    st.markdown(f"✉️ **School Email:** {t_info.get('school_email', '-')}")
                    st.markdown(f"📧 **Personal Email:** {t_info.get('personal_email', '-')}")
                    st.markdown(f"📱 **Telephone:** {t_info.get('phone', '-')}")

                st.markdown("---")
                st.subheader("📅 Weekly Schedule")
                
                if not t_data.empty:
                    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                    for day_name in days_order:
                        day_t = t_data[t_data["Day"] == day_name].copy()
                        if not day_t.empty:
                            st.markdown(f"##### 📅 {day_name.upper()}")
                            day_t["Time"] = day_t.apply(format_time_range, axis=1)
                            t_disp = day_t[["Time", "Student", "Grade", "Instrument", "Room", "Campus"]].copy()
                            t_disp.columns = ["Time", "Student", "Class", "Instrument", "Room", "Campus"]
                            st.dataframe(t_disp, use_container_width=True, hide_index=True)
                else:
                    st.caption("No scheduled lessons for this teacher.")

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
