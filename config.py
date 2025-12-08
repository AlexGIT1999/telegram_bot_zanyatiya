import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Конфигурация бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

# Конфигурация для продакшена
PROD_BOT_TOKEN = os.getenv('PROD_BOT_TOKEN')
PROD_ADMIN_ID = os.getenv('PROD_ADMIN_ID')

# Флаг для определения окружения
IS_PRODUCTION = os.getenv('IS_PRODUCTION', 'False').lower() == 'true'
