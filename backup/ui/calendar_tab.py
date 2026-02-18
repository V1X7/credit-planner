import streamlit as st
from datetime import datetime, timedelta, date
import calendar
import pandas as pd
import plotly.graph_objects as go
from models import Credit, Deposit
from database import get_income_diary


# Словарь для русских дней недели
RUSSIAN_WEEKDAYS = {
    'Monday': 'Пн',
    'Tuesday': 'Вт',
    'Wednesday': 'Ср',
    'Thursday': 'Чт',
    'Friday': 'Пт',
    'Saturday': 'Сб',
    'Sunday': 'Вс'
}

RUSSIAN_WEEKDAYS_FULL = {
    'Monday': 'Понедельник',
    'Tuesday': 'Вторник',
    'Wednesday': 'Среда',
    'Thursday': 'Четверг',
    'Friday': 'Пятница',
    'Saturday': 'Суббота',
    'Sunday': 'Воскресенье'
}

# Словарь для русских месяцев
RUSSIAN_MONTHS = {
    'January': 'Январь',
    'February': 'Февраль',
    'March': 'Март',
    'April': 'Апрель',
    'May': 'Май',
    'June': 'Июнь',
    'July': 'Июль',
    'August': 'Август',
    'September': 'Сентябрь',
    'October': 'Октябрь',
    'November': 'Ноябрь',
    'December': 'Декабрь'
}


def get_russian_date(date):
    """Форматирование даты на русском"""
    day = date.day
    month = RUSSIAN_MONTHS.get(date.strftime('%B'), date.strftime('%B'))
    year = date.year
    weekday = RUSSIAN_WEEKDAYS_FULL.get(date.strftime('%A'), date.strftime('%A'))
    
    return f"{day} {month} {year} ({weekday})"


def render_calendar_grid(events_by_day, year, month):
    """Отрисовка календарной сетки как на картинке"""
    
    month_name_ru = RUSSIAN_MONTHS.get(calendar.month_name[month], calendar.month_name[month])
    
    st.markdown(f"## {month_name_ru} {year}")
    
    # Получаем календарь месяца
    cal = calendar.monthcalendar(year, month)
    
    # Дни недели (начиная с понедельника)
    weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    
    # CSS для календаря
    calendar_css = """
    <style>
        .calendar-grid {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 2px;
            background-color: #333;
            border: 2px solid #333;
            margin: 20px 0;
        }
        .calendar-header {
            background-color: #f8f9fa;
            padding: 10px;
            text-align: center;
            font-weight: bold;
            font-size: 14px;
            border: 1px solid #dee2e6;
        }
        .calendar-cell {
            background-color: white;
            min-height: 100px;
            padding: 8px;
            border: 1px solid #dee2e6;
            position: relative;
        }
        .calendar-cell-empty {
            background-color: #f8f9fa;
        }
        .calendar-day-number {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 8px;
        }
        .calendar-event {
            font-size: 11px;
            padding: 2px 4px;
            margin: 2px 0;
            border-radius: 3px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .event-income {
            background-color: #d4edda;
            color: #155724;
        }
        .event-payment {
            background-color: #f8d7da;
            color: #721c24;
        }
        .event-extra {
            background-color: #fff3cd;
            color: #856404;
        }
        .event-deposit {
            background-color: #d1ecf1;
            color: #0c5460;
        }
        .calendar-total {
            font-size: 12px;
            font-weight: bold;
            margin-top: 4px;
            padding-top: 4px;
            border-top: 1px solid #dee2e6;
        }
        .total-positive {
            color: #28a745;
        }
        .total-negative {
            color: #dc3545;
        }
        .today {
            background-color: #e3f2fd !important;
            border: 2px solid #2196f3 !important;
        }
    </style>
    """
    
    st.markdown(calendar_css, unsafe_allow_html=True)
    
    # Начинаем формировать HTML календаря
    calendar_html = '<div class="calendar-grid">'
    
    # Заголовки дней недели
    for weekday in weekdays:
        calendar_html += f'<div class="calendar-header">{weekday}</div>'
    
    # Получаем сегодняшнюю дату
    today = datetime.now().date()
    
    # Отрисовка недель
    for week in cal:
        for day in week:
            if day == 0:
                # Пустая ячейка
                calendar_html += '<div class="calendar-cell calendar-cell-empty"></div>'
            else:
                # Проверяем, сегодня ли это
                is_today = (year == today.year and month == today.month and day == today.day)
                today_class = ' today' if is_today else ''
                
                # Формируем ключ дня
                day_key = f"{year}-{month:02d}-{day:02d}"
                
                # Получаем события дня
                day_events = events_by_day.get(day_key, [])
                
                # Считаем общую сумму
                day_total = sum(e['amount'] for e in day_events)
                day_inflow = sum(e['amount'] for e in day_events if e['amount'] > 0)
                day_outflow = sum(abs(e['amount']) for e in day_events if e['amount'] < 0)
                
                # Начинаем ячейку дня
                calendar_html += f'<div class="calendar-cell{today_class}">'
                calendar_html += f'<div class="calendar-day-number">{day}</div>'
                
                # Показываем максимум 3 события
                for i, event in enumerate(day_events[:3]):
                    event_class = {
                        'income': 'event-income',
                        'regular_payment': 'event-payment',
                        'extra_payment': 'event-extra',
                        'deposit_close': 'event-deposit'
                    }.get(event['type'], 'event-payment')
                    
                    event_icon = event['icon']
                    event_text = event['name'].replace('💵 ', '').replace('💳 ', '').replace('💰 ', '').replace('💎 ', '')
                    
                    # Укорачиваем название если длинное
                    if len(event_text) > 15:
                        event_text = event_text[:12] + '...'
                    
                    calendar_html += f'<div class="calendar-event {event_class}">{event_icon} {event_text}</div>'
                
                # Если событий больше 3
                if len(day_events) > 3:
                    calendar_html += f'<div class="calendar-event" style="background-color:#e9ecef;color:#495057;">+ ещё {len(day_events) - 3}</div>'
                
                # Показываем итоговую сумму, если есть события
                if day_events:
                    total_class = 'total-positive' if day_total >= 0 else 'total-negative'
                    sign = '+' if day_total >= 0 else ''
                    calendar_html += f'<div class="calendar-total {total_class}">{sign}{day_total:,.0f}₽</div>'
                
                calendar_html += '</div>'
    
    calendar_html += '</div>'
    
    st.markdown(calendar_html, unsafe_allow_html=True)


