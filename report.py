import db
import sqlite3

def get_daily_revenue(vendor_id: int, date_str: str):
    """
    Връща:
    - общ оборот за даден vendor и дата (формат 'YYYY-MM-DD')
    - списък с продукти: (product_name, quantity, revenue)
    """
    conn = db.get_connection()
    cur = conn.cursor()

    # Общо по ден
    cur.execute(
        """
        SELECT SUM(revenue) AS total_revenue
        FROM sales
        WHERE vendor_id = ?
          AND substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2) = ?;
        """,
        (vendor_id, date_str)
    )
    row = cur.fetchone()
    total_revenue = row["total_revenue"] if row and row["total_revenue"] is not None else 0.0

    # По продукти
    cur.execute(
        """
        SELECT product_name,
               SUM(quantity) AS total_qty,
               SUM(revenue) AS total_product_revenue
        FROM sales
        WHERE vendor_id = ?
          AND substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2) = ?
        GROUP BY product_name
        ORDER BY total_product_revenue DESC;
        """,
        (vendor_id, date_str)
    )

    rows = cur.fetchall()
    conn.close()

    products = [
        {
            "product_name": r["product_name"],
            "quantity": r["total_qty"],
            "revenue": r["total_product_revenue"]
        }
        for r in rows
    ]

    return total_revenue, products

if __name__ == "__main__":
    print("Избери vendor:")
    print("1) WhiteMe (192)")
    print("2) AirWays (419)")
    choice = input("Въведи номер (1 или 2): ").strip()

    if choice == "1":
        vendor_id = 192
    elif choice == "2":
        vendor_id = 419
    else:
        print("Невалиден избор.")
        exit(1)

    date_str = input("Въведи дата (формат YYYY-MM-DD), напр. 2025-12-04: ").strip()

    total_revenue, products = get_daily_revenue(vendor_id, date_str)

    print(f"\nОборот за vendor {vendor_id} на {date_str}: {total_revenue:.2f} лв.\n")
    print("По продукти:")
    for p in products:
        print(f"- {p['product_name']}: {p['quantity']} бр. | {p['revenue']:.2f} лв.")

