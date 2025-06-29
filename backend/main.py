import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import shutil
import requests
import re
from dotenv import load_dotenv
import chromadb
from initialize_chromadb import initialize_finance_chromadb
from datetime import datetime
import uuid
from utils.feedback_utils import save_feedback_to_json, load_feedback_to_chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from utils.logging_utils import setup_logging, get_logger, set_log_level, get_current_log_level
from utils.question_utils import get_all_questions

# Load environment variables from .env file
load_dotenv()

logger = setup_logging()

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")
MODEL_NAME = os.getenv("MODEL_NAME")
ST_MODEL_NAME = os.getenv("ST_MODEL_NAME")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

embedding_fn = SentenceTransformerEmbeddingFunction(model_name=ST_MODEL_NAME)

# Database config
engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")

client = chromadb.HttpClient(host="chromadb", port=8000)


def clean_excel_data(df):
    df.columns = df.columns.str.strip().str.lower()
    df = df.map(lambda x: str(x).strip() if isinstance(x, str) else x)
    df = df.map(lambda x: None if str(x).lower() in ["null", "none", "nan"] else x)
    return df


def load_accounts_from_excel(filepath: str):
    df = pd.read_excel(filepath)
    df = clean_excel_data(df)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM accounts"))
        df.to_sql("accounts", con=conn, if_exists="append", index=False)


def load_account_snapshots_from_excel(filepath: str):
    df = pd.read_excel(filepath)
    df = clean_excel_data(df)
    df["payment_due"] = df["payment_due"].fillna(0)
    df["balance"] = df["balance"].fillna(0)
    df = df.dropna(subset=["bank", "type", "last_updated_date"], how="any")
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM account_weekly_snapshot"))
        df.to_sql("account_weekly_snapshot", con=conn, if_exists="append", index=False)


def normalize_question(question):
    """Normalize question text for better matching"""
    if not question:
        return ""
    import string
    normalized = question.strip().lower()
    normalized = normalized.translate(str.maketrans('', '', string.punctuation))
    normalized = ' '.join(normalized.split())
    return normalized


