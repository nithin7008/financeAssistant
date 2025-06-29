import streamlit as st
import requests
from typing import List, Dict, Optional

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_available_questions():
    """Load all available questions from the backend"""
    try:
        # You'll need to define API_BASE_URL or import it
        API_BASE_URL = "http://backend:8000"  # Adjust this to your backend URL
        response = requests.get(f"{API_BASE_URL}/questions")
        if response.status_code == 200:
            data = response.json()
            return data.get("questions", [])
        else:
            st.warning("Could not load example questions")
            return []
    except Exception as e:
        st.warning(f"Error loading questions: {e}")
        return []

def create_simple_question_selector() -> Optional[str]:
    """
    Create a simple question selector with searchable dropdown
    """
    # Load questions
    available_questions = load_available_questions()
    
    if not available_questions:
        return st.text_input(
            "Enter your question:",
            placeholder="e.g., What is my total credit card debt?"
        )
    
    # Prepare options for selectbox
    question_options = ["Type your own question..."] + [
        f"{q['question']}" for q in available_questions
    ]
    
    # Create selectbox
    selected_option = st.selectbox(
        "Choose a question or select 'Type your own question':",
        options=question_options,
        index=0
    )
    
    if selected_option == "Type your own question...":
        return st.text_input(
            "Enter your question:",
            placeholder="e.g., What is my total credit card debt?"
        )
    else:
        # Extract the actual question from the formatted option
        for q in available_questions:
            if f"{q['question']}" == selected_option:
                # st.info(f"Selected: {q['question']}")
                return q['question']
    
    return None
