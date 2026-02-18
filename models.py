from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, List, Dict, Tuple
from copy import deepcopy
import calendar


class Credit:
    """Класс для работы с кредитом"""
    
    def __init__(self, name: str, balance: float, annual_rate: float, 
                 monthly_payment: float, start_date, payment_day: int, 
                 end_date=None, extra_payments: Optional[Dict] = None):
        self.name = name
        self.balance = float(balance)
        self.annual_rate = float(annual_rate)
        self.monthly_payment = float(monthly_payment)
        self.start_date = self._to_datetime(start_date)
        self.payment_day = int(payment_day)
        self.end_date = self._to_datetime(end_date) if end_date else None
        self.extra_payments = extra_payments or {}
    
    @staticmethod
    def _to_datetime(dt) -> Optional[datetime]:
        """Преобразование в datetime"""
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt
        if isinstance(dt, date):
            return datetime.combine(dt, datetime.min.time())
        if isinstance(dt, str):
            return datetime.fromisoformat(dt)
        return dt
    
    @staticmethod
    def _to_date(dt) -> Optional[date]:
        """Преобразование в date"""
        if dt is None:
            return None
        if isinstance(dt, date) and not isinstance(dt, datetime):
            return dt
        if isinstance(dt, datetime):
            return dt.date()
        return dt
    
    def _get_payment_date(self, year: int, month: int) -> datetime:
        """Получение даты платежа для месяца"""
        try:
            return datetime(year, month, self.payment_day)
        except ValueError:
            # Если день больше количества дней в месяце
            last_day = calendar.monthrange(year, month)[1]
            return datetime(year, month, min(self.payment_day, last_day))
    
    def calculate_schedule(self, end_date) -> List[Dict]:
        """Расчёт графика платежей до указанной даты"""
        schedule = []
        current_balance = self.balance
        current_date = self._to_date(self.start_date)
        end_date = self._to_date(end_date)
        
        if not current_date or not end_date:
            return []
        
        monthly_rate = self.annual_rate / 12 / 100
        
        while current_balance > 0.01 and current_date <= end_date:
            # Дата платежа
            payment_date = self._get_payment_date(current_date.year, current_date.month)
            
            # Проценты за месяц
            interest = current_balance * monthly_rate
            
            # Основной долг
            principal = self.monthly_payment - interest
            
            # Защита от отрицательного principal
            if principal < 0:
                principal = 0
            
            # Не гасим больше остатка
            principal = min(principal, current_balance)
            
            # Обновляем баланс
            current_balance = max(0, current_balance - principal)
            
            # Добавляем в график
            schedule.append({
                'date': payment_date,
                'total_payment': min(self.monthly_payment, interest + principal),
                'interest': interest,
                'principal': principal,
                'balance': current_balance
            })
            
            # Если долг погашен, выходим
            if current_balance <= 0.01:
                break
            
            # Следующий месяц
            current_date = (datetime(current_date.year, current_date.month, 1) + 
                          relativedelta(months=1)).date()
        
        return schedule
    
    def get_total_interest(self, months: Optional[int] = None) -> float:
        """Расчёт общей суммы процентов"""
        if months is None:
            months = 360  # Максимум 30 лет
        
        end_date = datetime.now() + relativedelta(months=months)
        schedule = self.calculate_schedule(end_date)
        
        return sum(payment['interest'] for payment in schedule)
    
    def calculate_payoff_date(self) -> Optional[datetime]:
        """Расчёт даты полного погашения"""
        monthly_rate = self.annual_rate / 12 / 100
        monthly_interest = self.balance * monthly_rate
        
        # Проверка: погашается ли кредит
        if self.monthly_payment <= monthly_interest:
            return None
        
        principal_payment = self.monthly_payment - monthly_interest
        
        if principal_payment <= 0:
            return None
        
        # Упрощённый расчёт (без учёта уменьшения процентов)
        months_left = self.balance / principal_payment
        
        payoff_date = datetime.now() + relativedelta(months=int(months_left))
        return payoff_date
    
    def calculate_months_remaining(self) -> Optional[int]:
        """Расчёт оставшихся месяцев до погашения"""
        if self.end_date:
            now = datetime.now()
            months = ((self.end_date.year - now.year) * 12 + 
                     (self.end_date.month - now.month))
            return max(0, months)
        
        monthly_rate = self.annual_rate / 12 / 100
        monthly_interest = self.balance * monthly_rate
        
        if self.monthly_payment <= monthly_interest:
            return None
        
        principal_payment = self.monthly_payment - monthly_interest
        
        if principal_payment <= 0:
            return None
        
        months_left = self.balance / principal_payment
        return int(months_left)
    
    def calculate_with_extra_payment(self, extra_amount: float, 
                                    payment_date=None) -> Dict:
        """Расчёт экономии от досрочного платежа"""
        if extra_amount <= 0:
            return {
                'savings': 0,
                'roi': 0,
                'new_balance': self.balance,
                'base_interest': 0,
                'new_interest': 0
            }
        
        # Базовый сценарий
        base_interest = self.get_total_interest()
        
        # Новый баланс после досрочного платежа
        new_balance = max(0, self.balance - extra_amount)
        
        # Сценарий с досрочным платежом
        temp_credit = Credit(
            name=self.name,
            balance=new_balance,
            annual_rate=self.annual_rate,
            monthly_payment=self.monthly_payment,
            start_date=self.start_date,
            payment_day=self.payment_day,
            end_date=self.end_date
        )
        
        new_interest = temp_credit.get_total_interest()
        
        savings = max(0, base_interest - new_interest)
        roi = (savings / extra_amount * 100) if extra_amount > 0 else 0
        
        return {
            'savings': savings,
            'roi': roi,
            'new_balance': new_balance,
            'base_interest': base_interest,
            'new_interest': new_interest
        }
    
    def add_extra_payment(self, amount: float, payment_date) -> bool:
        """Добавление досрочного платежа"""
        if amount <= 0:
            return False
        
        date_str = self._to_datetime(payment_date).strftime('%Y-%m-%d')
        self.extra_payments[date_str] = amount
        return True
    
    def __repr__(self) -> str:
        return f"Credit(name='{self.name}', balance={self.balance:,.0f}₽, rate={self.annual_rate}%)"


