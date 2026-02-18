import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd


# ==================== КОНСТАНТЫ ====================

CREDIT_COLORS = [
    "#FF6B6B",  # Красный
    "#FFA07A",  # Оранжевый
    "#FFD700",  # Жёлтый
    "#98D8C8",  # Бирюзовый
    "#DDA0DD",  # Фиолетовый
    "#F08080",  # Коралловый
    "#87CEEB",  # Небесно-голубой
    "#FF69B4",  # Розовый
]

DEPOSIT_COLOR = "#4ECDC4"  # Бирюзовый
INTERSECTION_COLOR = "#FFD700"  # Золотой


# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================

def render_forecast_chart(credits, deposits):
    """Главная функция графика прогноза"""
    
    st.header("📈 Прогноз: Кредиты vs Вклады")
    
    st.info("""
    **Интерактивный график прогноза** показывает траекторию погашения кредитов и роста вкладов.
    
    - 🔴 **Кредиты** — уменьшаются с каждым платежом
    - 🟢 **Вклады** — растут за счёт процентов и пополнений
    - ⭐ **Точки пересечения** — даты, когда можно закрыть кредит средствами вкладов
    """)
    
    # ИСПРАВЛЕНО: Проверка только на наличие хотя бы одного источника данных
    if not credits and not deposits:
        st.warning("⚠️ Добавьте кредиты или вклады для построения прогноза")
        return
    
    st.divider()
    
    # ==================== НАСТРОЙКИ ОТОБРАЖЕНИЯ ====================
    
    chart_height, forecast_years, show_facts, show_forecasts, show_intersections = render_display_settings()
    
    st.divider()
    
    # ==================== ВЫБОР КРЕДИТОВ ====================
    
    selected_credits = []
    if credits:
        selected_credits = render_credit_selector(credits)
        
        if not selected_credits:
            st.warning("⚠️ Выберите хотя бы один кредит для отображения")
            return
        
        st.divider()
    
    # ==================== РАСЧЁТ ТРАЕКТОРИЙ ====================
    
    with st.spinner("🔄 Рассчитываем траектории..."):
        # Траектории кредитов
        credits_timelines = {}
        if selected_credits:
            for credit_info in selected_credits:
                timeline = calculate_credit_timeline(
                    credit_info['data'],
                    forecast_years
                )
                if timeline:  # ИСПРАВЛЕНО: Проверка на пустой timeline
                    credits_timelines[credit_info['id']] = {
                        'timeline': timeline,
                        'name': credit_info['data'].get('name', 'Без названия'),
                        'color': credit_info['color']
                    }
        
        # Траектория вкладов
        deposits_timeline = {}
        if deposits:
            deposits_timeline = calculate_deposits_timeline(deposits, forecast_years)
        
        # Точки пересечения (последовательное закрытие)
        intersections = []
        if show_intersections and selected_credits and deposits_timeline:
            intersections = calculate_sequential_intersections(
                selected_credits,
                deposits_timeline,
                credits_timelines
            )
    
    # ==================== ПОСТРОЕНИЕ ГРАФИКА ====================
    
    # ИСПРАВЛЕНО: Проверка на наличие данных для графика
    if not credits_timelines and not deposits_timeline:
        st.error("❌ Нет данных для построения графика")
        return
    
    fig = create_forecast_figure(
        credits_timelines,
        deposits_timeline,
        intersections,
        chart_height,
        show_facts,
        show_forecasts
    )
    
    # Отображение графика
    st.plotly_chart(fig, use_container_width=True, config={
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
        'toImageButtonOptions': {
            'format': 'png',
            'filename': f'forecast_{datetime.now().strftime("%Y%m%d")}',
            'height': 1080,
            'width': 1920,
            'scale': 2
        }
    })
    
    st.divider()
    
    # ==================== МЕТРИКИ ТОЧЕК ПЕРЕСЕЧЕНИЯ ====================
    
    if intersections:
        render_intersections_metrics(intersections)
        st.divider()
    
    # ==================== СЦЕНАРИИ "ЧТО ЕСЛИ?" ====================
    
    if selected_credits or deposits:
        render_what_if_scenarios(selected_credits, deposits, forecast_years, credits_timelines, deposits_timeline)


