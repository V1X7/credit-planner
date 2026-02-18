# ui/heatmap_tab.py
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import calendar
import pandas as pd
from models import Credit
from database import get_distribution_settings, get_income_settings, get_all_credits
from ui.utils import create_credit_object, safe_float


@st.cache_data(ttl=600)
def calculate_roi_for_day(credit_name: str, credit_balance: float, credit_rate: float, 
                          credit_payment_day: int, extra_amount: float, 
                          payment_date_str: str) -> dict:
    """Расчёт ROI для конкретного дня с учётом дней до платежа (кэшировано)"""
    from datetime import datetime, date
    
    payment_date = datetime.fromisoformat(payment_date_str)
    
    # Безопасное получение payment_day
    payment_day = int(credit_payment_day) if credit_payment_day else 10
    
    # Конвертация payment_date в datetime если нужно
    if isinstance(payment_date, date) and not isinstance(payment_date, datetime):
        payment_date = datetime.combine(payment_date, datetime.min.time())
    
    current_month = payment_date.replace(day=1)
    
    # Определяем дату следующего платежа
    try:
        if payment_date.day >= payment_day:
            if current_month.month == 12:
                next_payment_date = datetime(current_month.year + 1, 1, payment_day)
            else:
                next_payment_date = datetime(current_month.year, current_month.month + 1, payment_day)
        else:
            next_payment_date = current_month.replace(day=payment_day)
    except ValueError:
        # Если payment_day = 31, а в месяце 30 дней
        if current_month.month == 12:
            next_payment_date = datetime(current_month.year + 1, 1, 28)
        else:
            next_payment_date = datetime(current_month.year, current_month.month + 1, 28)
    
    # Дни до следующего платежа
    days_until_payment = (next_payment_date - payment_date).days
    
    if days_until_payment <= 0:
        return {'roi': 0, 'savings': 0, 'new_balance': credit_balance, 'overpayment': 0}
    
    # Проверка на переплату
    overpayment = 0
    actual_extra_amount = float(extra_amount)
    
    if actual_extra_amount > credit_balance:
        overpayment = actual_extra_amount - credit_balance
        actual_extra_amount = credit_balance
    
    # Дневная ставка
    daily_rate = float(credit_rate) / 100 / 365
    
    # Проценты за период БЕЗ досрочного платежа
    interest_standard = float(credit_balance) * daily_rate * days_until_payment
    
    # Проценты за период С досрочным платежом
    new_balance = max(0, float(credit_balance) - actual_extra_amount)
    interest_with_extra = new_balance * daily_rate * days_until_payment
    
    # Экономия на процентах
    interest_saved = interest_standard - interest_with_extra
    
    # ROI в %
    roi = (interest_saved / actual_extra_amount * 100) if actual_extra_amount > 0 else 0
    
    return {
        'roi': roi,
        'savings': interest_saved,
        'new_balance': new_balance,
        'overpayment': overpayment
    }


def get_extra_payment_amount():
    """Получение суммы досрочных платежей из ПОСЛЕДНЕГО распределения"""
    
    from database import get_latest_distribution
    
    distribution = get_latest_distribution()
    
    if distribution:
        return float(distribution.get('extra_payments', 0))
    
    # Если нет распределений, возвращаем 0
    return 0


