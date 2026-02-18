from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional, Tuple
from models import Credit, Deposit
from copy import deepcopy


def calculate_combined_schedule(
    credits: List[Credit], 
    deposits: List[Deposit], 
    end_date: Optional[datetime] = None,
    months_ahead: int = 60
) -> List[Dict]:
    """
    Рассчитывает совмещённый график платежей по кредитам и доходов от вкладов
    
    Args:
        credits: Список кредитов
        deposits: Список вкладов
        end_date: Конечная дата расчёта (если None, то + months_ahead)
        months_ahead: Количество месяцев вперёд (по умолчанию 5 лет)
    
    Returns:
        Список словарей с данными по месяцам
    """
    
    if not credits and not deposits:
        return []
    
    # Определяем конечную дату
    if end_date is None:
        end_date = datetime.now() + relativedelta(months=months_ahead)
    
    # Приводим к datetime если date
    if isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = datetime.combine(end_date, datetime.min.time())
    
    schedule = []
    current_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    while current_date <= end_date:
        month_data = {
            'date': current_date,
            'credit_payments': 0.0,
            'credit_interest': 0.0,
            'credit_principal': 0.0,
            'deposit_interest': 0.0,
            'deposit_balance': 0.0,
            'net_flow': 0.0,
            'cumulative_net': 0.0
        }
        
        # Обработка кредитов
        if credits:
            for credit in credits:
                try:
                    # Рассчитываем график для следующего месяца
                    next_month = current_date + relativedelta(months=1)
                    credit_schedule = credit.calculate_schedule(next_month)
                    
                    # Ищем платежи текущего месяца
                    for payment in credit_schedule:
                        payment_date = payment.get('date')
                        
                        # Приводим к datetime
                        if isinstance(payment_date, date) and not isinstance(payment_date, datetime):
                            payment_date = datetime.combine(payment_date, datetime.min.time())
                        
                        # Проверяем совпадение месяца и года
                        if (payment_date.year == current_date.year and 
                            payment_date.month == current_date.month):
                            
                            month_data['credit_payments'] += float(payment.get('total_payment', 0))
                            month_data['credit_interest'] += float(payment.get('interest', 0))
                            month_data['credit_principal'] += float(payment.get('principal', 0))
                
                except Exception as e:
                    # Логируем ошибку, но продолжаем
                    print(f"Ошибка расчёта кредита {credit.name}: {str(e)}")
                    continue
        
        # Обработка вкладов
        if deposits:
            for deposit in deposits:
                try:
                    # Рассчитываем график для следующего месяца
                    next_month = current_date + relativedelta(months=1)
                    deposit_schedule = deposit.calculate_schedule(next_month)
                    
                    # Ищем данные текущего месяца
                    for month in deposit_schedule:
                        month_date = month.get('date')
                        
                        # Приводим к datetime
                        if isinstance(month_date, date) and not isinstance(month_date, datetime):
                            month_date = datetime.combine(month_date, datetime.min.time())
                        
                        # Проверяем совпадение месяца и года
                        if (month_date.year == current_date.year and 
                            month_date.month == current_date.month):
                            
                            month_data['deposit_interest'] += float(month.get('interest', 0))
                            month_data['deposit_balance'] += float(month.get('balance', 0))
                
                except Exception as e:
                    # Логируем ошибку, но продолжаем
                    print(f"Ошибка расчёта вклада {deposit.name}: {str(e)}")
                    continue
        
        # Рассчитываем чистый поток
        month_data['net_flow'] = month_data['deposit_interest'] - month_data['credit_payments']
        
        # Накопительный чистый поток
        if schedule:
            month_data['cumulative_net'] = schedule[-1]['cumulative_net'] + month_data['net_flow']
        else:
            month_data['cumulative_net'] = month_data['net_flow']
        
        schedule.append(month_data)
        current_date += relativedelta(months=1)
    
    return schedule