def get_dynamic_threshold(question1, question2):
    """Calculate dynamic threshold based on question characteristics"""
    # Shorter questions tend to have higher variance in embeddings
    avg_length = (len(question1.split()) + len(question2.split())) / 2
    
    if avg_length <= 3:  # Very short questions like "401k balance"
        return 0.85
    elif avg_length <= 6:  # Medium questions
        return 0.75
    else:  # Longer questions
        return 0.65


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        load_accounts_from_excel("db/accounts.xlsx")
        load_account_snapshots_from_excel("db/account_weekly_snapshot.xlsx")
        initialize_finance_chromadb()
        load_feedback_to_chromadb(client, embedding_fn)
        logger.info("Backend and ChromaDB initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
    yield


app = FastAPI(lifespan=lifespan)


# Allow CORS for frontend (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#  ----- Questions Dropdown -----
@app.get("/questions")
async def get_questions():
    """
    Get all available questions from examples and user feedback
    """
    try:
        questions = get_all_questions()
        return {
            "questions": questions,
            "total": len(questions)
        }
    except Exception as e:
        logger.error(f"Error getting questions: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving questions: {str(e)}")


@app.post("/reload_snapshots")
async def reload_snapshots():
    try:
        load_account_snapshots_from_excel("db/account_weekly_snapshot.xlsx")
        logger.info("Snapshots reloaded from Excel successfully")
        return {"message": "Snapshots reloaded from Excel successfully."}
    except Exception as e:
        logger.error(f"Failed to reload snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tables")
def get_tables():
    try:
        tables_df = pd.read_sql("SHOW TABLES", engine)
        table_names = [t[0] for t in tables_df.values]
        logger.debug(f"Retrieved tables: {table_names}")
        return {"tables": table_names}
    except Exception as e:
        logger.error(f"Failed to get tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/table/{table_name}")
def get_table_data(table_name: str):
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
        df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
        logger.debug(f"Retrieved {len(df)} rows from table {table_name}")
        return {"columns": list(df.columns), "data": df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"Failed to get table data for {table_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------- File upload functionality ----------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File '{file.filename}' uploaded successfully to {save_path}")
        return {"message": f"File '{file.filename}' uploaded successfully.", "path": save_path}
    except Exception as e:
        logger.error(f"Failed to upload file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------- AI-powered SQL generation ----------
def load_prompt_template(template_name):
    """Load prompt template from file"""
    template_path = os.path.join("prompts", f"{template_name}.txt")
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        logger.error(f"Prompt template not found: {template_path}")
        raise HTTPException(status_code=500, detail="Prompt template missing")


class QueryRequest(BaseModel):
    question: str

class SmartQueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    sql: str
    source: str
    confidence: str

class SmartQueryResponse(BaseModel):
    question: str
    source: str
    confidence: str
    sql: str = None
    columns: list = None
    data: list = None
    error: str = None

@app.post("/query", response_model=QueryResponse)
async def query_to_sql(request: QueryRequest):
    nl_query = request.question
    logger.info(f"Processing query: '{nl_query}'")
    
    # Track the source of the SQL for feedback storage decisions
    sql_source = "unknown"
    confidence = "low"  # Default to low confidence
    
    try:
        # Get user_feedback collection - handle embedding function gracefully
        try:
            feedback_collection = client.get_collection("user_feedback")
            logger.debug("Using existing user_feedback collection")
        except Exception as e:
            logger.warning(f"Could not get user_feedback collection: {e}")
            feedback_collection = None

        # Step 1: Check for GOOD feedback first (proven working queries)
        logger.debug("STEP 1A: Checking for good feedback...")
        if feedback_collection:
            try:
                good_results = feedback_collection.query(
                    query_texts=[nl_query],
                    where={"feedback": "good"},
                    n_results=1
                )
                
                if good_results and good_results["documents"] and good_results["documents"][0]:
                    metadata = good_results["metadatas"][0][0]
                    distance = good_results["distances"][0][0] if good_results.get("distances") and good_results["distances"][0] else None
                    
                    logger.debug(f"Found good feedback entry")
                    logger.debug(f"Similarity distance: {distance}")
                    logger.debug(f"Good feedback question: '{metadata.get('question', 'N/A')}'")
                    
                    # Check for exact match with better normalization
                    feedback_question_normalized = normalize_question(metadata.get('question', ''))
                    current_question_normalized = normalize_question(nl_query)
                    is_exact_match = feedback_question_normalized == current_question_normalized
                    
                    logger.debug(f"Normalized good feedback: '{feedback_question_normalized}'")
                    logger.debug(f"Normalized current: '{current_question_normalized}'")
                    logger.debug(f"Good feedback exact match: {is_exact_match}")
                    
                    # Use higher confidence threshold for good queries (0.25 instead of dynamic)
                    good_threshold = 0.25
                    logger.debug(f"Good feedback threshold: {good_threshold}")
                    
                    if (metadata.get("generated_sql") and
                        (is_exact_match or (distance is not None and distance < good_threshold))):
                        logger.info("SOURCE: GOOD_FEEDBACK - Returning proven working SQL")
                        logger.debug(f"Good SQL: {metadata.get('generated_sql')}")
                        sql_source = "good_feedback"
                        confidence = "high"
                        return QueryResponse(sql=metadata["generated_sql"], source=sql_source, confidence=confidence)
                    else:
                        logger.debug(f"Good feedback not similar enough (distance: {distance}, threshold: {good_threshold})")
                else:
                    logger.debug("No good feedback entries found")
                    
            except Exception as e:
                logger.warning(f"Error querying good feedback: {e}")

        # Step 1B: Check for BAD feedback (corrected queries)
        logger.debug("STEP 1B: Checking for bad feedback corrections...")
        if feedback_collection:
            try:
                bad_results = feedback_collection.query(
                    query_texts=[nl_query],
                    where={"feedback": "bad"},
                    n_results=1
                )
                
                if bad_results and bad_results["documents"] and bad_results["documents"][0]:
                    metadata = bad_results["metadatas"][0][0]
                    distance = bad_results["distances"][0][0] if bad_results.get("distances") and bad_results["distances"][0] else None
                    
                    logger.debug(f"Found bad feedback entry with corrected_sql: {bool(metadata.get('corrected_sql'))}")
                    logger.debug(f"Similarity distance: {distance}")
                    logger.debug(f"Bad feedback question: '{metadata.get('question', 'N/A')}'")
                    
                    # Check for exact match with better normalization
                    feedback_question_normalized = normalize_question(metadata.get('question', ''))
                    current_question_normalized = normalize_question(nl_query)
                    is_exact_match = feedback_question_normalized == current_question_normalized
                    
                    logger.debug(f"Normalized bad feedback: '{feedback_question_normalized}'")
                    logger.debug(f"Normalized current: '{current_question_normalized}'")
                    logger.debug(f"Bad feedback exact match: {is_exact_match}")
                    
                    # Calculate dynamic threshold for bad feedback
                    dynamic_threshold = get_dynamic_threshold(metadata.get('question', ''), nl_query)
                    logger.debug(f"Bad feedback dynamic threshold: {dynamic_threshold}")
                    
                    if (metadata.get("corrected_sql") and
                        (is_exact_match or (distance is not None and distance < dynamic_threshold))):
                        logger.info("SOURCE: BAD_FEEDBACK_CORRECTED - Returning corrected SQL from user feedback")
                        logger.debug(f"Corrected SQL: {metadata.get('corrected_sql')}")
                        sql_source = "bad_feedback_corrected"
                        confidence = "high"
                        return QueryResponse(sql=metadata["corrected_sql"], source=sql_source, confidence=confidence)
                    else:
                        if not metadata.get("corrected_sql"):
                            logger.debug(f"Skipping bad feedback - missing corrected_sql")
                        elif not is_exact_match and (distance is None or distance >= dynamic_threshold):
                            logger.debug(f"Skipping bad feedback - not similar enough (distance: {distance}, threshold: {dynamic_threshold})")
                else:
                    logger.debug("No bad feedback entries found")
                    
            except Exception as e:
                logger.warning(f"Error querying bad feedback: {e}")
        else:
            logger.debug("Feedback collection not available")

        # Step 2: Try to find similar examples in query_examples collection
        logger.debug("STEP 2: Checking query_examples collection...")
        try:
            examples_collection = client.get_collection("query_examples")
            example_results = examples_collection.query(
                query_texts=[nl_query],
                n_results=1
            )
            
            if example_results and example_results["documents"] and example_results["documents"][0]:
                example_distance = example_results["distances"][0][0] if example_results.get("distances") and example_results["distances"][0] else None
                example_metadata = example_results["metadatas"][0][0] if example_results["metadatas"][0] else {}
                
                logger.debug(f"Found matching example - distance: {example_distance}")
                logger.debug(f"Example question: '{example_metadata.get('question', 'N/A')}'")
                
                # Check for exact match with better normalization for examples
                example_question_normalized = normalize_question(example_metadata.get('question', ''))
                current_question_normalized = normalize_question(nl_query)
                is_exact_match_example = example_question_normalized == current_question_normalized
                
                logger.debug(f"Normalized example: '{example_question_normalized}'")
                logger.debug(f"Normalized current: '{current_question_normalized}'")
                logger.debug(f"Example exact match: {is_exact_match_example}")
                
                # Calculate dynamic threshold for examples
                example_dynamic_threshold = get_dynamic_threshold(example_metadata.get('question', ''), nl_query)
                logger.debug(f"Example dynamic threshold: {example_dynamic_threshold}")
                
                if ("sql" in example_metadata and
                    (is_exact_match_example or (example_distance is not None and example_distance < example_dynamic_threshold))):
                    logger.info("SOURCE: QUERY_EXAMPLES - Returning SQL from examples collection")
                    logger.debug(f"Example SQL: {example_metadata['sql']}")
                    sql_source = "query_examples"
                    confidence = "high"
                    return QueryResponse(sql=example_metadata["sql"], source=sql_source, confidence=confidence)
                else:
                    if "sql" not in example_metadata:
                        logger.debug("Example found but no SQL in metadata")
                    elif not is_exact_match_example and (example_distance is None or example_distance >= example_dynamic_threshold):
                        logger.debug(f"Skipping example - not similar enough (distance: {example_distance}, threshold: {example_dynamic_threshold})")
            else:
                logger.debug("No matching examples found")
                
        except Exception as e:
            logger.warning(f"Error querying examples collection: {e}")

        # Step 3: If no feedback match or example found, proceed to generate SQL from Ollama
        logger.debug("STEP 3: Generating SQL using Ollama...")
        schema_collection = client.get_collection("table_schemas")
        rules_collection = client.get_collection("sql_rules")
        examples_collection = client.get_collection("query_examples")

        schemas = [d for d in schema_collection.get()["documents"]]
        rules = [d for d in rules_collection.get()["documents"]]
        examples = [d for d in examples_collection.get()["documents"]]

        # Get user feedback/corrections
        user_feedbacks = []
        try:
            feedback_collection = client.get_collection("user_feedback")
            feedback_results = feedback_collection.get()
            user_feedbacks = [d for d in feedback_results["documents"]]
        except Exception as e:
            logger.warning(f"Could not retrieve feedback: {e}")
            user_feedbacks = ["No previous corrections available"]

        prompt_template = load_prompt_template("sql_generation_prompt")
        prompt = prompt_template.format(
            schemas=chr(10).join(schemas),
            rules=chr(10).join(rules),
            examples=chr(10).join(examples),
            user_feedbacks=chr(10).join(user_feedbacks),
            nl_query=nl_query
        )

        logger.debug("Sending request to Ollama...")
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": 6144,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 200
                }
            }
        )
        response.raise_for_status()
        full_response = response.json()["response"]
        logger.info("SOURCE: OLLAMA - Generated SQL using AI model")
        logger.debug(f"Model Response: {full_response}")

        code_block = re.search(r"```(?:sql)?\s*(.*?)```", full_response, re.DOTALL)
        if code_block:
            generated_sql = code_block.group(1).strip()
        else:
            fallback = re.search(r"(SELECT\s.+?;)", full_response, re.IGNORECASE | re.DOTALL)
            if fallback:
                generated_sql = fallback.group(1).strip()
            else:
                raise ValueError("Could not find SQL query in model response.")

        logger.debug(f"Final SQL: {generated_sql}")
        sql_source = "ollama_generated"
        confidence = "low" 
        return QueryResponse(sql=generated_sql, source=sql_source, confidence=confidence)

    except requests.exceptions.RequestException as req_err:
        logger.error(f"Ollama request error: {req_err}")
        raise HTTPException(status_code=500, detail=f"Ollama request error: {req_err}")
    except Exception as e:
        logger.error(f"General error in query_to_sql: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/smart_query", response_model=SmartQueryResponse)