# ==================== НАСТРОЙКИ ОТОБРАЖЕНИЯ ====================

def render_display_settings():
    """Панель настроек отображения графика"""
    
    st.subheader("⚙️ Настройки графика")
    
    col1, col2 = st.columns(2)
    
    with col1:
        chart_height = st.slider(
            "📏 Высота графика (px)",
            min_value=400,
            max_value=1200,
            value=700,
            step=50,
            key="chart_height"
        )
        
        forecast_years = st.slider(
            "📅 Период прогноза (лет)",
            min_value=1,
            max_value=10,
            value=5,
            step=1,
            key="forecast_years"
        )
    
    with col2:
        st.write("**Отображение элементов:**")
        
        show_facts = st.checkbox(
            "📊 Показывать факт (сплошные линии)",
            value=True,
            key="show_facts"
        )
        
        show_forecasts = st.checkbox(
            "🔮 Показывать прогноз (пунктирные линии)",
            value=True,
            key="show_forecasts"
        )
        
        show_intersections = st.checkbox(
            "⭐ Показывать точки пересечения",
            value=True,
            key="show_intersections"
        )
    
    return chart_height, forecast_years, show_facts, show_forecasts, show_intersections


# ==================== ВЫБОР КРЕДИТОВ ====================

def render_credit_selector(credits):
    """Выбор кредитов для отображения на графике"""
    
    st.subheader("💳 Выбор кредитов для отображения")
    
    st.write("Отметьте кредиты, которые хотите отобразить на графике:")
    
    selected_credits = []
    
    # Определяем количество колонок динамически
    num_cols = min(len(credits), 3)
    cols = st.columns(num_cols)
    
    for i, (credit_id, credit_dict) in enumerate(credits):
        color = CREDIT_COLORS[i % len(CREDIT_COLORS)]
        
        with cols[i % num_cols]:
            # ИСПРАВЛЕНО: Безопасное получение значений с float()
            name = str(credit_dict.get('name', 'Без названия'))
            balance = float(credit_dict.get('balance', 0))
            rate = float(credit_dict.get('annual_rate', 0))
            
            is_visible = st.checkbox(
                f"**{name}**",
                value=True,
                key=f"credit_visible_{credit_id}",
                help=f"{balance:,.0f} ₽ @ {rate:.2f}%"
            )
            
            # Индикатор цвета
            st.markdown(
                f"<div style='width:100%; height:5px; background-color:{color}; border-radius:3px; margin-bottom:10px;'></div>",
                unsafe_allow_html=True
            )
            
            # Краткая информация
            st.caption(f"💰 {balance:,.0f} ₽")
            st.caption(f"📊 {rate:.2f}% годовых")
        
        if is_visible:
            selected_credits.append({
                "id": credit_id,
                "data": credit_dict,
                "color": color
            })
    
    if selected_credits:
        st.success(f"✅ Выбрано кредитов: {len(selected_credits)}")
    
    return selected_credits


# ==================== РАСЧЁТ ТРАЕКТОРИЙ ====================

