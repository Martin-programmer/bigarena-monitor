import html
import re
from datetime import datetime

from bigarena_client import login, get_products_for_vendor
import db


def clean_product_name(raw_html_name: str) -> str:
    """Изчиства HTML името до чист текст."""
    if not raw_html_name:
        return "Unknown Product"
    decoded_html = html.unescape(raw_html_name)
    match = re.search(r'class="item-data-title">([^<]+)<', decoded_html)
    if match:
        return match.group(1).strip()
    # fallback – махаме всички тагове
    return re.sub(r"<[^>]+>", "", decoded_html).strip()


def process_inventory(products_list):
    """Връща (inventory_dict, total_stock) – само qty и име, без цена."""
    inventory = {}
    total_stock = 0

    for prod in products_list:
        p_id = str(prod.get("id"))
        raw_name = prod.get("name", "")
        clean_name = clean_product_name(raw_name)

        qty = 0
        variants = prod.get("variants", [])
        for v in variants:
            qty += int(v.get("on_hand_quantity", 0))

        inventory[p_id] = {
            "name": clean_name,
            "qty": qty
        }
        total_stock += qty

    return inventory, total_stock


def run_for_vendor(
    vendor_id: int,
    state_file: str,      # вече НЕ се използва за логика, само за съвместимост със стария код
    log_file: str,
    vendor_name: str = "",
    already_logged_in: bool = False
):
    """Логика за един вендор – login (по избор), fetch, сравнение, лог."""
    print(f"\n=== Стартирам проверка за {vendor_name or vendor_id} ===")

    # Инициализираме базата (ако не е готова)
    db.init_db()

    # 1. login (само ако не сме вече логнати глобално)
    if not already_logged_in:
        if not login():
            print("❌ Неуспешен логин, прекратяване.")
            return

    # 2. взимаме данните
    data = get_products_for_vendor(vendor_id)

    # ако сесията е изтекла – опитваме още веднъж
    if data == "RETRY":
        from bigarena_client import session
        print("🔄 Опресняване на сесията и повторен опит...")
        session.cookies.clear()
        if not login():
            print("❌ Неуспешен логин при повторен опит.")
            return
        data = get_products_for_vendor(vendor_id)

    if data is None or data == "RETRY":
        print("❌ Неуспешно извличане на данни за този vendor.")
        return

    # 3. Обработваме текущите наличности
    current_inventory, current_total = process_inventory(data)
    timestamp = datetime.now().strftime("%d.%m.%Y/%H:%M")

    # 4. Взимаме предишното състояние от базата (last_stock)
    previous_inventory = db.get_last_inventory_for_vendor(vendor_id)

    # Ако няма нищо в last_stock за този vendor → приемаме, че е първи рън
    if not previous_inventory:
        msg = (
            f"{timestamp} - ПЪРВОНАЧАЛЕН ЗАПИС [{vendor_name or vendor_id}]. "
            f"Обща наличност: {current_total} бр. "
            f"(Брой уникални продукти: {len(current_inventory)})"
        )
        print(msg)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n" + "-" * 50 + "\n")

        # Записваме текущото състояние в last_stock
        db.replace_inventory_for_vendor(vendor_id, current_inventory)
        return

    # 5. Има предишно състояние – сравняваме
    sales_details = []
    total_sales_count = 0

    for p_id, p_data in current_inventory.items():
        current_qty = p_data["qty"]
        name = p_data["name"]

        if p_id in previous_inventory:
            prev_qty = previous_inventory[p_id]["qty"]
            if current_qty < prev_qty:
                sold = prev_qty - current_qty
                total_sales_count += sold

                # Взимаме цена от базата (ако има)
                price = db.get_price(vendor_id, p_id)
                if price is None:
                    price_info = "⚠️ НЯМА ЦЕНА (оборота ще е 0, добави цена в product_prices)"
                else:
                    price_info = f"цена: {price:.2f}"

                sales_details.append(
                    f"   - {name}: продадени {sold} бр. (Остават: {current_qty}) | {price_info}"
                )

                # Записваме продажбата в таблица sales (цената се взима вътре)
                db.insert_sale(
                    vendor_id=vendor_id,
                    product_id=p_id,
                    product_name=name,
                    timestamp=timestamp,
                    quantity=sold
                )
        else:
            # нов продукт – просто го приемаме като нова наличност
            pass

    header = (
        f"{timestamp} - [{vendor_name or vendor_id}] Обща наличност: {current_total} ; "
        f"Продадени от последната проверка: {total_sales_count}"
    )

    log_lines = [header]
    if sales_details:
        log_lines.append("Детайли за продажбите:")
        log_lines.extend(sales_details)
    else:
        log_lines.append("(Няма засечени продажби)")
    log_lines.append("")

    final_log = "\n".join(log_lines)
    print(final_log)

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(final_log + "\n")

    # 6. Обновяваме състоянието в last_stock за следващия рън
    db.replace_inventory_for_vendor(vendor_id, current_inventory)
