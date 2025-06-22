import json
import os
from datetime import datetime

FEEDBACK_FILE = "/app/chromadb_data/user_feedback.json"

def save_feedback_to_json(feedback_entry: dict):
    """Append a feedback entry to the feedback JSON file."""
    try:
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, "r") as f:
                feedback_list = json.load(f)
        else:
            feedback_list = []
        # Assign an ID if not present
        feedback_entry["id"] = f"feedback_{len(feedback_list)}"
        feedback_entry["timestamp"] = datetime.utcnow().isoformat()
        feedback_list.append(feedback_entry)
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(feedback_list, f, indent=2)
        print("✅ Feedback saved to JSON")
    except Exception as e:
        print(f"❌ Failed to save feedback to JSON: {e}")

def load_feedback_to_chromadb(client, embedding_fn):
    """Load feedback from JSON and insert into ChromaDB collection."""
    try:
        with open(FEEDBACK_FILE, "r") as f:
            feedback_list = json.load(f)
        
        # Handle embedding function conflict gracefully
        try:
            # Try to get existing collection without embedding function
            collection = client.get_collection("user_feedback")
            print("📋 Using existing user_feedback collection")
        except:
            # Create new collection with embedding function
            collection = client.create_collection(
                name="user_feedback",
                embedding_function=embedding_fn
            )
            print("🆕 Created new user_feedback collection")
        
        for i, fb in enumerate(feedback_list):
            document = f"Question: {fb['question']}\nCorrected SQL: {fb['corrected_sql']}"
            collection.add(
                documents=[document],
                metadatas=[{
                    "type": "user_feedback",
                    "question": fb.get("question"),
                    "generated_sql": fb.get("generated_sql"),
                    "corrected_sql": fb.get("corrected_sql"),
                    "feedback": fb.get("feedback"),
                    "timestamp": fb.get("timestamp")
                }],
                ids=[fb.get("id", f"user_feedback_{i}")]
            )
        print(f"✅ Loaded {len(feedback_list)} feedback entries into ChromaDB.")
    except Exception as e:
        print(f"❌ Failed to load feedback into ChromaDB: {e}")