async def smart_query(request: SmartQueryRequest):
    """
    Smart query endpoint that:
    - For high confidence queries: auto-executes and returns results only
    - For low confidence queries: returns SQL for user review
    """
    try:
        # First get the SQL and confidence from the existing query logic
        query_result = await query_to_sql(QueryRequest(question=request.question))
        
        response = SmartQueryResponse(
            question=request.question,
            source=query_result.source,
            confidence=query_result.confidence
        )
        
        if query_result.confidence == "high":
            # High confidence: auto-execute and return results
            logger.info(f"High confidence query - auto-executing SQL from {query_result.source}")
            try:
                # Execute the SQL
                sql_lower = query_result.sql.lower()
                df = pd.read_sql(sql_lower, engine)
                df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
                
                response.columns = list(df.columns)
                response.data = df.to_dict(orient="records")
                logger.info(f"High confidence query executed successfully, returned {len(df)} rows")
                
            except Exception as e:
                logger.error(f"Error executing high confidence SQL: {e}")
                response.error = f"Error executing query: {str(e)}"
                # Fall back to showing SQL for user to fix
                response.sql = query_result.sql
                response.confidence = "low"
        else:
            # Low confidence: return SQL for user review
            logger.info(f"Low confidence query - returning SQL for user review")
            response.sql = query_result.sql
            
        return response
        
    except Exception as e:
        logger.error(f"Error in smart_query: {e}")
        return SmartQueryResponse(
            question=request.question,
            source="error",
            confidence="low",
            error=f"Error processing query: {str(e)}"
        )

