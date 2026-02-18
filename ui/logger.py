# ui/logger.py
"""Логирование для отладки и мониторинга"""

import logging
import streamlit as st
from datetime import datetime
from pathlib import Path


# Создаём папку для логов
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Настройка логирования
LOG_FILE = LOG_DIR / f"app_{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def log_action(action: str, details: dict = None, level: str = "INFO"):
    """Логирование действий пользователя"""
    message = f"[{action}]"
    
    if details:
        message += f" {details}"
    
    if level == "INFO":
        logger.info(message)
    elif level == "WARNING":
        logger.warning(message)
    elif level == "ERROR":
        logger.error(message)
    elif level == "DEBUG":
        logger.debug(message)


def log_credit_action(action: str, credit_name: str, credit_id: int = None, details: dict = None):
    """Логирование действий с кредитами"""
    log_data = {
        'action': action,
        'credit': credit_name,
        'credit_id': credit_id,
        **(details or {})
    }
    log_action(f"CREDIT_{action}", log_data)


def log_deposit_action(action: str, deposit_name: str, deposit_id: int = None, details: dict = None):
    """Логирование действий с вкладами"""
    log_data = {
        'action': action,
        'deposit': deposit_name,
        'deposit_id': deposit_id,
        **(details or {})
    }
    log_action(f"DEPOSIT_{action}", log_data)


def log_income_action(action: str, amount: float, income_type: str, details: dict = None):
    """Логирование действий с доходом"""
    log_data = {
        'action': action,
        'amount': amount,
        'type': income_type,
        **(details or {})
    }
    log_action(f"INCOME_{action}", log_data)


def log_calculation(calc_type: str, inputs: dict, result: dict):
    """Логирование расчётов"""
    log_data = {
        'type': calc_type,
        'inputs': inputs,
        'result': result
    }
    log_action(f"CALC_{calc_type}", log_data, level="DEBUG")


def get_recent_logs(lines: int = 50) -> list:
    """Получение последних логов"""
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return all_lines[-lines:]
    except:
        return []