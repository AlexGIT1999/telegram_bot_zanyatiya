import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Конфигурация бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

# Поддержка нескольких админов
SECONDARY_ADMIN_ID = os.getenv('SECONDARY_ADMIN_ID')
ADMIN_IDS = [ADMIN_ID]
if SECONDARY_ADMIN_ID:
    ADMIN_IDS.append(SECONDARY_ADMIN_ID)

# Конфигурация для продакшена
PROD_BOT_TOKEN = os.getenv('PROD_BOT_TOKEN')
PROD_ADMIN_ID = os.getenv('PROD_ADMIN_ID')

# Конфигурация для нескольких админов в продакшене
PROD_SECONDARY_ADMIN_ID = os.getenv('PROD_SECONDARY_ADMIN_ID')
PROD_ADMIN_IDS = [PROD_ADMIN_ID] if PROD_ADMIN_ID else []
if PROD_SECONDARY_ADMIN_ID:
    PROD_ADMIN_IDS.append(PROD_SECONDARY_ADMIN_ID)

# Флаг для определения окружения
IS_PRODUCTION = os.getenv('IS_PRODUCTION', 'False').lower() == 'true'

# Используем правильные значения в зависимости от окружения
if IS_PRODUCTION:
    BOT_TOKEN = PROD_BOT_TOKEN or BOT_TOKEN
    ADMIN_IDS = PROD_ADMIN_IDS or ADMIN_IDS
