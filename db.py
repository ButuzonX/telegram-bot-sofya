# import sqlite3

# DB_NAME = "bot.db"


# def get_connection():
#     return sqlite3.connect(DB_NAME)


# def init_db():
#     conn = get_connection()
#     cur = conn.cursor()

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS users (
#         telegram_id INTEGER PRIMARY KEY,
#         full_name TEXT,
#         username TEXT,
#         email TEXT,
#         status TEXT NOT NULL,
#         created_at TEXT NOT NULL
#     )       
#     """)            

#     #cur.execute("""
#     # CREATE TABLE IF NOT EXISTS users (
#     #     telegram_id INTEGER PRIMARY KEY,
#     #     full_name TEXT NOT NULL,
#     #     username TEXT NOT NULL,
#     #     email TEXT,
#     #     question TEXT
#     # )
#     #""")

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS payments (
#         telegram_id INTEGER PRIMARY KEY,
#         status TEXT NOT NULL,
#         reminder_24h_sent INTEGER DEFAULT 0,
#         reminder_1h_sent INTEGER DEFAULT 0
#     )
#     """)


#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS settings (
#         key TEXT PRIMARY KEY,
#         value TEXT
#     )
#     """)




#     conn.commit()
#     conn.close()


import sqlite3
from datetime import datetime

DB_NAME = "bot.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return column in [row[1] for row in cur.fetchall()]


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # базовая таблица (если БД пустая)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        full_name TEXT,
        username TEXT,
        email TEXT
    )
    """)

    # миграция: status
    if not column_exists(cur, "users", "status"):
        cur.execute("ALTER TABLE users ADD COLUMN status TEXT")
        cur.execute("UPDATE users SET status = 'зашёл в бота' WHERE status IS NULL")

    # миграция: created_at
    if not column_exists(cur, "users", "created_at"):
        cur.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
        cur.execute(
            "UPDATE users SET created_at = ? WHERE created_at IS NULL",
            (datetime.utcnow().isoformat(),)
        )

    # payments
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        telegram_id INTEGER PRIMARY KEY,
        status TEXT NOT NULL,
        reminder_24h_sent INTEGER DEFAULT 0,
        reminder_1h_sent INTEGER DEFAULT 0
    )
    """)

    # settings
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    conn.commit()
    conn.close()

def update_user_status(user_id: int, status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET status=? WHERE telegram_id=?",
        (status, user_id)
    )
    conn.commit()
    conn.close()


