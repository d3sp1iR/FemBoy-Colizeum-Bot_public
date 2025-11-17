import db as db
import telebot
import time 

TOKEN = "7849791400:AAHi9JlJFwF_bVlMmWUwaXEhdP7chlHQSCw"
bot = telebot.TeleBot(TOKEN)
bot.start_time = time.time()  
conn = db.init_db()


def get_inventory(conn, femboy_id):
    cur = conn.cursor()
    cur.execute("SELECT name, type, COUNT(*) as qty FROM femboy_items fi "
                "JOIN items i ON fi.item_id = i.id "
                "WHERE fi.femboy_id = ? "
                "GROUP BY fi.item_id", (femboy_id,))
    items = cur.fetchall()
    return items  # список словарей: {"name": ..., "type": ..., "qty": ...}

def get_user(message):
    if not message.from_user:
        return None
    return db.get_user_by_tid(conn, message.from_user.id)

def calculate_max_hp(level):
    """HP по уровням"""
    return 50 + (level - 1) * 20

def calculate_xp_to_next_level(level):
    """XP для перехода на следующий уровень"""
    return level * 1000

def check_level_up(femboy):
    """Проверка апа уровня"""
    leveled_up = False
    xp_needed = calculate_xp_to_next_level(femboy["lvl"])
    
    while femboy["xp"] >= xp_needed:
        femboy["xp"] -= xp_needed
        femboy["lvl"] += 1
        leveled_up = True
        xp_needed = calculate_xp_to_next_level(femboy["lvl"])
    if leveled_up:
        femboy["hp"] = calculate_max_hp(femboy["lvl"])

    db.update_warrior(conn, femboy["id"], femboy)
    return femboy

def is_user_admin_by_id(id):
    return id in [1749731920,6199647470]

def is_user_admin_by_message(message):
    return is_user_admin_by_id(message.from_user.id)