def calculate_optimization_strategy(
    credits: List[Credit], 
    available_amount: float
) -> Dict[str, Dict]:
    """
    Рассчитывает оптимальную стратегию досрочного погашения
    
    Args:
        credits: Список кредитов
        available_amount: Доступная сумма для досрочного погашения
    
    Returns:
        Словарь со стратегиями и их эффективностью
    """
    
    if not credits or available_amount <= 0:
        return {}
    
    strategies = {}
    
    # Стратегия 1: Максимальная ставка (Avalanche)
    try:
        sorted_by_rate = sorted(
            enumerate(credits), 
            key=lambda x: float(x[1].annual_rate), 
            reverse=True
        )
        
        if sorted_by_rate:
            idx, credit = sorted_by_rate[0]
            savings = calculate_strategy_savings(credit, available_amount)
            
            strategies['avalanche'] = {
                'credit_index': idx,
                'credit_name': credit.name,
                'credit_rate': float(credit.annual_rate),
                'credit_balance': float(credit.balance),
                'savings': savings,
                'roi': (savings / available_amount * 100) if available_amount > 0 else 0,
                'description': 'Гасим кредит с максимальной ставкой (математически оптимально)'
            }
    except Exception as e:
        print(f"Ошибка расчёта Avalanche: {str(e)}")
    
    # Стратегия 2: Минимальный остаток (Snowball)
    try:
        sorted_by_balance = sorted(
            enumerate(credits), 
            key=lambda x: float(x[1].balance)
        )
        
        if sorted_by_balance:
            idx, credit = sorted_by_balance[0]
            savings = calculate_strategy_savings(credit, available_amount)
            
            strategies['snowball'] = {
                'credit_index': idx,
                'credit_name': credit.name,
                'credit_rate': float(credit.annual_rate),
                'credit_balance': float(credit.balance),
                'savings': savings,
                'roi': (savings / available_amount * 100) if available_amount > 0 else 0,
                'can_close': available_amount >= float(credit.balance),
                'description': 'Гасим самый маленький кредит (психологически легче)'
            }
    except Exception as e:
        print(f"Ошибка расчёта Snowball: {str(e)}")
    
    # Стратегия 3: Максимальный платёж (Highest Payment)
    try:
        sorted_by_payment = sorted(
            enumerate(credits), 
            key=lambda x: float(x[1].monthly_payment), 
            reverse=True
        )
        
        if sorted_by_payment:
            idx, credit = sorted_by_payment[0]
            savings = calculate_strategy_savings(credit, available_amount)
            
            strategies['highest_payment'] = {
                'credit_index': idx,
                'credit_name': credit.name,
                'credit_rate': float(credit.annual_rate),
                'credit_balance': float(credit.balance),
                'monthly_payment': float(credit.monthly_payment),
                'savings': savings,
                'roi': (savings / available_amount * 100) if available_amount > 0 else 0,
                'description': 'Гасим кредит с максимальным платежом (снижаем нагрузку)'
            }
    except Exception as e:
        print(f"Ошибка расчёта Highest Payment: {str(e)}")
    
    # Определяем лучшую стратегию
    if strategies:
        best_strategy = max(strategies.items(), key=lambda x: x[1].get('savings', 0))
        
        for strategy_name, strategy_data in strategies.items():
            strategy_data['is_best'] = (strategy_name == best_strategy[0])
    
    return strategies


def calculate_strategy_savings(credit: Credit, extra_amount: float) -> float:
    """
    Рассчитывает экономию от досрочного платежа
    
    Args:
        credit: Кредит
        extra_amount: Сумма досрочного платежа
    
    Returns:
        Экономия в рублях
    """
    
    try:
        # Сохраняем оригинальную переплату
        original_interest = credit.get_total_interest()
        
        # Создаём копию кредита
        credit_copy = deepcopy(credit)
        
        # Добавляем досрочный платёж
        credit_copy.add_extra_payment(extra_amount, datetime.now())
        
        # Рассчитываем новую переплату
        new_interest = credit_copy.get_total_interest()
        
        # Экономия
        savings = max(0, original_interest - new_interest)
        
        return savings
    
    except Exception as e:
        print(f"Ошибка расчёта экономии: {str(e)}")
        return 0.0


def compare_strategies(
    credits: List[Credit], 
    available_amount: float
) -> Tuple[Dict, str]:
    """
    Сравнивает все стратегии и возвращает лучшую
    
    Args:
        credits: Список кредитов
        available_amount: Доступная сумма
    
    Returns:
        Кортеж (словарь всех стратегий, название лучшей)
    """
    
    strategies = calculate_optimization_strategy(credits, available_amount)
    
    if not strategies:
        return {}, None
    
    best_strategy_name = max(
        strategies.items(), 
        key=lambda x: x[1].get('savings', 0)
    )[0]
    
    return strategies, best_strategy_name


def get_strategy_recommendation(strategy_name: str, strategy_data: Dict) -> str:
    """
    Формирует текстовую рекомендацию для стратегии
    
    Args:
        strategy_name: Название стратегии
        strategy_data: Данные стратегии
    
    Returns:
        Текстовая рекомендация
    """
    
    recommendations = {
        'avalanche': f"""
        ✅ **Рекомендация:** Внесите досрочно на кредит "{strategy_data['credit_name']}"
        
        📊 **Почему:**
        - Самая высокая ставка ({strategy_data['credit_rate']:.2f}%)
        - Максимальная экономия на процентах
        - Математически оптимальное решение
        
        💰 **Экономия:** {strategy_data['savings']:,.0f} ₽
        📈 **ROI:** {strategy_data['roi']:.2f}%
        """,
        
        'snowball': f"""
        ✅ **Рекомендация:** Внесите досрочно на кредит "{strategy_data['credit_name']}"
        
        📊 **Почему:**
        - Самый маленький остаток ({strategy_data['credit_balance']:,.0f} ₽)
        - {'Можно закрыть полностью!' if strategy_data.get('can_close') else 'Быстрее закроете кредит'}
        - Психологически легче видеть прогресс
        
        💰 **Экономия:** {strategy_data['savings']:,.0f} ₽
        📈 **ROI:** {strategy_data['roi']:.2f}%
        """,
        
        'highest_payment': f"""
        ✅ **Рекомендация:** Внесите досрочно на кредит "{strategy_data['credit_name']}"
        
        📊 **Почему:**
        - Самый большой платёж ({strategy_data['monthly_payment']:,.0f} ₽/мес)
        - Быстро снизится месячная нагрузка
        - Высвободятся средства для других целей
        
        💰 **Экономия:** {strategy_data['savings']:,.0f} ₽
        📈 **ROI:** {strategy_data['roi']:.2f}%
        """
    }
    
    return recommendations.get(strategy_name, "Нет рекомендации")
