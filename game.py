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
    round_num = 1

    while a["hp"] > 0 and b["hp"] > 0:
        # Считаем суммарный урон за раунд
        damage_a = max(0, a["atk"] + a["weapon_atk"] - (b["def"] + b["armor_def"])) + random.randint(0,5)
        damage_b = max(0, b.get("atk",10) + b.get("weapon_atk",0) - (a["def"] + a["armor_def"])) + random.randint(0,5)

        b["hp"] -= damage_a
        a["hp"] -= damage_b

        log.append(
            f"Раунд {round_num}: {a['name']} наносит {damage_a}, {b['name']} наносит {damage_b} | "
            f"HP: {a['name']}={max(a['hp'],0)}, {b['name']}={max(b['hp'],0)}"
        )

        round_num += 1

        if a["hp"] <= 0 or b["hp"] <= 0:
            break

    winner = a if a["hp"] > 0 else b
    winner["xp"] += 50
    winner["gold"] += 30
    log.append(f"\n🏆 Победитель: {winner['name']}! +50 XP, +30 gold")

    return {"winner": winner, "log": log}

