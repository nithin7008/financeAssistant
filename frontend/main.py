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

# --- Log Level Toggle Function ---
def render_log_level_toggle():
    """Render log level toggle in sidebar"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔧 Debug Controls")
        
        # Get current log level
        try:
            response = requests.get(f"{BACKEND_URL}/log_level")
            if response.status_code == 200:
                current_level = response.json().get("log_level", "INFO")
            else:
                current_level = "INFO"
        except:
            current_level = "INFO"
        
        # Log level selector
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        selected_level = st.selectbox(
            "Log Level:",
            levels,
            index=levels.index(current_level) if current_level in levels else 1,
            help="DEBUG: Show all logs (detailed)\nINFO: Show important events\nWARNING: Show warnings and errors\nERROR: Show errors only"
        )
        
        # Update log level if changed
        if selected_level != current_level:
            try:
                response = requests.post(
                    f"{BACKEND_URL}/log_level",
                    json={"level": selected_level}
                )
                if response.status_code == 200:
                    st.success(f"✅ Log level set to {selected_level}")
                    st.rerun()
                else:
                    st.error("❌ Failed to update log level")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        
        # Show current status
        if selected_level == "DEBUG":
            st.info("🔍 **DEBUG MODE**: Showing detailed logs")
        elif selected_level == "INFO":
            st.info("ℹ️ **INFO MODE**: Showing important events")
        elif selected_level == "WARNING":
            st.info("⚠️ **WARNING MODE**: Showing warnings & errors")
        else:
            st.info("🚨 **ERROR MODE**: Showing errors only")

# --- Navigation Icons ---
col1, col2, col3, col4 = st.columns([0.9, 0.05, 0.05, 0.05])
with col1:
    st.title("💰 Finance Assistant")
with col2:
    if st.button("🏠", help="Home"):
        st.session_state.page = "home"
with col3:
    if st.button("📊", help="Admin Console"):
        st.session_state.page = "admin"
with col4:
    if st.button("🧪", help="Developer Mode"):
        st.session_state.page = "developer"

# Render log level toggle on all pages
render_log_level_toggle()

# --- HOME PAGE ---
if st.session_state.page == "home":
    if "mode" not in st.session_state:
        st.session_state.mode = "input"
    if "edited_sql" not in st.session_state:
        st.session_state.edited_sql = ""
    if "feedback_saved" not in st.session_state:
        st.session_state.feedback_saved = False
    if "sql_source" not in st.session_state:
        st.session_state.sql_source = "unknown"
    if "current_generated_sql" not in st.session_state:
        st.session_state.current_generated_sql = ""
    if "current_nl_query" not in st.session_state:
        st.session_state.current_nl_query = ""
    if "query_executed" not in st.session_state:
        st.session_state.query_executed = False
    if "execution_successful" not in st.session_state:
        st.session_state.execution_successful = False

    nl_query = st.text_input("Ask a question about your finances:")
    
    if nl_query:
        # Store current query for feedback purposes
        st.session_state.current_nl_query = nl_query
        
        response = requests.post(f"{BACKEND_URL}/query", json={"question": nl_query})
        if response.status_code == 200:
            response_data = response.json()
            generated_sql = response_data.get("sql", "")
            sql_source = response_data.get("source", "unknown")
            
            # Store for feedback purposes
            st.session_state.current_generated_sql = generated_sql
            st.session_state.sql_source = sql_source
            
            st.markdown("### Generated SQL:")
            st.code(generated_sql)
            
            # Show source information for transparency
            source_emoji = {
                "ollama_generated": "🤖",
                "good_feedback": "✅", 
                "bad_feedback_corrected": "🔧",
                "query_examples": "📚",
                "unknown": "❓"
            }
            source_description = {
                "ollama_generated": "AI Generated",
                "good_feedback": "From Good Feedback",
                "bad_feedback_corrected": "From Corrected Feedback", 
                "query_examples": "From Examples",
                "unknown": "Unknown Source"
            }
            
            st.info(f"{source_emoji.get(sql_source, '❓')} **Source:** {source_description.get(sql_source, 'Unknown')}")
            
        else:
            st.error("Failed to generate SQL")
            generated_sql = ""
            sql_source = "unknown"

        # Execute SQL button
        if st.button("🔍 Execute SQL"):
            result = requests.post(f"{BACKEND_URL}/execute_sql", json={"sql": generated_sql})
            if result.status_code == 200:
                response_json = result.json()
                columns = response_json.get("columns", [])
                data = response_json.get("data", [])
                
                if data:
                    df = pd.DataFrame(data, columns=columns)
                    st.markdown("### Query Results:")
                    st.dataframe(df)
                else:
                    st.warning("No results found.")
                
                st.session_state.query_executed = True
                st.session_state.execution_successful = True
                st.success("✅ Query executed successfully!")
                
            else:
                st.error(f"❌ SQL Execution failed: {result.text}")
                st.session_state.query_executed = True
                st.session_state.execution_successful = False

        # Show feedback buttons only after execution
        if st.session_state.query_executed:
            st.markdown("### 📝 How was this query?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("👍 Good Query"):
                    if st.session_state.execution_successful:
                        # Only save good feedback if SQL was generated by Ollama
                        if sql_source == "ollama_generated":
                            feedback_response = requests.post(f"{BACKEND_URL}/feedback", json={
                                "question": st.session_state.current_nl_query,
                                "generated_sql": st.session_state.current_generated_sql,
                                "corrected_sql": st.session_state.current_generated_sql,  # Same as generated for good feedback
                                "feedback": "good",
                                "source": sql_source
                            })
                            
                            if feedback_response.status_code == 200:
                                response_msg = feedback_response.json().get("message", "Good feedback saved!")
                                st.success(f"✅ {response_msg}")
                            else:
                                st.success("✅ Thanks for the feedback! (Save failed, but noted)")
                        else:
                            # Don't save good feedback for retrieved queries
                            source_msg = {
                                "good_feedback": "already learned from this pattern",
                                "bad_feedback_corrected": "already corrected", 
                                "query_examples": "from examples collection",
                                "unknown": "unknown source"
                            }
                            st.success(f"✅ Thanks for the feedback! (Not saved - {source_msg.get(sql_source, 'not from AI')})")
                        
                        # Reset state
                        st.session_state.mode = "input"
                        st.session_state.query_executed = False
                        st.session_state.execution_successful = False
                        st.session_state.feedback_saved = False
                    else:
                        st.warning("⚠️ Cannot mark as good - the query failed to execute properly.")

            with col2:
                if st.button("👎 Bad Query"):
                    st.session_state.mode = "bad"
                    st.session_state.edited_sql = generated_sql
                    st.session_state.feedback_saved = False

        # Bad feedback handling
        if st.session_state.mode == "bad":
            st.markdown("### 🔧 Edit the SQL Query:")
            st.session_state.edited_sql = st.text_area(
                "Edit SQL:", 
                value=st.session_state.edited_sql,
                height=150
            )
            
            col3, col4 = st.columns(2)
            
            with col3:
                if st.button("🔍 Test Edited SQL"):
                    if st.session_state.edited_sql.strip():
                        result = requests.post(f"{BACKEND_URL}/execute_sql", json={"sql": st.session_state.edited_sql})
                        if result.status_code == 200:
                            response_json = result.json()
                            columns = response_json.get("columns", [])
                            data = response_json.get("data", [])
                            
                            if data:
                                df = pd.DataFrame(data, columns=columns)
                                st.markdown("### Corrected Query Results:")
                                st.dataframe(df)
                                st.success("✅ Edited SQL works! You can now save the feedback.")
                            else:
                                st.warning("No results found, but query executed successfully.")
                            
                            st.session_state.feedback_saved = False
                        else:
                            st.error(f"❌ SQL Execution failed: {result.text}")
                    else:
                        st.warning("Please enter some SQL to test.")

            with col4:
                if not st.session_state.feedback_saved:
                    if st.button("💾 Save Bad Feedback"):
                        if st.session_state.edited_sql.strip():
                            # Always save bad feedback regardless of source
                            feedback_response = requests.post(f"{BACKEND_URL}/feedback", json={
                                "question": st.session_state.current_nl_query,
                                "generated_sql": st.session_state.current_generated_sql,
                                "corrected_sql": st.session_state.edited_sql,
                                "feedback": "bad",
                                "source": st.session_state.sql_source
                            })
                            
                            if feedback_response.status_code == 200:
                                response_msg = feedback_response.json().get("message", "Feedback saved!")
                                st.success(f"✅ {response_msg}")
                                st.session_state.feedback_saved = True
                                
                                # Auto-reset after successful save
                                if st.button("🔄 Start New Query"):
                                    st.session_state.mode = "input"
                                    st.session_state.feedback_saved = False
                                    st.session_state.query_executed = False
                                    st.session_state.execution_successful = False
                                    st.rerun()
                            else:
                                st.error("❌ Failed to save feedback")
                        else:
                            st.warning("Please provide a corrected SQL query before saving feedback.")
                else:
                    st.success("✅ Feedback already saved!")
                    if st.button("🔄 Start New Query"):
                        st.session_state.mode = "input"
                        st.session_state.feedback_saved = False
                        st.session_state.query_executed = False
                        st.session_state.execution_successful = False
                        st.rerun()

            # Show comparison for transparency
            if st.session_state.mode == "bad":
                st.markdown("### 📊 Comparison:")
                col5, col6 = st.columns(2)
                
                with col5:
                    st.markdown("**Original SQL:**")
                    st.code(st.session_state.current_generated_sql, language="sql")
                
                with col6:
                    st.markdown("**Your Corrected SQL:**")
                    st.code(st.session_state.edited_sql, language="sql")


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
