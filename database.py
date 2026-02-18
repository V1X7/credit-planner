import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any
from contextlib import contextmanager
import streamlit as st

DATABASE_PATH = 'credits.db'


@contextmanager
def get_connection():
    """Контекстный менеджер для безопасной работы с БД"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        st.error(f"❌ Ошибка БД: {e}")
        if conn:
            conn.rollback()
        yield None
    finally:
        if conn:
            conn.close()


def execute_query(query: str, params: tuple = (), fetch: str = None) -> Any:
    """Универсальная функция выполнения запросов"""
    with get_connection() as conn:
        if not conn:
            return None if fetch else False
        
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch == 'one':
                return cursor.fetchone()
            elif fetch == 'all':
                return cursor.fetchall()
            elif fetch == 'lastrowid':
                conn.commit()
                return cursor.lastrowid
            else:
                conn.commit()
                return True
        except sqlite3.Error as e:
            st.error(f"❌ Ошибка SQL: {e}")
            return None if fetch else False


def init_db() -> bool:
    """Инициализация БД с миграциями"""
    
    tables = {
        'credits': '''
            CREATE TABLE IF NOT EXISTS credits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                balance REAL NOT NULL CHECK(balance >= 0),
                annual_rate REAL NOT NULL CHECK(annual_rate >= 0 AND annual_rate <= 100),
                monthly_payment REAL NOT NULL CHECK(monthly_payment > 0),
                start_date TEXT NOT NULL,
                payment_day INTEGER NOT NULL CHECK(payment_day >= 1 AND payment_day <= 31),
                end_date TEXT,
                extra_payments TEXT DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'deposits': '''
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                balance REAL NOT NULL CHECK(balance >= 0),
                annual_rate REAL NOT NULL CHECK(annual_rate >= 0 AND annual_rate <= 100),
                start_date TEXT NOT NULL,
                end_date TEXT,
                auto_renewal INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'deposit_contributions': '''
            CREATE TABLE IF NOT EXISTS deposit_contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deposit_id INTEGER NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                date TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (deposit_id) REFERENCES deposits(id) ON DELETE CASCADE
            )
        ''',
        'income_settings': '''
            CREATE TABLE IF NOT EXISTS income_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salary REAL NOT NULL DEFAULT 0,
                advance REAL NOT NULL DEFAULT 0,
                other REAL NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'distribution_settings': '''
            CREATE TABLE IF NOT EXISTS distribution_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                credits_amount REAL NOT NULL DEFAULT 0,
                deposits_percent REAL NOT NULL DEFAULT 0,
                extra_payments_percent REAL NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'distribution_history': '''
            CREATE TABLE IF NOT EXISTS distribution_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE DEFAULT CURRENT_DATE,
                total_income REAL NOT NULL,
                credits REAL NOT NULL,
                deposits REAL NOT NULL,
                extra_payments REAL NOT NULL,
                life REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'income_diary': '''
            CREATE TABLE IF NOT EXISTS income_diary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                salary_type TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'history': '''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                old_values TEXT,
                new_values TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'distribution_rules': '''
            CREATE TABLE IF NOT EXISTS distribution_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deposits_percent REAL NOT NULL DEFAULT 20,
                extra_payments_percent REAL NOT NULL DEFAULT 30,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'income_distribution_log': '''
            CREATE TABLE IF NOT EXISTS income_distribution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                income_id INTEGER NOT NULL,
                total_income REAL NOT NULL,
                credits REAL NOT NULL,
                deposits REAL NOT NULL,
                extra_payments REAL NOT NULL,
                life REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (income_id) REFERENCES income_diary(id) ON DELETE CASCADE
            )
        '''
    }
    
    with get_connection() as conn:
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            for table_sql in tables.values():
                cursor.execute(table_sql)
            
            # Миграция: добавление end_date если нет
            cursor.execute("PRAGMA table_info(credits)")
            columns = {col[1] for col in cursor.fetchall()}
            
            if 'end_date' not in columns:
                cursor.execute('ALTER TABLE credits ADD COLUMN end_date TEXT')
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            st.error(f"❌ Ошибка инициализации БД: {e}")
            return False


def log_history(action: str, entity_type: str, entity_id: Optional[int] = None,
                old_values: Optional[Dict] = None, new_values: Optional[Dict] = None) -> bool:
    """Логирование изменений"""
    return execute_query(
        'INSERT INTO history (action, entity_type, entity_id, old_values, new_values) VALUES (?, ?, ?, ?, ?)',
        (action, entity_type, entity_id,
         json.dumps(old_values, ensure_ascii=False) if old_values else None,
         json.dumps(new_values, ensure_ascii=False) if new_values else None)
    )


# ==================== ВАЛИДАЦИЯ ====================

def validate_credit(name: str, balance: float, annual_rate: float, 
                    monthly_payment: float, payment_day: int) -> List[str]:
    """Валидация кредита"""
    errors = []
    
    if not name or not name.strip():
        errors.append("Название не может быть пустым")
    
    if balance < 1000:
        errors.append("Минимальная сумма: 1,000 ₽")
    elif balance > 100_000_000:
        errors.append("Максимальная сумма: 100,000,000 ₽")
    
    if annual_rate <= 0 or annual_rate > 100:
        errors.append("Ставка должна быть от 0% до 100%")
    
    if monthly_payment <= 0:
        errors.append("Платёж должен быть > 0")
    elif monthly_payment > balance:
        errors.append("Платёж не может быть больше суммы кредита")
    
    if payment_day < 1 or payment_day > 31:
        errors.append("День платежа: от 1 до 31")
    
    return errors


# ==================== КРЕДИТЫ ====================

def save_credit(name: str, balance: float, annual_rate: float, monthly_payment: float,
                start_date, payment_day: int, end_date=None) -> Optional[int]:
    """Сохранение кредита"""
    errors = validate_credit(name, balance, annual_rate, monthly_payment, payment_day)
    if errors:
        for error in errors:
            st.error(f"❌ {error}")
        return None
    
    credit_id = execute_query(
        '''INSERT INTO credits (name, balance, annual_rate, monthly_payment, start_date, payment_day, end_date, extra_payments)
           VALUES (?, ?, ?, ?, ?, ?, ?, '{}')''',
        (name, balance, annual_rate, monthly_payment, 
         start_date.isoformat(), payment_day,
         end_date.isoformat() if end_date else None),
        fetch='lastrowid'
    )
    
    if credit_id:
        log_history('CREATE', 'credit', credit_id, None, {
            'name': name, 'balance': balance, 'annual_rate': annual_rate
        })
        st.success(f"✅ Кредит '{name}' добавлен!")
    
    return credit_id


def get_all_credits() -> List[Tuple[int, Dict]]:
    """Получение всех кредитов"""
    rows = execute_query('SELECT * FROM credits ORDER BY created_at DESC', fetch='all')
    
    if not rows:
        return []
    
    credits = []
    for row in rows:
        try:
            extra_payments = json.loads(row['extra_payments'] or '{}')
        except:
            extra_payments = {}
        
        end_date = None
        if row['end_date']:
            try:
                end_date = datetime.fromisoformat(row['end_date'])
            except:
                pass
        
        credits.append((row['id'], {
            'name': row['name'],
            'balance': float(row['balance']),
            'annual_rate': float(row['annual_rate']),
            'monthly_payment': float(row['monthly_payment']),
            'start_date': datetime.fromisoformat(row['start_date']),
            'payment_day': int(row['payment_day']),
            'end_date': end_date,
            'extra_payments': extra_payments
        }))
    
    return credits


def get_credit_by_id(credit_id: int) -> Optional[Dict]:
    """Получение кредита по ID"""
    row = execute_query('SELECT * FROM credits WHERE id=?', (credit_id,), fetch='one')
    
    if not row:
        return None
    
    try:
        extra_payments = json.loads(row['extra_payments'] or '{}')
    except:
        extra_payments = {}
    
    end_date = None
    if row['end_date']:
        try:
            end_date = datetime.fromisoformat(row['end_date'])
        except:
            pass
    
    return {
        'id': row['id'],
        'name': row['name'],
        'balance': float(row['balance']),
        'annual_rate': float(row['annual_rate']),
        'monthly_payment': float(row['monthly_payment']),
        'start_date': datetime.fromisoformat(row['start_date']),
        'payment_day': int(row['payment_day']),
        'end_date': end_date,
        'extra_payments': extra_payments
    }


def update_credit(credit_id: int, name: str, balance: float, annual_rate: float,
                  monthly_payment: float, start_date, payment_day: int,
                  end_date=None, extra_payments=None) -> bool:
    """Обновление кредита"""
    errors = validate_credit(name, balance, annual_rate, monthly_payment, payment_day)
    if errors:
        for error in errors:
            st.error(f"❌ {error}")
        return False
    
    success = execute_query(
        '''UPDATE credits SET name=?, balance=?, annual_rate=?, monthly_payment=?,
           start_date=?, payment_day=?, end_date=?, extra_payments=?, updated_at=CURRENT_TIMESTAMP
           WHERE id=?''',
        (name, balance, annual_rate, monthly_payment, start_date.isoformat(),
         payment_day, end_date.isoformat() if end_date else None,
         json.dumps(extra_payments or {}), credit_id)
    )
    
    if success:
        st.success(f"✅ Кредит '{name}' обновлён!")
    
    return success


def delete_credit(credit_id: int) -> bool:
    """Удаление кредита"""
    success = execute_query('DELETE FROM credits WHERE id=?', (credit_id,))
    if success:
        log_history('DELETE', 'credit', credit_id, None, None)
        st.success("✅ Кредит удалён!")
    return success


# ==================== ДОСРОЧНЫЕ ПЛАТЕЖИ ====================

def get_extra_payments(credit_id: int) -> Dict:
    """Получение досрочных платежей для кредита"""
    row = execute_query(
        'SELECT extra_payments FROM credits WHERE id=?',
        (credit_id,),
        fetch='one'
    )
    
    if not row:
        return {}
    
    try:
        extra_payments = json.loads(row['extra_payments'] or '{}')
        return extra_payments if isinstance(extra_payments, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def add_extra_payment(credit_id: int, date, amount: float) -> bool:
    """Добавление досрочного платежа"""
    if amount <= 0 or amount > 100_000_000:
        st.error("❌ Некорректная сумма")
        return False
    
    row = execute_query('SELECT extra_payments FROM credits WHERE id=?', (credit_id,), fetch='one')
    if not row:
        st.error("❌ Кредит не найден")
        return False
    
    try:
        extra_payments = json.loads(row['extra_payments'] or '{}')
    except:
        extra_payments = {}
    
    date_str = date.isoformat() if hasattr(date, 'isoformat') else str(date)
    extra_payments[date_str] = amount
    
    success = execute_query(
        'UPDATE credits SET extra_payments=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
        (json.dumps(extra_payments), credit_id)
    )
    
    if success:
        log_history('ADD_EXTRA_PAYMENT', 'credit', credit_id, None, {
            'date': date_str,
            'amount': amount
        })
        st.success(f"✅ Досрочный платёж {amount:,.0f} ₽ добавлен!")
    
    return success


def delete_extra_payment(credit_id: int, date) -> bool:
    """Удаление досрочного платежа"""
    row = execute_query('SELECT extra_payments FROM credits WHERE id=?', (credit_id,), fetch='one')
    if not row:
        return False
    
    try:
        extra_payments = json.loads(row['extra_payments'] or '{}')
    except:
        return False
    
    date_str = date.isoformat() if hasattr(date, 'isoformat') else str(date)
    
    if date_str in extra_payments:
        old_amount = extra_payments[date_str]
        del extra_payments[date_str]
        
        success = execute_query(
            'UPDATE credits SET extra_payments=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (json.dumps(extra_payments), credit_id)
        )
        
        if success:
            log_history('DELETE_EXTRA_PAYMENT', 'credit', credit_id, {
                'date': date_str,
                'amount': old_amount
            }, None)
            st.success("✅ Платёж удалён!")
        
        return success
    
    return False


def update_extra_payments(credit_id: int, extra_payments: Dict) -> bool:
    """Обновление всех досрочных платежей"""
    return execute_query(
        'UPDATE credits SET extra_payments=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
        (json.dumps(extra_payments), credit_id)
    )


# ==================== ВКЛАДЫ ====================

def get_all_deposits() -> List[Tuple[int, Dict]]:
    """Получение всех вкладов"""
    rows = execute_query('SELECT * FROM deposits ORDER BY created_at DESC', fetch='all')
    
    if not rows:
        return []
    
    deposits = []
    for row in rows:
        deposits.append((row['id'], {
            'name': row['name'],
            'balance': float(row['balance']),
            'annual_rate': float(row['annual_rate']),
            'start_date': datetime.fromisoformat(row['start_date']),
            'end_date': datetime.fromisoformat(row['end_date']) if row['end_date'] else None,
            'auto_renewal': bool(row['auto_renewal'])
        }))
    
    return deposits


def get_deposit_by_id(deposit_id: int) -> Optional[Dict]:
    """Получение вклада по ID"""
    row = execute_query('SELECT * FROM deposits WHERE id=?', (deposit_id,), fetch='one')
    
    if not row:
        return None
    
    return {
        'id': row['id'],
        'name': row['name'],
        'balance': float(row['balance']),
        'annual_rate': float(row['annual_rate']),
        'start_date': datetime.fromisoformat(row['start_date']),
        'end_date': datetime.fromisoformat(row['end_date']) if row['end_date'] else None,
        'auto_renewal': bool(row['auto_renewal'])
    }


def save_deposit(name: str, balance: float, annual_rate: float,
                 start_date, end_date, auto_renewal: bool) -> Optional[int]:
    """Сохранение вклада"""
    if balance < 0 or annual_rate < 0 or annual_rate > 100:
        st.error("❌ Некорректные данные")
        return None
    
    deposit_id = execute_query(
        'INSERT INTO deposits (name, balance, annual_rate, start_date, end_date, auto_renewal) VALUES (?, ?, ?, ?, ?, ?)',
        (name, balance, annual_rate, start_date.isoformat(),
         end_date.isoformat() if end_date else None, int(auto_renewal)),
        fetch='lastrowid'
    )
    
    if deposit_id:
        log_history('CREATE', 'deposit', deposit_id, None, {
            'name': name, 'balance': balance, 'annual_rate': annual_rate
        })
        st.success(f"✅ Вклад '{name}' добавлен!")
    
    return deposit_id


def update_deposit(deposit_id: int, name: str, balance: float, annual_rate: float,
                   start_date, end_date, auto_renewal: bool) -> bool:
    """Обновление вклада"""
    if balance < 0 or annual_rate < 0 or annual_rate > 100:
        st.error("❌ Некорректные данные")
        return False
    
    success = execute_query(
        '''UPDATE deposits SET name=?, balance=?, annual_rate=?, start_date=?,
           end_date=?, auto_renewal=?, updated_at=CURRENT_TIMESTAMP WHERE id=?''',
        (name, balance, annual_rate, start_date.isoformat(),
         end_date.isoformat() if end_date else None, int(auto_renewal), deposit_id)
    )
    
    if success:
        st.success(f"✅ Вклад '{name}' обновлён!")
    
    return success


def delete_deposit(deposit_id: int) -> bool:
    """Удаление вклада"""
    success = execute_query('DELETE FROM deposits WHERE id=?', (deposit_id,))
    if success:
        log_history('DELETE', 'deposit', deposit_id, None, None)
        st.success("✅ Вклад удалён!")
    return success


# ==================== ПОПОЛНЕНИЯ ВКЛАДОВ ====================

def get_deposit_contributions(deposit_id: int) -> List[Dict]:
    """Получение пополнений вклада"""
    rows = execute_query(
        'SELECT * FROM deposit_contributions WHERE deposit_id=? ORDER BY date ASC',
        (deposit_id,), fetch='all'
    )
    
    if not rows:
        return []
    
    return [{
        'id': row['id'],
        'deposit_id': row['deposit_id'],
        'amount': float(row['amount']),
        'date': datetime.fromisoformat(row['date'])
    } for row in rows]


def add_deposit_contribution(deposit_id: int, date, amount: float) -> bool:
    """Добавление пополнения вклада"""
    if amount <= 0 or amount > 100_000_000:
        st.error("❌ Некорректная сумма")
        return False
    
    date_str = date.isoformat() if hasattr(date, 'isoformat') else str(date)
    
    success = execute_query(
        'INSERT INTO deposit_contributions (deposit_id, amount, date) VALUES (?, ?, ?)',
        (deposit_id, amount, date_str)
    )
    
    if success:
        st.success(f"✅ Пополнение {amount:,.0f} ₽ добавлено!")
    
    return success


def delete_deposit_contribution(contribution_id: int) -> bool:
    """Удаление пополнения вклада"""
    success = execute_query('DELETE FROM deposit_contributions WHERE id=?', (contribution_id,))
    if success:
        st.success("✅ Пополнение удалено!")
    return success


# ==================== ДОХОД И РАСПРЕДЕЛЕНИЕ ====================

def get_income_settings() -> Dict:
    """Получение настроек дохода"""
    row = execute_query('SELECT * FROM income_settings ORDER BY created_at DESC LIMIT 1', fetch='one')
    
    if not row:
        return {'salary': 0, 'advance': 0, 'other': 0}
    
    return {
        'salary': float(row['salary']),
        'advance': float(row['advance']),
        'other': float(row['other'])
    }


def save_income_settings(salary: float, advance: float, other: float = 0) -> bool:
    """Сохранение настроек дохода"""
    execute_query('DELETE FROM income_settings')
    success = execute_query(
        'INSERT INTO income_settings (salary, advance, other) VALUES (?, ?, ?)',
        (salary, advance, other)
    )
    if success:
        st.success("✅ Настройки дохода сохранены!")
    return success


def get_distribution_settings() -> Dict:
    """Получение настроек распределения"""
    row = execute_query('SELECT * FROM distribution_settings ORDER BY created_at DESC LIMIT 1', fetch='one')
    
    if not row:
        return {'credits_amount': 0, 'deposits_percent': 20, 'extra_payments_percent': 10}
    
    return {
        'credits_amount': float(row['credits_amount']),
        'deposits_percent': float(row['deposits_percent']),
        'extra_payments_percent': float(row['extra_payments_percent'])
    }


def save_distribution_settings(credits_amount: float, deposits_percent: float,
                                extra_payments_percent: float) -> bool:
    """Сохранение настроек распределения"""
    execute_query('DELETE FROM distribution_settings')
    success = execute_query(
        'INSERT INTO distribution_settings (credits_amount, deposits_percent, extra_payments_percent) VALUES (?, ?, ?)',
        (credits_amount, deposits_percent, extra_payments_percent)
    )
    if success:
        st.success("✅ Настройки распределения сохранены!")
    return success


def save_distribution_history(total_income: float, credits: float, deposits: float,
                               extra_payments: float, life: float) -> bool:
    """Сохранение истории распределения"""
    return execute_query(
        'INSERT INTO distribution_history (total_income, credits, deposits, extra_payments, life) VALUES (?, ?, ?, ?, ?)',
        (total_income, credits, deposits, extra_payments, life)
    )


def get_distribution_history(limit: int = 12) -> List[Dict]:
    """Получение истории распределений"""
    rows = execute_query(
        'SELECT * FROM distribution_history ORDER BY date DESC LIMIT ?',
        (limit,), fetch='all'
    )
    
    if not rows:
        return []
    
    return [{
        'date': row['date'],
        'total_income': float(row['total_income']),
        'credits': float(row['credits']),
        'deposits': float(row['deposits']),
        'extra_payments': float(row['extra_payments']),
        'life': float(row['life'])
    } for row in rows]


# ==================== ДНЕВНИК ДОХОДОВ ====================

def save_income_diary_entry(date: str, salary_type: str, amount: float) -> bool:
    """Сохранение записи в дневник"""
    return execute_query(
        'INSERT INTO income_diary (date, salary_type, amount) VALUES (?, ?, ?)',
        (date, salary_type, amount)
    )


def get_income_diary(year: Optional[int] = None, month: Optional[int] = None) -> List[Dict]:
    """Получение записей дневника"""
    if year and month:
        rows = execute_query(
            "SELECT * FROM income_diary WHERE strftime('%Y', date)=? AND strftime('%m', date)=? ORDER BY date DESC",
            (str(year), f"{month:02d}"), fetch='all'
        )
    elif year:
        rows = execute_query(
            "SELECT * FROM income_diary WHERE strftime('%Y', date)=? ORDER BY date DESC",
            (str(year),), fetch='all'
        )
    else:
        rows = execute_query('SELECT * FROM income_diary ORDER BY date DESC', fetch='all')
    
    if not rows:
        return []
    
    return [{'date': row['date'], 'salary_type': row['salary_type'], 'amount': float(row['amount'])} for row in rows]


def get_income_diary_with_id(year: Optional[int] = None, month: Optional[int] = None) -> List[Dict]:
    """Получение записей дневника с ID"""
    if year and month:
        rows = execute_query(
            "SELECT id, date, salary_type, amount FROM income_diary WHERE strftime('%Y', date)=? AND strftime('%m', date)=? ORDER BY date DESC",
            (str(year), f"{month:02d}"), fetch='all'
        )
    elif year:
        rows = execute_query(
            "SELECT id, date, salary_type, amount FROM income_diary WHERE strftime('%Y', date)=? ORDER BY date DESC",
            (str(year),), fetch='all'
        )
    else:
        rows = execute_query('SELECT id, date, salary_type, amount FROM income_diary ORDER BY date DESC', fetch='all')
    
    if not rows:
        return []
    
    return [{'id': row['id'], 'date': row['date'], 'salary_type': row['salary_type'], 'amount': float(row['amount'])} for row in rows]


def get_income_diary_stats(year: Optional[int] = None) -> Dict:
    """Получение статистики по месяцам"""
    if year:
        rows = execute_query(
            "SELECT strftime('%m', date) as month, SUM(amount) as total, COUNT(*) as count FROM income_diary WHERE strftime('%Y', date)=? GROUP BY month ORDER BY month",
            (str(year),), fetch='all'
        )
    else:
        rows = execute_query(
            "SELECT strftime('%Y-%m', date) as month, SUM(amount) as total, COUNT(*) as count FROM income_diary GROUP BY month ORDER BY month DESC",
            fetch='all'
        )
    
    if not rows:
        return {}
    
    return {row['month']: {'total': float(row['total']), 'count': row['count']} for row in rows}


def update_income_diary_entry(entry_id: int, date: str, salary_type: str, amount: float) -> bool:
    """Обновление записи в дневнике"""
    return execute_query(
        'UPDATE income_diary SET date=?, salary_type=?, amount=? WHERE id=?',
        (date, salary_type, amount, entry_id)
    )


def delete_income_diary_entry(entry_id: int) -> bool:
    """Удаление записи из дневника"""
    success = execute_query('DELETE FROM income_diary WHERE id=?', (entry_id,))
    if success:
        st.success("✅ Запись удалена!")
    return success


def check_income_diary_due() -> bool:
    """Проверка: нужно ли запросить доход (10 или 25 число)"""
    return datetime.now().day in [10, 25]


# ==================== ПРАВИЛА РАСПРЕДЕЛЕНИЯ ====================

def save_distribution_rules(deposits_percent: float, extra_payments_percent: float) -> bool:
    """Сохранение правил распределения дохода"""
    execute_query('DELETE FROM distribution_rules')
    success = execute_query(
        'INSERT INTO distribution_rules (deposits_percent, extra_payments_percent) VALUES (?, ?)',
        (deposits_percent, extra_payments_percent)
    )
    if success:
        st.success("✅ Правила распределения сохранены!")
    return success


def get_distribution_rules() -> Dict:
    """Получение правил распределения"""
    row = execute_query('SELECT * FROM distribution_rules ORDER BY created_at DESC LIMIT 1', fetch='one')
    
    if not row:
        return {'deposits_percent': 20, 'extra_payments_percent': 30}
    
    return {
        'deposits_percent': float(row['deposits_percent']),
        'extra_payments_percent': float(row['extra_payments_percent'])
    }


def save_distribution_log(income_id: int, total_income: float, credits: float, 
                          deposits: float, extra_payments: float, life: float) -> bool:
    """Сохранение лога распределения"""
    success = execute_query(
        '''INSERT INTO income_distribution_log 
           (income_id, total_income, credits, deposits, extra_payments, life) 
           VALUES (?, ?, ?, ?, ?, ?)''',
        (income_id, total_income, credits, deposits, extra_payments, life)
    )
    if success:
        st.success("✅ Распределение зафиксировано!")
    return success


def get_distribution_logs(year: Optional[int] = None, month: Optional[int] = None) -> List[Dict]:
    """Получение логов распределения"""
    if year and month:
        rows = execute_query(
            '''SELECT idl.*, id.date, id.salary_type, id.amount 
               FROM income_distribution_log idl
               JOIN income_diary id ON idl.income_id = id.id
               WHERE strftime('%Y', id.date)=? AND strftime('%m', id.date)=?
               ORDER BY id.date DESC''',
            (str(year), f"{month:02d}"), fetch='all'
        )
    else:
        rows = execute_query(
            '''SELECT idl.*, id.date, id.salary_type, id.amount 
               FROM income_distribution_log idl
               JOIN income_diary id ON idl.income_id = id.id
               ORDER BY id.date DESC LIMIT 50''',
            fetch='all'
        )
    
    if not rows:
        return []
    
    return [{
        'id': row['id'],
        'income_id': row['income_id'],
        'date': row['date'],
        'salary_type': row['salary_type'],
        'amount': float(row['amount']),
        'total_income': float(row['total_income']),
        'credits': float(row['credits']),
        'deposits': float(row['deposits']),
        'extra_payments': float(row['extra_payments']),
        'life': float(row['life'])
    } for row in rows]


def get_latest_distribution() -> Optional[Dict]:
    """Получение последнего распределения"""
    row = execute_query(
        '''SELECT idl.*, id.date, id.salary_type 
           FROM income_distribution_log idl
           JOIN income_diary id ON idl.income_id = id.id
           ORDER BY idl.created_at DESC LIMIT 1''',
        fetch='one'
    )
    
    if not row:
        return None
    
    return {
        'date': row['date'],
        'salary_type': row['salary_type'],
        'total_income': float(row['total_income']),
        'credits': float(row['credits']),
        'deposits': float(row['deposits']),
        'extra_payments': float(row['extra_payments']),
        'life': float(row['life'])
    }


# ==================== УТИЛИТЫ ====================

def get_history(limit: int = 50) -> List[Dict]:
    """Получение истории изменений"""
    rows = execute_query('SELECT * FROM history ORDER BY timestamp DESC LIMIT ?', (limit,), fetch='all')
    
    if not rows:
        return []
    
    history = []
    for row in rows:
        history.append({
            'id': row['id'],
            'action': row['action'],
            'entity_type': row['entity_type'],
            'entity_id': row['entity_id'],
            'old_values': json.loads(row['old_values']) if row['old_values'] else None,
            'new_values': json.loads(row['new_values']) if row['new_values'] else None,
            'timestamp': row['timestamp']
        })
    
    return history


def clear_all_data() -> bool:
    """Очистка всех данных"""
    tables = ['credits', 'deposits', 'deposit_contributions', 'history', 
              'income_diary', 'distribution_history', 'distribution_rules', 
              'income_distribution_log']
    
    for table in tables:
        execute_query(f'DELETE FROM {table}')
    
    st.success("✅ Все данные удалены!")
    return True
