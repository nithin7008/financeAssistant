import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import shutil
import subprocess
import requests
import re
from dotenv import load_dotenv
import chromadb
from initialize_chromadb import initialize_finance_chromadb
from datetime import datetime
import uuid

# Load environment variables from .env file
load_dotenv()

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")
MODEL_NAME = os.getenv("MODEL_NAME")

host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Database config
engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")

client = chromadb.HttpClient(host="chromadb", port=8000)

def clean_excel_data(df):
    df.columns = df.columns.str.strip().str.lower()
    df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)  # Trim strings
    df = df.applymap(lambda x: None if str(x).lower() in ["null", "none", "nan"] else x)
    return df


def load_accounts_from_excel(filepath: str):
    df = pd.read_excel(filepath)
    df = clean_excel_data(df)

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM accounts"))  # Truncate
        df.to_sql("accounts", con=conn, if_exists="append", index=False)

def load_account_snapshots_from_excel(filepath: str):
    df = pd.read_excel(filepath)
    df = clean_excel_data(df)

    # Fill payment_due with 0 if null
    df["payment_due"] = df["payment_due"].fillna(0)

    # Fill balance with 0 if null (optional fallback)
    df["balance"] = df["balance"].fillna(0)

    # Drop rows with missing required keys
    df = df.dropna(subset=["bank", "type", "last_updated_date"], how="any")

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM account_weekly_snapshot"))
        df.to_sql("account_weekly_snapshot", con=conn, if_exists="append", index=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        load_accounts_from_excel("db/accounts.xlsx")
        load_account_snapshots_from_excel("db/account_weekly_snapshot.xlsx")
        initialize_finance_chromadb()
        print("✅ Backend and ChromaDB initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
    yield


app = FastAPI(lifespan=lifespan)


# Allow CORS for frontend (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/reload_snapshots")
async def reload_snapshots():
    try:
        load_account_snapshots_from_excel("db/account_weekly_snapshot.xlsx")
        return {"message": "Snapshots reloaded from Excel successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tables")
def get_tables():
    try:
        tables_df = pd.read_sql("SHOW TABLES", engine)
        table_names = [t[0] for t in tables_df.values]
        return {"tables": table_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/table/{table_name}")
def get_table_data(table_name: str):
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
        df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
        return {"columns": list(df.columns), "data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- File upload functionality ----------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": f"File '{file.filename}' uploaded successfully.", "path": save_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- AI-powered SQL generation ----------
class QueryRequest(BaseModel):
    question: str

def call_ollama(prompt: str) -> str:
    try:
        result = subprocess.run(
            ["ollama", "run", MODEL_NAME, prompt],
            capture_output=True,
            text=True,
            check=True
        )
        response = result.stdout.strip()

        # Clean up markdown/code formatting if present
        if "```sql" in response:
            response = response.split("```sql")[-1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[-1].strip()

        return response
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {e.stderr or str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected Ollama error: {str(e)}")

@app.post("/query")
async def query_to_sql(request: QueryRequest):
    nl_query = request.question
    client = chromadb.HttpClient(host="chromadb", port=8000)
    feedback_collection = client.get_or_create_collection("user_feedback")

    try:
        # 1. Check user_feedback collection for previous 'bad' feedback matching this question
        search_results = feedback_collection.query(
            query_texts=[nl_query],
            n_results=1,
            where={"feedback": "bad"}
        )

        if search_results and search_results["documents"] and search_results["documents"][0]:
            # Found a matching prior feedback
            corrected_sql = search_results["metadatas"][0][0].get("corrected_sql")
            if corrected_sql:
                print("💡 Returning corrected SQL from user feedback")
                return {"sql": corrected_sql}

        # 2. If no feedback match found, proceed to generate SQL from Ollama
        schema_collection = client.get_collection("table_schemas")
        rules_collection = client.get_collection("sql_rules")
        examples_collection = client.get_collection("query_examples")

        schemas = [d for d in schema_collection.get()["documents"]]
        rules = [d for d in rules_collection.get()["documents"]]
        examples = [d for d in examples_collection.get()["documents"]]

        prompt = f"""You are a helpful financial assistant that converts natural language to SQL queries.

## SCHEMA:
{chr(10).join(schemas)}

## RULES:
{chr(10).join(rules)}

## EXAMPLES:
{chr(10).join(examples)}

## USER QUESTION:
{nl_query}

Return only the SQL query, no explanation. Use table aliases if needed, always use the latest snapshot from account_weekly_snapshot using:
WHERE last_updated_date = (SELECT MAX(last_updated_date) FROM account_weekly_snapshot)
"""

        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        full_response = response.json()["response"]

        print("\n📥 Model Response:")
        print(full_response)

        code_block = re.search(r"```(?:sql)?\s*(.*?)```", full_response, re.DOTALL)
        if code_block:
            generated_sql = code_block.group(1).strip()
        else:
            fallback = re.search(r"(SELECT\s.+?;)", full_response, re.IGNORECASE | re.DOTALL)
            if fallback:
                generated_sql = fallback.group(1).strip()
            else:
                raise ValueError("Could not find SQL query in model response.")

        return {"sql": generated_sql}

    except requests.exceptions.RequestException as req_err:
        print(f"❌ Ollama request error: {req_err}")
        raise HTTPException(status_code=500, detail=f"Ollama request error: {req_err}")

    except Exception as e:
        print(f"❌ General error in query_to_sql: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# ---------- Feedback collection ----------
class FeedbackModel(BaseModel):
    question: str
    generated_sql: str
    corrected_sql: str
    feedback: str

@app.post("/feedback")
async def save_feedback(feedback: FeedbackModel):
    try:
        feedback_collection = client.get_collection("user_feedback")
        
        feedback_doc = f"Q: {feedback.question}\nOriginal SQL: {feedback.generated_sql}\nCorrected SQL: {feedback.corrected_sql}\nFeedback: {feedback.feedback}\nTime: {datetime.utcnow().isoformat()}"

        feedback_collection.add(
            documents=[feedback_doc],
            metadatas=[{
                "question": feedback.question,
                "generated_sql": feedback.generated_sql,
                "corrected_sql": feedback.corrected_sql,
                "feedback": feedback.feedback,
                "timestamp": datetime.utcnow().isoformat()
            }],
            ids=[str(uuid.uuid4())]
        )
        return {"message": "Feedback saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {str(e)}")
    
# ---------- SQL Execution ----------
class SQLQueryRequest(BaseModel):
    sql: str

@app.post("/execute_sql")
async def execute_sql(query: SQLQueryRequest):
    try:
        sql_lower = query.sql.lower()
        df = pd.read_sql(sql_lower, engine)
        df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
        return {"columns": list(df.columns), "data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL execution error: {str(e)}")
