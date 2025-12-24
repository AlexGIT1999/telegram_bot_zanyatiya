import psycopg2
from psycopg2.extras import RealDictCursor
import config
from datetime import datetime

# Используем строку подключения из config.py
DATABASE_URL = config.DATABASE_URL

def get_db_connection():
    """Создает и возвращает соединение с PostgreSQL."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    """Создает таблицы в PostgreSQL, если они не существуют."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Таблица пользователей (остаётся без изменений)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            parent_name TEXT NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица слотов (остаётся без изменений)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slots (
            id SERIAL PRIMARY KEY,
            date TEXT NOT NULL, -- в формате 'DD.MM.YYYY'
            time TEXT NOT NULL, -- в формате 'HH:MM-HH:MM'
            available BOOLEAN DEFAULT TRUE,
            deleted_by_admin BOOLEAN DEFAULT FALSE
        )
    ''')

    # Уникальный индекс (остаётся без изменений)
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_slots_date_time ON slots (date, time);
    ''')

    # Таблица записей (ИЗМЕНЕНО: добавлен parent_name)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            date TEXT NOT NULL, -- в формате 'DD.MM.YYYY'
            time TEXT NOT NULL, -- в формате 'HH:MM-HH:MM'
            child_name TEXT NOT NULL,
            phone TEXT,
            parent_name TEXT, -- <-- НОВОЕ ПОЛЕ
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed BOOLEAN DEFAULT FALSE,
            cancelled_by_user BOOLEAN DEFAULT FALSE,
            cancelled_by_admin BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Добавляем столбец, если его нет (на случай, если таблица уже существует)
    try:
        cursor.execute('ALTER TABLE bookings ADD COLUMN parent_name TEXT;')
    except psycopg2.errors.DuplicateColumn:
        pass # Столбец уже существует, всё ок
    conn.commit()

    # Таблица домашних заданий (остаётся без изменений)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS homeworks (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            file_type TEXT NOT NULL,
            comment TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_by_admin_id BIGINT,
            FOREIGN KEY (booking_id) REFERENCES bookings (id)
        )
    ''')

    conn.commit()
    conn.close()
    print("База данных PostgreSQL инициализирована.")

# --- Функции для работы с пользователями ---

def load_users():
    """Загружает всех пользователей из БД."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, parent_name, phone, created_at FROM users')
    rows = cursor.fetchall()
    conn.close()

    users = {}
    for row in rows:
        users[str(row['user_id'])] = {
            'parent_name': row['parent_name'],
            'phone': row['phone'],
            'created_at': row['created_at']
        }
    return users

def save_user(user_id, parent_name, phone):
    """Сохраняет или обновляет данные пользователя в БД."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # INSERT ... ON CONFLICT DO UPDATE (аналог REPLACE в SQLite)
    cursor.execute('''
        INSERT INTO users (user_id, parent_name, phone)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET parent_name = EXCLUDED.parent_name, phone = EXCLUDED.phone;
    ''', (user_id, parent_name, phone))
    conn.commit()
    conn.close()

# --- Функции для работы со слотами ---

def load_slots():
    """Загружает все слоты из БД и возвращает в старом формате (dict)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, date, time, available, deleted_by_admin FROM slots ORDER BY date, time')
    rows = cursor.fetchall()
    conn.close()

    slots = {}
    for row in rows:
        date = row['date']
        if date not in slots:
            slots[date] = []
        slots[date].append({
            'id': row['id'],
            'time': row['time'],
            'available': row['available'],
            'deleted_by_admin': row['deleted_by_admin']
        })
    return slots

def save_slots(slots_dict):
    """Полностью перезаписывает слоты в БД из словаря."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Удаляем все старые слоты
    cursor.execute('DELETE FROM slots')

    # Вставляем новые слоты
    for date, date_slots in slots_dict.items():
        for slot in date_slots:
            cursor.execute('''
                INSERT INTO slots (date, time, available, deleted_by_admin)
                VALUES (%s, %s, %s, %s)
            ''', (date, slot['time'], slot.get('available', True), slot.get('deleted_by_admin', False)))

    conn.commit()
    conn.close()

def add_slot(date, time, available=True):
    """Добавляет новый слот в БД."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO slots (date, time, available)
            VALUES (%s, %s, %s)
        ''', (date, time, available))
        conn.commit()
    except psycopg2.IntegrityError:
        print(f"Слот {date} {time} уже существует.")
    conn.close()

