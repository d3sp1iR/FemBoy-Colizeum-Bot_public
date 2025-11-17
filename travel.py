import datetime
import random
import db
from bot_utils import check_level_up

# Настройки приключений
ADVENTURE_DURATION = 3600  # 1 минута для теста

ADVENTURE_ITEMS = [
    {"id": 8, "name": "Потертый плащ", "type": "armor", "value": 2, "price": 60, "chance": 0.3},
    {"id": 9, "name": "Зачарованный амулет", "type": "armor", "value": 5, "price": 150, "chance": 0.2},
    {"id": 10, "name": "Острые когти", "type": "weapon", "value": 3, "price": 90, "chance": 0.25},
    {"id": 11, "name": "Древний свиток", "type": "weapon", "value": 7, "price": 210, "chance": 0.15},
    {"id": 12, "name": "Блестящее кольцо", "type": "armor", "value": 3, "price": 90, "chance": 0.3},
    {"id": 13, "name": "Магический жезл", "type": "weapon", "value": 10, "price": 300, "chance": 0.1}
]

ADVENTURE_EVENTS = [
    {
        "text": "встретил говорящего ежа, который научил его философии. +{xp} мудрости",
        "xp": [300, 850],
        "gold": [0, 0],
        "type": "philosophy"
    },
    {
        "text": "нашел сундук, но он оказался мимиком. Отбился и нашёл {gold} золота в его карманах",
        "xp": [50, 150],
        "gold": [20, 50],
        "type": "combat"
    },
    {
        "text": "пытался поймать фею, но та обокрала его и оставила {gold} золота 'из жалости'",
        "xp": [50, 100],
        "gold": [-15, -5],
        "type": "funny"
    },
    {
        "text": "проиграл в кости с гоблином {gold} золота, но выиграл {xp} опыта жизни",
        "xp": [150, 250],
        "gold": [-30, -10],
        "type": "gambling"
    },
    {
        "text": "научился готовить у местных орков. Съел что-то не то, но получил +{xp} к выносливости",
        "xp": [200, 420],
        "gold": [0, 0],
        "type": "training"
    },
    {
        "text": "подрался с собственным отражением в озере. Победил! +{xp} к самооценке",
        "xp": [450, 650],
        "gold": [0, 0],
        "type": "narcissism"
    },
    {
        "text": "нашел карту сокровищ, но это была реклама местной таверны. Потратил {gold} золота на эль",
        "xp": [50, 100],
        "gold": [-25, -15],
        "type": "tavern"
    },
    {
        "text": "помог старушке перейти дорогу. Та оказалась богиней и дала {xp} опыта",
        "xp": [700, 1200],
        "gold": [0, 0],
        "type": "divine"
    },
    {
        "text": "участвовал в конкурсе красоты среди фембоев. Занял {place} место!",
        "xp": [100, 300],
        "gold": [10, 40],
        "type": "contest"
    },
    {
        "text": "пытался приручить дракона, но тот съел его обед. Зато получил +{xp} к храбрости",
        "xp": [250, 350],
        "gold": [0, 0],
        "type": "dragon"
    }
]

