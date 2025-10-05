# Импорт необходимых библиотек
import sqlite3      # Библиотека для работы с SQLite базой данных
import json        # Библиотека для работы с JSON форматом
from datetime import datetime  # Библиотека для работы с датой и временем
import threading   # Библиотека для обеспечения потокобезопасности
import os

#константы путей к файлам
AUTH_CACHE_FILE = 'auth_cache.json'
CHAT_DB_NAME = 'chat_cache.db'

class CacheManager:
    """
    Менеджер кэша для хранения и извлечения данных аутентификации и чата.
    """
    
    def __init__(self):
        """
        Инициализирует менеджер кэша и загружает данные аутентификации.
        """
        self.auth_data = {}  #словарь для хранения данных аутентификации
        self._load_auth_cache()
    
    def _load_auth_cache(self):
        """
        Внутренняя функция для загрузки данных аутентификации из файла.
        """
        if os.path.exists(AUTH_CACHE_FILE):
            with open(AUTH_CACHE_FILE, 'r') as f:
                self.auth_data = json.load(f)
    
    def save_auth_cache(self):
        """
        Сохраняет данные аутентификации в файл.
        """
        with open(AUTH_CACHE_FILE, 'w') as f:
            json.dump(self.auth_data, f)
    
    def update_auth_data(self, api_key=None, pin=None):
        """
        Обновляет данные аутентификации.
        
        Args:
            api_key (str): Новый API ключ (если передан)
            pin (str): Новый PIN-код (если передан)
        """
        if api_key:
            self.auth_data['api_key'] = api_key
        if pin:
            self.auth_data['pin'] = pin
        self.save_auth_cache()
    
    def has_auth_data(self):
        """
        Возвращает True, если данные аутентификации существуют.
        """
        return 'api_key' in self.auth_data and 'pin' in self.auth_data
    
    def get_auth_data(self):
        """
        Возвращает текущий API ключ и PIN-код.
        """
        return self.auth_data.get('api_key'), self.auth_data.get('pin')
    
    def clear_auth_data(self):
        """
        Полностью очищает данные аутентификации.
        """
        self.auth_data = {}
        self.save_auth_cache()

