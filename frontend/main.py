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

# Initialize sidebar state - hidden by default
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = False

# --- Log Level Toggle Function ---
def render_log_level_toggle():
    """Render log level toggle in sidebar"""
    if st.session_state.sidebar_open:
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

# Custom CSS to hide sidebar by default and style the gear button
st.markdown("""
<style>
    /* Hide sidebar by default */
    .css-1d391kg {
        display: none;
    }
    
    /* Show sidebar when open */
    .sidebar-open .css-1d391kg {
        display: block !important;
    }
    
    /* Custom gear button styling */
    .gear-button {
        position: fixed;
        top: 70px;
        left: 10px;
        z-index: 999;
        background: #ff4b4b;
        color: white;
        border: none;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        font-size: 16px;
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .gear-button:hover {
        background: #ff6b6b;
    }
</style>
""", unsafe_allow_html=True)

# Add gear button to toggle sidebar
gear_col1, gear_col2 = st.columns([0.1, 0.9])
with gear_col1:
    if st.button("⚙️", help="Toggle Debug Controls", key="gear_toggle"):
        st.session_state.sidebar_open = not st.session_state.sidebar_open
        st.rerun()

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

# Render log level toggle only when sidebar is open
render_log_level_toggle()

# --- HOME PAGE ---
if st.session_state.page == "home":
    # Initialize session state variables
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
    if "confidence" not in st.session_state:
        st.session_state.confidence = "low"
    if "query_results" not in st.session_state:
        st.session_state.query_results = None

    nl_query = st.text_input("Ask a question about your finances:")
    
    if nl_query:
        # Store current query for feedback purposes
        st.session_state.current_nl_query = nl_query
        
        response = requests.post(f"{BACKEND_URL}/smart_query", json={"question": nl_query})
        
        if response.status_code == 200:
            response_data = response.json()
            confidence = response_data.get("confidence", "low")
            sql_source = response_data.get("source", "unknown")
            
            # Store for feedback purposes
            st.session_state.confidence = confidence
            st.session_state.sql_source = sql_source
            
            # Source information
            source_emoji = {
                "ollama_generated": "🤖",
                "good_feedback": "✅",
                "bad_feedback_corrected": "🔧",
                "query_examples": "📚",
                "unknown": "❓",
                "error": "❌"
            }
            source_description = {
                "ollama_generated": "AI Generated",
                "good_feedback": "From Good Feedback",
                "bad_feedback_corrected": "From Corrected Feedback", 
                "query_examples": "From Examples",
                "unknown": "Unknown Source",
                "error": "Error Occurred"
            }
            
            if confidence == "high":
                # HIGH CONFIDENCE: Show results directly, no SQL
                st.info(f"{source_emoji.get(sql_source, '❓')} **Source:** {source_description.get(sql_source, 'Unknown')} (High Confidence)")
                
                if response_data.get("error"):
                    st.error(f"❌ Error: {response_data['error']}")
                    # If high confidence query failed, show SQL for debugging
                    if response_data.get("sql"):
                        st.markdown("### SQL (for debugging):")
                        st.code(response_data["sql"])
                        st.session_state.current_generated_sql = response_data["sql"]
                        st.session_state.mode = "bad"  # Allow user to fix it
                elif response_data.get("data"):
                    # Show results directly
                    columns = response_data.get("columns", [])
                    data = response_data.get("data", [])
                    
                    if data:
                        df = pd.DataFrame(data, columns=columns)
                        st.markdown("### Results:")
                        st.dataframe(df)
                        st.success("✅ Query executed successfully!")
                        
                        # Store results for potential feedback
                        st.session_state.query_results = {"columns": columns, "data": data}
                        st.session_state.query_executed = True
                        st.session_state.execution_successful = True
                    else:
                        st.warning("No results found.")
                        st.session_state.query_executed = True
                        st.session_state.execution_successful = True
                else:
                    st.warning("No data returned from query.")
                    
            else:
                # LOW CONFIDENCE: Show SQL for review (current behavior)
                generated_sql = response_data.get("sql", "")
                st.session_state.current_generated_sql = generated_sql
                
                st.info(f"{source_emoji.get(sql_source, '❓')} **Source:** {source_description.get(sql_source, 'Unknown')} (Low Confidence - Please Review)")
                
                st.markdown("### Generated SQL:")
                st.code(generated_sql)
                
                # Execute SQL button for low confidence queries
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
                            st.session_state.query_results = {"columns": columns, "data": data}
                        else:
                            st.warning("No results found.")
                        
                        st.session_state.query_executed = True
                        st.session_state.execution_successful = True
                        st.success("✅ Query executed successfully!")
                    else:
                        st.error(f"❌ SQL Execution failed: {result.text}")
                        st.session_state.query_executed = True
                        st.session_state.execution_successful = False
        else:
            st.error("Failed to process query")
            confidence = "low"
            sql_source = "error"

        # Show feedback buttons after query execution or for high confidence results
        show_feedback = (
            (confidence == "high" and st.session_state.get("query_results")) or 
            st.session_state.query_executed
        )
        
        if show_feedback:
            st.markdown("### 📝 How was this query?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("👍 Good Query"):
                    if st.session_state.execution_successful or confidence == "high":
                        # Only save good feedback if SQL was generated by Ollama
                        if sql_source == "ollama_generated":
                            feedback_response = requests.post(f"{BACKEND_URL}/feedback", json={
                                "question": st.session_state.current_nl_query,
                                "generated_sql": st.session_state.current_generated_sql,
                                "corrected_sql": st.session_state.current_generated_sql,  # Same as generated for good feedback
                                "feedback": "good"
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
                        st.session_state.query_results = None
                    else:
                        st.warning("⚠️ Cannot mark as good - the query failed to execute properly.")
            
            with col2:
                if st.button("👎 Bad Query"):
                    # For high confidence queries that failed, we might not have the SQL
                    if not st.session_state.current_generated_sql and confidence == "high":
                        st.error("Cannot provide feedback - SQL not available for editing")
                    else:
                        st.session_state.mode = "bad"
                        st.session_state.edited_sql = st.session_state.current_generated_sql
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
                                "feedback": "bad"
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
                                    st.session_state.query_results = None
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
                        st.session_state.query_results = None
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

        # Add a toggle for advanced users to see SQL even for high confidence queries
        if confidence == "high" and st.session_state.get("query_results"):
            with st.expander("🔍 Show SQL (Advanced)"):
                if st.session_state.current_generated_sql:
                    st.code(st.session_state.current_generated_sql, language="sql")
                else:
                    st.info("SQL not available for this high-confidence query")

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
        st.rerun()
    
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
    
    # Add mode toggle for developer page
    dev_mode = st.radio(
        "Developer Mode:",
        ["SQL Notebook", "Query Testing"],
        horizontal=True
    )
    
    if dev_mode == "SQL Notebook":
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
    
    elif dev_mode == "Query Testing":
        st.markdown("### 🔬 Query Testing Mode")
        st.info("Compare regular /query vs /smart_query endpoints")
        
        test_query = st.text_input("Enter test query:")
        
        if test_query:
            col_test1, col_test2 = st.columns(2)
            
            with col_test1:
                st.markdown("#### Regular /query endpoint")
                if st.button("Test Regular Query"):
                    response = requests.post(f"{BACKEND_URL}/query", json={"question": test_query})
                    if response.status_code == 200:
                        data = response.json()
                        st.json(data)
                        st.code(data.get("sql", ""), language="sql")
                    else:
                        st.error(f"Error: {response.text}")
            
            with col_test2:
                st.markdown("#### Smart /smart_query endpoint")
                if st.button("Test Smart Query"):
                    response = requests.post(f"{BACKEND_URL}/smart_query", json={"question": test_query})
                    if response.status_code == 200:
                        data = response.json()
                        st.json(data)
                        
                        if data.get("confidence") == "high":
                            st.success("High confidence - would show results directly")
                            if data.get("data"):
                                df = pd.DataFrame(data["data"], columns=data.get("columns", []))
                                st.dataframe(df)
                        else:
                            st.warning("Low confidence - would show SQL for review")
                            if data.get("sql"):
                                st.code(data["sql"], language="sql")
                    else:
                        st.error(f"Error: {response.text}")

