import streamlit as st
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import pandas as pd
from database import (
    save_income_diary_entry,
    get_income_diary_with_id,
    get_income_diary_stats,
    check_income_diary_due,
    delete_income_diary_entry,
    update_income_diary_entry,
    get_all_credits,
    save_distribution_rules,
    get_distribution_rules,
    save_distribution_log,
    get_distribution_logs,
    get_latest_distribution
)
from ui.utils import clear_session_state
from ui.logger import log_income_action, log_action


MONTH_NAMES = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
]


def calculate_auto_distribution(total_income: float) -> dict:
    """Автоматический расчёт распределения дохода"""
    
    # 1. Обязательные платежи по кредитам
    credits = get_all_credits()
    credits_amount = sum(float(c[1].get('monthly_payment', 0)) for c in credits)
    
    # 2. Остаток после кредитов
    remaining = total_income - credits_amount
    
    if remaining < 0:
        return {
            'total_income': total_income,
            'credits': credits_amount,
            'deposits': 0,
            'extra_payments': 0,
            'life': 0,
            'remaining': remaining,
            'error': 'Сумма кредитов больше дохода!'
        }
    
    # 3. Правила распределения
    rules = get_distribution_rules()
    deposits_percent = float(rules.get('deposits_percent', 20))
    extra_percent = float(rules.get('extra_payments_percent', 30))
    
    # 4. Расчёт сумм
    deposits_amount = remaining * (deposits_percent / 100)
    extra_amount = remaining * (extra_percent / 100)
    life_amount = remaining - deposits_amount - extra_amount
    
    return {
        'total_income': total_income,
        'credits': credits_amount,
        'deposits': deposits_amount,
        'extra_payments': extra_amount,
        'life': life_amount,
        'remaining': remaining,
        'deposits_percent': deposits_percent,
        'extra_percent': extra_percent,
        'life_percent': 100 - deposits_percent - extra_percent
    }


def render_income_tab():
    """Главная функция вкладки доходов"""
    
    st.header("💰 Доход и распределение")
    
    # ==================== 1. УВЕДОМЛЕНИЕ ====================
    
    today = datetime.now()
    
    if check_income_diary_due():
        st.warning(f"🔔 **Сегодня {today.day} число!** Не забудьте внести доход.")
        st.divider()
    
    # ==================== 2. БЫСТРЫЙ ВВОД ДОХОДА ====================
    
    st.subheader("📝 Ввод дохода")
    
    with st.form("quick_income_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            income_date = st.date_input("Дата", value=today, max_value=today)
        
        with col2:
            income_type = st.selectbox("Тип", ["Зарплата", "Аванс"])
        
        with col3:
            income_amount = st.number_input("Сумма (₽)", min_value=0.0, step=1000.0, format="%.0f")
        
        with col4:
            st.write("")
            st.write("")
            submit = st.form_submit_button("✅ Внести", type="primary", use_container_width=True)
        
        if submit:
            if income_amount > 0:
                # Сохраняем доход
                from database import execute_query
                income_id = execute_query(
                    'INSERT INTO income_diary (date, salary_type, amount) VALUES (?, ?, ?)',
                    (income_date.strftime('%Y-%m-%d'), income_type, income_amount),
                    fetch='lastrowid'
                )
                
                if income_id:
                    st.success(f"✅ Доход {income_amount:,.0f} ₽ добавлен!")
                    log_income_action("ADDED", income_amount, income_type, {
                        'date': income_date.strftime('%Y-%m-%d')
                    })
                    
                    # Сохраняем распределение в session_state для отображения
                    st.session_state['new_income_id'] = income_id
                    st.session_state['new_income_amount'] = income_amount
                    st.rerun()
            else:
                st.error("❌ Введите сумму > 0")
    
    st.divider()
    
    # ==================== 3. АВТОМАТИЧЕСКОЕ РАСПРЕДЕЛЕНИЕ ====================
    
    # Проверяем, есть ли новый доход для распределения
    if 'new_income_id' in st.session_state and 'new_income_amount' in st.session_state:
        render_auto_distribution_block(
            st.session_state['new_income_id'],
            st.session_state['new_income_amount']
        )
        st.divider()
    
    # Показываем последнее распределение
    latest = get_latest_distribution()
    if latest:
        st.subheader("📊 Последнее распределение")
        render_distribution_summary(latest)
        st.divider()
    
    # ==================== 4. НАСТРОЙКИ РАСПРЕДЕЛЕНИЯ ====================
    
    st.subheader("⚙️ Правила распределения")
    
    rules = get_distribution_rules()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"💎 **Вклады:** {rules['deposits_percent']:.0f}% от остатка после кредитов")
    
    with col2:
        st.info(f"💰 **Досрочные платежи:** {rules['extra_payments_percent']:.0f}% от остатка")
    
    with st.expander("🔧 Изменить правила"):
        with st.form("rules_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_deposits_percent = st.slider(
                    "💎 Вклады (%)",
                    0, 100,
                    int(rules['deposits_percent'])
                )
            
            with col2:
                new_extra_percent = st.slider(
                    "💰 Досрочные (%)",
                    0, 100,
                    int(rules['extra_payments_percent'])
                )
            
            life_percent = 100 - new_deposits_percent - new_extra_percent
            
            st.write(f"🏠 **На жизнь:** {life_percent}%")
            
            if new_deposits_percent + new_extra_percent > 100:
                st.error("❌ Сумма процентов не может быть больше 100%!")
            
            if st.form_submit_button("💾 Сохранить правила", type="primary", use_container_width=True):
                if new_deposits_percent + new_extra_percent <= 100:
                    if save_distribution_rules(new_deposits_percent, new_extra_percent):
                        st.rerun()
                else:
                    st.error("❌ Сумма процентов > 100%!")
    
    st.divider()
    
    # ==================== 5. ИСТОРИЯ И АНАЛИТИКА ====================
    
    tab1, tab2, tab3 = st.tabs(["📋 История доходов", "📊 Статистика", "📈 Графики"])
    
    with tab1:
        render_income_history()
    
    with tab2:
        render_income_statistics()
    
    with tab3:
        render_income_charts()


