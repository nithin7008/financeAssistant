import streamlit as st
import requests

BACKEND_URL = "http://backend:8000"

def get_sql_from_backend(nl_query: str):
    response = requests.post(f"{BACKEND_URL}/query", json={"question": nl_query})
    if response.status_code == 200:
        return response.json().get("sql", "")
    else:
        st.error("Failed to generate SQL")
        return ""

def run_sql_query(sql: str):
    response = requests.post(f"{BACKEND_URL}/execute_sql", json={"sql": sql})
    if response.status_code == 200:
        json_resp = response.json()
        return json_resp.get("columns", []), json_resp.get("data", [])
    else:
        st.error("Failed to run SQL")
        return [], []

st.title("AI Text-to-SQL Finance Assistant")

nl_query = st.text_input("Ask a question about your finances:")

if nl_query:
    generated_sql = get_sql_from_backend(nl_query)
    st.markdown("### Generated SQL:")
    st.code(generated_sql)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Good"):
            columns, data = run_sql_query(generated_sql)
            st.markdown("### Query Results:")
            if columns and data:
                st.dataframe(data)
            else:
                st.write("No results to display")

    # Manage 'Bad' button state
    if 'bad_clicked' not in st.session_state:
        st.session_state.bad_clicked = False

    with col2:
        if st.button("Bad"):
            st.session_state.bad_clicked = True

    if st.session_state.bad_clicked:
        edited_sql = st.text_area("Edit SQL:", value=generated_sql)
        if st.button("Run Edited SQL"):
            columns, data = run_sql_query(edited_sql)
            st.markdown("### Query Results:")
            if columns and data:
                st.dataframe(data)
            else:
                st.write("No results to display")
