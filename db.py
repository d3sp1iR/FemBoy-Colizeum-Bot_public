# db.py
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

DB_PATH = "fembo_colos.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Пользователи
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_training TIMESTAMP
    );
    """)

    # Фембои
    cur.execute("""
    CREATE TABLE IF NOT EXISTS femboys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        lvl INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        hp INTEGER DEFAULT 100,
        atk INTEGER DEFAULT 10,
        def INTEGER DEFAULT 5,
        gold INTEGER DEFAULT 0,
        weapon_atk INTEGER DEFAULT 0,
        armor_def INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS duels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challenger_id INTEGER NOT NULL,
        opponent_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending', -- pending, accepted, finished
        winner_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Магазин
    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL,
        value INTEGER NOT NULL,
        price INTEGER NOT NULL
    );
    """)
    # Начальные предметы
    items = [
        ("Бычий Член", "weapon", 3, 100),
        ("Митенки", "armor", 3, 80),
        ("Волшебный Жезл", "weapon", 9, 280),
        ("Костюм горничной", "armor", 9, 200),
        ("Меч Астольфо", "weapon", 50, 1000),
        ("Кошачьи ушки", "armor", 25, 450),
        ("Благородная Слизь", "armor", 80, 5000)
    ]
    for item in items:
        cur.execute("SELECT 1 FROM items WHERE name = ?", (item[0],))
        if not cur.fetchone():
            cur.execute("INSERT INTO items (name, type, value, price) VALUES (?, ?, ?, ?)", item)

    # Битвы
    cur.execute("""
    CREATE TABLE IF NOT EXISTS battles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        femboy_a INTEGER,
        femboy_b INTEGER,
        winner INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    return conn

# === Пользователи ===
def get_user_by_tid(conn, tid: int) -> Optional[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id=?", (tid,))
    return cur.fetchone()

def create_user(conn, tid: int, username: str = None):
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)", (tid, username))
    conn.commit()
    return get_user_by_tid(conn, tid)

def add_missing_columns(conn):
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE femboys ADD COLUMN weapon_atk INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # колонка уже есть
    try:
        cur.execute("ALTER TABLE femboys ADD COLUMN armor_def INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()


# === Фембои ===
def create_femboy(conn, user_id: int, name: str) -> sqlite3.Row:
    cur = conn.cursor()
    cur.execute("INSERT INTO femboys (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    cur.execute("SELECT * FROM femboys WHERE id = last_insert_rowid()")
    return cur.fetchone()

def get_femboy_by_user(conn, user_id: int) -> Optional[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM femboys WHERE user_id=?", (user_id,))
    return cur.fetchone()

def list_other_femboys(conn, exclude_user_id: int):
    cur = conn.cursor()
    cur.execute("SELECT f.*, u.username FROM femboys f JOIN users u ON f.user_id=u.id WHERE f.user_id != ?", (exclude_user_id,))
    return cur.fetchall()

def get_femboy_dict(conn, user_id: int) -> Optional[dict]:
    f = get_femboy_by_user(conn, user_id)
    if not f:
        return None
    d = dict(f)
    # на всякий случай ставим дефолты, если чего нет
    d.setdefault("lvl", 1)
    d.setdefault("xp", 0)
    d.setdefault("hp", 100)
    d.setdefault("atk", 10)
    d.setdefault("def", 5)
    d.setdefault("gold", 0)
    d.setdefault("weapon_atk", 0)
    d.setdefault("armor_def", 0)
    return d



# === Битвы ===
def record_battle(conn, a_id: int, b_id: int, winner_id: int):
    cur = conn.cursor()
    cur.execute("INSERT INTO battles (femboy_a, femboy_b, winner) VALUES (?, ?, ?)", (a_id, b_id, winner_id))
    conn.commit()

# === Тренировка ===
def get_last_training(conn, user_id: int):
    cur = conn.cursor()
    cur.execute("SELECT last_training FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    if row and row["last_training"]:
        return datetime.fromisoformat(row["last_training"])
    return None

def can_train(conn, user_id: int):
    last = get_last_training(conn, user_id)
    if not last:
        return True
    return datetime.now() - last > timedelta(days=1)

def update_training_time(conn, user_id: int):
    cur = conn.cursor()
    cur.execute("UPDATE users SET last_training=? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()

def update_warrior(conn, femboy_id: int, data: dict):
    cur = conn.cursor()
    fields = []
    values = []
    for key, val in data.items():
        fields.append(f"{key}=?")
        values.append(val)
    values.append(femboy_id)
    cur.execute(f"UPDATE femboys SET {', '.join(fields)} WHERE id=?", values)
    conn.commit()

def get_user_by_username(conn, username):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    return cur.fetchone()



