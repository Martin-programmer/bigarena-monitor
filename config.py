from dotenv import load_dotenv
import os

# Зареждаме .env файла
load_dotenv()

BIGARENA_EMAIL = os.getenv("BIGARENA_EMAIL")
BIGARENA_PASSWORD = os.getenv("BIGARENA_PASSWORD")

# Проверка, за да не се чудим ако липсват
if not BIGARENA_EMAIL or not BIGARENA_PASSWORD:
    raise RuntimeError("Липсват BIGARENA_EMAIL или BIGARENA_PASSWORD в .env файла.")