def render_heatmap_tab(credits, deposits):
    """Главная функция вкладки температурной карты"""
    
    st.header("🔥 Температурная карта досрочных платежей")
    
    st.info("""
    **Температурная карта** показывает оптимальные дни и суммы для досрочного погашения кредитов.
    
    - 🟢 **Зелёные зоны** — максимальная выгода (высокий ROI)
    - 🟡 **Жёлтые зоны** — хорошая выгода
    - 🔴 **Красные зоны** — низкая выгода
    """)
    
    if not credits:
        st.warning("⚠️ Нет добавленных кредитов. Перейдите на вкладку 'Кредиты'.")
        return
    
    default_extra_payment = get_extra_payment_amount()
    
    if default_extra_payment <= 0:
        st.error("❌ Сумма досрочных платежей равна 0. Проверьте настройки распределения дохода.")
        return
    
    st.success(f"💰 **Плановый бюджет на досрочные платежи: {default_extra_payment:,.0f} ₽**")
    
    st.divider()
    
    # Выбор кредитов
    st.subheader("1️⃣ Выберите кредиты для анализа")
    
    credit_options = {}
    for credit_id, credit_dict in credits:
        name = credit_dict.get('name', 'Без названия')
        balance = float(credit_dict.get('balance', 0))
        rate = float(credit_dict.get('annual_rate', 0))
        label = f"{name} ({balance:,.0f} ₽ @ {rate}%)"
        credit_options[label] = (credit_id, credit_dict)
    
    selected_credit_names = st.multiselect(
        "Кредиты",
        options=list(credit_options.keys()),
        default=list(credit_options.keys())[:min(3, len(credit_options))]
    )
    
    selected_credits = [credit_options[name] for name in selected_credit_names]
    
    if not selected_credits:
        st.warning("⚠️ Выберите хотя бы один кредит")
        return
    
    st.divider()
    
    # Вкладки анализа
    tab1, tab2, tab3 = st.tabs(["📊 Сумма × День", "💡 Рекомендации", "🎯 Стратегия"])
    
    with tab1:
        render_heatmap_amounts_tab(selected_credits, default_extra_payment)
    
    with tab2:
        render_recommendations_tab(selected_credits, default_extra_payment)
    
    with tab3:
        render_distribution_strategy_tab(selected_credits, default_extra_payment)