def render_auto_distribution_block(income_id: int, income_amount: float):
    """Блок автоматического распределения после ввода дохода"""
    
    st.success(f"✅ Доход {income_amount:,.0f} ₽ успешно добавлен!")
    
    st.subheader("📊 Автоматическое распределение")
    
    distribution = calculate_auto_distribution(income_amount)
    
    if 'error' in distribution:
        st.error(f"❌ {distribution['error']}")
        
        # Удаляем из session_state
        clear_session_state('new_income_id', 'new_income_amount')
        return
    
    # Визуализация распределения
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.metric("💵 Доход", f"{distribution['total_income']:,.0f} ₽")
        st.metric("💳 Кредиты", f"{distribution['credits']:,.0f} ₽")
        st.metric("📌 Остаток", f"{distribution['remaining']:,.0f} ₽")
    
    with col2:
        # Круговая диаграмма
        fig = go.Figure(data=[go.Pie(
            labels=['💎 Вклады', '💰 Досрочные', '🏠 Жизнь'],
            values=[
                distribution['deposits'],
                distribution['extra_payments'],
                distribution['life']
            ],
            marker=dict(colors=['#4ECDC4', '#FFD93D', '#95E1D3']),
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>%{value:,.0f} ₽<extra></extra>'
        )])
        
        fig.update_layout(
            title=f"Распределение остатка ({distribution['remaining']:,.0f} ₽)",
            height=300,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Детальная разбивка
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "💎 На вклады",
            f"{distribution['deposits']:,.0f} ₽",
            delta=f"{distribution['deposits_percent']:.0f}%"
        )
    
    with col2:
        st.metric(
            "💰 Досрочные платежи",
            f"{distribution['extra_payments']:,.0f} ₽",
            delta=f"{distribution['extra_percent']:.0f}%"
        )
    
    with col3:
        st.metric(
            "🏠 На жизнь",
            f"{distribution['life']:,.0f} ₽",
            delta=f"{distribution['life_percent']:.0f}%"
        )
    
    # Кнопка сохранения распределения
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("📌 Зафиксировать распределение", type="primary", use_container_width=True):
            if save_distribution_log(
                income_id,
                distribution['total_income'],
                distribution['credits'],
                distribution['deposits'],
                distribution['extra_payments'],
                distribution['life']
            ):
                st.success("✅ Распределение зафиксировано!")
                
                # Удаляем из session_state
                del st.session_state['new_income_id']
                del st.session_state['new_income_amount']
                st.rerun()
    
    with col2:
        if st.button("❌ Отменить", use_container_width=True):
            # Удаляем из session_state
            del st.session_state['new_income_id']
            del st.session_state['new_income_amount']
            st.rerun()


def render_distribution_summary(distribution: dict):
    """Краткая сводка последнего распределения"""
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📅 Дата", distribution['date'])
    
    with col2:
        st.metric("💵 Доход", f"{distribution['total_income']:,.0f} ₽")
    
    with col3:
        st.metric("💳 Кредиты", f"{distribution['credits']:,.0f} ₽")
    
    with col4:
        st.metric("💎 Вклады", f"{distribution['deposits']:,.0f} ₽")
    
    with col5:
        st.metric("💰 Досрочные", f"{distribution['extra_payments']:,.0f} ₽")


