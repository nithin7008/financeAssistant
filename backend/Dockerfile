# Step 1: Base image
FROM python:3.10-slim

# Step 2: Set working directory
WORKDIR /app

# Step 3: Install system dependencies (only if needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libffi-dev \
    libpq-dev \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Step 4: Copy ONLY requirements first for cache efficiency
COPY requirements.txt .

# Step 5: Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Step 6: Copy the rest of the code
COPY . .

# Step 7: Command to run your app
# Expose port
EXPOSE 8000

# Run the FastAPI app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
