import sqlite3
import secrets
from datetime import datetime

DB_NAME = "edunotify.db"

def connect_db():
    return sqlite3.connect(DB_NAME)

def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns

def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Batch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_name TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Student (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone_number TEXT,
            batch_id INTEGER,
            FOREIGN KEY (batch_id) REFERENCES Batch(id)
        )
    """)

    # Add the column for databases created before phone numbers were supported.
    if not column_exists(cursor, "Student", "phone_number"):
        cursor.execute("ALTER TABLE Student ADD COLUMN phone_number TEXT")
    if not column_exists(cursor, "Student", "telegram_chat_id"):
        cursor.execute("ALTER TABLE Student ADD COLUMN telegram_chat_id TEXT")
    if not column_exists(cursor, "Student", "is_opted_in"):
        cursor.execute("ALTER TABLE Student ADD COLUMN is_opted_in INTEGER DEFAULT 0")
    if not column_exists(cursor, "Student", "telegram_link_code"):
        cursor.execute("ALTER TABLE Student ADD COLUMN telegram_link_code TEXT")
    if not column_exists(cursor, "Student", "telegram_link_email_sent_at"):
        cursor.execute("ALTER TABLE Student ADD COLUMN telegram_link_email_sent_at TEXT")
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_student_telegram_link_code
        ON Student(telegram_link_code)
        WHERE telegram_link_code IS NOT NULL
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS MessageHistory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER,
            student_id INTEGER,
            message TEXT NOT NULL,
            date_time TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (faculty_id) REFERENCES Faculty(id),
            FOREIGN KEY (student_id) REFERENCES Student(id) ON DELETE SET NULL
        )
    """)

    conn.commit()
    conn.close()


