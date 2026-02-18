# config.py
"""Конфигурация приложения Credit Planner"""

from pathlib import Path
import os

# ==================== ПУТИ ====================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
EXPORTS_DIR = BASE_DIR / "exports"
BACKUP_DIR = BASE_DIR / "backup"

# Создаём папки если их нет
for directory in [DATA_DIR, LOGS_DIR, EXPORTS_DIR, BACKUP_DIR]:
    directory.mkdir(exist_ok=True)

# ==================== БД ====================
DATABASE_PATH = BASE_DIR / "credits.db"

# ==================== ЦВЕТА ====================
CREDIT_COLORS = [
    "#FF6B6B",      # Красный
    "#FFA07A",      # Оранжевый
    "#FFD700",      # Жёлтый
    "#98D8C8",      # Бирюзовый
    "#DDA0DD",      # Фиолетовый
    "#F08080",      # Коралловый
    "#87CEEB",      # Небесно-голубой
    "#FF69B4",      # Розовый
]

DEPOSIT_COLOR = "#4ECDC4"           # Бирюзовый
INTERSECTION_COLOR = "#FFD700"      # Золотой
HEATMAP_COLD = "#ff0000"            # Красный (холодно)
HEATMAP_WARM = "#ffff00"            # Жёлтый (тепло)
HEATMAP_HOT = "#00aa00"             # Зелёный (горячо)

# ==================== КЭШИРОВАНИЕ ====================
CACHE_TTL = 600                     # 10 минут
HEATMAP_CACHE_TTL = 600             # 10 минут
FORECAST_CACHE_TTL = 300            # 5 минут
DASHBOARD_CACHE_TTL = 300           # 5 минут

# ==================== ЛОГИРОВАНИЕ ====================
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ==================== ПОРОГИ И ЛИМИТЫ ====================
DEBT_RATIO_WARNING = 50             # % - предупреждение
DEBT_RATIO_CRITICAL = 100           # % - критично

MIN_PAYMENT_AMOUNT = 1000.0         # ₽
MAX_PAYMENT_AMOUNT = 500_000.0      # ₽

MIN_DEPOSIT_AMOUNT = 1000.0         # ₽
MAX_DEPOSIT_AMOUNT = 10_000_000.0   # ₽

MIN_ANNUAL_RATE = 0.0               # %
MAX_ANNUAL_RATE = 100.0             # %

MIN_MONTHLY_PAYMENT = 100.0         # ₽
MAX_MONTHLY_PAYMENT = 100_000.0     # ₽

# ==================== РАСЧЁТЫ ====================
DAYS_IN_YEAR = 365
MONTHS_IN_YEAR = 12

# ROI расчёты
ROI_DECIMAL_PLACES = 2
SAVINGS_DECIMAL_PLACES = 2

# ==================== ПРОГНОЗ ====================
DEFAULT_FORECAST_YEARS = 5
MIN_FORECAST_YEARS = 1
MAX_FORECAST_YEARS = 10

# ==================== СТРАТЕГИИ ====================
STRATEGIES = {
    'avalanche': 'Лавинная (макс. ставка)',
    'snowball': 'Снежный ком (мин. остаток)',
    'optimal': 'Оптимальная (макс. ROI)'
}

# ==================== РАСПРЕДЕЛЕНИЕ ДОХОДА ====================
DEFAULT_DEPOSITS_PERCENT = 20       # %
DEFAULT_EXTRA_PAYMENTS_PERCENT = 30 # %
DEFAULT_LIFE_PERCENT = 50           # %

# ==================== STREAMLIT ====================
PAGE_TITLE = "💰 Credit Planner"
PAGE_ICON = "💰"
LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "expanded"

# ==================== МЕСЯЦЫ ====================
MONTH_NAMES = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
]

# ==================== ВАЛЮТА ====================
CURRENCY = "₽"
CURRENCY_FORMAT = "{:,.0f}"

# ==================== ВЕРСИЯ ====================
APP_VERSION = "1.1.0"
APP_NAME = "Credit Planner"

# ==================== ОКРУЖЕНИЕ ====================
ENV = os.getenv("ENV", "development")

# Для production
if ENV == "production":
    CACHE_TTL = 1800                # 30 минут
    LOG_LEVEL = "WARNING"
else:
    CACHE_TTL = 600                 # 10 минут
    LOG_LEVEL = "DEBUG"