def calculate_credit_timeline(credit_dict, forecast_years):
    """Расчёт траектории одного кредита"""
    
    try:
        balance = float(credit_dict.get('balance', 0))
        annual_rate = float(credit_dict.get('annual_rate', 0))
        monthly_payment = float(credit_dict.get('monthly_payment', 0))
    except (ValueError, TypeError):
        return {}
    
    if balance <= 0 or monthly_payment <= 0:
        return {}
    
    monthly_rate = annual_rate / 100 / 12
    
    timeline = {}
    current_date = datetime.now()
    current_balance = balance
    
    # Расчёт на период прогноза
    months = forecast_years * 12
    
    for month in range(months + 1):
        date = current_date + relativedelta(months=month)
        
        # Расчёт процентов
        interest = current_balance * monthly_rate
        
        # Гашение тела долга
        principal = monthly_payment - interest
        
        # Сохраняем текущий баланс
        timeline[date] = {
            'balance': max(0, current_balance),
            'type': 'fact' if month == 0 else 'forecast'
        }
        
        # Уменьшаем баланс
        if principal > 0:
            current_balance -= principal
        
        # Не уходим в минус
        current_balance = max(0, current_balance)
        
        # Если кредит погашен, заполняем остаток нулями
        if current_balance <= 0.01:  # ИСПРАВЛЕНО: Учёт погрешности
            for remaining_month in range(month + 1, months + 1):
                future_date = current_date + relativedelta(months=remaining_month)
                timeline[future_date] = {
                    'balance': 0,
                    'type': 'forecast'
                }
            break
    
    return timeline


def calculate_deposits_timeline(deposits, forecast_years):
    """Расчёт траектории вкладов"""
    
    if not deposits:
        return {}
    
    try:
        total_balance = sum(float(d[1].get('balance', 0)) for d in deposits)
    except (ValueError, TypeError):
        return {}
    
    if total_balance <= 0:
        return {}
    
    # ИСПРАВЛЕНО: Защита от деления на ноль
    try:
        weighted_rate = sum(
            float(d[1].get('balance', 0)) * float(d[1].get('annual_rate', 0))
            for d in deposits
        ) / total_balance
    except (ValueError, TypeError, ZeroDivisionError):
        weighted_rate = 0
    
    monthly_rate = weighted_rate / 100 / 12
    
    timeline = {}
    current_date = datetime.now()
    current_balance = total_balance
    
    months = forecast_years * 12
    
    for month in range(months + 1):
        date = current_date + relativedelta(months=month)
        
        timeline[date] = {
            'balance': current_balance,
            'type': 'fact' if month == 0 else 'forecast'
        }
        
        # Начисление процентов
        interest = current_balance * monthly_rate
        current_balance += interest
    
    return timeline


def calculate_sequential_intersections(selected_credits, deposits_timeline, credits_timelines):
    """Расчёт точек пересечения с последовательным закрытием кредитов"""
    
    if not selected_credits or not deposits_timeline:
        return []
    
    # Сортируем кредиты по остатку (сначала маленькие)
    sorted_credits = sorted(
        selected_credits,
        key=lambda c: float(c['data'].get('balance', 0))
    )
    
    intersections = []
    accumulated_closed = 0
    
    for i, credit_info in enumerate(sorted_credits):
        credit_id = credit_info['id']
        credit_data = credit_info['data']
        credit_timeline = credits_timelines.get(credit_id, {}).get('timeline', {})
        
        if not credit_timeline:
            continue
        
        # Ищем точку пересечения
        intersection_date = None
        intersection_amount = None
        
        for date in sorted(credit_timeline.keys()):
            credit_balance = credit_timeline[date]['balance']
            deposit_balance = deposits_timeline.get(date, {}).get('balance', 0)
            
            # Вычитаем то, что уже потратили на предыдущие кредиты
            available_deposits = deposit_balance - accumulated_closed
            
            # ИСПРАВЛЕНО: Учёт погрешности
            if available_deposits >= credit_balance and credit_balance > 0.01:
                intersection_date = date
                intersection_amount = credit_balance
                break
        
        if intersection_date and intersection_amount:
            deposit_balance = deposits_timeline[intersection_date]['balance']
            available = deposit_balance - accumulated_closed
            
            intersections.append({
                "order": i + 1,
                "credit_id": credit_id,
                "credit_name": credit_data.get('name', 'Без названия'),
                "credit_balance": float(credit_data.get('balance', 0)),
                "date": intersection_date,
                "amount": intersection_amount,
                "deposits_total": deposit_balance,
                "deposits_available": available,
                "surplus": available - intersection_amount,
                "days_from_now": (intersection_date - datetime.now()).days,
                "depends_on": [c['data'].get('name', 'Без названия') for c in sorted_credits[:i]] if i > 0 else [],
                "color": credit_info['color']
            })
            
            # Добавляем к накопленной сумме
            accumulated_closed += intersection_amount
    
    return intersections


