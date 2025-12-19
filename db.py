import sqlite3

DB_NAME = "bot.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        full_name TEXT NOT NULL,
        username TEXT NOT NULL,
        email TEXT,
        question TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        telegram_id INTEGER PRIMARY KEY,
        status TEXT NOT NULL,
        reminder_24h_sent INTEGER DEFAULT 0,
        reminder_1h_sent INTEGER DEFAULT 0
    )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)




    conn.commit()
    conn.close()
