import db
import pandas as pd


def get_daily_revenue(vendor_id: int, date_str: str):
    """
    Връща:
    - общ оборот за даден vendor и дата (формат 'YYYY-MM-DD')
    - списък с продукти: {product_name, quantity, revenue}
    """
    engine = db.get_sqlalchemy_engine()

    # Общо по ден
    query_total = """
        SELECT SUM(revenue) AS total_revenue
        FROM sales
        WHERE vendor_id = ?
          AND substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2) = ?;
    """
    total_df = pd.read_sql_query(query_total, engine, params=(vendor_id, date_str))
    total_revenue = float(total_df["total_revenue"].iloc[0]) if not total_df.empty and total_df["total_revenue"].iloc[0] is not None else 0.0

    # По продукти
    query_products = """
        SELECT product_name,
               SUM(quantity) AS quantity,
               SUM(revenue) AS revenue
        FROM sales
        WHERE vendor_id = ?
          AND substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2) = ?
        GROUP BY product_name
        ORDER BY revenue DESC;
    """
    products_df = pd.read_sql_query(query_products, engine, params=(vendor_id, date_str))

    products = []
    if not products_df.empty:
        for _, row in products_df.iterrows():
            products.append(
                {
                    "product_name": row["product_name"],
                    "quantity": int(row["quantity"]),
                    "revenue": float(row["revenue"]),
                }
            )

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