def insert_sample_data():
    conn = connect_db()
    cursor = conn.cursor()

    # Insert faculty only if not exists
    cursor.execute("SELECT COUNT(*) FROM Faculty WHERE username=?", ("faculty",))
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO Faculty (username, password) VALUES (?, ?)",
            ("demo_faculty", "change-me-before-use")
        )

    # Insert batches only if not exists
    batches = [("Python Batch",), ("Data Science Batch",), ("ML Batch",)]
    for batch_name, in batches:
        cursor.execute("SELECT COUNT(*) FROM Batch WHERE batch_name=?", (batch_name,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO Batch (batch_name) VALUES (?)", (batch_name,))

    # Get batch IDs
    cursor.execute("SELECT id FROM Batch WHERE batch_name=?", ("Python Batch",))
    python_batch_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM Batch WHERE batch_name=?", ("Data Science Batch",))
    ds_batch_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM Batch WHERE batch_name=?", ("ML Batch",))
    ml_batch_id = cursor.fetchone()[0]

    # Insert sample students only if not exists
    # Public/demo seed data only. Replace with your own records locally.
    sample_students = [
        ("Demo Student 1", "student1@example.com", "9000000001", python_batch_id),
        ("Demo Student 2", "student2@example.com", "9000000002", ds_batch_id),
        ("Demo Student 3", "student3@example.com", "9000000003", ml_batch_id),
        ("Demo Student 4", "student4@example.com", "9000000004", ds_batch_id),
    ]

    for name, email, phone_number, batch_id in sample_students:
        cursor.execute("SELECT COUNT(*) FROM Student WHERE name=? AND batch_id=?", (name, batch_id))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO Student (name, email, phone_number, batch_id) VALUES (?, ?, ?, ?)",
                (name, email, phone_number, batch_id)
            )
        else:
            # Populate the newly added field for the existing sample students.
            cursor.execute(
                """
                UPDATE Student
                SET phone_number=?
                WHERE name=? AND batch_id=?
                """,
                (phone_number, name, batch_id)
            )

    conn.commit()
    conn.close()

def check_login(username, password):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM Faculty WHERE username=? AND password=?", (username, password))
    faculty = cursor.fetchone()
    conn.close()
    return faculty

def get_batches():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, batch_name FROM Batch ORDER BY batch_name")
    batches = cursor.fetchall()
    conn.close()
    return batches

def get_students_by_batch(batch_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, phone_number, email, telegram_chat_id, is_opted_in,
               telegram_link_code, telegram_link_email_sent_at
        FROM Student
        WHERE batch_id=?
        ORDER BY name
    """, (batch_id,))
    students = cursor.fetchall()
    conn.close()
    return students


def get_linked_students_by_batch(batch_id):
    """Return only students who completed Telegram account linking."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, phone_number, email, telegram_chat_id, is_opted_in,
               telegram_link_code, telegram_link_email_sent_at
        FROM Student
        WHERE batch_id=? AND telegram_chat_id IS NOT NULL AND is_opted_in=1
        ORDER BY name
    """, (batch_id,))
    students = cursor.fetchall()
    conn.close()
    return students


def _new_link_code(cursor):
    """Generate a unique, non-guessable code for a student's Telegram link."""
    while True:
        code = f"STD-{secrets.token_hex(4).upper()}"
        cursor.execute("SELECT 1 FROM Student WHERE telegram_link_code=?", (code,))
        if cursor.fetchone() is None:
            return code


def ensure_student_link_codes():
    """Give every existing student a link code without changing other data."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Student WHERE telegram_link_code IS NULL OR telegram_link_code='' ")
    for (student_id,) in cursor.fetchall():
        cursor.execute(
            "UPDATE Student SET telegram_link_code=? WHERE id=?",
            (_new_link_code(cursor), student_id)
        )
    conn.commit()
    conn.close()


def link_student_telegram(link_code, chat_id):
    """Attach a Telegram chat to one student. A code may only be used once."""
    normalized_code = (link_code or "").strip().upper()
    if not normalized_code:
        return "missing_code", None

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, telegram_chat_id, is_opted_in FROM Student WHERE telegram_link_code=?",
        (normalized_code,)
    )
    student = cursor.fetchone()
    if not student:
        conn.close()
        return "invalid_code", None

    student_id, student_name, saved_chat_id, linked = student
    if saved_chat_id:
        conn.close()
        if str(saved_chat_id) == str(chat_id) and linked:
            return "already_linked", student_name
        return "code_already_used", student_name

    cursor.execute(
        "UPDATE Student SET telegram_chat_id=?, is_opted_in=1 WHERE id=?",
        (str(chat_id), student_id)
    )
    conn.commit()
    conn.close()
    return "linked", student_name


def get_student_link_codes():
    """Return students and their link codes for the faculty/admin workflow."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, telegram_link_code FROM Student ORDER BY name")
    records = cursor.fetchall()
    conn.close()
    return records


def mark_telegram_link_email_sent(student_id):
    """Record email delivery without changing actual Telegram link status."""
    conn = connect_db()
    cursor = conn.cursor()
    sent_at = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    cursor.execute(
        "UPDATE Student SET telegram_link_email_sent_at=? WHERE id=?",
        (sent_at, student_id)
    )
    conn.commit()
    conn.close()

def save_message_history(faculty_id, student_id, message, status):
    conn = connect_db()
    cursor = conn.cursor()
    date_time = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    cursor.execute("""
        INSERT INTO MessageHistory (faculty_id, student_id, message, date_time, status)
        VALUES (?, ?, ?, ?, ?)
    """, (faculty_id, student_id, message, date_time, status))
    conn.commit()
    conn.close()

def get_message_history():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            Faculty.username,
            Batch.batch_name,
            Student.name,
            'Telegram',
            MessageHistory.message,
            MessageHistory.date_time,
            MessageHistory.status
        FROM MessageHistory
        LEFT JOIN Faculty ON MessageHistory.faculty_id = Faculty.id
        LEFT JOIN Student ON MessageHistory.student_id = Student.id
        LEFT JOIN Batch ON Student.batch_id = Batch.id
        ORDER BY MessageHistory.id DESC
    """)
    history = cursor.fetchall()
    conn.close()
    return history

def setup_database():
    create_tables()
    insert_sample_data()
    ensure_student_link_codes()

if __name__ == "__main__":
    setup_database()
    print("✅ Database created/updated successfully.")