class ChatCache:
    """
    Класс для кэширования истории чата в SQLite базе данных.
    
    Обеспечивает:
    - Потокобезопасное хранение истории сообщений
    - Сохранение метаданных (модель, токены, время)
    - Форматированный вывод истории
    - Очистку истории
    """
    
    def __init__(self):
        """
        Инициализация системы кэширования.
        
        Создает:
        - Файл базы данных SQLite
        - Потокобезопасное хранилище соединений
        - Необходимые таблицы в базе данных
        """
        #имя файла SQLite базы данных
        self.db_name = 'chat_cache.db'
        
        #создание потокобезопасного хранилища соединений
        #каждый поток будет иметь свое собственное соединение с базой
        self.local = threading.local()
        
        #создание необходимых таблиц при инициализации
        self.create_tables()

    def get_connection(self):
        """
        Получение соединения с базой данных для текущего потока.
        
        Returns:
            sqlite3.Connection: Объект соединения с базой данных
            
        Note:
            Каждый поток получает свое собственное соединение,
            что обеспечивает потокобезопасность работы с базой.
        """
        #проверяем, есть ли уже соединение в текущем потоке
        if not hasattr(self.local, 'connection'):
            #если соединения нет - создаем новое
            self.local.connection = sqlite3.connect(self.db_name)
        return self.local.connection

    def create_tables(self):
        """
        Создание необходимых таблиц в базе данных.
        
        Создает таблицу messages со следующими полями:
        - id: уникальный идентификатор сообщения
        - model: идентификатор использованной модели
        - user_message: текст сообщения пользователя
        - ai_response: ответ AI модели
        - timestamp: время создания сообщения
        - tokens_used: количество использованных токенов
        """
        #создаем новое соединение с базой
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        #SQL запросы для создания таблиц
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Уникальный ID сообщения
                model TEXT,                           -- Идентификатор модели
                user_message TEXT,                    -- Текст от пользователя
                ai_response TEXT,                     -- Ответ от AI
                timestamp DATETIME,                   -- Время создания
                tokens_used INTEGER                   -- Использовано токенов
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                model TEXT,
                message_length INTEGER,
                response_time FLOAT,
                tokens_used INTEGER
            )
        ''')
        
        conn.commit()  #сохранение изменений в базе
        conn.close()   #закрытие соединения

    def save_message(self, model, user_message, ai_response, tokens_used):
        """
        Сохранение нового сообщения в базу данных.
        
        Args:
            model (str): Идентификатор использованной модели
            user_message (str): Текст сообщения пользователя
            ai_response (str): Ответ AI модели
            tokens_used (int): Количество использованных токенов
        """
        conn = self.get_connection()  #получение соединения для текущего потока
        cursor = conn.cursor()
        
        #вставка новой записи в таблицу messages
        cursor.execute('''
            INSERT INTO messages (model, user_message, ai_response, timestamp, tokens_used)
            VALUES (?, ?, ?, ?, ?)
        ''', (model, user_message, ai_response, datetime.now(), tokens_used))
        conn.commit()  #сохранение изменений

    def get_chat_history(self, limit=50):
        """
        Получение последних сообщений из истории чата.
        
        Args:
            limit (int): Максимальное количество возвращаемых сообщений
            
        Returns:
            list: Список кортежей с данными сообщений, отсортированных
                 по времени в обратном порядке (новые сначала)
        """
        conn = self.get_connection()  #получение соединения для текущего потока
        cursor = conn.cursor()
        
        #получение последних сообщений с ограничением по количеству
        cursor.execute('''
            SELECT * FROM messages
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()  #возврат всех найденных записей

    def save_analytics(self, timestamp, model, message_length, response_time, tokens_used):
        """
        Сохранение данных аналитики в базу данных.
        
        Args:
            timestamp (datetime): Время создания записи
            model (str): Идентификатор использованной модели
            message_length (int): Длина сообщения
            response_time (float): Время ответа
            tokens_used (int): Количество использованных токенов
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO analytics_messages
            (timestamp, model, message_length, response_time, tokens_used)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, model, message_length, response_time, tokens_used))
        conn.commit()

    def get_analytics_history(self):
        """
        Получение всей истории аналитики.
        
        Returns:
            list: Список записей аналитики
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, model, message_length, response_time, tokens_used
            FROM analytics_messages
            ORDER BY timestamp ASC
        ''')
        return cursor.fetchall()

    def __del__(self):
        """
        Деструктор класса.
        
        Закрывает соединения с базой данных при уничтожении объекта,
        предотвращая утечки ресурсов.
        """
        #проверка наличия соединения в текущем потоке
        if hasattr(self.local, 'connection'):
            self.local.connection.close()  #закрытие соединения
            
    def clear_history(self):
        """
        Очистка всей истории сообщений.
        
        Удаляет все записи из таблицы messages,
        эффективно очищая всю историю чата.
        """
        conn = self.get_connection()  # Получение соединения
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages')  # Удаление всех записей
        conn.commit()  # Сохранение изменений

    def get_formatted_history(self):
        """
        Получение отформатированной истории диалога.
        
        Returns:
            list: Список словарей с данными сообщений в формате:
                {
                    "id": int,              # ID сообщения
                    "model": str,           # Использованная модель
                    "user_message": str,    # Сообщение пользователя
                    "ai_response": str,     # Ответ AI
                    "timestamp": datetime,  # Время создания
                    "tokens_used": int      # Использовано токенов
                }
        """
        conn = self.get_connection()  # Получение соединения
        cursor = conn.cursor()
        
        # Получение всех сообщений, отсортированных по времени
        cursor.execute('''
            SELECT
                id,
                model,
                user_message,
                ai_response,
                timestamp,
                tokens_used
            FROM messages
            ORDER BY timestamp ASC
        ''')
        
        # Формирование списка словарей с данными сообщений
        history = []
        for row in cursor.fetchall():
            history.append({
                "id": row[0],              # ID сообщения
                "model": row[1],           # Использованная модель
                "user_message": row[2],    # Сообщение пользователя
                "ai_response": row[3],     # Ответ AI
                "timestamp": row[4],       # Временная метка
                "tokens_used": row[5]      # Использовано токенов
            })
        return history  # Возврат форматированной истории