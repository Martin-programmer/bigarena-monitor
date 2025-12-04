import json

def generate_inserts_from_state(state_file: str, vendor_id: int):
    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    values = []
    for product_id, info in data.items():
        name = info.get("name", "").replace("'", "''")  # escape на '
        values.append(
            f"( {vendor_id}, '{product_id}', '{name}', 0 )"
        )

    sql = (
        "INSERT INTO product_prices (vendor_id, product_id, product_name, unit_price) VALUES\n"
        + ",\n".join(values)
        + ";"
    )

    return sql

if __name__ == "__main__":
    # Пример за AirWays:
    state_file = "airways_inventory_state.json"
    vendor_id = 419

    sql = generate_inserts_from_state(state_file, vendor_id)
    print(sql)
