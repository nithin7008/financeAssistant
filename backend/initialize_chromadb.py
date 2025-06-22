import json
import chromadb

def load_json_file(path):
    with open(path, "r") as f:
        return json.load(f)

def initialize_finance_chromadb():
    client = chromadb.HttpClient(host="chromadb", port=8000)

    schema_collection = client.get_or_create_collection("table_schemas")
    rules_collection = client.get_or_create_collection("sql_rules")
    examples_collection = client.get_or_create_collection("query_examples")
    feedback_collection = client.get_or_create_collection("user_feedback")

    # Load and insert schemas
    schemas = load_json_file("chromadb_data/schemas.json")
    for entry in schemas:
        schema_collection.add(
            documents=[entry["document"]],
            metadatas=[{k: entry[k] for k in entry if k not in ["document", "id"]}],
            ids=[entry["id"]]
        )

    # Load and insert rules
    rules = load_json_file("chromadb_data/rules.json")
    for rule in rules:
        rules_collection.add(
            documents=[rule["document"]],
            metadatas=[{k: rule[k] for k in rule if k not in ["document", "id"]}],
            ids=[rule["id"]]
        )

    # Load and insert example queries
    examples = load_json_file("chromadb_data/examples.json")
    for example in examples:
        examples_collection.add(
            documents=[example["document"]],
            metadatas=[{k: example[k] for k in example if k not in ["document", "id"]}],
            ids=[example["id"]]
        )

    print("✅ ChromaDB initialization complete from JSON files.")
    
    collections = client.list_collections()
    for collection in collections:
        count = client.get_or_create_collection(collection.name).count()
        print(f"🔎 Collection '{collection.name}' has {count} items")

