from database import execute_query

# 1. Добавляем income_id в deposit_contributions
execute_query(
    'ALTER TABLE deposit_contributions ADD COLUMN income_id INTEGER REFERENCES income_diary(id) ON DELETE SET NULL',
    fetch=None
)
print("✅ deposit_contributions.income_id добавлен")

# 2. Создаём таблицу extra_payments_log
execute_query(
    '''CREATE TABLE IF NOT EXISTS extra_payments_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        income_id INTEGER REFERENCES income_diary(id) ON DELETE SET NULL,
        credit_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''',
    fetch=None
)
print("✅ extra_payments_log создана")