# Finance Assistant Application

## Overview

The Finance Assistant is a comprehensive financial data management system that leverages AI to provide natural language querying capabilities for personal finance data. Users can ask questions in plain English about their financial accounts, and the system converts these queries into SQL and returns meaningful results.

## Architecture

The application follows a microservices architecture with the following components:

### Core Services
- **Backend API** (FastAPI) - Main application logic and API endpoints
- **Frontend** (Streamlit) - User interface for interacting with the system
- **MySQL Database** - Stores financial account data and snapshots
- **ChromaDB** - Vector database for storing schemas, rules, examples, and user feedback
- **Ollama** - Local AI model service for natural language to SQL conversion

### Directory Structure
```
financeAssistant/
├── backend/
│   ├── main.py                 # Main FastAPI application
│   ├── initialize_chromadb.py  # ChromaDB initialization
│   ├── utils/
│   │   └── feedback_utils.py   # Feedback management utilities
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── main.py                 # Streamlit UI
│   ├── Dockerfile
│   └── requirements.txt
├── mysql/
│   └── init.sql               # Database schema
├── chromadb/
│   └── vector_store/          # Vector database storage
├── ollama/
│   ├── main.py
│   └── Dockerfile
├── db/
│   ├── accounts.xlsx          # Account master data
│   └── account_weekly_snapshot.xlsx  # Weekly balance snapshots
└── docker-compose files...
```

## Database Schema

### Tables

#### `accounts` Table
Stores master account information:
- `bank` (VARCHAR(100)) - Bank/Institution name
- `type` (ENUM) - Account type: 'credit', 'checking', 'stocks', 'crypto'
- `apr` (DECIMAL(5,2)) - Annual Percentage Rate (credit cards only)
- `credit_limit` (INTEGER) - Credit limit (credit cards only)
- `due_date_day` (INTEGER) - Payment due date (credit cards only)

#### `account_weekly_snapshot` Table
Stores weekly account balance snapshots:
- `bank` (VARCHAR(100)) - Bank/Institution name
- `type` (ENUM) - Account type
- `balance` (DECIMAL(10,2)) - Current balance
- `payment_due` (DECIMAL(10,2)) - Amount due for payment
- `last_updated_date` (DATETIME) - Snapshot timestamp

## Key Features

### 1. Natural Language to SQL Conversion
- Users can ask questions in plain English
- AI model (via Ollama) converts natural language to SQL queries
- Context-aware query generation using ChromaDB for schema information

### 2. Data Management
- Excel file upload and processing
- Automatic data cleaning and validation
- Real-time database updates

### 3. Feedback Learning System
- Users can provide feedback on generated SQL queries
- System learns from corrections and improves future responses
- Feedback stored in both JSON files and ChromaDB

### 4. Financial Data Analysis
- Account balance tracking
- Payment due monitoring
- Multi-account type support (credit, checking, stocks, crypto)

## API Endpoints

### Core Endpoints

#### `GET /tables`
Returns list of all database tables.

#### `GET /table/{table_name}`
Returns data from a specific table with columns and records.

#### `POST /query`
**Main AI Query Endpoint**
- Input: Natural language question
- Process: Converts to SQL using AI model and ChromaDB context
- Output: Generated SQL query

```json
{
  "question": "What's my total credit card debt?"
}
```

#### `POST /execute_sql`
Executes SQL query against the database.
```json
{
  "sql": "SELECT SUM(balance) FROM account_weekly_snapshot WHERE type='credit'"
}
```

#### `POST /feedback`
Saves user feedback for query improvements.
```json
{
  "question": "Original question",
  "generated_sql": "AI generated SQL",
  "corrected_sql": "User corrected SQL",
  "feedback": "good/bad"
}
```

### Utility Endpoints

#### `POST /upload`
Upload Excel files for data import.

#### `POST /reload_snapshots`
Reload account snapshots from Excel file.

## AI Integration

### ChromaDB Collections

1. **table_schemas** - Database schema information
2. **sql_rules** - SQL generation rules and best practices
3. **query_examples** - Example queries for context
4. **user_feedback** - User corrections and feedback

### Query Generation Process

1. **Feedback Check**: First checks if similar question has previous bad feedback with corrections
2. **Context Retrieval**: Retrieves relevant schemas, rules, and examples from ChromaDB
3. **AI Generation**: Sends context-rich prompt to Ollama model
4. **SQL Extraction**: Extracts clean SQL from AI response
5. **Execution**: Executes SQL against MySQL database

### Learning Mechanism

The system implements a feedback loop:
- Users can mark queries as "good" or "bad"
- For "bad" queries, users provide corrected SQL
- Future similar questions use corrected SQL instead of regenerating
- Continuous improvement through user interaction

## Data Flow

```
User Question → ChromaDB Context → AI Model → SQL Generation → Database Execution → Results
     ↓
User Feedback → ChromaDB Storage → Future Query Improvement
```

## Configuration

### Environment Variables
```env
# Database Configuration
DB_HOST=mysql
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=finance_db

# AI Model Configuration
OLLAMA_API_URL=http://ollama:11434/api/generate
MODEL_NAME=llama2

# ChromaDB Configuration
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
```

## Deployment

The application uses Docker Compose for orchestration:

```bash
# Start all services
./run.sh

# Or start individual services
docker-compose -f docker-compose-db.yml up -d
docker-compose -f docker-compose-backend.yml up -d
docker-compose -f docker-compose-frontend.yml up -d
docker-compose -f docker-compose-ollama.yml up -d
```

## Data Processing Features

### Excel Data Cleaning
- Automatic column name standardization (strip, lowercase)
- Null value handling ("null", "none", "nan" → NULL)
- Data type validation and conversion
- Missing value imputation for numeric fields

### Financial Data Validation
- Account type constraints
- Balance and payment validation
- Date format standardization
- Foreign key relationship enforcement

## Security Considerations

- CORS middleware configured for cross-origin requests
- SQL injection prevention through parameterized queries
- File upload validation and secure storage
- Environment variable configuration for sensitive data

## Use Cases

1. **Personal Finance Tracking**
   - "What's my total debt across all credit cards?"
   - "Show me accounts with balances over $1000"
   - "When is my next credit card payment due?"

2. **Financial Analysis**
   - "What's my net worth?"
   - "Compare my checking account balances over time"
   - "Which credit card has the highest utilization?"

3. **Data Management**
   - Upload new account data via Excel
   - Update weekly balance snapshots
   - Maintain account information

## Future Enhancements

- Multi-user support with authentication
- Advanced financial analytics and reporting
- Integration with bank APIs for real-time data
- Mobile application interface
- Advanced AI models for better query understanding
- Automated financial insights and recommendations

## Technical Stack

- **Backend**: FastAPI, SQLAlchemy, Pandas, NumPy
- **Frontend**: Streamlit
- **Database**: MySQL
- **Vector DB**: ChromaDB
- **AI**: Ollama (Local LLM)
- **Containerization**: Docker, Docker Compose
- **Data Processing**: Pandas, Excel integration

This Finance Assistant provides a powerful, AI-driven approach to personal finance management, making complex financial data accessible through natural language queries while continuously learning and improving from user interactions.
