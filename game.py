# game.py
import random

def buy_item(conn, femboy_id: int, item_id: int) -> str:
    cur = conn.cursor()
    # Получаем фембоя и предмет
    cur.execute("SELECT * FROM femboys WHERE id=?", (femboy_id,))
    femboy = cur.fetchone()
    cur.execute("SELECT * FROM items WHERE id=?", (item_id,))
    item = cur.fetchone()
    if not item:
        return "Такого предмета нет!"

    if femboy["gold"] < item["price"]:
        return "Недостаточно золота!"

    # Списываем золото и даем бонус
    new_gold = femboy["gold"] - item["price"]
    if item["type"] == "weapon":
        cur.execute("UPDATE femboys SET gold=?, weapon_atk=? WHERE id=?", (new_gold, femboy["weapon_atk"] + item["value"], femboy_id))
    else:
        cur.execute("UPDATE femboys SET gold=?, armor_def=? WHERE id=?", (new_gold, femboy["armor_def"] + item["value"], femboy_id))
    conn.commit()
    return f"{item['name']} куплен!"


def battle(femboy_a: dict, femboy_b: dict) -> dict:
    log = []
    a = femboy_a.copy()
    b = femboy_b.copy()

    log.append(f"🔞 🔞 🔞  {a['name']} 🆚 {b['name']}  🔞 🔞 🔞 \n")

    #  Случайный выбор, кто атакует первым
    attacker, defender = (a, b) if random.choice([True, False]) else (b, a)
    log.append(f"🎲 {attacker['name']} выигрывает инициативу и атакует первым!\n")

    round_num = 1

    while a["hp"] > 0 and b["hp"] > 0:
        log.append(f"Раунд {round_num}:")

        #  Атака
        damage = max(0, attacker["atk"] + attacker["weapon_atk"] - (defender["def"] + defender["armor_def"])) + random.randint(0, 5)
        defender["hp"] = max(0, defender["hp"] - damage)
        log.append(f"{attacker['name']} наносит {damage} урона!💥\n У {defender['name']} осталось {defender['hp']} HP ❤ .")

        #  Проверка, жив ли защитник
        if defender["hp"] <= 0:
            log.append(f"{defender['name']} пал!💀💀💀")
            break

        #  Меняем роли
        attacker, defender = defender, attacker
        round_num += 1

    # Результаты боя
    if a["hp"] == 0 and b["hp"] == 0:
        # Ничья
        a["xp"] += 50
        b["xp"] += 50
        log.append("\n🤝 НИЧЬЯ! Оба фембоя получают по +50 XP💡, но без золота.")
        winner = None
    else:
        # Победа
        winner = a if a["hp"] > 0 else b
        loser = b if winner == a else a

        win = round(loser['gold'] / 2)
        winner["xp"] += 50
        winner['gold'] += win
        loser['gold'] = max(0, loser['gold'] - win)

        log.append(f"\n🏆 Победитель: {winner['name']}! +50 XP💡 , +{win} gold💰")

    return {"winner": winner, "log": log}