# ==================== ПОСТРОЕНИЕ ГРАФИКА ====================

def create_forecast_figure(credits_timelines, deposits_timeline, intersections,
                           chart_height, show_facts, show_forecasts):
    """Создание интерактивного графика Plotly"""
    
    fig = go.Figure()
    
    # ==================== КРИВЫЕ КРЕДИТОВ ====================
    
    for credit_id, credit_info in credits_timelines.items():
        timeline = credit_info.get('timeline', {})
        if not timeline:
            continue
        
        name = credit_info.get('name', 'Без названия')
        color = credit_info.get('color', '#FF6B6B')
        
        dates = sorted(timeline.keys())
        
        # Разделяем на факт и прогноз
        fact_dates = [d for d in dates if timeline[d]['type'] == 'fact']
        forecast_dates = [d for d in dates if timeline[d]['type'] == 'forecast']
        
        fact_balances = [timeline[d]['balance'] for d in fact_dates]
        forecast_balances = [timeline[d]['balance'] for d in forecast_dates]
        
        # Сплошная линия (факт)
        if show_facts and fact_dates:
            fig.add_trace(go.Scatter(
                x=fact_dates,
                y=fact_balances,
                name=f"💳 {name}",
                line=dict(color=color, width=3),
                mode='lines',
                legendgroup=f"credit_{credit_id}",
                hovertemplate=(
                    f"<b>{name}</b><br>"
                    "📅 %{x|%d.%m.%Y}<br>"
                    "💰 %{y:,.0f} ₽<br>"
                    "<extra></extra>"
                )
            ))
        
        # Пунктирная линия (прогноз)
        if show_forecasts and forecast_dates:
            if fact_dates and fact_balances:
                forecast_dates_full = [fact_dates[-1]] + forecast_dates
                forecast_balances_full = [fact_balances[-1]] + forecast_balances
            else:
                forecast_dates_full = forecast_dates
                forecast_balances_full = forecast_balances
            
            fig.add_trace(go.Scatter(
                x=forecast_dates_full,
                y=forecast_balances_full,
                name=f"🔮 {name} (прогноз)",
                line=dict(color=color, width=2, dash='dash'),
                mode='lines',
                legendgroup=f"credit_{credit_id}",
                showlegend=False,
                hovertemplate=(
                    f"<b>{name} (прогноз)</b><br>"
                    "📅 %{x|%d.%m.%Y}<br>"
                    "💰 %{y:,.0f} ₽<br>"
                    "<extra></extra>"
                )
            ))
    
    # ==================== КРИВАЯ ВКЛАДОВ ====================
    
    if deposits_timeline:
        dates = sorted(deposits_timeline.keys())
        fact_dates = [d for d in dates if deposits_timeline[d]['type'] == 'fact']
        forecast_dates = [d for d in dates if deposits_timeline[d]['type'] == 'forecast']
        
        fact_balances = [deposits_timeline[d]['balance'] for d in fact_dates]
        forecast_balances = [deposits_timeline[d]['balance'] for d in forecast_dates]
        
        # Сплошная линия вкладов
        if show_facts and fact_dates:
            fig.add_trace(go.Scatter(
                x=fact_dates,
                y=fact_balances,
                name="💎 Вклады",
                line=dict(color=DEPOSIT_COLOR, width=3),
                mode='lines',
                legendgroup="deposits",
                hovertemplate=(
                    "<b>Вклады</b><br>"
                    "📅 %{x|%d.%m.%Y}<br>"
                    "💰 %{y:,.0f} ₽<br>"
                    "<extra></extra>"
                )
            ))
        
        # Пунктирная линия вкладов
        if show_forecasts and forecast_dates:
            if fact_dates and fact_balances:
                forecast_dates_full = [fact_dates[-1]] + forecast_dates
                forecast_balances_full = [fact_balances[-1]] + forecast_balances
            else:
                forecast_dates_full = forecast_dates
                forecast_balances_full = forecast_balances
            
            fig.add_trace(go.Scatter(
                x=forecast_dates_full,
                y=forecast_balances_full,
                name="🔮 Вклады (прогноз)",
                line=dict(color=DEPOSIT_COLOR, width=2, dash='dash'),
                mode='lines',
                legendgroup="deposits",
                showlegend=False,
                hovertemplate=(
                    "<b>Вклады (прогноз)</b><br>"
                    "📅 %{x|%d.%m.%Y}<br>"
                    "💰 %{y:,.0f} ₽<br>"
                    "<extra></extra>"
                )
            ))
    
    # ==================== ТОЧКИ ПЕРЕСЕЧЕНИЯ ====================
    
    for intersection in intersections:
        fig.add_trace(go.Scatter(
            x=[intersection['date']],
            y=[intersection['amount']],
            mode='markers+text',
            marker=dict(
                symbol='star',
                size=25,
                color=INTERSECTION_COLOR,
                line=dict(color='white', width=2)
            ),
            text=f"{intersection['order']}",
            textposition='top center',
            textfont=dict(size=14, color='#333', family='Arial Black'),
            name=f"⭐ Закрытие {intersection['credit_name']}",
            hovertemplate=(
                f"<b>🎉 Можно закрыть {intersection['credit_name']}</b><br>"
                f"📅 {intersection['date'].strftime('%d.%m.%Y')}<br>"
                f"💰 Остаток: {intersection['amount']:,.0f} ₽<br>"
                f"🟢 Доступно вкладов: {intersection['deposits_available']:,.0f} ₽<br>"
                f"📊 Запас: +{intersection['surplus']:,.0f} ₽<br>"
                f"⏱️ Через {intersection['days_from_now']} дней<br>"
                "<extra></extra>"
            ),
            showlegend=True
        ))
        
        # Вертикальная линия от маркера до оси X
        fig.add_shape(
            type="line",
            x0=intersection['date'],
            y0=0,
            x1=intersection['date'],
            y1=intersection['amount'],
            line=dict(color=INTERSECTION_COLOR, width=2, dash="dot"),
            layer="below"
        )
    
    # ==================== НАСТРОЙКИ ГРАФИКА ====================
    
    fig.update_layout(
        title=dict(
            text="📈 Динамика кредитов и вкладов",
            font=dict(size=20, color='#333', family='Arial Black')
        ),
        xaxis=dict(
            title="Дата",
            showgrid=True,
            gridcolor='#E0E0E0',
            tickformat='%b %Y',
            dtick="M3"
        ),
        yaxis=dict(
            title="Сумма (₽)",
            showgrid=True,
            gridcolor='#E0E0E0',
            tickformat=',.0f',
            hoverformat=',.0f'
        ),
        hovermode='x unified',
        height=chart_height,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.01,
            bgcolor="rgba(255, 255, 255, 0.95)",
            bordercolor="#333",
            borderwidth=1,
            font=dict(size=11),
            itemclick="toggle",
            itemdoubleclick="toggleothers"
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial, sans-serif', size=12, color='#333'),
        margin=dict(l=80, r=200, t=80, b=80),
        dragmode='zoom'
    )
    
    return fig


