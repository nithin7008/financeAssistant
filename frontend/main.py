import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz


eastern = pytz.timezone("US/Eastern")
datetime.now(eastern)

BACKEND_URL = "http://backend:8000"

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "home"

# --- Navigation Icons ---
col1, col2, col3, col4 = st.columns([0.9, 0.05, 0.05, 0.05])
with col1:
    st.title("💰 AI Text-to-SQL Finance Assistant")
with col2:
    if st.button("🏠", help="Home"):
        st.session_state.page = "home"
with col3:
    if st.button("📊", help="Admin Console"):
        st.session_state.page = "admin"
with col4:
    if st.button("🧪", help="Developer Mode"):
        st.session_state.page = "developer"

# --- HOME PAGE ---
if st.session_state.page == "home":
    if "mode" not in st.session_state:
        st.session_state.mode = "input"
    if "edited_sql" not in st.session_state:
        st.session_state.edited_sql = ""

    nl_query = st.text_input("Ask a question about your finances:")

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
                    st.write(data)
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
            st.session_state.edited_sql = st.text_area("Edit SQL:", value=st.session_state.edited_sql)

            if st.button("Run Edited SQL"):
                result = requests.post(f"{BACKEND_URL}/execute_sql", json={"sql": st.session_state.edited_sql})
                if result.status_code == 200:
                    data = result.json()
                    st.markdown("### Query Results:")
                    st.write(data)
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

elif st.session_state.page == "admin":
    st.header("📊 Weekly Snapshot Editor")

    # Load existing snapshot file
    snapshot_df = pd.read_excel("db/account_weekly_snapshot.xlsx")
    snapshot_df.columns = snapshot_df.columns.str.strip().str.lower()
    snapshot_df = snapshot_df.sort_values(by=["type", "bank"])

    # Get unique (bank, type) pairs
    bank_type_pairs = list(snapshot_df[["bank", "type"]].drop_duplicates().itertuples(index=False, name=None))

    st.markdown("### Add or Update Weekly Snapshot")

    # Initialize fixed timestamp for session if not set
    if "fixed_last_updated" not in st.session_state:
        st.session_state.fixed_last_updated = datetime.now()

    fixed_timestamp = st.session_state.fixed_last_updated

    # Display timestamp and provide reset button
    st.write(f"Last updated timestamp for this session: {fixed_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

    if st.button("Reset Timestamp"):
        st.session_state.fixed_last_updated = datetime.now()
        st.experimental_rerun()

    # Create editable dataframe with columns and pre-filled bank/type from pairs
    editable_df = pd.DataFrame({
        "bank": [bt[0] for bt in bank_type_pairs],
        "type": [bt[1] for bt in bank_type_pairs],
        "balance": [None] * len(bank_type_pairs),
        "payment_due": [None] * len(bank_type_pairs),
        "last_updated_date": [fixed_timestamp] * len(bank_type_pairs),
    })

    edited_rows = st.data_editor(
        editable_df,
        num_rows="dynamic",
        disabled=["bank", "type", "last_updated_date"],
        use_container_width=True,
        key="weekly_snapshot_editor"
    )

    if st.button("📥 Submit Snapshot Data"):
        try:
            new_rows = pd.DataFrame(edited_rows)
            new_rows = new_rows.dropna(subset=["balance", "payment_due"], how="all")
            if not new_rows.empty:
                updated_df = pd.concat([snapshot_df, new_rows], ignore_index=True)
                updated_df.to_excel("db/account_weekly_snapshot.xlsx", index=False)

                # Call backend API to reload snapshots into DB
                reload_resp = requests.post(f"{BACKEND_URL}/reload_snapshots")
                if reload_resp.status_code == 200:
                    st.success("Snapshot data saved and backend DB reloaded successfully!")
                else:
                    st.warning("Snapshot saved but failed to reload backend DB.")
            else:
                st.warning("No valid rows to save.")
        except Exception as e:
            st.error(f"Error saving data: {str(e)}")

# --- DEVELOPER PAGE ---
elif st.session_state.page == "developer":
    st.header("🧪 Developer Notebook")

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
        if st.session_state.get("notebook_result"):
            st.markdown("### 📄 Notebook Output")
            if "data" in st.session_state.notebook_result:
                st.dataframe(st.session_state.notebook_result["data"])
                if st.session_state.mode == "bad":
                    if st.button("📋 Use This SQL"):
                        st.session_state.edited_sql = st.session_state.notebook_sql
                        st.success("Copied to Edit SQL")
            else:
                st.error(st.session_state.notebook_result.get("error", "Unknown error"))
