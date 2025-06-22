from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os
import shutil
import subprocess
import requests
import re
from dotenv import load_dotenv


load_dotenv()
app = FastAPI()

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")
MODEL_NAME = os.getenv("MODEL_NAME")

host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")


# Allow CORS for frontend (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database config
engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")


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
# UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
# os.makedirs(UPLOAD_DIR, exist_ok=True)
# @app.post("/upload")
# async def upload_file(file: UploadFile = File(...)):
#     save_path = os.path.join(UPLOAD_DIR, file.filename)
#     try:
#         with open(save_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
#         return {"message": f"File '{file.filename}' uploaded successfully.", "path": save_path}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# ---------- AI-powered SQL generation ----------
class QueryRequest(BaseModel):
    question: str

def call_ollama(prompt: str) -> str:
    try:
        result = subprocess.run(
            ["ollama", "run", "mistral", prompt],
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

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": MODEL_NAME,
                "prompt": f"Convert this to a SQL query. Only return the query without explanation:\n\n{nl_query}",
                "stream": False
            }
        )
        response.raise_for_status()
        full_response = response.json()["response"]

        # Try to extract SQL from triple backticks (```sql ... ```)
        code_block = re.search(r"```(?:sql)?\s*(.*?)```", full_response, re.DOTALL)
        if code_block:
            generated_sql = code_block.group(1).strip()
        else:
            # Fall back: find first SELECT ... ; statement
            fallback = re.search(r"(SELECT\s.+?;)", full_response, re.IGNORECASE | re.DOTALL)
            if fallback:
                generated_sql = fallback.group(1).strip()
            else:
                raise ValueError("Could not find SQL query in model response.")

        return {"sql": generated_sql}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model error: {str(e)}")


# ---------- SQL Execution ----------
class SQLQueryRequest(BaseModel):
    sql: str

@app.post("/execute_sql")
async def execute_sql(query: SQLQueryRequest):
    try:
        sql_lower = query.sql.lower()  # Convert SQL to lowercase
        df = pd.read_sql(sql_lower, engine)
        df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
        return {"columns": list(df.columns), "data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL execution error: {str(e)}")
