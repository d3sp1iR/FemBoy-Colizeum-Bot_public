
import os
import random
import telebot
from dotenv import load_dotenv
import db as db
from game import battle, buy_item
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time 
import datetime

# === Настройка ===
#load_dotenv()
TOKEN = "8429912189:AAFyM54mxHeQdupvmH9NJOfGLrUnPxHF9bQ"
bot = telebot.TeleBot(TOKEN)
conn = db.init_db()

# === Вспомогательные функции ===

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
    bot.send_message(message.chat.id, f"Фембой {femboy['name']} создан! 🏳️")

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
    
    femboy = check_level_up(femboy)

    femboy = db.get_femboy_dict(conn, user['id'])
    items = get_inventory(conn, femboy['id'])

    inv_text = ""
    if items:
        inv_text = "\n\n🎒 Инвентарь:\n"
        for item in items:
            count = f"x{item['qty']}" if item['qty'] > 1 else ""
            icon = "🗡️" if item["type"] == "weapon" else "🛡️" if item["type"] == "armor" else "❓"
            inv_text += f"{icon} {item['name']} {count}\n"
    else:
        inv_text = "\n\n🎒 Инвентарь пуст!"

    msg = (
        f"👤 {message.from_user.first_name}\n"
        f"🏳️ Фембой: {femboy['name']}\n"
        f"Уровень: {femboy['lvl']} | XP: {femboy['xp']} | HP: {femboy['hp']}/{calculate_max_hp(femboy['lvl'])}\n"
        f"Атака: {femboy['atk'] + femboy['weapon_atk']} | Защита: {femboy['def'] + femboy['armor_def']} | Золото: {femboy['gold']}"
        +inv_text
    )
    bot.send_message(message.chat.id, msg)

#=====boss fight =====
@bot.message_handler(commands=['boss'])
def cmd_boss(message):
    user = get_user(message)
    if not user:
        bot.send_message(message.chat.id, "Сначала зарегистрируйся /start")
        return
    
    femboy = dict(db.get_femboy_by_user(conn, user['id']))
    if not femboy:
        bot.send_message(message.chat.id, "У тебя ещё нет фембоя!")
        return

    # Стоимость участия в бою с боссом
    entry_fee = 50

    # Проверка золота
    if femboy["gold"] < entry_fee:
        bot.send_message(message.chat.id, f"💰 У тебя недостаточно золота! Нужно {entry_fee}, а у тебя всего {femboy['gold']}.")
        return

    # Списываем золото за вход
    femboy["gold"] -= entry_fee

    # === Определяем текущего босса ===
    bosses = {
        1: {"name": "Энергет", "hp": 100, "atk": 30, "def": 4, "lvl": 1, "xp": 0, "gold": 300, "armor_def": 0, "weapon_atk": 0},
        2: {"name": "Гигачад", "hp": 150, "atk": 40, "def": 6, "lvl": 2, "xp": 0, "gold": 600, "armor_def": 0, "weapon_atk": 0},
        3: {"name": "Синьор ФемБой", "hp": 200, "atk": 60, "def": 8, "lvl": 3, "xp": 0, "gold": 2000, "armor_def": 0, "weapon_atk": 0},
        4: {"name": "Лорд Глиттер", "hp": 250, "atk": 100, "def": 10, "lvl": 4, "xp": 0, "gold": 3500, "armor_def": 0, "weapon_atk": 0}
    }

    boss_num = femboy.get("current_boss", 1)
    if boss_num not in bosses:
        bot.send_message(message.chat.id, "🎉 Ты уже победил всех доступных боссов! Жди обновления 👑")
        return

    boss = bosses[boss_num]

    # Начало боя
    result = battle(femboy, boss)
    winner = result["winner"]
    log_text = "\n".join(result["log"])

    if winner["name"] == femboy["name"]:
        # === Победа ===
        femboy["xp"] += 1000 * boss_num
        femboy["gold"] += boss["gold"]  # получаем награду
        femboy["hp"] = min(calculate_max_hp(femboy["lvl"]), femboy["hp"] + 20)
        femboy = check_level_up(femboy)
        femboy["current_boss"] = boss_num + 1  # следующий босс

        db.update_warrior(conn, femboy["id"], femboy)

        bot.send_message(
            message.chat.id,
            f"🏆 Победа над {boss['name']}!\n\n{log_text}\n\n"
            f"🌟 XP: {femboy['xp']} | Уровень: {femboy['lvl']}\n"
            f"💰 Получено золота: +{boss['gold']} (вход стоил {entry_fee})\n"
            f"➡️ Следующий босс: {femboy['current_boss']}"
        )
    else:
        # === Поражение ===
        complexity_lvl = result["complexity_lvl"]
        femboy["xp"] += round(complexity_lvl/2)
        db.update_warrior(conn, femboy["id"], femboy)
        bot.send_message(
            message.chat.id,
            f"💀 Ты пал от руки {boss['name']}!\n\n{log_text}\n\n"
            f"Ты потерял {entry_fee} золота за участие... А ещё тебя отымели и ты теперь заднеприводный :) ⚔️"
        )

        
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


    trainer_easy = {"name": "Тренер Святик", "hp": 50, "atk": 10, "def": 4, "lvl": 1, "xp": 0, "gold": 100, "armor_def": 0, "weapon_atk": 0}
    trainer_medium = {"name": "Тренер Блестяшка", "hp": 50, "atk": 30, "def": 4, "lvl": 1, "xp": 0, "gold": 200, "armor_def": 0, "weapon_atk": 0}
    trainer_medium_plus = {"name": "ИБМщик", "hp": 50, "atk": 50, "def": 4, "lvl": 1, "xp": 0, "gold": 300, "armor_def": 0, "weapon_atk": 0}
    

    if (femboy['atk'] + femboy["weapon_atk"]) <= 20:
        trainer = trainer_easy
    elif (femboy['atk'] + femboy["weapon_atk"]) <= 40:
        trainer = trainer_medium
    elif (femboy['atk'] + femboy["weapon_atk"]) <= 55:
        trainer = trainer_medium_plus

    result = battle(femboy, trainer)
    femboy["xp"] += result["winner"]["xp"] - femboy["xp"]  # прибавляем разницу
    femboy = check_level_up(femboy)

    winner = result["winner"]
    if winner["name"] == femboy["name"]:
        if trainer == trainer_easy:
            femboy["xp"] += 200
            femboy["atk"] += 5
            femboy["gold"] += 50
        elif trainer == trainer_medium:
            femboy["xp"] += 500
            femboy["atk"] += 5
            femboy["gold"] += 100
        elif trainer == trainer_medium_plus:
            femboy["xp"] += 750
            femboy["atk"] += 5
            femboy["gold"] += 150
        femboy["hp"] = min(calculate_max_hp(femboy["lvl"]), femboy["hp"] + 10)
        femboy = check_level_up(femboy)
        db.update_warrior(conn, femboy["id"], femboy)
        db.update_training_time(conn, user['id'])
        log_text = "\n".join(result["log"])
        bot.send_message(message.chat.id, f"🏆 Победитель: {winner['name']}\n\n{log_text}")
        bot.send_message(message.chat.id, f"Ты стал сильнее! Твоя атака увеличилась на 5 единиц и теперь {femboy['atk']}\n 🌟 XP: {femboy['xp']} | Уровень: {femboy['lvl']}")
    else:
        log_text = "\n".join(result["log"])
        bot.send_message(message.chat.id, "Тренировка окончена! Но не сдавайся 💪")

