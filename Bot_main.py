import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from hand import user

# Загружаем переменные из .env файла
load_dotenv()

async def main():
    print("Запуск...")
    
    # Получаем токен из переменной окружения
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не найден в .env файле!")
        return
    
    bot = Bot(token=bot_token)
    dp = Dispatcher()
    dp.include_router(user)
    print("БОТ ЗАПУЩЕН! Нажмите Ctrl+C для остановки")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), poll_timeout=10)

if __name__ == '__main__':
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        pass