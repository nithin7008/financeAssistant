#!/bin/bash

# set -e  # exit on any failure

echo "Building and starting DB..."
docker-compose -f docker-compose-db.yml up --build -d

echo "Building and starting Backend..."
docker-compose -f docker-compose-backend.yml up --build -d

# Optional: uncomment when frontend is ready
# echo "Building and starting Frontend..."
# docker-compose -f docker-compose-frontend.yml up --build -d

echo "All services are up!"