# ---------- Feedback collection ----------
class FeedbackModel(BaseModel):
    question: str
    generated_sql: str
    corrected_sql: str
    feedback: str

@app.post("/feedback")
async def save_feedback(feedback: FeedbackModel):
    try:
        # Get or create feedback collection with proper embedding function
        try:
            feedback_collection = client.get_collection("user_feedback")
        except:
            # If collection doesn't exist, create it with embedding function
            feedback_collection = client.create_collection("user_feedback", embedding_function=embedding_fn)
            logger.info("Created new user_feedback collection for feedback")

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

        save_feedback_to_json(feedback.dict())
        logger.info(f"Feedback saved successfully for query: '{feedback.question}'")
        return {"message": "Feedback saved successfully."}
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {str(e)}")

# ---------- SQL Execution ----------
class SQLQueryRequest(BaseModel):
    sql: str

@app.post("/execute_sql")
async def execute_sql(query: SQLQueryRequest):
    try:
        sql_lower = query.sql.lower()
        logger.debug(f"🔍 Executing SQL: {sql_lower}")
        df = pd.read_sql(sql_lower, engine)
        df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
        logger.info(f"SQL executed successfully, returned {len(df)} rows")
        return {"columns": list(df.columns), "data": df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"SQL execution error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"SQL execution error: {str(e)}")

# --------- LOG_LEVEL ----------
@app.get("/log_level")
def get_log_level():
    """Get current log level"""
    return get_current_log_level()

class LogLevelRequest(BaseModel):
    level: str

@app.post("/log_level")
def set_log_level_endpoint(request: LogLevelRequest):
    """Set log level dynamically"""
    try:
        level = set_log_level(request.level)
        logger.info(f"Log level changed to: {level}")
        return {"message": f"Log level set to {level}", "log_level": level}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set log level: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set log level: {str(e)}")