import sqlite3
from typing import Dict, List, Optional, Tuple

DB_NAME = "rpg_data.db"


def setup_database():
    """Cria as tabelas do banco de dados se elas não existirem."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        system TEXT NOT NULL,
        campaign TEXT NOT NULL,
        character_name TEXT NOT NULL,
        UNIQUE(user_id, system, campaign, character_name)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attributes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        value TEXT,
        FOREIGN KEY (character_id) REFERENCES characters (id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()


def find_character_id(user_id: int, system: str, campaign: str, char_name: str) -> Optional[int]:
    """Encontra o ID de um personagem. Retorna None se não encontrado."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM characters 
        WHERE user_id = ? AND lower(system) = ? AND lower(campaign) = ? AND lower(character_name) = ?
    """, (user_id, system.lower(), campaign.lower(), char_name.lower()))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def create_character_sheet(user_id: int, system: str, campaign: str, char_name: str, attributes: Dict[str, str]):
    """Cria uma nova ficha de personagem e seus atributos."""
    if find_character_id(user_id, system, campaign, char_name):
        raise ValueError("Você já possui um personagem com este nome nesta campanha.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO characters (user_id, system, campaign, character_name) 
            VALUES (?, ?, ?, ?)
        """, (user_id, system.lower(), campaign.lower(), char_name.lower()))

        character_id = cursor.lastrowid

        attr_data = [(character_id, name.lower(), value) for name, value in attributes.items()]
        cursor.executemany("""
            INSERT INTO attributes (character_id, name, value) 
            VALUES (?, ?, ?)
        """, attr_data)

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_character_sheet(char_id: int) -> Optional[Dict]:
    """Busca uma ficha completa pelo seu ID."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM characters WHERE id = ?", (char_id,))
    char_data = cursor.fetchone()

    if not char_data:
        return None

    cursor.execute("SELECT name, value FROM attributes WHERE character_id = ?", (char_id,))
    attributes = {row['name']: row['value'] for row in cursor.fetchall()}

    sheet = dict(char_data)
    sheet['attributes'] = attributes

    conn.close()
    return sheet


def list_characters(user_id: int, system: str) -> List[Tuple[str, str]]:
    """Lista as fichas de um usuário em um determinado sistema."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT campaign, character_name FROM characters 
        WHERE user_id = ? AND lower(system) = ?
        ORDER BY campaign, character_name
    """, (user_id, system.lower()))

    results = cursor.fetchall()
    conn.close()
    return results


def update_attribute(char_id: int, attr_name: str, new_value: str) -> bool:
    """Atualiza o valor de um atributo."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE attributes SET value = ? 
        WHERE character_id = ? AND lower(name) = ?
    """, (new_value, char_id, attr_name.lower()))

    updated_rows = cursor.rowcount
    conn.commit()
    conn.close()
    return updated_rows > 0