def update_slot(slot_id, available=None, deleted_by_admin=None):
    """Обновляет статус слота по ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    updates = []
    params = []

    if available is not None:
        updates.append('available = %s')
        params.append(available)
    if deleted_by_admin is not None:
        updates.append('deleted_by_admin = %s')
        params.append(deleted_by_admin)

    if updates:
        params.append(slot_id)
        query = f"UPDATE slots SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(query, params)
        conn.commit()
    conn.close()

def delete_slot_by_datetime(date, time):
    """Удаляет слот по дате и времени (ставит deleted_by_admin = 1)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE slots SET deleted_by_admin = TRUE, available = FALSE WHERE date = %s AND time = %s
    ''', (date, time))
    conn.commit()
    conn.close()

# --- Функции для работы с записями ---

def load_bookings():
    """Загружает все записи из БД и возвращает в старом формате (list)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # ИЗМЕНЕНО: SELECT теперь включает parent_name
    cursor.execute('''
        SELECT id, user_id, date, time, child_name, phone, parent_name, timestamp, confirmed, cancelled_by_user, cancelled_by_admin
        FROM bookings
        ORDER BY date, time
    ''')
    rows = cursor.fetchall()
    conn.close()

    bookings = []
    for row in rows:
        bookings.append({
            'id': row['id'],
            'user_id': row['user_id'],
            'date': row['date'],
            'time': row['time'],
            'child_name': row['child_name'],
            'phone': row['phone'],
            'parent_name': row['parent_name'], # <-- НОВОЕ ПОЛЕ
            'timestamp': row['timestamp'],
            'confirmed': row['confirmed'],
            'cancelled_by_user': row['cancelled_by_user'],
            'cancelled_by_admin': row['cancelled_by_admin']
        })
    return bookings

def save_booking(booking_data):
    """Сохраняет новую запись в БД."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # ИЗМЕНЕНО: INSERT теперь включает parent_name
    cursor.execute('''
        INSERT INTO bookings (user_id, date, time, child_name, phone, parent_name, confirmed, cancelled_by_user, cancelled_by_admin)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        booking_data['user_id'],
        booking_data['date'],
        booking_data['time'],
        booking_data['child_name'],
        booking_data['phone'],
        booking_data.get('parent_name'), # <-- Используем parent_name из booking_data
        booking_data.get('confirmed', False),
        booking_data.get('cancelled_by_user', False),
        booking_data.get('cancelled_by_admin', False)
    ))
    conn.commit()
    conn.close()

def save_bookings(bookings_list):
    """Полностью перезаписывает все записи в БД."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Удаляем все старые записи
    cursor.execute('DELETE FROM bookings')

    # Вставляем новые записи (ИЗМЕНЕНО: включая parent_name)
    for booking in bookings_list:
        cursor.execute('''
            INSERT INTO bookings (user_id, date, time, child_name, phone, parent_name, timestamp, confirmed, cancelled_by_user, cancelled_by_admin)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            booking['user_id'],
            booking['date'],
            booking['time'],
            booking['child_name'],
            booking['phone'],
            booking.get('parent_name'), # <-- Используем parent_name из booking
            booking.get('timestamp', datetime.now()),
            booking.get('confirmed', False),
            booking.get('cancelled_by_user', False),
            booking.get('cancelled_by_admin', False)
        ))

    conn.commit()
    conn.close()

def update_booking(booking_id, confirmed=None, cancelled_by_user=None, cancelled_by_admin=None, parent_name=None):
    """Обновляет статус записи по ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    updates = []
    params = []

    if confirmed is not None:
        updates.append('confirmed = %s')
        params.append(confirmed)
    if cancelled_by_user is not None:
        updates.append('cancelled_by_user = %s')
        params.append(cancelled_by_user)
    if cancelled_by_admin is not None:
        updates.append('cancelled_by_admin = %s')
        params.append(cancelled_by_admin)
    if parent_name is not None: # <-- Возможность обновить parent_name
        updates.append('parent_name = %s')
        params.append(parent_name)

    if updates:
        params.append(booking_id)
        query = f"UPDATE bookings SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(query, params)
        conn.commit()
    conn.close()