# ==================== МЕТРИКИ ТОЧЕК ПЕРЕСЕЧЕНИЯ ====================

def render_intersections_metrics(intersections):
    """Отображение метрик точек пересечения"""
    
    st.subheader("⭐ Точки пересечения (последовательное закрытие)")
    
    st.write("График показывает **последовательное** закрытие кредитов (от меньшего к большему):")
    
    for i, intersection in enumerate(intersections):
        with st.expander(
            f"{intersection['order']}️⃣ **{intersection['credit_name']}** — "
            f"{intersection['date'].strftime('%d.%m.%Y')} "
            f"(через {intersection['days_from_now']} дней)",
            expanded=(i == 0)
        ):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "📅 Дата закрытия",
                    intersection['date'].strftime('%d.%m.%Y')
                )
            
            with col2:
                st.metric(
                    "💰 Остаток кредита",
                    f"{intersection['amount']:,.0f} ₽"
                )
            
            with col3:
                st.metric(
                    "🟢 Доступно вкладов",
                    f"{intersection['deposits_available']:,.0f} ₽"
                )
            
            with col4:
                st.metric(
                    "📊 Запас",
                    f"+{intersection['surplus']:,.0f} ₽"
                )
            
            if intersection['depends_on']:
                st.info(
                    "⏳ **Доступно после закрытия:**\n\n" +
                    "\n".join(f"✅ {name}" for name in intersection['depends_on'])
                )
            else:
                st.success("✅ **Можно закрыть первым!**")
    
    if len(intersections) > 0:
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            first_intersection = intersections[0]
            st.metric(
                "🏆 Первое закрытие",
                first_intersection['credit_name'],
                delta=f"Через {first_intersection['days_from_now']} дней"
            )
        
        with col2:
            last_intersection = intersections[-1]
            st.metric(
                "🎯 Последнее закрытие",
                last_intersection['credit_name'],
                delta=f"Через {last_intersection['days_from_now']} дней"
            )
        
        with col3:
            total_days = (last_intersection['date'] - datetime.now()).days
            total_years = total_days / 365
            st.metric(
                "⏱️ Полное закрытие",
                f"~{total_years:.1f} лет",
                delta=f"{total_days} дней"
            )


