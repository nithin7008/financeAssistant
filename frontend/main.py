import streamlit as st
import requests

BACKEND_URL = "http://backend:8000"

st.set_page_config(layout="wide")
st.title("AI Text-to-SQL Finance Assistant")

# --- State initialization ---
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

# --- Developer Mode Toggle ---
with st.sidebar:
    st.markdown("## ⚙️ Developer Mode")
    st.session_state.developer_mode = st.checkbox("Enable Developer Mode")

# --- Natural language question input ---
nl_query = st.text_input("Ask a question about your finances:")

# Reset edit mode if new question is entered
if nl_query and nl_query != st.session_state.last_question:
    st.session_state.mode = "input"
    st.session_state.last_question = nl_query

if nl_query:
    response = requests.post(f"{BACKEND_URL}/query", json={"question": nl_query})
    if response.status_code == 200:
        generated_sql = response.json().get("sql", "")
        st.markdown("### Generated SQL:")
        st.code(generated_sql)
    else:
        st.error("Failed to generate SQL")
        generated_sql = ""

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Good"):
            result = requests.post(f"{BACKEND_URL}/execute_sql", json={"sql": generated_sql})
            if result.status_code == 200:
                data = result.json()
                st.markdown("### Query Results:")
                st.dataframe(data["data"])
                requests.post(f"{BACKEND_URL}/feedback", json={
                    "question": nl_query,
                    "generated_sql": generated_sql,
                    "corrected_sql": generated_sql,
                    "feedback": "good"
                })
                st.success("Feedback saved!")
                st.session_state.mode = "input"
            else:
                st.error("SQL Execution failed")

    with col2:
        if st.session_state.mode != "bad" and st.button("Bad"):
            st.session_state.mode = "bad"
            st.session_state.edited_sql = generated_sql

    if st.session_state.mode == "bad":
        st.markdown("### Edit SQL:")
        st.session_state.edited_sql = st.text_area("Edit SQL:", value=st.session_state.edited_sql)

        if st.button("Run Edited SQL"):
            result = requests.post(f"{BACKEND_URL}/execute_sql", json={"sql": st.session_state.edited_sql})
            if result.status_code == 200:
                data = result.json()
                st.markdown("### Query Results:")
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
                st.error("SQL Execution failed")

# --- Developer Notebook Mode ---
if st.session_state.developer_mode:
    st.markdown("## 🧪 Developer Notebook")

    col_dev1, col_dev2 = st.columns([2, 3])

    with col_dev1:
        st.session_state.notebook_sql = st.text_area("Write SQL to test manually:", height=150)

        if st.button("Run Notebook SQL"):
            result = requests.post(f"{BACKEND_URL}/execute_sql", json={"sql": st.session_state.notebook_sql})
            if result.status_code == 200:
                st.session_state.notebook_result = result.json()
            else:
                st.session_state.notebook_result = {"error": result.text}

    with col_dev2:
        if "notebook_result" in st.session_state:
            st.markdown("### Notebook Output")
            if "data" in st.session_state.notebook_result:
                st.dataframe(st.session_state.notebook_result["data"])
                if st.button("Use This SQL"):
                    st.session_state.edited_sql = st.session_state.notebook_sql
                    st.session_state.mode = "bad"
                    st.success("SQL copied to Edit window.")
            else:
                st.error(st.session_state.notebook_result.get("error", "Unknown error"))
