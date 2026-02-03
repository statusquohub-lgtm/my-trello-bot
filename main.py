import os
import requests
from aiogram import Bot, Dispatcher, executor, types
from groq import Groq

# Koyeb сам подставит эти данные из раздела Environment Variables
API_TOKEN = os.getenv('API_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
TRELLO_KEY = os.getenv('TRELLO_KEY')
TRELLO_TOKEN = os.getenv('TRELLO_TOKEN')
TRELLO_LIST_ID = os.getenv('TRELLO_LIST_ID')

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
groq_client = Groq(api_key=GROQ_API_KEY)

@dp.message_handler(content_types=['voice'])
async def handle_voice(message: types.Message):
    # 1. Скачиваем голосовое сообщение
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    destination = f"{file_id}.ogg"
    await bot.download_file(file_path, destination)

    # 2. Превращаем голос в текст через Groq (Whisper)
    with open(destination, "rb") as audio_file:
        transcription = groq_client.audio.transcriptions.create(
            file=(destination, audio_file.read()),
            model="whisper-large-v3",
        )
    
    raw_text = transcription.text

    # 3. Просим нейросеть сделать из текста короткую задачу
    completion = groq_client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "Ты помощник, который кратко формулирует задачу для Trello из текста. Пиши только саму задачу, без лишних слов."},
            {"role": "user", "content": raw_text}
        ]
    )
    task_name = completion.choices[0].message.content

    # 4. Отправляем в Trello
    url = "https://api.trello.com/1/cards"
    query = {
        'key': TRELLO_KEY,
        'token': TRELLO_TOKEN,
        'idList': TRELLO_LIST_ID,
        'name': task_name,
        'desc': f"Оригинал: {raw_text}"
    }
    
    response = requests.post(url, params=query)
    
    if response.status_code == 200:
        await message.reply(f"🚀 **Задача создана:** {task_name}")
    else:
        await message.reply("Ошибка при добавлении в Trello. Проверь ключи!")

    # Удаляем временный файл
    os.remove(destination)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
