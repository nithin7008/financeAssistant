# Use a lightweight Python image because we'll run a simple Python script to init SQLite
FROM python:3.11-slim

WORKDIR /app

# Copy init.sql and initialization script
COPY init.sql .
COPY init_db.py .

# Install SQLite3 (comes pre-installed in most Python images, but just in case)
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

# Run initialization script on container start
CMD ["python", "init_db.py"]