def render_calendar_tab(credits, deposits):
    """Вкладка календаря платежей"""
    
    st.header("📅 Календарь платежей")
    
    st.info("""
    **Календарь платежей** показывает все предстоящие финансовые события:
    - 💵 Доходы (зарплата, аванс)
    - 💳 Обязательные платежи по кредитам
    - 💰 Досрочные платежи
    - 💎 Закрытие вкладов
    """)
    
    # Параметры периода
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_year = st.selectbox(
            "Год",
            list(range(datetime.now().year - 1, datetime.now().year + 3)),
            index=1,
            key="calendar_year"
        )
    
    with col2:
        selected_month = st.selectbox(
            "Месяц",
            list(range(1, 13)),
            format_func=lambda x: RUSSIAN_MONTHS[calendar.month_name[x]],
            index=datetime.now().month - 1,
            key="calendar_month"
        )
    
    with col3:
        show_income = st.checkbox("Показать доходы", value=True, key="show_income")
    
    # Фильтры
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_credits = st.checkbox("💳 Кредиты", value=True, key="filter_credits")
    
    with col2:
        filter_deposits = st.checkbox("💎 Вклады", value=True, key="filter_deposits")
    
    with col3:
        filter_extra = st.checkbox("💰 Досрочные", value=True, key="filter_extra")
    
    # Период месяца
    start_datetime = datetime(selected_year, selected_month, 1)
    if selected_month == 12:
        end_datetime = datetime(selected_year + 1, 1, 1) - timedelta(days=1)
    else:
        end_datetime = datetime(selected_year, selected_month + 1, 1) - timedelta(days=1)
    
    end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
    
    # Собираем все события
    events = []
    
    # ==================== ДОХОДЫ ИЗ ДНЕВНИКА ====================
    
    if show_income:
        try:
            diary_entries = get_income_diary(year=selected_year, month=selected_month)
            
            if diary_entries:
                for entry in diary_entries:
                    try:
                        entry_date = datetime.strptime(entry['date'], '%Y-%m-%d')
                        
                        if start_datetime <= entry_date <= end_datetime:
                            events.append({
                                'date': entry_date,
                                'type': 'income',
                                'name': f"💵 {entry['salary_type']}",
                                'amount': float(entry['amount']),
                                'icon': '💵',
                                'color': '#6BCB77'
                            })
                    except Exception as e:
                        st.warning(f"⚠️ Ошибка обработки дохода: {e}")
        except Exception as e:
            st.error(f"❌ Ошибка получения доходов: {e}")
    
    # ==================== КРЕДИТЫ ====================
    
    if filter_credits and credits:
        for credit_id, credit_dict in credits:
            try:
                name = str(credit_dict.get('name', 'Без названия'))
                balance = float(credit_dict.get('balance', 0))
                annual_rate = float(credit_dict.get('annual_rate', 0))
                monthly_payment = float(credit_dict.get('monthly_payment', 0))
                payment_day = int(credit_dict.get('payment_day', 10))
                
                start_date_val = credit_dict.get('start_date', datetime.now())
                if isinstance(start_date_val, str):
                    start_date_val = datetime.fromisoformat(start_date_val)
                elif isinstance(start_date_val, date) and not isinstance(start_date_val, datetime):
                    start_date_val = datetime.combine(start_date_val, datetime.min.time())
                
                end_date_val = credit_dict.get('end_date')
                if end_date_val:
                    if isinstance(end_date_val, str):
                        end_date_val = datetime.fromisoformat(end_date_val)
                    elif isinstance(end_date_val, date) and not isinstance(end_date_val, datetime):
                        end_date_val = datetime.combine(end_date_val, datetime.min.time())
                
                credit = Credit(
                    name=name,
                    balance=balance,
                    annual_rate=annual_rate,
                    monthly_payment=monthly_payment,
                    start_date=start_date_val,
                    payment_day=payment_day,
                    end_date=end_date_val
                )
                
                # ✅ ИСПРАВЛЕННЫЙ КОД: Создаём платежи для каждого месяца в периоде
                current_month = start_datetime.replace(day=1)
                
                while current_month <= end_datetime:
                    try:
                        # Создаём дату платежа для текущего месяца
                        payment_date = current_month.replace(day=payment_day)
                        
                        # Если день платежа больше дней в месяце (31 февраля), берём последний день
                        if payment_date.month != current_month.month:
                            payment_date = current_month.replace(day=1) - timedelta(days=1)
                        
                        # Проверяем, что дата в периоде
                        if start_datetime <= payment_date <= end_datetime:
                            # Рассчитываем баланс на эту дату для точности
                            schedule_check = credit.calculate_schedule(payment_date)
                            
                            events.append({
                                'date': payment_date,
                                'type': 'regular_payment',
                                'name': f"💳 {name}",
                                'amount': -monthly_payment,
                                'interest': float(schedule_check[-1].get('interest', 0)) if schedule_check else 0,
                                'principal': float(schedule_check[-1].get('principal', 0)) if schedule_check else 0,
                                'balance': float(schedule_check[-1].get('balance', 0)) if schedule_check else balance,
                                'icon': '💳',
                                'color': '#4ECDC4'
                            })
                        
                    except ValueError:
                        # День не существует в месяце — пропускаем
                        pass
                    
                    # Следующий месяц
                    if current_month.month == 12:
                        current_month = current_month.replace(year=current_month.year + 1, month=1)
                    else:
                        current_month = current_month.replace(month=current_month.month + 1)
                
                # ==================== ДОСРОЧНЫЕ ПЛАТЕЖИ ====================
                
                if filter_extra:
                    extra_payments = credit_dict.get('extra_payments', {})
                    if isinstance(extra_payments, dict):
                        for payment_date_str, amount in extra_payments.items():
                            try:
                                if isinstance(payment_date_str, str):
                                    payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d')
                                elif isinstance(payment_date_str, datetime):
                                    payment_date = payment_date_str
                                elif isinstance(payment_date_str, date):
                                    payment_date = datetime.combine(payment_date_str, datetime.min.time())
                                else:
                                    continue
                                
                                if start_datetime <= payment_date <= end_datetime:
                                    events.append({
                                        'date': payment_date,
                                        'type': 'extra_payment',
                                        'name': f"💰 {name} (досрочный)",
                                        'amount': -float(amount),
                                        'icon': '💰',
                                        'color': '#FFD93D'
                                    })
                            except Exception:
                                pass
            
            except Exception as e:
                st.error(f"❌ Ошибка обработки кредита: {str(e)}")
    
    # ==================== ВКЛАДЫ ====================
    
    if filter_deposits and deposits:
        for deposit_id, deposit_dict in deposits:
            try:
                name = str(deposit_dict.get('name', 'Без названия'))
                balance = float(deposit_dict.get('balance', 0))
                annual_rate = float(deposit_dict.get('annual_rate', 0))
                auto_renewal = bool(deposit_dict.get('auto_renewal', False))
                
                start_date_val = deposit_dict.get('start_date', datetime.now())
                if isinstance(start_date_val, str):
                    start_date_val = datetime.fromisoformat(start_date_val)
                elif isinstance(start_date_val, date) and not isinstance(start_date_val, datetime):
                    start_date_val = datetime.combine(start_date_val, datetime.min.time())
                
                end_date_val = deposit_dict.get('end_date')
                if end_date_val:
                    if isinstance(end_date_val, str):
                        end_date_val = datetime.fromisoformat(end_date_val)
                    elif isinstance(end_date_val, date) and not isinstance(end_date_val, datetime):
                        end_date_val = datetime.combine(end_date_val, datetime.min.time())
                
                deposit = Deposit(
                    name=name,
                    balance=balance,
                    annual_rate=annual_rate,
                    start_date=start_date_val,
                    end_date=end_date_val,
                    auto_renewal=auto_renewal
                )
                
                if deposit.end_date:
                    end_date_check = deposit.end_date if isinstance(deposit.end_date, datetime) else datetime.combine(deposit.end_date, datetime.min.time())
                    
                    if start_datetime <= end_date_check <= end_datetime:
                        final_amount = deposit.calculate_final_amount()
                        profit = final_amount - deposit.balance
                        
                        events.append({
                            'date': end_date_check,
                            'type': 'deposit_close',
                            'name': f"💎 {name}",
                            'amount': final_amount,
                            'profit': profit,
                            'icon': '💎',
                            'color': '#45B7D1'
                        })
            except Exception as e:
                st.error(f"❌ Ошибка обработки вклада: {str(e)}")
    
    # Группируем события по дням
    events_by_day = {}
    
    for event in events:
        day_key = event['date'].strftime('%Y-%m-%d')
        if day_key not in events_by_day:
            events_by_day[day_key] = []
        events_by_day[day_key].append(event)
    
    # Статистика месяца
    total_outflow = sum(abs(e['amount']) for e in events if e['amount'] < 0)
    total_inflow = sum(e['amount'] for e in events if e['amount'] > 0)
    net_flow = total_inflow - total_outflow
    
    st.divider()
    
    # Метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📤 Расходы", f"{total_outflow:,.0f} ₽")
    
    with col2:
        st.metric("📥 Доходы", f"{total_inflow:,.0f} ₽")
    
    with col3:
        st.metric("💰 Баланс", f"{net_flow:,.0f} ₽")
    
    with col4:
        st.metric("📅 Событий", len(events))
    
    st.divider()
    
    # ==================== КАЛЕНДАРНАЯ СЕТКА ====================
    
    render_calendar_grid(events_by_day, selected_year, selected_month)
    
    st.divider()
    
    # ==================== ДЕТАЛИ ПО ДНЯМ ====================
    
    if events_by_day:
        st.subheader("📋 Детали по дням")
        
        for day_key in sorted(events_by_day.keys()):
            day_events = events_by_day[day_key]
            day_date = datetime.strptime(day_key, '%Y-%m-%d')
            
            day_total = sum(e['amount'] for e in day_events)
            day_inflow = sum(e['amount'] for e in day_events if e['amount'] > 0)
            day_outflow = sum(abs(e['amount']) for e in day_events if e['amount'] < 0)
            
            emoji = "✅" if day_total >= 0 else "⚠️"
            
            with st.expander(
                f"{emoji} **{get_russian_date(day_date)}** — "
                f"События: {len(day_events)} | "
                f"Доходы: {day_inflow:,.0f}₽ | "
                f"Расходы: {day_outflow:,.0f}₽ | "
                f"Баланс: {day_total:+,.0f}₽",
                expanded=False
            ):
                for i, event in enumerate(day_events, 1):
                    col1, col2, col3 = st.columns([1, 3, 2])
                    
                    with col1:
                        st.markdown(f"**{i}.** {event['icon']}")
                    
                    with col2:
                        st.write(f"**{event['name']}**")
                    
                    with col3:
                        if event['amount'] >= 0:
                            st.success(f"**+{event['amount']:,.0f} ₽**")
                        else:
                            st.error(f"**{event['amount']:,.0f} ₽**")
                    
                    st.markdown("---")
                
                # Итог дня
                if day_total < 0:
                    st.error(f"🔻 **Дефицит дня: {abs(day_total):,.0f} ₽**")
                elif day_total > 0:
                    st.success(f"🔺 **Профицит дня: +{day_total:,.0f} ₽**")
                else:
                    st.info("⚖️ **Баланс дня: 0 ₽**")
    else:
        st.info("📭 Нет событий в этом месяце")