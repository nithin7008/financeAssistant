Finance Assistant Project Overview
• AI-Powered Financial Query System: Users ask natural language questions about their financial data (e.g., "What's my total credit card debt?"), and the system converts these to SQL queries using a local Ollama LLM model for privacy and control

• Multi-Layered Query Resolution Flow: The system follows a hierarchical approach - first checks for GOOD feedback (proven working queries), then BAD feedback corrections, then query examples, and finally generates new SQL via Ollama if no matches found

• RAG (Retrieval-Augmented Generation) Implementation: Uses ChromaDB vector database to store and retrieve contextual information including database schemas, SQL rules, query examples, and user feedback to enhance AI prompt generation

• Smart Feedback Learning System: Implements a continuous learning loop where users can mark queries as "good/bad" and provide SQL corrections, which are stored in ChromaDB and prioritized for future similar questions using semantic similarity matching

• Dynamic Similarity Thresholds: Uses intelligent threshold calculation based on question length and characteristics - shorter questions (≤3 words) use 0.85 threshold, medium questions use 0.75, longer questions use 0.65 for better matching accuracy

• Context-Rich Prompt Engineering: Constructs comprehensive prompts by combining database schemas, SQL rules, example queries, and user feedback corrections from ChromaDB collections, then sends to Ollama model with specific parameters (temperature=0.1, top_p=0.9)

• Multi-Database Architecture: Integrates MySQL for structured financial data (accounts, snapshots), ChromaDB for vector embeddings and semantic search, and uses SentenceTransformer embeddings for natural language processing

• Excel-to-Database Pipeline: Automatically processes uploaded Excel files with data cleaning (normalization, null handling, validation) and loads account information and weekly balance snapshots into MySQL database

• Microservices Container Architecture: Deployed using Docker Compose with separate services for FastAPI backend, Streamlit frontend, MySQL database, ChromaDB vector store, and Ollama AI model service

• Financial Data Management: Supports multiple account types (credit cards, checking, stocks, crypto) with features like balance tracking, payment due monitoring, and real-time financial analysis through natural language queries