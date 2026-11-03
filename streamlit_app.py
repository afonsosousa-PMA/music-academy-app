import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Page configuration
st.set_page_config(
    page_title="Park Music Academy Management Portal",
    page_icon="🎵",
    layout="wide"
)

st.title("🎵 PARK MUSIC ACADEMY — MANAGEMENT PORTAL")

# -----------------------------------------------------------------------------
# 1. DATA LOADING & METRICS LOGIC
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
        st.error(f"Error reading 'DATABASE' tab: {e}")
        return pd.DataFrame()

df = load_data()

# Ensure optional columns exist
for col in ["Parent Name", "Parent Phone", "Parent Email", "Teacher Email", "Notes"]:
    if col not in df.columns:
        df[col] = ""

# Filter out empty student rows
valid_df = df[df["Student"] != ""].copy() if not df.empty and "Student" in df.columns else pd.DataFrame()

# Helper logic to calculate exact Enrollments (handling 30+30 split lessons)
def calculate_enrollments(data):
    if data.empty:
        return 0
    # A single enrollment is defined by a unique combination of Student + Campus + Instrument
    # This automatically combines two 30-min split rows (e.g. 30+30) for the same instrument into 1 enrollment!
    if "Instrument" in data.columns and "Campus" in data.columns:
        return data.groupby(["Student", "Campus", "Instrument"]).ngroups
    return len(data)

# Helper logic for Unique Students
def calculate_unique_students(data):
    if data.empty or "Student" not in data.columns:
        return 0
    return data["Student"].nunique()

# -----------------------------------------------------------------------------
# 2. LOGIN & ROLE SELECTION (Sidebar)
# -----------------------------------------------------------------------------
st.sidebar.title("🔐 Portal Login")

user_role = st.sidebar.selectbox(
    "Select Role",
    ["Academy Coordinator", "School Coordinator", "Academy Teacher"]
)

user_email = st.sidebar.text_input("Enter School Email", value="").strip().lower()
st.sidebar.markdown("---")

# -----------------------------------------------------------------------------
# 3. TIER 1: ACADEMY COORDINATOR (Matching Dashboard Screenshot)
# -----------------------------------------------------------------------------
if user_role == "Academy Coordinator":
    st.header("🏛️ Academy Coordinator Portal")

    # Executive Overview Dashboard (Matching your Google Sheet layout)
    st.subheader("📊 EXECUTIVE DASHBOARD")
    
    # Top-level totals
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

    # Campus Breakdown Cards (Enrollments vs Unique Students)
    st.subheader("📍 Campus Enrollments & Unique Students Breakdown")
    c_alfragide, c_pde, c_restelo = st.columns(3)

    # Alfragide Data
    df_alfragide = valid_df[valid_df["Campus"] == "Alfragide"] if not valid_df.empty else pd.DataFrame()
    with c_alfragide:
        st.info("### 🏫 Alfragide")
        st.metric("Enrollments", calculate_enrollments(df_alfragide))
        st.metric("Unique Students", calculate_unique_students(df_alfragide))

    # PdE Data
    df_pde = valid_df[valid_df["Campus"] == "PdE"] if not valid_df.empty else pd.DataFrame()
    with c_pde:
        st.success("### 🏫 PdE")
        st.metric("Enrollments", calculate_enrollments(df_pde))
        st.metric("Unique Students", calculate_unique_students(df_pde))

    # Restelo Data
    df_restelo = valid_df[valid_df["Campus"] == "Restelo"] if not valid_df.empty else pd.DataFrame()
    with c_restelo:
        st.warning("### 🏫 Restelo")
        st.metric("Enrollments", calculate_enrollments(df_restelo))
        st.metric("Unique Students", calculate_unique_students(df_restelo))

    st.markdown("---")

    # Total Summary Metrics
    sum1, sum2 = st.columns(2)
    sum1.metric("📌 TOTAL ENROLLMENTS (All Campuses)", calculate_enrollments(valid_df))
    sum2.metric("👤 TOTAL UNIQUE STUDENTS (All Campuses)", total_unique_students)

    st.markdown("---")

    # Coordinator Navigation Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📅 General Schedule & Filters", 
        "📞 Parent Contact Directory", 
        "➕ Add New Booking / Record", 
        "✏️ Edit / Update Existing Records"
    ])

    # TAB 1: General Schedule