class Deposit:
    """Класс для работы с вкладом"""
    
    def __init__(self, name: str, balance: float, annual_rate: float, 
                 start_date, end_date=None, auto_renewal: bool = False):
        self.name = name
        self.balance = float(balance)
        self.annual_rate = float(annual_rate)
        self.start_date = self._to_datetime(start_date)
        self.end_date = self._to_datetime(end_date) if end_date else None
        self.auto_renewal = bool(auto_renewal)
    
    @staticmethod
    def _to_datetime(dt) -> Optional[datetime]:
        """Преобразование в datetime"""
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt
        if isinstance(dt, date):
            return datetime.combine(dt, datetime.min.time())
        if isinstance(dt, str):
            return datetime.fromisoformat(dt)
        return dt
    
    def calculate_final_amount(self, target_date=None) -> float:
        """Расчёт итоговой суммы с процентами"""
        if target_date is None:
            target_date = self.end_date if self.end_date else datetime.now()
        
        target = self._to_datetime(target_date)
        start = self.start_date
        
        if not start or not target:
            return self.balance
        
        # Количество дней
        days = (target - start).days
        
        if days <= 0:
            return self.balance
        
        years = days / 365.0
        
        # Простые проценты
        interest = self.balance * (self.annual_rate / 100) * years
        
        return self.balance + interest
    
    def calculate_schedule(self, end_date) -> List[Dict]:
        """Расчёт графика начислений по месяцам"""
        schedule = []
        current_balance = self.balance
        current_date = self.start_date
        end = self._to_datetime(end_date)
        
        if not current_date or not end:
            return []
        
        monthly_rate = self.annual_rate / 12 / 100
        
        while current_date <= end:
            # Начисление процентов
            interest = current_balance * monthly_rate
            current_balance += interest
            
            schedule.append({
                'date': current_date,
                'interest': interest,
                'balance': current_balance
            })
            
            # Следующий месяц
            current_date = current_date + relativedelta(months=1)
        
        return schedule
    
    def calculate_monthly_income(self) -> float:
        """Расчёт ежемесячного дохода"""
        monthly_rate = self.annual_rate / 12 / 100
        return self.balance * monthly_rate
    
    def calculate_yearly_income(self) -> float:
        """Расчёт годового дохода"""
        return self.balance * (self.annual_rate / 100)
    
    def get_days_until_end(self) -> Optional[int]:
        """Количество дней до закрытия вклада"""
        if not self.end_date:
            return None
        
        now = datetime.now()
        days = (self.end_date - now).days
        return max(0, days)
    
    def is_active(self) -> bool:
        """Проверка активности вклада"""
        if not self.end_date:
            return True
        
        days_left = self.get_days_until_end()
        return days_left > 0 if days_left is not None else True
    
    def should_renew(self) -> bool:
        """Проверка необходимости автопролонгации"""
        if not self.auto_renewal or not self.end_date:
            return False
        
        days_left = self.get_days_until_end()
        return days_left is not None and days_left <= 7
    
    def __repr__(self) -> str:
        return f"Deposit(name='{self.name}', balance={self.balance:,.0f}₽, rate={self.annual_rate}%)"


