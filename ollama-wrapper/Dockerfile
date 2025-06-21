FROM python:3.11-slim

WORKDIR /app

COPY main.py .

RUN pip install fastapi uvicorn pydantic

# Mount the host ollama binary and models folder at runtime

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
