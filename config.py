import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

def get_env_var(name, default=None, required=False):
    """Получает переменную из env, с проверкой на пустоту и обязательность."""
    value = os.getenv(name, default)
    if required and not value:
        raise EnvironmentError(f"Переменная окружения {name} обязательна и не может быть пустой.")
    return value.strip() if isinstance(value, str) else value

def parse_admin_ids(primary_env, secondary_env):
    """Парсит и возвращает список администраторов."""
    admin_ids = []
    primary = get_env_var(primary_env)
    if primary:
        admin_ids.append(primary)
    secondary = get_env_var(secondary_env)
    if secondary:
        admin_ids.append(secondary)
    return admin_ids

# --- НОВОЕ: Загружаем строку подключения к БД ---
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ПРЕДУПРЕЖДЕНИЕ: DATABASE_URL не задан. Используется локальная SQLite база данных.")
    DATABASE_URL = 'sqlite:///bot_database.db' # Значение по умолчанию для локальной разработки
# ------------------------------------------------

# Конфигурация бота
BOT_TOKEN = get_env_var('BOT_TOKEN', required=True)
DEV_ADMIN_IDS = parse_admin_ids('ADMIN_ID', 'SECONDARY_ADMIN_ID')

# Конфигурация для продакшена
PROD_BOT_TOKEN = get_env_var('PROD_BOT_TOKEN')
PROD_ADMIN_IDS = parse_admin_ids('PROD_ADMIN_ID', 'PROD_SECONDARY_ADMIN_ID')

# Флаг для определения окружения
IS_PRODUCTION = os.getenv('IS_PRODUCTION', '').lower() in ('true', '1', 'on', 'yes')

# Используем правильные значения в зависимости от окружения
if IS_PRODUCTION:
    BOT_TOKEN = PROD_BOT_TOKEN or BOT_TOKEN
    ADMIN_IDS = PROD_ADMIN_IDS or DEV_ADMIN_IDS
else:
    ADMIN_IDS = DEV_ADMIN_IDS

# Убедимся, что список админов не пуст
if not ADMIN_IDS:
    raise EnvironmentError("Не указан ни один администратор (ADMIN_ID).")