# test_beget_db.py
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

def test_connection():
    try:
        # Получаем данные из .env
        db_url = os.getenv("DATABASE_URL")
        
        # Парсим URL (пример: mysql+pymysql://user:pass@host/db)
        parts = db_url.replace('mysql+pymysql://', '').split('@')
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        
        host = host_db[0]
        database = host_db[1]
        user = user_pass[0]
        password = user_pass[1]
        
        print(f"🔍 Подключаемся к: {host}")
        print(f"📁 База: {database}")
        print(f"👤 Пользователь: {user}")
        
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        print("✅ Подключение к базе успешно!")
        
        # Проверяем можем ли выполнить запрос
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"📊 Таблицы в базе: {tables}")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

if __name__ == "__main__":
    test_connection()