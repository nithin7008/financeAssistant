from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess

app = FastAPI()

class QueryRequest(BaseModel):
    question: str

@app.post("/generate_sql")
async def generate_sql(request: QueryRequest):
    prompt = f"Generate a SQL query for the question: \"{request.question}\""
    try:
        result = subprocess.run(
            ["ollama", "run", "mistral", "--prompt", prompt],
            capture_output=True,
            text=True,
            check=True
        )
        sql = result.stdout.strip()
        return {"sql": sql}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {e.stderr.strip()}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
