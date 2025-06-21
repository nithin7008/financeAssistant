import streamlit as st
import requests

BACKEND_URL = "http://localhost:8000"  # Adjust if backend is remote

st.sidebar.title("Choose Action")
option = st.sidebar.radio("", ["📋 View MySQL Tables", "📤 Upload File"])

if option == "📋 View MySQL Tables":
    st.title("📋 MySQL Table Viewer")

    try:
        res = requests.get(f"{BACKEND_URL}/tables")
        res.raise_for_status()
        tables = res.json()["tables"]

        selected_table = st.selectbox("Select a table", tables)

        if selected_table:
            table_res = requests.get(f"{BACKEND_URL}/table/{selected_table}")
            table_res.raise_for_status()
            data = table_res.json()
            st.dataframe(data["data"])

    except Exception as e:
        st.error(f"❌ Error: {e}")

elif option == "📤 Upload File":
    st.title("📤 Upload a File into Container")

    uploaded_file = st.file_uploader("Choose a file to upload", type=["csv", "txt", "sql", "json", "xlsx"])

    if uploaded_file is not None:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        try:
            upload_res = requests.post(f"{BACKEND_URL}/upload", files=files)
            upload_res.raise_for_status()
            msg = upload_res.json().get("message", "Upload succeeded")
            st.success(f"✅ {msg}")
        except Exception as e:
            st.error(f"❌ Upload failed: {e}")
