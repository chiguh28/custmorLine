import sqlite3
import os
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(os.path.dirname(Config.DB_PATH)):
        os.makedirs(os.path.dirname(Config.DB_PATH))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Friends table (Customer Bot)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS friends (
            user_id TEXT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    # Therapist state table (Therapist Bot)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS therapist_state (
            user_id TEXT PRIMARY KEY,
            state TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized.")

def add_friend(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO friends (user_id, is_active) VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET is_active=1, added_at=CURRENT_TIMESTAMP
        ''', (user_id,))
        conn.commit()
    finally:
        conn.close()

def remove_friend(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE friends SET is_active=0 WHERE user_id = ?', (user_id,))
        conn.commit()
    finally:
        conn.close()

def get_active_friends():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT user_id FROM friends WHERE is_active=1')
        friends = [row['user_id'] for row in cursor.fetchall()]
        return friends
    finally:
        conn.close()

def set_therapist_state(user_id, state):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO therapist_state (user_id, state) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET state=?, updated_at=CURRENT_TIMESTAMP
        ''', (user_id, state, state))
        conn.commit()
    finally:
        conn.close()

def get_therapist_state(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT state FROM therapist_state WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return row['state'] if row else None
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
