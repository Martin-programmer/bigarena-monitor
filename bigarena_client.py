import requests
import re
from config import BIGARENA_EMAIL, BIGARENA_PASSWORD

LOGIN_URL = "https://my.bigarena.net/login"
API_URL = "https://my.bigarena.net/orders/get-products"

# Създаваме сесия (помни бисквитките)
session = requests.Session()

# Базови хедъри
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://my.bigarena.net/"
})

def get_csrf_from_html(html_text: str):
    """Вади CSRF токена от meta tag или hidden input."""
    match = re.search(r'<meta name="csrf-token" content="(.*?)">', html_text)
    if match:
        return match.group(1)

    match_input = re.search(r'name="_token" value="(.*?)"', html_text)
    if match_input:
        return match_input.group(1)

    return None

def login() -> bool:
    """Влиза в акаунта и настройва CSRF токените в session headers."""
    print("⏳ Опит за автоматичен вход...")

    try:
        resp = session.get(LOGIN_URL)
        token = get_csrf_from_html(resp.text)

        if not token:
            print("ГРЕШКА: Не мога да намеря CSRF токен на логин страницата.")
            return False

        payload = {
            "_token": token,
            "email": BIGARENA_EMAIL,
            "password": BIGARENA_PASSWORD,
            "remember": "on"
        }

        post_resp = session.post(LOGIN_URL, data=payload)

        if post_resp.status_code == 200:
            # опит да извадим токен от HTML
            dashboard_token = get_csrf_from_html(post_resp.text)
            if dashboard_token:
                session.headers.update({
                    "X-CSRF-TOKEN": dashboard_token,
                    "X-Requested-With": "XMLHttpRequest"
                })
                print("✅ Успешен вход! (CSRF от HTML)")
                return True

            # fallback: от cookie XSRF-TOKEN
            if "XSRF-TOKEN" in session.cookies:
                import urllib.parse
                token_unquoted = urllib.parse.unquote(session.cookies["XSRF-TOKEN"])
                session.headers.update({
                    "X-CSRF-TOKEN": token_unquoted,
                    "X-Requested-With": "XMLHttpRequest"
                })
                print("✅ Успешен вход! (CSRF от cookie XSRF-TOKEN)")
                return True

        print("❌ Неуспешен вход. Провери имейл/парола.")
        return False

    except Exception as e:
        print(f"Грешка при логин: {e}")
        return False

def get_products_for_vendor(vendor_id: int):
    """Взима продуктите за даден vendor_id чрез логнатата сесия."""
    payload = {
        "draw": "1",
        "start": "0",
        "length": "2000",
        "vendor_id": str(vendor_id),
        "search[value]": "",
        "search[regex]": "false"
    }

    try:
        resp = session.post(API_URL, data=payload)

        if resp.status_code == 200:
            try:
                return resp.json().get("data", [])
            except Exception:
                print("Грешка: Отговорът не е валиден JSON.")
                return None
        elif resp.status_code == 419:
            print("⚠️ Сесията е изтекла (419).")
            return "RETRY"
        else:
            print(f"ГРЕШКА: Status {resp.status_code}")
            return None

    except Exception as e:
        print(f"Connection Error: {e}")
        return None
