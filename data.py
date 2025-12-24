import sqlite3
import config
from datetime import datetime

DATABASE_PATH = config.DATABASE_PATH or 'bot_database.db' # Используем путь из config или по умолчанию

def get_db_connection():
    """Создает и возвращает соединение с БД с Row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # Позволяет обращаться к столбцам по имени
    return conn

def init_db():
    """Создает таблицы в БД, если они не существуют."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            parent_name TEXT NOT NULL,
            phone TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица слотов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, -- в формате 'DD.MM.YYYY'
            time TEXT NOT NULL, -- в формате 'HH:MM-HH:MM'
            available BOOLEAN DEFAULT 1,
            deleted_by_admin BOOLEAN DEFAULT 0
        )
    ''')

    # Уникальный индекс, чтобы не было дубликатов слотов (дата + время)
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_slots_date_time ON slots (date, time);
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS homeworks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            file_type TEXT NOT NULL,
            comment TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            sent_by_admin_id INTEGER,
            FOREIGN KEY (booking_id) REFERENCES bookings (id)
        )
    ''')

    # Таблица записей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL, -- в формате 'DD.MM.YYYY'
            time TEXT NOT NULL, -- в формате 'HH:MM-HH:MM'
            child_name TEXT NOT NULL,
            phone TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            confirmed BOOLEAN DEFAULT 0,
            cancelled_by_user BOOLEAN DEFAULT 0,
            cancelled_by_admin BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    conn.commit()
    conn.close()
    print("База данных инициализирована.")


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
    # INSERT OR REPLACE обновит запись, если user_id уже существует
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, parent_name, phone)
        VALUES (?, ?, ?)
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
            'id': row['id'], # Добавим ID слота для удобства
            'time': row['time'],
            'available': bool(row['available']),
            'deleted_by_admin': bool(row['deleted_by_admin'])
        })
    return slots

def save_homework(booking_id, file_id, file_type, comment, sent_by_admin_id):
    """Сохраняет домашнее задание в БД."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO homeworks (booking_id, file_id, file_type, comment, sent_by_admin_id)
        VALUES (?, ?, ?, ?, ?)
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
        WHERE b.user_id = ?
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
        WHERE booking_id = ?
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
    # Формат даты в bookings - 'DD.MM.YYYY', время - 'HH:MM-HH:MM'
    cursor.execute('''
        SELECT id, user_id, date, time, child_name, phone
        FROM bookings
        WHERE cancelled_by_user = 0 AND cancelled_by_admin = 0
        AND datetime(date || ' ' || substr(time, 1, 5), '+1 hour') < ?
        ORDER BY date DESC, time DESC
    ''', (now.isoformat(),)) # Это работает в SQLite, если формат даты и времени корректный
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
            'phone': row['phone']
        })
    return bookings

def save_slots(slots_dict):
    """
    Полностью перезаписывает слоты в БД из словаря.
    ВНИМАНИЕ: Это может быть неэффективно для больших объемов данных.
    Лучше использовать update_slot или delete_slot + add_slot.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Удаляем все старые слоты (осторожно!)
    cursor.execute('DELETE FROM slots')

    # Вставляем новые слоты
    for date, date_slots in slots_dict.items():
        for slot in date_slots:
            cursor.execute('''
                INSERT INTO slots (date, time, available, deleted_by_admin)
                VALUES (?, ?, ?, ?)
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
            VALUES (?, ?, ?)
        ''', (date, time, available))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Слот {date} {time} уже существует.")
    conn.close()

def update_slot(slot_id, available=None, deleted_by_admin=None):
    """Обновляет статус слота по ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    updates = []
    params = []

    if available is not None:
        updates.append('available = ?')
        params.append(available)
    if deleted_by_admin is not None:
        updates.append('deleted_by_admin = ?')
        params.append(deleted_by_admin)

    if updates:
        params.append(slot_id)
        query = f"UPDATE slots SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
    conn.close()

def delete_slot_by_datetime(date, time):
    """Удаляет слот по дате и времени (ставит deleted_by_admin = 1)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE slots SET deleted_by_admin = 1, available = 0 WHERE date = ? AND time = ?
    ''', (date, time))
    conn.commit()
    conn.close()


# --- Функции для работы с записями ---

def load_bookings():
    """Загружает все записи из БД и возвращает в старом формате (list)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_id, date, time, child_name, phone, timestamp, confirmed, cancelled_by_user, cancelled_by_admin
        FROM bookings
        ORDER BY date, time
    ''')
    rows = cursor.fetchall()
    conn.close()

    bookings = []
    for row in rows:
        bookings.append({
            'id': row['id'], # Добавим ID записи
            'user_id': row['user_id'],
            'date': row['date'],
            'time': row['time'],
            'child_name': row['child_name'],
            'phone': row['phone'],
            'timestamp': row['timestamp'],
            'confirmed': bool(row['confirmed']),
            'cancelled_by_user': bool(row['cancelled_by_user']),
            'cancelled_by_admin': bool(row['cancelled_by_admin'])
        })
    return bookings

def save_booking(booking_data):
    """Сохраняет новую запись в БД."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bookings (user_id, date, time, child_name, phone, confirmed, cancelled_by_user, cancelled_by_admin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        booking_data['user_id'],
        booking_data['date'],
        booking_data['time'],
        booking_data['child_name'],
        booking_data['phone'],
        booking_data.get('confirmed', False),
        booking_data.get('cancelled_by_user', False),
        booking_data.get('cancelled_by_admin', False)
    ))
    conn.commit()
    conn.close()

def save_bookings(bookings_list):
    """
    Полностью перезаписывает все записи в БД.
    ВНИМАНИЕ: Это может быть опасно и неэффективно.
    Лучше использовать update_booking.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Удаляем все старые записи
    cursor.execute('DELETE FROM bookings')

    # Вставляем новые записи
    for booking in bookings_list:
        cursor.execute('''
            INSERT INTO bookings (user_id, date, time, child_name, phone, timestamp, confirmed, cancelled_by_user, cancelled_by_admin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            booking['user_id'],
            booking['date'],
            booking['time'],
            booking['child_name'],
            booking['phone'],
            booking.get('timestamp', datetime.now().isoformat()),
            booking.get('confirmed', False),
            booking.get('cancelled_by_user', False),
            booking.get('cancelled_by_admin', False)
        ))

    conn.commit()
    conn.close()

def update_booking(booking_id, confirmed=None, cancelled_by_user=None, cancelled_by_admin=None):
    """Обновляет статус записи по ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    updates = []
    params = []

    if confirmed is not None:
        updates.append('confirmed = ?')
        params.append(confirmed)
    if cancelled_by_user is not None:
        updates.append('cancelled_by_user = ?')
        params.append(cancelled_by_user)
    if cancelled_by_admin is not None:
        updates.append('cancelled_by_admin = ?')
        params.append(cancelled_by_admin)

    if updates:
        params.append(booking_id)
        query = f"UPDATE bookings SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
    conn.close()

def delete_booking_by_datetime_user_id(date, time, user_id):
    """Удаляет запись по дате, времени и user_id (ставит cancelled_by_user = 1)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE bookings SET cancelled_by_user = 1 WHERE date = ? AND time = ? AND user_id = ?
    ''', (date, time, user_id))
    conn.commit()
    conn.close()
