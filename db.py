import sqlite3
from pathlib import Path

DB_FILE = "data.db"

def get_connection():
    """Връща нова връзка към SQLite базата."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Създава таблиците при първо пускане (ако ги няма)."""
    conn = get_connection()
    cur = conn.cursor()

    # Таблица с ръчно задавани цени за продукти
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS product_prices (
            vendor_id INTEGER NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT,
            unit_price REAL NOT NULL,
            PRIMARY KEY (vendor_id, product_id)
        );
        """
    )

    # Таблица с продажби (лог, генериран автоматично от скрипта)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            revenue REAL NOT NULL
        );
        """
    )

    # НОВО: таблица с последно известното състояние на наличностите
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS last_stock (
            vendor_id INTEGER NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT,
            qty INTEGER NOT NULL,
            PRIMARY KEY (vendor_id, product_id)
        );
        """
    )

    conn.commit()
    conn.close()

def get_last_inventory_for_vendor(vendor_id: int):
    """
    Връща dict {product_id: {"name": product_name, "qty": qty}}
    за даден vendor, на база last_stock.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT product_id, product_name, qty
        FROM last_stock
        WHERE vendor_id = ?;
        """,
        (vendor_id,)
    )
    rows = cur.fetchall()
    conn.close()

    inventory = {}
    for r in rows:
        inventory[str(r["product_id"])] = {
            "name": r["product_name"],
            "qty": int(r["qty"])
        }
    return inventory


def replace_inventory_for_vendor(vendor_id: int, inventory: dict):
    """
    Изтрива старото състояние за vendor_id и вкарва новото
    (цял snapshot на наличностите).
    inventory е dict {product_id: {"name": ..., "qty": ...}}
    """
    conn = get_connection()
    cur = conn.cursor()

    # Трием старите записи за този vendor
    cur.execute("DELETE FROM last_stock WHERE vendor_id = ?;", (vendor_id,))

    # Вмъкваме новите
    rows = []
    for product_id, data in inventory.items():
        rows.append(
            (vendor_id, product_id, data.get("name", ""), int(data.get("qty", 0)))
        )

    if rows:
        cur.executemany(
            """
            INSERT INTO last_stock (vendor_id, product_id, product_name, qty)
            VALUES (?, ?, ?, ?);
            """,
            rows
        )

    conn.commit()
    conn.close()


def get_price(vendor_id: int, product_id: str):
    """Връща цената на даден продукт за даден vendor, ако има такава, иначе None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT unit_price FROM product_prices WHERE vendor_id = ? AND product_id = ?;",
        (vendor_id, product_id)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return float(row["unit_price"])
    return None

def upsert_price(vendor_id: int, product_id: str, product_name: str, unit_price: float):
    """
    Ръчно (или чрез помощен скрипт) може да викнеш това за задаване/обновяване на цена.
    В момента няма да го ползваме от мониторинга, но е полезно за бъдеще.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO product_prices (vendor_id, product_id, product_name, unit_price)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(vendor_id, product_id) DO UPDATE SET
          product_name = excluded.product_name,
          unit_price = excluded.unit_price;
        """,
        (vendor_id, product_id, product_name, unit_price)
    )
    conn.commit()
    conn.close()

def insert_sale(vendor_id: int, product_id: str, product_name: str,
                timestamp: str, quantity: int):
    """
    Вмъква продажба:
    - взима цената от product_prices;
    - ако няма цена – приема 0.0 (ще знаем, че липсва и трябва да я добавим).
    """
    price = get_price(vendor_id, product_id)
    if price is None:
        price = 0.0  # без цена => оборот 0, но имаме лог за бройките

    revenue = quantity * price

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sales (vendor_id, product_id, product_name, timestamp, quantity, unit_price, revenue)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (vendor_id, product_id, product_name, timestamp, quantity, price, revenue)
    )
    conn.commit()
    conn.close()