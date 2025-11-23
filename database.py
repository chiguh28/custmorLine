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

    # Users table (Customer info)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            line_user_id TEXT PRIMARY KEY,
            name TEXT,
            phone_number TEXT,
            is_banned BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Courses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            price INTEGER NOT NULL,
            description TEXT
        )
    ''')

    # Schedules table (Therapist availability)
    # status: 'available', 'unavailable', 'booked'
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, -- YYYY-MM-DD
            start_time TEXT NOT NULL, -- HH:MM
            end_time TEXT NOT NULL, -- HH:MM
            status TEXT DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Reservations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            course_id INTEGER NOT NULL,
            reservation_date TEXT NOT NULL, -- YYYY-MM-DD
            start_time TEXT NOT NULL, -- HH:MM
            end_time TEXT NOT NULL, -- HH:MM
            total_price INTEGER NOT NULL,
            status TEXT DEFAULT 'confirmed', -- confirmed, cancelled
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (line_user_id),
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
    ''')

    # Seed initial courses if empty
    cursor.execute('SELECT count(*) FROM courses')
    if cursor.fetchone()[0] == 0:
        courses = [
            ('スタンダードコース', 60, 6000, '基本のコースです。'),
            ('ロングコース', 90, 9000, 'ゆったりとしたコースです。'),
            ('ショートコース', 30, 3000, 'お試しのコースです。')
        ]
        cursor.executemany('INSERT INTO courses (name, duration_minutes, price, description) VALUES (?, ?, ?, ?)', courses)
        print("Seeded initial courses.")

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

# --- New Helper Functions ---

