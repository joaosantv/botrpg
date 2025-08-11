import sqlite3
import json
from typing import Dict, List, Optional, Tuple

DB_NAME = "rpg_data.db"


# Banco de Dados
def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, system TEXT NOT NULL, campaign TEXT NOT NULL,
        character_name TEXT NOT NULL, money REAL DEFAULT 0,
        UNIQUE(user_id, system, campaign, character_name)
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attributes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, character_id INTEGER NOT NULL,
        name TEXT NOT NULL, value TEXT,
        FOREIGN KEY (character_id) REFERENCES characters (id) ON DELETE CASCADE
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS npcs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        name TEXT NOT NULL, stats TEXT, UNIQUE(user_id, name)
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT, character_id INTEGER NOT NULL,
        item_name TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 1, description TEXT,
        FOREIGN KEY (character_id) REFERENCES characters (id) ON DELETE CASCADE
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS status_effects (
        id INTEGER PRIMARY KEY AUTOINCREMENT, character_id INTEGER NOT NULL,
        effect_name TEXT NOT NULL, duration INTEGER NOT NULL,
        caster_id INTEGER NOT NULL,
        FOREIGN KEY (character_id) REFERENCES characters (id) ON DELETE CASCADE
    )""")
    conn.commit()
    conn.close()


# Função personagem
def find_character_id(user_id: int, system: str, campaign: str, char_name: str) -> Optional[int]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM characters WHERE user_id = ? AND lower(system) = ? AND lower(campaign) = ? AND lower(character_name) = ?",
        (user_id, system.lower(), campaign.lower(), char_name.lower()))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def create_character_sheet(user_id: int, system: str, campaign: str, char_name: str, attributes: Dict[str, str]):
    if find_character_id(user_id, system, campaign, char_name): raise ValueError("Personagem já existe.")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO characters (user_id, system, campaign, character_name) VALUES (?, ?, ?, ?)",
                       (user_id, system.lower(), campaign.lower(), char_name.lower()))
        char_id = cursor.lastrowid
        attr_data = [(char_id, name.lower(), value) for name, value in attributes.items()]
        cursor.executemany("INSERT INTO attributes (character_id, name, value) VALUES (?, ?, ?)", attr_data)
        conn.commit()
    finally:
        conn.close()


def get_character_sheet(char_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM characters WHERE id = ?", (char_id,))
    char_data = cursor.fetchone()
    if not char_data: return None
    cursor.execute("SELECT name, value FROM attributes WHERE character_id = ?", (char_id,))
    attributes = {row['name']: row['value'] for row in cursor.fetchall()}
    sheet = dict(char_data)
    sheet['attributes'] = attributes
    conn.close()
    return sheet


def list_characters(user_id: int, system: str) -> List[Tuple[str, str]]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT campaign, character_name FROM characters WHERE user_id = ? AND lower(system) = ? ORDER BY campaign, character_name",
        (user_id, system.lower()))
    results = cursor.fetchall()
    conn.close()
    return results


def update_attribute(char_id: int, attr_name: str, new_value: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE attributes SET value = ? WHERE character_id = ? AND lower(name) = ?",
                   (new_value, char_id, attr_name.lower()))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


# Função inv e dinheiro
def modify_money(char_id: int, amount: float):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE characters SET money = money + ? WHERE id = ?", (amount, char_id))
    conn.commit()
    conn.close()


def add_item(char_id: int, item_name: str, quantity: int, description: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, quantity FROM inventory WHERE character_id = ? AND lower(item_name) = ?",
                   (char_id, item_name.lower()))
    item = cursor.fetchone()
    if item:
        new_quantity = item[1] + quantity
        cursor.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_quantity, item[0]))
    else:
        cursor.execute("INSERT INTO inventory (character_id, item_name, quantity, description) VALUES (?, ?, ?, ?)",
                       (char_id, item_name, quantity, description))
    conn.commit()
    conn.close()


def remove_item(char_id: int, item_name: str, quantity: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, quantity FROM inventory WHERE character_id = ? AND lower(item_name) = ?",
                   (char_id, item_name.lower()))
    item = cursor.fetchone()
    if not item: raise ValueError("Item não encontrado no inventário.")
    if item[1] < quantity: raise ValueError("Quantidade a ser removida é maior que a existente.")

    new_quantity = item[1] - quantity
    if new_quantity == 0:
        cursor.execute("DELETE FROM inventory WHERE id = ?", (item[0],))
    else:
        cursor.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_quantity, item[0]))
    conn.commit()
    conn.close()


def get_inventory(char_id: int) -> List[Dict]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity, description FROM inventory WHERE character_id = ? ORDER BY item_name",
                   (char_id,))
    inventory = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return inventory


# --- FUNÇÕES DE EFEITOS DE STATUS ---
def apply_effect(char_id: int, effect_name: str, duration: int, caster_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO status_effects (character_id, effect_name, duration, caster_id) VALUES (?, ?, ?, ?)",
                   (char_id, effect_name, duration, caster_id))
    conn.commit()
    conn.close()


def get_effects(char_id: int) -> List[Dict]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, effect_name, duration FROM status_effects WHERE character_id = ?", (char_id,))
    effects = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return effects


def advance_effects_turn(char_id: int) -> List[str]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE status_effects SET duration = duration - 1 WHERE character_id = ?", (char_id,))
    cursor.execute("SELECT effect_name FROM status_effects WHERE character_id = ? AND duration = 0", (char_id,))
    expired_effects = [row[0] for row in cursor.fetchall()]
    cursor.execute("DELETE FROM status_effects WHERE character_id = ? AND duration <= 0", (char_id,))
    conn.commit()
    conn.close()
    return expired_effects


def remove_effect(char_id: int, effect_name: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM status_effects WHERE character_id = ? AND lower(effect_name) = ?",
                   (char_id, effect_name.lower()))
    conn.commit()
    conn.close()


# Função NPC
def create_npc(user_id: int, name: str, stats: Dict[str, str]):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        stats_json = json.dumps(stats)
        cursor.execute("INSERT INTO npcs (user_id, name, stats) VALUES (?, ?, ?)", (user_id, name, stats_json))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"Você já possui um NPC chamado '{name}'.")
    finally:
        conn.close()


def get_npc(user_id: int, name: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, stats FROM npcs WHERE user_id = ? AND lower(name) = ?", (user_id, name.lower()))
    result = cursor.fetchone()
    conn.close()
    if not result: return None
    return {"name": result[0], "stats": json.loads(result[1])}


def list_npcs(user_id: int) -> List[str]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM npcs WHERE user_id = ? ORDER BY name", (user_id,))
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results


def delete_npc(user_id: int, name: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM npcs WHERE user_id = ? AND lower(name) = ?", (user_id, name.lower()))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated