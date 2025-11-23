import sqlite3
import os
from config import Config

# Connect to database
conn = sqlite3.connect(Config.DB_PATH)
cursor = conn.cursor()

# Check if is_banned column exists
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()
column_names = [col[1] for col in columns]

print("Current columns in users table:", column_names)

if 'is_banned' not in column_names:
    print("Adding is_banned column...")
    cursor.execute("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0")
    conn.commit()
    print("is_banned column added successfully!")
else:
    print("is_banned column already exists")

# Insert test customer
print("\nInserting test customer...")
cursor.execute('''
    INSERT OR REPLACE INTO users (line_user_id, name, phone_number, is_banned)
    VALUES (?, ?, ?, ?)
''', ('CUSTOMER_BAN_TEST', 'テスト顧客', '09012345678', 0))

cursor.execute('''
    INSERT OR REPLACE INTO users (line_user_id, name, phone_number, is_banned)
    VALUES (?, ?, ?, ?)
''', ('CUSTOMER_ALLOWED_TEST', '許可顧客', '09087654321', 0))

conn.commit()

# Verify
cursor.execute("SELECT * FROM users")
users = cursor.fetchall()
print("\nCurrent users in database:")
for user in users:
    print(user)

conn.close()
print("\nDatabase migration completed!")
