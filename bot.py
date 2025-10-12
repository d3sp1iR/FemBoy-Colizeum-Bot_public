# bot.py
import os
import random
import telebot
from dotenv import load_dotenv
import db
from game import battle, buy_item
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# === Настройка ===
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
conn = db.init_db()

# === Вспомогательные функции ===
def get_user(message):
    if not message.from_user:
        return None
    return db.get_user_by_tid(conn, message.from_user.id)

def calculate_max_hp(level):
    """HP по уровням"""
    return 50 + (level - 1) * 10

def calculate_xp_to_next_level(level):
    """XP для перехода на следующий уровень"""
    return level * 500

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
    return femboy

# === /start ===
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user = get_user(message)
    if not user:
        db.create_user(conn, message.from_user.id, message.from_user.username)
        bot.send_message(message.chat.id, "Добро пожаловать в Колизей Фембоев! Создай своего фембоя командой /create_femboy <имя>")
    else:
        bot.send_message(message.chat.id, "Ты уже зарегистрирован!")

# === /create_femboy ===
@bot.message_handler(commands=['create_femboy'])
def cmd_create(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Укажи имя: /create_femboy Имя")
        return

    user = get_user(message)
    if not user:
        bot.send_message(message.chat.id, "Сначала зарегистрируйся /start")
        return

    femboy = db.get_femboy_by_user(conn, user['id'])
    if femboy:
        bot.send_message(message.chat.id, "У тебя уже есть фембой!")
        return

    femboy = db.create_femboy(conn, user['id'], args[1])
    bot.send_message(message.chat.id, f"Фембой {femboy['name']} создан! 🏳️‍🌈")

# === /profile ===
@bot.message_handler(commands=['profile'])
def cmd_profile(message):
    user = get_user(message)
    if not user:
        bot.send_message(message.chat.id, "Сначала зарегистрируйся /start")
        return

    femboy = db.get_femboy_dict(conn, user['id'])
    if not femboy:
        bot.send_message(message.chat.id, "У тебя ещё нет фембоя!")
        return

    msg = (
        f"👤 {message.from_user.first_name}\n"
        f"🏳️‍🌈 Фембой: {femboy['name']}\n"
        f"Уровень: {femboy['lvl']} | XP: {femboy['xp']} | HP: {femboy['hp']}/{calculate_max_hp(femboy['lvl'])}\n"
        f"Атака: {femboy['atk']} | Защита: {femboy['def']} | Золото: {femboy['gold']}"
    )
    bot.send_message(message.chat.id, msg)

# === /train ===
@bot.message_handler(commands=['train'])
def cmd_train(message):
    user = get_user(message)
    if not user:
        bot.send_message(message.chat.id, "Сначала зарегистрируйся /start")
        return

    if not db.can_train(conn, user['id']):
        bot.send_message(message.chat.id, "Тренировка доступна только 1 раз в день!")
        return

    femboy = dict(db.get_femboy_by_user(conn, user['id']))
    if not femboy:
        bot.send_message(message.chat.id, "У тебя ещё нет фембоя!")
        return

    trainer = {"name": "Тренер", "hp": 40, "atk": 7, "def": 4, "lvl": 1, "xp": 0, "gold": 0}

    result = battle(femboy, trainer)
    for line in result["log"]:
        bot.send_message(message.chat.id, line)

    winner = result["winner"]
    if winner["name"] == femboy["name"]:
        femboy["xp"] += 200
        femboy["gold"] += 10
        femboy["hp"] = min(calculate_max_hp(femboy["lvl"]), femboy["hp"] + 10)
        femboy = check_level_up(femboy)
        db.update_warrior(conn, femboy["id"], femboy)
        db.update_training_time(conn, user['id'])
        bot.send_message(message.chat.id, f"Ты стал сильнее! 🌟 XP: {femboy['xp']} | Уровень: {femboy['lvl']}")
    else:
        bot.send_message(message.chat.id, "Тренировка окончена! Но не сдавайся 💪")

# === /shop ===
@bot.message_handler(commands=['shop'])
def cmd_shop(message):
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM items")
        items = cur.fetchall()
        if not items:
            bot.send_message(message.chat.id, "Магазин пуст!")
            return

        msg = "🏬 Магазин:\n"
        for i in items:
            msg += f"{i['id']}. {i['name']} ({i['type']}) — {i['value']} | 💰 {i['price']} gold\n"
        msg += "\nЧтобы купить: /buy <id>"
        bot.send_message(message.chat.id, msg)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

# === /buy ===
@bot.message_handler(commands=['buy'])
def cmd_buy(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Укажи ID предмета: /buy <id>")
        return

    user = get_user(message)
    if not user:
        bot.send_message(message.chat.id, "Сначала зарегистрируйся /start")
        return

    femboy = db.get_femboy_by_user(conn, user['id'])
    if not femboy:
        bot.send_message(message.chat.id, "У тебя ещё нет фембоя!")
        return

    try:
        item_id = int(args[1])
    except ValueError:
        bot.send_message(message.chat.id, "ID должно быть числом!")
        return

    result = buy_item(conn, femboy['id'], item_id)
    bot.send_message(message.chat.id, result)

# === /duel ===
@bot.message_handler(commands=['duel'])
def cmd_duel(message):
    conn = db.get_conn()
    user = db.get_user_by_tid(conn, message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "Сначала зарегистрируйся /start")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Укажи оппонента: /duel @username")
        return

    opponent_username = args[1].lstrip('@')
    opponent = db.get_user_by_username(conn, opponent_username)
    if not opponent:
        bot.send_message(message.chat.id, f"Пользователь @{opponent_username} не найден!")
        return

    cur = conn.cursor()
    cur.execute(
        "INSERT INTO duels (challenger_id, opponent_id, status) VALUES (?, ?, 'pending')",
        (user['id'], opponent['id'])
    )
    conn.commit()
    duel_id = cur.lastrowid

    markup = InlineKeyboardMarkup()
    btn = InlineKeyboardButton(f"Принять дуэль от @{user['username']}", callback_data=f"accept_duel:{duel_id}")
    markup.add(btn)

    bot.send_message(message.chat.id, f"@{opponent_username}, тебя вызвали на дуэль!", reply_markup=markup)

# === Принятие дуэли ===
@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_duel:"))
def accept_duel_callback(call):
    try:
        duel_id = int(call.data.split(":")[1])
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM duels WHERE id=? AND status='pending'", (duel_id,))
        duel = cur.fetchone()

        if not duel:
            bot.answer_callback_query(call.id, "Дуэль уже завершена или не найдена.")
            return

        f_a = dict(db.get_femboy_by_user(conn, duel['challenger_id']))
        f_b = dict(db.get_femboy_by_user(conn, duel['opponent_id']))

        result = battle(f_a, f_b)
        winner = result["winner"]
        loser = f_b if winner["name"] == f_a["name"] else f_a

        # Награда
        gold_gain = min(30, loser["gold"])
        winner["gold"] += gold_gain
        loser["gold"] -= gold_gain
        winner["xp"] += 200
        winner = check_level_up(winner)

        winner["hp"] = calculate_max_hp(winner["lvl"])
        loser["hp"] = calculate_max_hp(loser["lvl"])

        db.update_warrior(conn, winner["id"], winner)
        db.update_warrior(conn, loser["id"], loser)

        cur.execute("UPDATE duels SET status='finished', winner_id=? WHERE id=?", (winner["id"], duel_id))
        conn.commit()

        log_text = "\n".join(result["log"])
        bot.send_message(call.message.chat.id, f"🏆 Победитель: {winner['name']}\n\n{log_text}")
        bot.answer_callback_query(call.id, "Дуэль завершена!")
    except Exception as e:
        print("ERROR in accept_duel_callback:", e)
        bot.answer_callback_query(call.id, f"Ошибка: {e}")

# === Запуск ===
if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling()