def render_income_history():
    """История доходов с редактированием"""
    
    st.subheader("📋 История доходов")
    
    col1, col2 = st.columns(2)
    
    with col1:
        filter_year = st.selectbox("Год", [2024, 2025, 2026], index=1, key="hist_year")
    
    with col2:
        filter_month = st.selectbox("Месяц", list(range(1, 13)), format_func=lambda x: MONTH_NAMES[x-1], key="hist_month")
    
    diary_entries = get_income_diary_with_id(year=filter_year, month=filter_month)
    
    if not diary_entries:
        st.info("📭 Нет записей за выбранный период")
        return
    
    total_diary = sum(float(entry['amount']) for entry in diary_entries)
    st.metric(f"💰 Итого за {MONTH_NAMES[filter_month-1]} {filter_year}", f"{total_diary:,.0f} ₽")
    
    st.divider()
    
    for entry in diary_entries:
        entry_id = entry['id']
        
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            st.write(f"📅 **{entry['date']}**")
        
        with col2:
            st.write(f"**{entry['salary_type']}**")
        
        with col3:
            st.write(f"💰 **{entry['amount']:,.0f} ₽**")
        
        with col4:
            if st.button("🗑️", key=f"del_{entry_id}", use_container_width=True):
                if delete_income_diary_entry(entry_id):
                    st.success("✅ Удалено!")
                    st.rerun()


def render_income_statistics():
    """Статистика доходов"""
    
    st.subheader("📊 Статистика")
    
    stat_year = st.selectbox("Год", [2024, 2025, 2026], index=1, key="stat_year")
    
    stats = get_income_diary_stats(year=stat_year)
    
    if not stats:
        st.info("📭 Нет данных за выбранный год")
        return
    
    stat_data = []
    
    for month_str, stat in stats.items():
        month_num = int(month_str)
        month_name = MONTH_NAMES[month_num - 1]
        
        stat_data.append({
            'Месяц': month_name,
            'Доход': f"{stat['total']:,.0f} ₽",
            'Записей': stat['count']
        })
    
    df = pd.DataFrame(stat_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    total_year = sum(float(stat['total']) for stat in stats.values())
    avg_month = total_year / len(stats) if stats else 0
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("💰 Итого за год", f"{total_year:,.0f} ₽")
    
    with col2:
        st.metric("📊 Средний месяц", f"{avg_month:,.0f} ₽")


def render_income_charts():
    """Графики доходов"""
    
    st.subheader("📈 Графики")
    
    graph_year = st.selectbox("Год", [2024, 2025, 2026], index=1, key="graph_year")
    
    from database import get_income_diary
    diary_all = get_income_diary(year=graph_year)
    
    if not diary_all:
        st.info("📭 Нет данных")
        return
    
    dates = []
    amounts = []
    salary_amounts = []
    advance_amounts = []
    
    for entry in sorted(diary_all, key=lambda x: x['date']):
        dates.append(entry['date'])
        amount = float(entry['amount'])
        amounts.append(amount)
        
        if entry['salary_type'] == 'Зарплата':
            salary_amounts.append(amount)
            advance_amounts.append(0)
        else:
            salary_amounts.append(0)
            advance_amounts.append(amount)
    
    # График линий
    fig_line = go.Figure()
    
    fig_line.add_trace(go.Scatter(
        x=dates, y=amounts,
        mode='lines+markers',
        name='Доход',
        line=dict(color='#4ECDC4', width=3),
        marker=dict(size=8)
    ))
    
    fig_line.update_layout(
        title=f"Динамика доходов {graph_year}",
        xaxis_title="Дата",
        yaxis_title="Сумма (₽)",
        height=400,
        yaxis=dict(tickformat=',.0f')
    )
    
    st.plotly_chart(fig_line, use_container_width=True)
    
    # График столбцов
    fig_bar = go.Figure()
    
    fig_bar.add_trace(go.Bar(
        x=dates, y=salary_amounts,
        name='Зарплата',
        marker=dict(color='#FF6B6B')
    ))
    
    fig_bar.add_trace(go.Bar(
        x=dates, y=advance_amounts,
        name='Аванс',
        marker=dict(color='#FFD93D')
    ))
    
    fig_bar.update_layout(
        title=f"По типам {graph_year}",
        xaxis_title="Дата",
        yaxis_title="Сумма (₽)",
        height=400,
        barmode='stack',
        yaxis=dict(tickformat=',.0f')
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)