class Strategy:
    """Класс для анализа стратегий погашения кредитов"""
    
    def __init__(self, credits: List[Tuple]):
        self.credits = credits
    
    def _create_credit(self, credit_dict: Dict) -> Credit:
        """Создание объекта Credit из словаря"""
        return Credit(
            name=credit_dict.get('name', 'Без названия'),
            balance=float(credit_dict.get('balance', 0)),
            annual_rate=float(credit_dict.get('annual_rate', 0)),
            monthly_payment=float(credit_dict.get('monthly_payment', 0)),
            start_date=credit_dict.get('start_date', datetime.now()),
            payment_day=int(credit_dict.get('payment_day', 10)),
            end_date=credit_dict.get('end_date')
        )
    
    def _calculate_strategy(self, sort_key: str, reverse: bool, 
                           extra_amount: float) -> List[Tuple[Credit, Dict]]:
        """Универсальный метод расчёта стратегии"""
        sorted_credits = sorted(
            self.credits,
            key=lambda x: float(x[1].get(sort_key, 0)),
            reverse=reverse
        )
        
        results = []
        for _, credit_dict in sorted_credits:
            try:
                credit = self._create_credit(credit_dict)
                result = credit.calculate_with_extra_payment(extra_amount, datetime.now())
                results.append((credit, result))
            except Exception:
                continue
        
        return results
    
    def avalanche(self, extra_amount: float) -> List[Tuple[Credit, Dict]]:
        """Метод лавины - гасим кредит с максимальной ставкой"""
        return self._calculate_strategy('annual_rate', True, extra_amount)
    
    def snowball(self, extra_amount: float) -> List[Tuple[Credit, Dict]]:
        """Метод снежного кома - гасим самый маленький кредит"""
        return self._calculate_strategy('balance', False, extra_amount)
    
    def highest_payment(self, extra_amount: float) -> List[Tuple[Credit, Dict]]:
        """Гасим кредит с максимальным ежемесячным платежом"""
        return self._calculate_strategy('monthly_payment', True, extra_amount)
    
    def compare_all(self, extra_amount: float) -> Dict[str, List]:
        """Сравнение всех стратегий"""
        return {
            'avalanche': self.avalanche(extra_amount),
            'snowball': self.snowball(extra_amount),
            'highest_payment': self.highest_payment(extra_amount)
        }
