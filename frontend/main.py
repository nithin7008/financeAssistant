import streamlit as st
import requests

# App Config
st.set_page_config(layout="wide", page_title="Finance Assistant", page_icon="💸")
BACKEND_URL = "http://backend:8000"

# --- State ---
if "mode" not in st.session_state:
    st.session_state.mode = "input"
if "edited_sql" not in st.session_state:
    st.session_state.edited_sql = ""
if "last_question" not in st.session_state:
    st.session_state.last_question = ""
if "developer_mode" not in st.session_state:
    st.session_state.developer_mode = False
if "notebook_sql" not in st.session_state:
    st.session_state.notebook_sql = ""
if "notebook_result" not in st.session_state:
    st.session_state.notebook_result = {}

# --- Title Row with Developer Mode Icon ---
col_title, col_icon = st.columns([8, 1])
with col_title:
    st.markdown("<h1 style='color:#3e8ed0;'>AI Text-to-SQL Finance Assistant</h1>", unsafe_allow_html=True)
with col_icon:
    if st.button("🛠️", help="Toggle Developer Mode"):
        st.session_state.developer_mode = not st.session_state.get("developer_mode", False)


# --- Main Title ---
# st.markdown("<h1 style='color:#3e8ed0;'>AI Text-to-SQL Finance Assistant</h1>", unsafe_allow_html=True)
st.markdown("Ask questions like: *'What is my current credit card balance?'*")

# --- Input ---
nl_query = st.text_input("💬 Your Question:", placeholder="e.g., How much did I invest last month?")

# Reset edit box if question changes
if nl_query and nl_query != st.session_state.last_question:
    st.session_state.mode = "input"
    st.session_state.last_question = nl_query

if nl_query:
    response = requests.post(f"{BACKEND_URL}/query", json={"question": nl_query})
    if response.status_code == 200:
        generated_sql = response.json().get("sql", "")
        with st.expander("🛠️ Generated SQL", expanded=True):
            st.code(generated_sql, language="sql")
    else:
        st.error("❌ Failed to generate SQL")
        generated_sql = ""

    # --- Feedback Buttons ---
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Good", use_container_width=True):
            result = requests.post(f"{BACKEND_URL}/execute_sql", json={"sql": generated_sql})
            if result.status_code == 200:
                data = result.json()
                st.success("Feedback saved!")
                st.markdown("### 📊 Query Results")
                st.dataframe(data["data"])
                requests.post(f"{BACKEND_URL}/feedback", json={
                    "question": nl_query,
                    "generated_sql": generated_sql,
                    "corrected_sql": generated_sql,
                    "feedback": "good"
                })
                st.session_state.mode = "input"
            else:
                st.error("❌ SQL Execution failed")

    with col2:
        if st.session_state.mode != "bad" and st.button("❌ Bad", use_container_width=True):
            st.session_state.mode = "bad"
            st.session_state.edited_sql = generated_sql

    # --- Edit SQL if Bad ---
    if st.session_state.mode == "bad":
        st.markdown("### ✏️ Edit SQL")
        st.session_state.edited_sql = st.text_area("Modify the SQL below and re-run:", value=st.session_state.edited_sql, height=150)

        if st.button("🚀 Run Edited SQL", type="primary"):
            result = requests.post(f"{BACKEND_URL}/execute_sql", json={"sql": st.session_state.edited_sql})
            if result.status_code == 200:
                data = result.json()
                st.markdown("### 📊 Edited Query Results")
                st.dataframe(data["data"])
                requests.post(f"{BACKEND_URL}/feedback", json={
                    "question": nl_query,
                    "generated_sql": generated_sql,
                    "corrected_sql": st.session_state.edited_sql,
                    "feedback": "bad"
                })
                st.success("Feedback saved!")
                st.session_state.mode = "input"
            else:
                st.error("❌ SQL Execution failed")

# --- Developer Mode Section ---
if st.session_state.developer_mode:
    st.markdown("## 🧪 Developer Notebook")

    col_dev1, col_dev2 = st.columns([2, 3])
    with col_dev1:
        st.session_state.notebook_sql = st.text_area("Write SQL to test:", height=150)

        if st.button("⚙️ Run Notebook SQL"):
            result = requests.post(f"{BACKEND_URL}/execute_sql", json={"sql": st.session_state.notebook_sql})
            if result.status_code == 200:
                st.session_state.notebook_result = result.json()
            else:
                st.session_state.notebook_result = {"error": result.text}

    with col_dev2:
        if st.session_state.notebook_result:
            st.markdown("### 📄 Notebook Output")
            if "data" in st.session_state.notebook_result:
                st.dataframe(st.session_state.notebook_result["data"])
                # Show "Use This SQL" button only when mode is 'bad'
                if st.session_state.mode == "bad":
                    if st.button("📋 Use This SQL"):
                        st.session_state.edited_sql = st.session_state.notebook_sql
                        st.success("Copied to Edit SQL")
            else:
                st.error(st.session_state.notebook_result.get("error", "Unknown error"))