def render_heatmap_amounts_tab(selected_credits, default_extra_payment):
    """Вкладка с температурной картой"""
    
    st.subheader("💰 Оптимальные суммы по дням")
    
    # Параметры
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_amount = st.number_input(
            "Минимальная сумма (₽)",
            min_value=1000.0,
            value=max(1000.0, default_extra_payment * 0.5),
            step=1000.0,
            key="heatmap_min"
        )
    
    with col2:
        max_amount = st.number_input(
            "Максимальная сумма (₽)",
            min_value=min_amount + 1000.0,
            value=default_extra_payment * 1.5,
            step=1000.0,
            key="heatmap_max"
        )
    
    with col3:
        num_steps = st.slider(
            "Количество шагов",
            3, 10, 6,
            key="heatmap_steps"
        )
    
    st.divider()
    
    # Генерируем суммы
    amounts = [min_amount + i * (max_amount - min_amount) / (num_steps - 1) for i in range(num_steps)]
    
    # Создаём Credit объекты
    credit_objects = []
    for credit_id, credit_dict in selected_credits:
        try:
            credit = Credit(
                name=credit_dict.get('name', ''),
                balance=float(credit_dict.get('balance', 0)),
                annual_rate=float(credit_dict.get('annual_rate', 0)),
                monthly_payment=float(credit_dict.get('monthly_payment', 0)),
                start_date=credit_dict.get('start_date', datetime.now()),
                payment_day=int(credit_dict.get('payment_day', 10))
            )
            credit_objects.append(credit)
        except Exception as e:
            st.error(f"❌ Ошибка создания кредита: {str(e)}")
    
    if not credit_objects:
        st.error("❌ Не удалось создать объекты кредитов")
        return
    
    # Расчёт матрицы
    today = datetime.now()
    current_month = datetime(today.year, today.month, 1)
    days_in_month = calendar.monthrange(current_month.year, current_month.month)[1]
    
    roi_matrix = {}
    
    with st.spinner("🔄 Рассчитываем..."):
        for amount_idx, extra_amount in enumerate(amounts):
            for day in range(1, days_in_month + 1):
                try:
                    payment_date = current_month.replace(day=day)
                except ValueError:
                    continue
                
                total_savings = 0
                
                for credit in credit_objects:
                    result = calculate_roi_for_day(
                        credit.name,
                        credit.balance,
                        credit.annual_rate,
                        credit.payment_day,
                        extra_amount,
                        payment_date.isoformat()
                    )
                    total_savings += result['savings']
                
                total_roi = (total_savings / extra_amount * 100) if extra_amount > 0 else 0
                
                roi_matrix[(amount_idx, day)] = {
                    'roi': total_roi,
                    'savings': total_savings,
                    'amount': extra_amount
                }
    
    # Подготовка для heatmap
    z_data = []
    hover_text = []
    y_labels = []
    
    for amount_idx, extra_amount in enumerate(amounts):
        y_labels.append(f"{extra_amount:,.0f} ₽")
        row_data = []
        row_hover = []
        
        for day in range(1, days_in_month + 1):
            data = roi_matrix.get((amount_idx, day), {'roi': 0, 'savings': 0, 'amount': 0})
            
            row_data.append(data['roi'])
            
            try:
                date_str = current_month.replace(day=day).strftime('%d.%m.%Y')
            except:
                date_str = f"{day}.{current_month.month}"
            
            hover = (
                f"<b>{date_str}</b><br>"
                f"Сумма: {data['amount']:,.0f} ₽<br>"
                f"ROI: {data['roi']:.2f}%<br>"
                f"Экономия: {data['savings']:,.0f} ₽"
            )
            row_hover.append(hover)
        
        z_data.append(row_data)
        hover_text.append(row_hover)
    
    # Построение графика
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=list(range(1, days_in_month + 1)),
        y=y_labels,
        text=hover_text,
        hovertemplate='%{text}<extra></extra>',
        colorscale=[
            [0.0, '#ff0000'],
            [0.5, '#ffff00'],
            [1.0, '#00aa00']
        ],
        colorbar=dict(title="ROI %")
    ))
    
    fig.update_layout(
        title=f"Температурная карта ({current_month.strftime('%B %Y')})",
        xaxis_title="День месяца",
        yaxis_title="Размер платежа",
        height=700
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Статистика
    col1, col2, col3 = st.columns(3)
    
    with col1:
        max_roi = max((d['roi'] for d in roi_matrix.values()), default=0)
        st.metric("Макс ROI", f"{max_roi:.2f}%")
    
    with col2:
        avg_roi = sum(d['roi'] for d in roi_matrix.values()) / len(roi_matrix) if roi_matrix else 0
        st.metric("Средний ROI", f"{avg_roi:.2f}%")
    
    with col3:
        max_savings = max((d['savings'] for d in roi_matrix.values()), default=0)
        st.metric("Макс экономия", f"{max_savings:,.0f} ₽")


def render_recommendations_tab(selected_credits, default_extra_payment):
    """Вкладка рекомендаций"""
    
    st.subheader("💡 Рекомендации")
    
    credit_objects = []
    for _, credit_dict in selected_credits:
        try:
            credit = Credit(
                name=credit_dict.get('name', ''),
                balance=float(credit_dict.get('balance', 0)),
                annual_rate=float(credit_dict.get('annual_rate', 0)),
                monthly_payment=float(credit_dict.get('monthly_payment', 0)),
                start_date=credit_dict.get('start_date', datetime.now()),
                payment_day=int(credit_dict.get('payment_day', 10))
            )
            credit_objects.append(credit)
        except:
            pass
    
    if not credit_objects:
        st.error("❌ Нет данных")
        return
    
    today = datetime.now()
    current_month = datetime(today.year, today.month, 1)
    days_in_month = calendar.monthrange(current_month.year, current_month.month)[1]
    
    roi_data = []
    
    for day in range(1, days_in_month + 1):
        try:
            payment_date = current_month.replace(day=day)
        except:
            continue
        
        total_savings = 0
        for credit in credit_objects:
            result = calculate_roi_for_day(
                credit.name,
                credit.balance,
                credit.annual_rate,
                credit.payment_day,
                default_extra_payment,  # ИСПРАВЛЕНО: Используем default_extra_payment
                payment_date.isoformat()
            )
            total_savings += result['savings']
        
        total_roi = (total_savings / default_extra_payment * 100) if default_extra_payment > 0 else 0
        
        roi_data.append({
            'date': payment_date,
            'roi': total_roi,
            'savings': total_savings
        })
    
    roi_data.sort(key=lambda x: x['roi'], reverse=True)
    
    st.success(f"**🟢 ТОП-5 дней для платежа {default_extra_payment:,.0f} ₽:**")
    
    for i, data in enumerate(roi_data[:5], 1):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**{i}. {data['date'].strftime('%d.%m.%Y')}**")
        
        with col2:
            st.write(f"ROI: **{data['roi']:.2f}%**")
        
        with col3:
            st.write(f"Экономия: **{data['savings']:,.0f} ₽**")


def render_distribution_strategy_tab(selected_credits, default_extra_payment):
    """Стратегия распределения"""
    
    st.subheader("🎯 Стратегия распределения")
    
    strategy = st.radio(
        "Выберите стратегию:",
        ["Лавинная (макс. ставка)", "Снежный ком (мин. остаток)", "Оптимальная (макс. ROI)"],
        key="strategy"
    )
    
    credit_objects = []
    for _, credit_dict in selected_credits:
        try:
            credit = Credit(
                name=credit_dict.get('name', ''),
                balance=float(credit_dict.get('balance', 0)),
                annual_rate=float(credit_dict.get('annual_rate', 0)),
                monthly_payment=float(credit_dict.get('monthly_payment', 0)),
                start_date=credit_dict.get('start_date', datetime.now()),
                payment_day=int(credit_dict.get('payment_day', 10))
            )
            credit_objects.append(credit)
        except:
            pass
    
    if not credit_objects:
        return
    
    distribution = {}
    
    if "Лавинная" in strategy:
        sorted_credits = sorted(credit_objects, key=lambda c: c.annual_rate, reverse=True)
        distribution[sorted_credits[0].name] = default_extra_payment
        for credit in sorted_credits[1:]:
            distribution[credit.name] = 0
    
    elif "Снежный" in strategy:
        sorted_credits = sorted(credit_objects, key=lambda c: c.balance)
        distribution[sorted_credits[0].name] = min(default_extra_payment, sorted_credits[0].balance)
    
    else:  # Оптимальная
        roi_list = []
        today = datetime.now()
        payment_date = today  # ИСПРАВЛЕНО: Определяем payment_date
        
        for credit in credit_objects:
            result = calculate_roi_for_day(
                credit.name,
                credit.balance,
                credit.annual_rate,
                credit.payment_day,
                default_extra_payment,  # ИСПРАВЛЕНО: Используем default_extra_payment
                payment_date.isoformat()
            )
            roi_list.append((credit, result['roi']))
        
        sorted_by_roi = sorted(roi_list, key=lambda x: x[1], reverse=True)
        distribution[sorted_by_roi[0][0].name] = default_extra_payment
    
    st.success("**📌 Рекомендация:**")
    
    today = datetime.now()
    payment_date = today  # ИСПРАВЛЕНО: Определяем payment_date
    
    for credit in credit_objects:
        amount = distribution.get(credit.name, 0)
        if amount > 0:
            result = calculate_roi_for_day(
                credit.name,
                credit.balance,
                credit.annual_rate,
                credit.payment_day,
                amount,  # ИСПРАВЛЕНО: Используем amount вместо extra_amount
                payment_date.isoformat()
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**💳 {credit.name}**")
            
            with col2:
                st.metric("Платёж", f"{amount:,.0f} ₽")
            
            with col3:
                st.metric("ROI", f"{result['roi']:.2f}%")