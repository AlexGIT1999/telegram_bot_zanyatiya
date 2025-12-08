import telebot
import config
from handlers import client_handlers, admin_handlers
import reminders

# Получаем токен и список админов из конфига
BOT_TOKEN = config.BOT_TOKEN
ADMIN_IDS = config.ADMIN_IDS

if not BOT_TOKEN:
    raise ValueError("Не найден токен бота. Проверь файл .env")

# Создаем бота
bot = telebot.TeleBot(BOT_TOKEN)

# Настраиваем команды меню
def setup_bot_commands():
    """Настраиваем команды бота"""
    commands = [
        telebot.types.BotCommand("/start", "Главное меню"),
        telebot.types.BotCommand("/help", "Помощь"),
        telebot.types.BotCommand("/admin", "Админ панель"),
        telebot.types.BotCommand("/admin_help", "Помощь администратора"),
    ]
    bot.set_my_commands(commands)

# Инициализируем данные бота
admin_handlers.init_bot_data(bot)

# Регистрируем обработчики
client_handlers.register_client_handlers(bot, ADMIN_IDS)
admin_handlers.register_admin_handlers(bot, ADMIN_IDS)

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    print(f"Администраторские ID: {ADMIN_IDS}")
    print(f"Production mode: {config.IS_PRODUCTION}")
    
    # Настраиваем команды меню
    setup_bot_commands()
    
    # Запускаем напоминания (только в продакшене или для тестирования)
    if config.IS_PRODUCTION or True:  # Всегда запускаем для тестирования
        reminders.setup_reminders(bot)
    
    bot.polling(none_stop=True)