def get_user(line_user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE line_user_id = ?', (line_user_id,))
        return cursor.fetchone()
    finally:
        conn.close()

def upsert_user(line_user_id, name, phone_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (line_user_id, name, phone_number) VALUES (?, ?, ?)
            ON CONFLICT(line_user_id) DO UPDATE SET name=?, phone_number=?
        ''', (line_user_id, name, phone_number, name, phone_number))
        conn.commit()
    finally:
        conn.close()

def get_courses():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM courses')
        return cursor.fetchall()
    finally:
        conn.close()

def get_course(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM courses WHERE id = ?', (course_id,))
        return cursor.fetchone()
    finally:
        conn.close()

def upsert_course(course_id, name, duration, price, description):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if course_id:
            cursor.execute('''
                UPDATE courses 
                SET name = ?, duration_minutes = ?, price = ?, description = ?
                WHERE id = ?
            ''', (name, duration, price, description, course_id))
        else:
            cursor.execute('''
                INSERT INTO courses (name, duration_minutes, price, description)
                VALUES (?, ?, ?, ?)
            ''', (name, duration, price, description))
        conn.commit()
    finally:
        conn.close()

def get_reservations(start_date=None, end_date=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = '''
            SELECT r.*, u.name as user_name, c.name as course_name 
            FROM reservations r
            JOIN users u ON r.user_id = u.line_user_id
            JOIN courses c ON r.course_id = c.id
        '''
        params = []
        if start_date and end_date:
            query += ' WHERE r.reservation_date BETWEEN ? AND ?'
            params.extend([start_date, end_date])
        
        query += ' ORDER BY r.reservation_date, r.start_time'
        
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        conn.close()

def get_user_reservations(user_id):
    """Get all future reservations for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT r.*, c.name as course_name, c.duration_minutes
            FROM reservations r
            JOIN courses c ON r.course_id = c.id
            WHERE r.user_id = ? 
            AND r.status = 'confirmed'
            AND r.reservation_date >= date('now')
            ORDER BY r.reservation_date, r.start_time
        ''', (user_id,))
        return cursor.fetchall()
    finally:
        conn.close()

def create_reservation(user_id, course_id, date, start_time, end_time, total_price):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check for conflicts
        cursor.execute('''
            SELECT count(*) FROM reservations 
            WHERE reservation_date = ? 
            AND status = 'confirmed'
            AND (
                (start_time < ? AND end_time > ?) OR
                (start_time >= ? AND start_time < ?)
            )
        ''', (date, end_time, start_time, start_time, end_time))
        
        if cursor.fetchone()[0] > 0:
            return False # Conflict

        cursor.execute('''
            INSERT INTO reservations (user_id, course_id, reservation_date, start_time, end_time, total_price)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, course_id, date, start_time, end_time, total_price))
        conn.commit()
        return True
    finally:
        conn.close()

def get_monthly_income(year, month):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # SQLite strftime('%Y-%m', reservation_date)
        month_str = f"{year}-{month:02d}"
        cursor.execute('''
            SELECT SUM(total_price) FROM reservations 
            WHERE strftime('%Y-%m', reservation_date) = ? AND status = 'confirmed'
        ''', (month_str,))
        result = cursor.fetchone()[0]
        return result if result else 0
    finally:
        conn.close()

def get_therapist_schedules(start_date, end_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT * FROM schedules 
            WHERE date BETWEEN ? AND ?
        ''', (start_date, end_date))
        return cursor.fetchall()
    finally:
        conn.close()

def upsert_schedule(date, start_time, end_time, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if exists
        cursor.execute('SELECT id FROM schedules WHERE date = ?', (date,))
        row = cursor.fetchone()
        
        if row:
            cursor.execute('''
                UPDATE schedules 
                SET start_time = ?, end_time = ?, status = ?
                WHERE date = ?
            ''', (start_time, end_time, status, date))
        else:
            cursor.execute('''
                INSERT INTO schedules (date, start_time, end_time, status)
                VALUES (?, ?, ?, ?)
            ''', (date, start_time, end_time, status))
        conn.commit()
    finally:
        conn.close()

# --- Customer Management Functions ---

def get_all_customers():
    """Get all customers with their booking statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT 
                u.line_user_id,
                u.name,
                u.phone_number,
                u.is_banned,
                u.created_at,
                COUNT(r.id) as reservation_count,
                MAX(r.reservation_date) as last_reservation_date
            FROM users u
            LEFT JOIN reservations r ON u.line_user_id = r.user_id
            GROUP BY u.line_user_id
            ORDER BY u.created_at DESC
        ''')
        return cursor.fetchall()
    finally:
        conn.close()

def update_customer(line_user_id, name=None, phone_number=None, is_banned=None):
    """Update customer information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Build dynamic update query based on provided parameters
        updates = []
        params = []
        
        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if phone_number is not None:
            updates.append('phone_number = ?')
            params.append(phone_number)
        if is_banned is not None:
            updates.append('is_banned = ?')
            params.append(1 if is_banned else 0)
        
        if not updates:
            return False
        
        params.append(line_user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE line_user_id = ?"
        
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def delete_customer(line_user_id):
    """Delete customer and all their reservations"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Delete reservations first (foreign key constraint)
        cursor.execute('DELETE FROM reservations WHERE user_id = ?', (line_user_id,))
        # Delete user
        cursor.execute('DELETE FROM users WHERE line_user_id = ?', (line_user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting customer: {e}")
        return False
    finally:
        conn.close()

def is_customer_banned(line_user_id):
    """Check if a customer is banned"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT is_banned FROM users WHERE line_user_id = ?', (line_user_id,))
        row = cursor.fetchone()
        return bool(row['is_banned']) if row else False
    finally:
        conn.close()

def seed_schedules():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Clear existing schedules for clean state (for this specific request)
        cursor.execute('DELETE FROM schedules')
        
        # 11/25 11:00 - 20:00
        cursor.execute('''
            INSERT INTO schedules (date, start_time, end_time, status)
            VALUES (?, ?, ?, ?)
        ''', ('2025-11-25', '11:00', '20:00', 'available'))
        
        # 11/26 11:00 - 20:00
        cursor.execute('''
            INSERT INTO schedules (date, start_time, end_time, status)
            VALUES (?, ?, ?, ?)
        ''', ('2025-11-26', '11:00', '20:00', 'available'))
        
        conn.commit()
        print("Seeded schedules for 11/25 and 11/26.")
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    seed_schedules()
