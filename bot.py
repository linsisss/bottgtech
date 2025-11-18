import gspread
from google.oauth2.service_account import Credentials
import requests
import time
import os

# Настройки
SERVICE_ACCOUNT_FILE = 'service-account.json'
SPREADSHEET_ID = '13gis15gvu6iplVr-YiSf9dGyApMBPzGd6MEmkI7xM_Q'
BOT_TOKEN = "8069522685:AAEPLR66tlwY9GlSAFd60ZyE4BmIznwdv5s"

# Проверка наличия файла
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    print(f"❌ Файл {SERVICE_ACCOUNT_FILE} не найден!")
    print("Текущая папка:", os.getcwd())
    print("Файлы в папке:", os.listdir('.'))
    exit(1)

# Остальной код без изменений...
user_positions = {}

def get_google_sheet():
    """Подключение к Google таблице"""
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ])
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        return sheet
    except Exception as e:
        print(f"Ошибка подключения к Google Sheets: {e}")
        return None

def get_all_rows():
    """Получение всех заполненных строк"""
    try:
        sheet = get_google_sheet()
        if not sheet:
            return []
        
        all_data = sheet.get_all_values()
        # Фильтруем пустые строки
        non_empty_rows = []
        for row in all_data:
            if any(cell.strip() for cell in row):
                non_empty_rows.append(row)
        return non_empty_rows
    except Exception as e:
        print(f"Ошибка получения данных: {e}")
        return []

def send_message(chat_id, text):
    """Отправка сообщения через Telegram API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        return None

def format_row_data(row):
    """Форматирование строки для вывода"""
    formatted_parts = []
    for cell in row:
        if cell.strip():
            formatted_parts.append(cell)
    
    if not formatted_parts:
        return "Нет данных о клубе"
    
    return "\n".join(formatted_parts)

def process_update(update):
    """Обработка входящего обновления"""
    if "message" not in update:
        return
    
    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    
    user_id = chat_id
    
    # Инициализация позиции
    if user_id not in user_positions:
        user_positions[user_id] = 0
    
    # Команда /start
    if text == "/start":
        user_positions[user_id] = 0
        send_message(chat_id, 
            "👋 Привет! Я бот для выдачи клубов для проверки.\n\n"
            "Отправь любое сообщение или /next чтобы получить следующий клуб."
        )
        return
    
    # Команда /reset
    if text == "/reset":
        user_positions[user_id] = 0
        send_message(chat_id, "🔄 Прогресс сброшен! Начинаем с первого клуба.")
        return
    
    # Команда /status
    if text == "/status":
        all_rows = get_all_rows()
        current_pos = user_positions[user_id]
        total_clubs = len(all_rows)
        remaining = max(0, total_clubs - current_pos)
        
        send_message(chat_id,
            f"📊 Статус проверки:\n"
            f"✅ Проверено: {current_pos}\n"
            f"🔄 Осталось: {remaining}\n"
            f"📋 Всего клубов: {total_clubs}"
        )
        return
    
    # Любое другое сообщение или /next
    all_rows = get_all_rows()
    
    if not all_rows:
        send_message(chat_id, "❌ Не удалось загрузить данные из таблицы")
        return
    
    current_pos = user_positions[user_id]
    
    if current_pos < len(all_rows):
        current_row = all_rows[current_pos]
        club_info = format_row_data(current_row)
        user_positions[user_id] += 1
        
        send_message(chat_id, f"🎯 Клуб для проверки #{current_pos + 1}:\n\n{club_info}")
    else:
        send_message(chat_id, "📭 Больше клубов для проверки пока что нет, проверьте позже")

def get_updates(offset=None):
    """Получение обновлений от Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    
    try:
        response = requests.get(url, params=params, timeout=35)
        return response.json()
    except Exception as e:
        print(f"Ошибка получения обновлений: {e}")
        return {"ok": False}

def main():
    """Основная функция бота"""
    print("Бот запущен...")
    
    last_update_id = None
    
    while True:
        try:
            # Получаем обновления
            result = get_updates(offset=last_update_id)
            
            if result.get("ok"):
                updates = result["result"]
                if updates:
                    for update in updates:
                        process_update(update)
                        last_update_id = update["update_id"] + 1
            else:
                print("Ошибка при получении обновлений")
                
            # Небольшая пауза между запросами
            time.sleep(1)
            
        except Exception as e:
            print(f"Ошибка в главном цикле: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
