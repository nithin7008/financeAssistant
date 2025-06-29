import json
import os
from typing import List, Dict
from utils.logging_utils import get_logger

logger = get_logger(__name__)

def get_all_questions() -> List[Dict[str, str]]:
    """
    Extract all questions from examples.json and user_feedback.json
    Returns list of dictionaries with question and source
    """
    questions = []
    
    # Check for examples.json (might be in different locations)
    examples_paths = [
        "/app/chromadb_data/examples.json",
        "/app/backend/chromadb_data/examples.json",
        "chromadb_data/examples.json",
        "backend/chromadb_data/examples.json"
    ]
    
    # Load from examples.json
    for examples_path in examples_paths:
        if os.path.exists(examples_path):
            try:
                with open(examples_path, "r") as f:
                    examples_data = json.load(f)
                    if isinstance(examples_data, list):
                        for item in examples_data:
                            if isinstance(item, dict) and "question" in item:
                                questions.append({
                                    "question": item["question"],
                                    "source": "examples",
                                    "type": "example"
                                })
                    elif isinstance(examples_data, dict) and "examples" in examples_data:
                        for item in examples_data["examples"]:
                            if isinstance(item, dict) and "question" in item:
                                questions.append({
                                    "question": item["question"],
                                    "source": "examples",
                                    "type": "example"
                                })
                logger.info(f"Loaded {len([q for q in questions if q['source'] == 'examples'])} questions from examples.json")
                break
            except Exception as e:
                logger.warning(f"Could not load examples from {examples_path}: {e}")
    
    # Load from user_feedback.json
    feedback_path = "/app/chromadb_data/user_feedback.json"
    if not os.path.exists(feedback_path):
        feedback_path = "backend/chromadb_data/user_feedback.json"
    
    if os.path.exists(feedback_path):
        try:
            with open(feedback_path, "r") as f:
                feedback_data = json.load(f)
                for item in feedback_data:
                    if isinstance(item, dict) and "question" in item:
                        # Only include questions with good feedback or unique questions
                        feedback_type = item.get("feedback", "unknown")
                        questions.append({
                            "question": item["question"],
                            "source": "user_feedback",
                            "type": f"feedback_{feedback_type}",
                            "feedback": feedback_type
                        })
            logger.info(f"Loaded {len([q for q in questions if q['source'] == 'user_feedback'])} questions from user_feedback.json")
        except Exception as e:
            logger.warning(f"Could not load user feedback: {e}")
    
    # Remove duplicates while preserving order
    seen_questions = set()
    unique_questions = []
    for q in questions:
        question_lower = q["question"].lower().strip()
        if question_lower not in seen_questions:
            seen_questions.add(question_lower)
            unique_questions.append(q)
    
    # Sort by source (examples first, then good feedback, then other feedback)
    def sort_key(item):
        if item["source"] == "examples":
            return (0, item["question"])
        elif item["source"] == "user_feedback" and item.get("feedback") == "good":
            return (1, item["question"])
        else:
            return (2, item["question"])
    
    unique_questions.sort(key=sort_key)
    
    logger.info(f"Total unique questions available: {len(unique_questions)}")
    return unique_questions
