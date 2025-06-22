#!/bin/bash

docker compose -f docker-compose-db.yml up -d --build
docker compose -f docker-compose-backend.yml up -d --build
docker compose -f docker-compose-frontend.yml up -d --build
# docker compose -f docker-compose-ollama.yml up -d --build
# docker compose -f docker-compose-chromadb.yml up -d --build

