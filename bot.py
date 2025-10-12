# bot.py
import os
import random
import telebot
from dotenv import load_dotenv
import db
from game import battle 
from game import buy_item

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
conn = db.init_db()

# === Личные и групповые чаты ===
def get_user(message):
    if not message.from_user:
        return None
    return db.get_user_by_tid(conn, message.from_user.id)

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

    # Преобразуем sqlite3.Row в словарь
    femboy_dict = {
        "id": femboy["id"],
        "name": femboy["name"],
        "lvl": femboy["lvl"],
        "xp": femboy["xp"],
        "hp": femboy["hp"],
        "atk": femboy["atk"],
        "def": femboy["def"],
        "gold": femboy["gold"],
        "weapon_atk": femboy.get("weapon_atk", 0),
        "armor_def": femboy.get("armor_def", 0)
    }

    msg = f"👤 {message.from_user.first_name}\n"
    msg += f"🏳️‍🌈 Фембой: {femboy_dict['name']}\n"
    msg += f"Уровень: {femboy_dict['lvl']} | XP: {femboy_dict['xp']} | HP: {femboy_dict['hp']}\n"
    msg += f"Атака: {femboy_dict['atk']} + {femboy_dict['weapon_atk']} | Защита: {femboy_dict['def']} + {femboy_dict['armor_def']} | Золото: {femboy_dict['gold']}"
    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['train'])
def cmd_train(message):
    user = get_user(message)
    if not user:
        bot.send_message(message.chat.id, "Сначала зарегистрируйся /start")
        return

    if not db.can_train(conn, user['id']):
        bot.send_message(message.chat.id, "Тренировка доступна только 1 раз в день!")
        return

    femboy = db.get_femboy_by_user(conn, user['id'])
    if not femboy:
        bot.send_message(message.chat.id, "У тебя ещё нет фембоя!")
        return

    # Преобразуем sqlite3.Row в обычный словарь
    femboy_dict = {
        "id": femboy["id"],
        "name": femboy["name"],
        "lvl": femboy["lvl"],
        "xp": femboy["xp"],
        "hp": femboy["hp"],
        "atk": femboy["atk"],
        "def": femboy["def"],
        "gold": femboy["gold"],
        "weapon_atk": femboy["weapon_atk"],
        "armor_def": femboy["armor_def"]
    }

    # Тренер (CPU) — заполняем все ключи
    trainer = {
        "name": "Тренер",
        "hp": 50,
        "atk": 7,
        "def": 3,
        "lvl": 1,
        "xp": 0,
        "gold": 0,
        "weapon_atk": 0,
        "armor_def": 0
    }

    # Пошаговый бой
    result = battle(femboy_dict, trainer)
    for line in result["log"]:
        bot.send_message(message.chat.id, line)

    # Обновляем время тренировки
    db.update_training_time(conn, user['id'])
    db.update_warrior(conn, femboy["id"], {
        "xp": result["winner"]["xp"],
        "gold": result["winner"]["gold"],
        "hp": 100  # восстанавливаем здоровье после тренировки
    })

# /shop — показать магазин
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
            msg += f"{i['id']}. {i['name']} ({i['type']}) — {i['value']} | Цена: {i['price']} gold\n"
        msg += "\nЧтобы купить: /buy <id>"
        bot.send_message(message.chat.id, msg)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

# /buy <id> — покупка
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

# /duel <@username> — вызвать на дуэль
@bot.message_handler(commands=['duel'])
def cmd_duel(message):
    user = get_user(message)
    if not user:
        bot.send_message(message.chat.id, "Сначала зарегистрируйся /start")
        return

    femboy = db.get_femboy_by_user(conn, user['id'])
    if not femboy:
        bot.send_message(message.chat.id, "У тебя ещё нет фембоя!")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Укажи оппонента: /duel @username")
        return

    # Ищем игрока по username
    opponent_username = args[1].lstrip('@')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (opponent_username,))
    opponent = cur.fetchone()
    if not opponent:
        bot.send_message(message.chat.id, f"Пользователь @{opponent_username} не найден!")
        return

    if opponent['id'] == user['id']:
        bot.send_message(message.chat.id, "Нельзя вызвать на дуэль себя 😅")
        return

    # Создаем запись дуэли
    cur.execute("INSERT INTO duels (challenger_id, opponent_id) VALUES (?, ?)", (user['id'], opponent['id']))
    conn.commit()
    bot.send_message(message.chat.id, f"@{opponent_username}, тебя вызвали на дуэль! Напиши /accept_duel @{user['username']} чтобы принять.")

# /accept_duel <@username>
@bot.message_handler(commands=['accept_duel'])
def cmd_accept_duel(message):
    user = get_user(message)
    if not user:
        bot.send_message(message.chat.id, "Сначала зарегистрируйся /start")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Укажи, чью дуэль принимаешь: /accept_duel @username")
        return

    challenger_username = args[1].lstrip('@')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (challenger_username,))
    challenger = cur.fetchone()
    if not challenger:
        bot.send_message(message.chat.id, f"Пользователь @{challenger_username} не найден!")
        return

    # Берем дуэль
    cur.execute("SELECT * FROM duels WHERE challenger_id=? AND opponent_id=? AND status='pending'", 
                (challenger['id'], user['id']))
    duel = cur.fetchone()
    if not duel:
        bot.send_message(message.chat.id, "Такой дуэли нет или она уже завершена!")
        return

    # Получаем фембоев
    f_a = db.get_femboy_by_user(conn, challenger['id'])
    f_b = db.get_femboy_by_user(conn, user['id'])

    # Запускаем бой
    from game import battle
    result = battle(dict(f_a), dict(f_b))

    # Обновляем победителя
    winner = result["winner"]
    winner_id = f_a["id"] if winner["name"] == f_a["name"] else f_b["id"]
    cur.execute("UPDATE duels SET status='finished', winner_id=? WHERE id=?", (winner_id, duel['id']))
    conn.commit()

    # Отправляем лог боя
    msg = "\n".join(result["log"])
    bot.send_message(message.chat.id, msg)



if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling()