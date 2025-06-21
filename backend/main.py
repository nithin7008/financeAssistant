from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np  # Added for handling NaN and inf
from sqlalchemy import create_engine
import os
import shutil

app = FastAPI()

# Allow CORS for frontend (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to frontend URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database config
host = "db"
port = "3306"
user = "user"
password = "password"
database = "testdb"
engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
        df = df.replace({np.nan: None, np.inf: None, -np.inf: None})  # ✅ Sanitize invalid floats
        return {"columns": list(df.columns), "data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": f"File '{file.filename}' uploaded successfully.", "path": save_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