def delete_booking_by_datetime_user_id(date, time, user_id):
    """Удаляет запись по дате, времени и user_id (ставит cancelled_by_user = 1)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE bookings SET cancelled_by_user = TRUE WHERE date = %s AND time = %s AND user_id = %s
    ''', (date, time, user_id))
    conn.commit()
    conn.close()

# --- Функции для работы с домашними заданиями ---

def save_homework(booking_id, file_id, file_type, comment, sent_by_admin_id):
    """Сохраняет домашнее задание в БД."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO homeworks (booking_id, file_id, file_type, comment, sent_by_admin_id)
        VALUES (%s, %s, %s, %s, %s)
    ''', (booking_id, file_id, file_type, comment, sent_by_admin_id))
    conn.commit()
    conn.close()

def load_homeworks_for_user(user_id):
    """Загружает все ДЗ для конкретного пользователя."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Присоединяем bookings, чтобы получить booking_id, связанный с user_id
    cursor.execute('''
        SELECT h.id, h.booking_id, h.file_id, h.file_type, h.comment, h.sent_at, h.sent_by_admin_id
        FROM homeworks h
        JOIN bookings b ON h.booking_id = b.id
        WHERE b.user_id = %s
        ORDER BY h.sent_at DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()

    homeworks = []
    for row in rows:
        homeworks.append({
            'id': row['id'],
            'booking_id': row['booking_id'],
            'file_id': row['file_id'],
            'file_type': row['file_type'],
            'comment': row['comment'],
            'sent_at': row['sent_at'],
            'sent_by_admin_id': row['sent_by_admin_id']
        })
    return homeworks

def load_homeworks_by_booking_id(booking_id):
    """Загружает ДЗ по ID записи."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, file_id, file_type, comment, sent_at, sent_by_admin_id
        FROM homeworks
        WHERE booking_id = %s
        ORDER BY sent_at DESC
    ''', (booking_id,))
    rows = cursor.fetchall()
    conn.close()

    homeworks = []
    for row in rows:
        homeworks.append({
            'id': row['id'],
            'file_id': row['file_id'],
            'file_type': row['file_type'],
            'comment': row['comment'],
            'sent_at': row['sent_at'],
            'sent_by_admin_id': row['sent_by_admin_id']
        })
    return homeworks

def load_past_bookings_for_homework():
    """Загружает прошедшие и неотменённые записи, для которых можно отправить ДЗ."""
    from datetime import datetime
    now = datetime.now()

    conn = get_db_connection()
    cursor = conn.cursor()
    # Сравниваем дату и время записи с текущим
    cursor.execute('''
        SELECT id, user_id, date, time, child_name, phone, parent_name -- <-- parent_name добавлено сюда
        FROM bookings
        WHERE cancelled_by_user = FALSE AND cancelled_by_admin = FALSE
        AND to_timestamp(date || ' ' || left(time, 5), 'DD.MM.YYYY HH24:MI') < %s
        ORDER BY date DESC, time DESC
    ''', (now,))
    rows = cursor.fetchall()
    conn.close()

    bookings = []
    for row in rows:
        bookings.append({
            'id': row['id'],
            'user_id': row['user_id'],
            'date': row['date'],
            'time': row['time'],
            'child_name': row['child_name'],
            'phone': row['phone'],
            'parent_name': row['parent_name'], # <-- parent_name добавлено сюда
        })
    return bookings
