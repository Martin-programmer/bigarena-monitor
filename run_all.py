import time
from monitor import run_for_vendor
from vendors_config import VENDORS
from bigarena_client import login  # <-- важно

if __name__ == "__main__":
    print("=== Стартирам общ мониторинг за всички вендори ===")

    # 1. Логваме се веднъж
    if not login():
        print("❌ Глобален логин неуспешен. Прекратявам.")
        exit(1)

    # 2. Минаваме през всички вендори, ползвайки вече логнатата сесия
    for v in VENDORS:
        name = v["name"]
        vendor_id = v["vendor_id"]
        state_file = v["state_file"]
        log_file = v["log_file"]

        run_for_vendor(
            vendor_id=vendor_id,
            state_file=state_file,
            log_file=log_file,
            vendor_name=name,
            already_logged_in=True  # <-- КАЗВАМЕ, ЧЕ СМЕ ВЕЧЕ ЛОГНАТИ
        )

        time.sleep(5)

    print("=== Мониторингът приключи за всички вендори ===")