def start_adventure(conn, femboy, message):
    now = datetime.datetime.now()
    end_time = now + datetime.timedelta(seconds=ADVENTURE_DURATION)

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO adventures (femboy_id, start_time, end_time, completed, chat_id)
        VALUES (?, ?, ?, 0, ?)
    """, (femboy["id"], now.isoformat(), end_time.isoformat(), message.chat.id))
    adventure_id = cur.lastrowid
    conn.commit()
    
    return end_time

def generate_adventure_report(femboy_name):
    """Генерирует полный отчет о приключении"""
    num_events = random.randint(2, 4)
    events_log = []
    total_xp = 0
    total_gold = 0
    found_items = []
    
    for i in range(num_events):
        event = random.choice(ADVENTURE_EVENTS)
        
        xp_gained = random.randint(event["xp"][0], event["xp"][1])
        gold_gained = random.randint(event["gold"][0], event["gold"][1])
        
        event_text = event["text"]
        event_text = event_text.replace("{xp}", str(xp_gained))
        
        if gold_gained >= 0:
            event_text = event_text.replace("{gold}", str(gold_gained))
        else:
            event_text = event_text.replace("{gold}", str(abs(gold_gained)))
        
        if event["type"] == "contest":
            places = ["первое", "второе", "третье", "последнее"]
            event_text = event_text.replace("{place}", random.choice(places))
        
        events_log.append(f"📜 {femboy_name} {event_text}")
        total_xp += xp_gained
        total_gold += gold_gained
        
        # Увеличим шанс на предмет для тестирования
        if random.random() < 0.3:  # 30% шанс на предмет для теста
            possible_items = [item for item in ADVENTURE_ITEMS if random.random() < item["chance"]]
            if possible_items:
                found_item = random.choice(possible_items)
                found_items.append({
                    "id": found_item["id"],
                    "name": found_item["name"],
                    "type": found_item["type"],
                    "value": found_item["value"]
                })
                events_log.append(f"🎁 {femboy_name} нашел {found_item['name']}!")
    
    return {
        "events": events_log,
        "total_xp": total_xp,
        "total_gold": total_gold,
        "found_items": found_items
    }

def apply_item_bonuses(conn, femboy_id, found_items):
    """Применяет бонусы найденных предметов к характеристикам фембоя"""
    cur = conn.cursor()
    
    # Получаем текущие характеристики фембоя
    cur.execute("SELECT weapon_atk, armor_def FROM femboys WHERE id=?", (femboy_id,))
    femboy_stats = cur.fetchone()
    
    total_weapon_bonus = 0
    total_armor_bonus = 0
    
    print(f"Найдено предметов для фембоя {femboy_id}: {len(found_items)}")
    
    for item in found_items:
        print(f"Добавляем предмет: {item['name']} (ID: {item['id']})")
        
        # Проверяем, есть ли уже такой предмет у фембоя
        cur.execute("SELECT id FROM femboy_items WHERE femboy_id=? AND item_id=?", 
                   (femboy_id, item["id"]))
        existing_item = cur.fetchone()
        
        if existing_item:
            print(f"Предмет {item['name']} уже есть в инвентаре, пропускаем")
            continue
        
        # Добавляем предмет в инвентарь
        try:
            cur.execute("INSERT INTO femboy_items (femboy_id, item_id) VALUES (?, ?)", 
                       (femboy_id, item["id"]))
            print(f"Предмет {item['name']} успешно добавлен в инвентарь")
        except Exception as e:
            print(f"Ошибка при добавлении предмета {item['name']}: {e}")
            continue
        
        # Суммируем бонусы для применения
        if item["type"] == "weapon":
            total_weapon_bonus += item["value"]
            print(f"Бонус к оружию: +{item['value']}")
        elif item["type"] == "armor":
            total_armor_bonus += item["value"]
            print(f"Бонус к броне: +{item['value']}")
    
    # Обновляем характеристики фембоя
    if total_weapon_bonus > 0 or total_armor_bonus > 0:
        new_weapon_atk = femboy_stats["weapon_atk"] + total_weapon_bonus
        new_armor_def = femboy_stats["armor_def"] + total_armor_bonus
        
        print(f"Обновляем характеристики: weapon_atk={new_weapon_atk}, armor_def={new_armor_def}")
        
        cur.execute("""
            UPDATE femboys SET weapon_atk=?, armor_def=? WHERE id=?
        """, (new_weapon_atk, new_armor_def, femboy_id))
    else:
        print("Нет бонусов для применения")
    
    return total_weapon_bonus, total_armor_bonus

def complete_adventure(adv_id, femboy_id, chat_id):
    """Завершает приключение и возвращает отчет"""
    try:
        conn = db.get_conn()
        cur = conn.cursor()
        
        # Сначала проверяем, не завершено ли уже приключение
        cur.execute("SELECT completed FROM adventures WHERE id=?", (adv_id,))
        adventure = cur.fetchone()
        if adventure and adventure["completed"] == 1:
            print(f"Приключение {adv_id} уже завершено, пропускаем")
            conn.close()
            return None
        
        cur.execute("SELECT * FROM femboys WHERE id=?", (femboy_id,))
        femboy_row = cur.fetchone()
        if not femboy_row:
            print(f"Фембой {femboy_id} не найден")
            conn.close()
            return None
            
        femboy = dict(femboy_row)
        print(f"Завершаем приключение для фембоя: {femboy['name']}")
        
        report = generate_adventure_report(femboy["name"])
        print(f"Сгенерирован отчет: {len(report['found_items'])} предметов")
        
        femboy["xp"] += report["total_xp"]
        femboy["gold"] += report["total_gold"]
        
        if femboy["gold"] < 0:
            femboy["gold"] = 0
        
        femboy = check_level_up(femboy)
        
        # Обновляем фембоя в базе
        cur.execute("""
            UPDATE femboys SET xp=?, gold=?, lvl=?, hp=? 
            WHERE id=?
        """, (femboy["xp"], femboy["gold"], femboy["lvl"], femboy["hp"], femboy_id))
        
        # Добавляем найденные предметы и применяем их бонусы
        weapon_bonus, armor_bonus = apply_item_bonuses(conn, femboy_id, report["found_items"])
        
        # Отмечаем приключение завершенным
        cur.execute("UPDATE adventures SET completed=1 WHERE id=?", (adv_id,))
        
        conn.commit()
        conn.close()
        
        report["weapon_bonus"] = weapon_bonus
        report["armor_bonus"] = armor_bonus
        
        print(f"Приключение {adv_id} успешно завершено")
        return report
        
    except Exception as e:
        print(f"Ошибка завершения приключения {adv_id}: {e}")
        return None

def adventure_checker(bot):
    """Проверяет завершенные приключения"""
    import time
    import threading
    
    def run():
        while True:
            time.sleep(30)
            try:
                conn = db.get_conn()
                cur = conn.cursor()
                
                now = datetime.datetime.now()
                cur.execute("""
                    SELECT id, femboy_id, chat_id 
                    FROM adventures 
                    WHERE completed=0 AND end_time <= ?
                """, (now.isoformat(),))
                adventures = cur.fetchall()
                conn.close()
                
                print(f"Найдено приключений для завершения: {len(adventures)}")
                
                completed_count = 0
                for adv in adventures:
                    print(f"Обрабатываем приключение {adv['id']}")
                    report = complete_adventure(adv["id"], adv["femboy_id"], adv["chat_id"])
                    
                    if report:
                        completed_count += 1
                        report_text = format_adventure_report(report, adv["femboy_id"])
                        try:
                            bot.send_message(adv["chat_id"], report_text, parse_mode="HTML")
                            print(f"Отчет отправлен для приключения {adv['id']}")
                        except Exception as e:
                            print(f"Не удалось отправить отчет: {e}")
                
                if completed_count > 0:
                    print(f"Успешно завершено приключений: {completed_count}")
                
            except Exception as e:
                print(f"Ошибка в adventure_checker: {e}")
                time.sleep(10)
    
    threading.Thread(target=run, daemon=True).start()

def format_adventure_report(report, femboy_id):
    """Форматирует отчет о приключении в красивый текст"""
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM femboys WHERE id=?", (femboy_id,))
    femboy_row = cur.fetchone()
    if not femboy_row:
        conn.close()
        return "Ошибка: фембой не найден"
    
    femboy_name = femboy_row["name"]
    conn.close()
    
    text = f"🏁 <b>{femboy_name} вернулся из приключения!</b>\n\n"
    
    text += "<b>📖 Хроники приключения:</b>\n"
    for event in report["events"]:
        text += f"• {event}\n"
    
    text += f"\n<b>📊 Итоги:</b>\n"
    text += f"✨ Опыта получено: {report['total_xp']}\n"
    
    if report['total_gold'] >= 0:
        text += f"💰 Золота найдено: +{report['total_gold']}\n"
    else:
        text += f"💰 Золота потеряно: {report['total_gold']}\n"
    
    if report["found_items"]:
        item_names = [item["name"] for item in report["found_items"]]
        text += f"🎁 Найдены предметы: {', '.join(item_names)}\n"
        
        if report.get("weapon_bonus", 0) > 0:
            text += f"⚔️ Бонус к атаке: +{report['weapon_bonus']}\n"
        if report.get("armor_bonus", 0) > 0:
            text += f"🛡️ Бонус к защите: +{report['armor_bonus']}\n"
    else:
        text += "🎁 Найдены предметы: нет\n"
    
    return text