# === /shop ===
@bot.message_handler(commands=['shop'])
def cmd_shop(message):
    try:
        user = get_user(message)
        if not user:
            bot.send_message(message.chat.id, "Сначала зарегистрируйся /start")
            return
    
        femboy = dict(db.get_femboy_by_user(conn, user['id']))
        if not femboy:
            bot.send_message(message.chat.id, "У тебя ещё нет фембоя!")
            return
        cur = conn.cursor()
        cur.execute("SELECT * FROM items")
        items = cur.fetchall()
        if not items:
            bot.send_message(message.chat.id, "Магазин пуст!")
            return

        msg = "🏬 Магазин:\n"
        for i in items:
            msg += f"{i['id']}. {i['name']} ({i['type']}) — {i['value']} | 💰 {i['price']} gold\n"
        msg += f"\nЧтобы купить: /buy <id>\nТвой баланс: {femboy['gold']}"
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
# /duel @username
@bot.message_handler(commands=['duel'])
def cmd_duel(message):
    user = get_user(message)
    if not user:
        bot.send_message(message.chat.id, "Сначала зарегистрируйся /start")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(message.chat.id, "Укажи оппонента: /duel @username")
        return

    opponent_username = args[1].lstrip('@')
    # ищем по username в базе, но если None — ищем по Telegram ID через get_user_by_tid
    opponent = None
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (opponent_username,))
    opponent = cur.fetchone()
    if not opponent:
        bot.send_message(message.chat.id, f"Пользователь @{opponent_username} не найден или не зарегистрирован!")
        return

    if opponent["id"] == user["id"]:
        bot.send_message(message.chat.id, "Нельзя вызвать себя 😅")
        return

    cur.execute(
        "INSERT INTO duels (challenger_id, opponent_id) VALUES (?, ?)",
        (user["id"], opponent["id"])
    )
    conn.commit()
    duel_id = cur.lastrowid

    markup = InlineKeyboardMarkup()
    accept_button = InlineKeyboardButton(
        text=f"Принять дуэль от @{user['username'] or 'игрок'}",
        callback_data=f"accept_duel:{duel_id}:{opponent['telegram_id']}"
    )
    markup.add(accept_button)

    bot.send_message(message.chat.id, f"@{opponent_username}, тебя вызвали на дуэль!", reply_markup=markup)


