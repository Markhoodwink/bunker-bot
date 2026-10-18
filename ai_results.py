import os
from groq import Groq
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Инициализация клиента Groq
# Убедись, что в .env файле есть строка: GROQ_API_KEY=gsk_...
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_final_verdict(game):
    """Генерирует итог игры с помощью нейросети Qwen через Groq"""
    
    # 1. Собираем данные об условиях
    cat = game["scenario"]["catastrophe"]
    bun = game["scenario"]["bunker"]
    
    # 2. Собираем данные о выживших
    survivors_text = ""
    for pid in game["players"]:
        card = game["cards"][pid]
        survivors_text += f"- {card['profession']}, Здоровье: {card['health']} {card['biology']}, Навык: {card['skill']}, Инвентарь: {card['inventory']}\n"
        
    # 3. Собираем данные о погибших
    exiled_text = ""
    for pid in game["exiled"]:
        card = game["cards"].get(pid, "Неизвестно") 
        if isinstance(card, dict):
            exiled_text += f"- {card['profession']}, Здоровье: {card['health']} {card['biology']}, Навык: {card['skill']}, Инвентарь: {card['inventory']}\n"
        else:
            exiled_text += f"- Игрок {pid}\n"

    # 4. Формируем ПРОМПТ (запрос к нейросети)
    prompt = f"""
    Ты — циничный, но справедливый ИИ-наблюдатель, который анализирует выживание человечества. 
    Напиши драматичный и логичный итог игры «Бункер» на русском языке. Используй эмодзи и HTML-теги (<b>, <i>) для выделения главного.

    🌍 КАТАСТРОФА: {cat['name']} ({cat['description']})
    🏠 БУНКЕР: {bun['name']} (Вместимость: {bun['capacity']}. Ресурсы: {bun['resources']})

    ✅ ВЫЖИЛИ (прошли в бункер):
    {survivors_text}

    💀 ПОГИБЛИ (были изгнаны):
    {exiled_text}

    ТВОЯ ЗАДАЧА:
    1. Краткий вердикт: процентный шанс выживания, насколько удачным получился состав для выживания в ЭТИХ конкретных условиях.
    2. Разбор выживших: чем именно их навыки или инвентарь спасли группу? (Например: "Инженер починил фильтры").
    3. Разбор погибших: была ли это ошибка? Могли ли они быть полезны, или их изгнание было верным решением?
    4. В конце сделай мрачный или ироничный вывод о человеческой природе, и можно ли было сделать выбор лучше?.
    """

    # 5. Отправляем запрос к нейросети через Groq
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b", # Быстрая и очень умная модель Qwen на Groq
            messages=[
                {"role": "system", "content": "Ты полезный и драматичный помощник. Отвечай строго на русском языке, используя HTML-теги <b> и <i> для выделения."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Нейросеть не смогла оценить ваш выбор. Ошибка: {e}"