# ==================== СЦЕНАРИИ "ЧТО ЕСЛИ?" ====================

def render_what_if_scenarios(selected_credits, deposits, forecast_years, credits_timelines, deposits_timeline):
    """Сценарии 'Что если?'"""
    
    st.subheader("🎮 Сценарии 'Что если?'")
    
    st.write("Измените параметры и посмотрите, как изменится прогноз:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        extra_payment = st.number_input(
            "💸 Досрочный платёж/месяц (₽)",
            min_value=0,
            max_value=500_000,
            value=0,
            step=5_000,
            key="extra_payment_scenario",
            help="Дополнительный платёж к стандартному"
        )
    
    with col2:
        extra_deposit = st.number_input(
            "💎 Пополнение вкладов/месяц (₽)",
            min_value=0,
            max_value=500_000,
            value=0,
            step=5_000,
            key="extra_deposit_scenario",
            help="Ежемесячное пополнение вкладов"
        )
    
    with col3:
        rate_increase = st.number_input(
            "📈 Изменение ставки вкладов (%)",
            min_value=-10.0,
            max_value=10.0,
            value=0.0,
            step=0.5,
            key="rate_change_scenario",
            help="Изменение ставки (может быть отрицательным)"
        )
    
    if st.button("🔄 Пересчитать прогноз", type="primary"):
        if extra_payment == 0 and extra_deposit == 0 and rate_increase == 0:
            st.warning("⚠️ Измените хотя бы один параметр для пересчёта")
        else:
            st.info("🚧 Функция 'Что если?' в разработке. Скоро добавим полный пересчёт с новыми параметрами!")
            
            if extra_payment > 0:
                total_extra_year = extra_payment * 12
                st.success(f"✅ **Досрочные платежи:** {extra_payment:,.0f} ₽/мес = {total_extra_year:,.0f} ₽/год")
            
            if extra_deposit > 0:
                total_deposit_year = extra_deposit * 12
                st.success(f"✅ **Пополнение вкладов:** {extra_deposit:,.0f} ₽/мес = {total_deposit_year:,.0f} ₽/год")
            
            if rate_increase != 0:
                direction = "увеличение" if rate_increase > 0 else "уменьшение"
                st.success(f"✅ **Изменение ставки:** {direction} на {abs(rate_increase):.1f}%")