# === Принятие дуэли ===
@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_duel:"))
def accept_duel_callback(call):
    try:
        # Разбираем callback_data
        parts = call.data.split(":")
        duel_id = int(parts[1])
        allowed_tid = int(parts[2])  # Telegram ID того, кто должен принять

        if call.from_user.id != allowed_tid:
            bot.answer_callback_query(call.id, "Эту дуэль может принять только приглашённый игрок!")
            return

        # Подключаемся к базе и создаём курсор
        conn = db.get_conn()
        cur = conn.cursor()

        # Берём дуэль
        cur.execute("SELECT * FROM duels WHERE id=? AND status='pending'", (duel_id,))
        duel = cur.fetchone()
        if not duel:
            bot.answer_callback_query(call.id, "Дуэль уже завершена или не найдена.")
            return

        # Получаем фембоев
        f_a = dict(db.get_femboy_by_user(conn, duel['challenger_id']))
        f_b = dict(db.get_femboy_by_user(conn, duel['opponent_id']))

        # Запускаем бой
        result = battle(f_a, f_b,)
        winner = result["winner"]
        loser = f_b if winner["name"] == f_a["name"] else f_a
        
        #Баблишко накидываем
        winner['gold'] += round(loser["gold"]/2)
        loser['gold'] -= round(loser["gold"]/2)

        # Восстанавливаем HP победителю
        winner_max_hp = calculate_max_hp(winner["lvl"])
        winner["hp"] = winner_max_hp
        loser["hp"] = max(1, loser["hp"])

        complexity_lvl = result["complexity_lvl"]

        loser["xp"] += round(complexity_lvl/10)

        winner = check_level_up(winner)
        loser = check_level_up(loser)

        # Обновляем фембоев
        db.update_warrior(conn, loser["id"], {"hp": loser["hp"], "gold": loser["gold"], "xp": loser["xp"]})
        db.update_warrior(conn, winner["id"], {"xp": winner["xp"], "gold": winner["gold"], "hp": winner["hp"]})


        # Завершаем дуэль
        cur.execute("UPDATE duels SET status='finished', winner_id=? WHERE id=?", (winner["id"], duel_id))
        conn.commit()

        log_text = "\n".join(result["log"])
        bot.send_message(call.message.chat.id, f"🏆 Победитель: {winner['name']}\n\n{log_text}")
        bot.answer_callback_query(call.id, "Дуэль завершена!")

    except Exception as e:
        print("ERROR in accept_duel_callback:", e)
        bot.answer_callback_query(call.id, f"Произошла ошибка: {e}")

@bot.message_handler(commands=['tops']) 
def cmd_tops(message):
    try:
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT name, lvl, xp
            FROM femboys
            ORDER BY lvl DESC, xp DESC
            LIMIT 10
        """)
        top_players = cur.fetchall()

        if not top_players:
            bot.send_message(message.chat.id, "Пока нет ни одного покорителя колизея!")
            return
        
        text = "<b>ТОП ФЕМБОЙЧИКОВ КОЛИЗЕЯ</b>\n\n"
        for i, player in enumerate(top_players, start=1):
            name = player["name"]
            lvl = player["lvl"]
            xp = player["xp"]
            text += f"<b>{i}.</b> {name} - Уровень: {lvl}, Опыт: {xp}\n"

        bot.send_message(message.chat.id, text, parse_mode="HTML")

    except Exception as e:
        print("ERROR IN /tops:", e)
        bot.send_message(message.chat.id, f"ПРОИЗОШЛА ОШИБКА, ТОПА НЕТ, ВЫ ВСЕ ЛОХИ :/")


    
@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.send_message(message.chat.id, ""
    "/create_femboy <name> - создание своего персонажа\n "
    "/profile - просмотреть профиль персонажа\n "
    "/shop - магазин\n "
    "/duel <@username> - вызвать пользователя на дуэль\n "
    "/train - провести тренировочный бой с персонажем-тренером\n")

@bot.message_handler(commands=['reset_all'])
def cmd_reset_all(message):
    if message.from_user.id != 1749731920:
        bot.reply_to(message, "ты не админ, хатьфу, соси.")
        return

    try:
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE femboys
            SET lvl = 1,
                xp = 0,
                gold = 30,
                hp = 50,
                weapon_atk = 0,
                armor_def = 0,
                atk = 10,
                def = 5,
                current_boss = 1

        """)
        cur.execute("UPDATE users SET last_training = NULL") #сброс таймера трени
        cur.execute("DELETE FROM femboy_items") #сброс инвентаря
        conn.commit()
        bot.send_message(message.chat.id, "Все фембои возвращны в свои инкубаторы и откатились до заводских!")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error in /reset_all: {e}")
        print("Error in /reset_all:", e)
    finally:
        conn.close()


while True:
    try:
        print("Bot started...")
        bot.infinity_polling(timeout=30, long_polling_timeout=25)
    except Exception as e:
        print("Polling error:", e)
        time.sleep(5)
