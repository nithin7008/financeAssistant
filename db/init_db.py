import sqlite3
import os

DB_FILE = "/data/finance.db"
INIT_SQL_FILE = "init.sql"

def initialize_db():
    if not os.path.exists(DB_FILE):
        with open(INIT_SQL_FILE, "r") as f:
            sql_script = f.read()

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.executescript(sql_script)
        conn.commit()
        conn.close()
        print("Database initialized from init.sql")
    else:
        print("Database already exists")

if __name__ == "__main__":
    initialize_db()
