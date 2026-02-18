# ui/utils.py
"""Утилиты для работы с моделями и данными"""

from datetime import datetime
from models import Credit, Deposit
from typing import Dict, Optional, Any


def safe_float(value: Any, default: float = 0.0) -> float:
    """Безопасное преобразование в float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Безопасное преобразование в int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def create_credit_object(credit_dict: Dict) -> Optional[Credit]:
    """Безопасное создание объекта Credit"""
    try:
        return Credit(
            name=credit_dict.get('name', 'Без названия'),
            balance=safe_float(credit_dict.get('balance', 0)),
            annual_rate=safe_float(credit_dict.get('annual_rate', 0)),
            monthly_payment=safe_float(credit_dict.get('monthly_payment', 0)),
            start_date=credit_dict.get('start_date', datetime.now()),
            payment_day=safe_int(credit_dict.get('payment_day', 10)),
            end_date=credit_dict.get('end_date')
        )
    except Exception as e:
        print(f"❌ Ошибка создания Credit: {str(e)}")
        return None


def create_deposit_object(deposit_dict: Dict) -> Optional[Deposit]:
    """Безопасное создание объекта Deposit"""
    try:
        return Deposit(
            name=deposit_dict.get('name', 'Без названия'),
            balance=safe_float(deposit_dict.get('balance', 0)),
            annual_rate=safe_float(deposit_dict.get('annual_rate', 0)),
            start_date=deposit_dict.get('start_date', datetime.now()),
            end_date=deposit_dict.get('end_date'),
            auto_renewal=bool(deposit_dict.get('auto_renewal', False))
        )
    except Exception as e:
        print(f"❌ Ошибка создания Deposit: {str(e)}")
        return None


def clear_session_state(*keys: str) -> None:
    """Очистка session_state"""
    import streamlit as st
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]