import streamlit as st
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd
from models import Credit
from ui.utils import create_credit_object


def render_strategies_tab(credits, deposits):
    """Вкладка стратегий погашения кредитов"""
    
    st.header("🎯 Стратегии погашения кредитов")
    
    st.info("""
    **Три основные стратегии досрочного погашения:**
    
    - 🔥 **Avalanche (Лавина)** — гасим кредит с максимальной ставкой (математически оптимально)
    - ⛄ **Snowball (Снежный ком)** — гасим самый маленький кредит (психологически легче)
    - 💸 **Highest Payment** — гасим кредит с максимальным платежом (снижаем нагрузку)
    """)
    
    if not credits:
        st.warning("⚠️ Нет кредитов для анализа. Добавьте кредиты на вкладке 'Кредиты'.")
        return
    
    st.divider()
    
    # ==================== ПАРАМЕТРЫ АНАЛИЗА ====================
    
    st.subheader("💰 Параметры анализа")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Получаем сумму из последнего распределения
        from database import get_latest_distribution
        
        distribution = get_latest_distribution()
        
        if distribution:
            default_extra = float(distribution.get('extra_payments', 50000))
            st.success(f"💡 **Из распределения от {distribution['date']}:** {default_extra:,.0f} ₽")
        else:
            default_extra = 50000.0
            st.info("💡 Распределений нет. Используется значение по умолчанию.")
        
        extra_amount = st.number_input(
            "Сумма досрочного платежа (₽)",
            min_value=1000.0,
            value=default_extra,
            step=1000.0,
            help="Автоматически подтягивается из последнего распределения дохода"
        )
    
    with col2:
        frequency = st.selectbox(
            "Частота досрочных платежей",
            ["Разово", "Ежемесячно", "Ежеквартально", "Раз в полгода"],
            help="Как часто вы будете вносить досрочно"
        )
    
    st.divider()
    
    # ==================== ТЕКУЩЕЕ СОСТОЯНИЕ ====================
    
    render_current_state(credits)
    
    st.divider()
    
    # ==================== ВКЛАДКИ СТРАТЕГИЙ ====================
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔥 Avalanche", 
        "⛄ Snowball", 
        "💸 Highest Payment",
        "📊 Сравнение"
    ])
    
    with tab1:
        render_avalanche_strategy(credits, extra_amount)
    
    with tab2:
        render_snowball_strategy(credits, extra_amount)
    
    with tab3:
        render_highest_payment_strategy(credits, extra_amount)
    
    with tab4:
        render_comparison(credits, extra_amount)


def render_current_state(credits):
    """Текущее состояние кредитов"""
    
    st.subheader("📊 Текущее состояние")
    
    total_debt = sum(float(c[1].get('balance', 0)) for c in credits)
    total_monthly = sum(float(c[1].get('monthly_payment', 0)) for c in credits)
    
    # Расчёт общих процентов
    total_interest = 0
    for _, credit_dict in credits:
        try:
            credit = create_credit_object(credit_dict)
            total_interest += credit.get_total_interest()
        except:
            pass
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💳 Всего долгов", f"{total_debt:,.0f} ₽")
    
    with col2:
        st.metric("📅 Месячные платежи", f"{total_monthly:,.0f} ₽")
    
    with col3:
        st.metric("📉 Всего процентов", f"{total_interest:,.0f} ₽")


def render_strategy(credits, extra_amount, sort_key, reverse, title, emoji, description):
    """Универсальная функция для рендера стратегии"""
    
    st.subheader(f"{emoji} {title}")
    st.info(description)
    
    # Сортировка
    sorted_credits = sorted(
        credits,
        key=lambda x: float(x[1].get(sort_key, 0)),
        reverse=reverse
    )
    
    st.subheader("📋 Порядок погашения:")
    
    total_savings = 0
    
    for i, (_, credit_dict) in enumerate(sorted_credits, 1):
        try:
            credit = create_credit_object(credit_dict)
            result = credit.calculate_with_extra_payment(extra_amount, datetime.now())
            total_savings += result['savings']
            
            can_close = extra_amount >= credit.balance
            
            # Формируем заголовок expander
            if sort_key == 'annual_rate':
                header = f"{i}. **{credit.name}** — {credit.annual_rate:.2f}% ставка"
            elif sort_key == 'balance':
                header = f"{i}. **{credit.name}** — {credit.balance:,.0f} ₽ долга"
            else:  # monthly_payment
                header = f"{i}. **{credit.name}** — {credit.monthly_payment:,.0f} ₽/мес"
            
            with st.expander(header, expanded=(i == 1)):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Текущий долг", f"{credit.balance:,.0f} ₽")
                    st.metric("Ставка", f"{credit.annual_rate:.2f}%")
                
                with col2:
                    st.metric("Экономия", f"{result['savings']:,.0f} ₽")
                    st.metric("ROI", f"{result['roi']:.2f}%")
                
                with col3:
                    st.metric("Новый долг", f"{result['new_balance']:,.0f} ₽")
                    
                    if can_close:
                        st.success("✅ Можно закрыть!")
                    else:
                        months = result['new_balance'] / credit.monthly_payment if credit.monthly_payment > 0 else 0
                        st.metric("Осталось мес.", f"~{int(months)}")
                
                if i == 1:
                    if can_close:
                        remaining = extra_amount - credit.balance
                        st.success(f"🎯 **Рекомендация:** Закройте этот кредит! Останется {remaining:,.0f} ₽")
                    else:
                        st.success(f"🎯 **Рекомендация:** Внесите {extra_amount:,.0f} ₽ на этот кредит!")
        
        except Exception as e:
            st.error(f"❌ Ошибка расчёта: {str(e)}")
    
    st.divider()
    
    # Итого
    st.subheader("💡 Итого по стратегии:")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("💰 Общая экономия", f"{total_savings:,.0f} ₽")
    
    with col2:
        avg_roi = (total_savings / extra_amount * 100) if extra_amount > 0 else 0
        st.metric("📈 Средний ROI", f"{avg_roi:.2f}%")


def render_avalanche_strategy(credits, extra_amount):
    """Стратегия Avalanche"""
    
    description = """
    **Суть стратегии:** Гасим кредит с **максимальной процентной ставкой**.
    
    ✅ **Плюсы:**
    - Математически оптимальна (минимальная переплата)
    - Максимальная экономия на процентах
    
    ⚠️ **Минусы:**
    - Психологически сложнее (результат виден не сразу)
    - Требует дисциплины
    """
    
    render_strategy(
        credits, extra_amount,
        'annual_rate', True,
        'Avalanche (Лавина)', '🔥',
        description
    )


def render_snowball_strategy(credits, extra_amount):
    """Стратегия Snowball"""
    
    description = """
    **Суть стратегии:** Гасим кредит с **минимальным остатком долга**.
    
    ✅ **Плюсы:**
    - Психологически легче (быстро закрываем кредиты)
    - Мотивация растёт с каждым закрытым кредитом
    - Снижается количество обязательств
    
    ⚠️ **Минусы:**
    - Немного больше переплата по сравнению с Avalanche
    """
    
    render_strategy(
        credits, extra_amount,
        'balance', False,
        'Snowball (Снежный ком)', '⛄',
        description
    )


def render_highest_payment_strategy(credits, extra_amount):
    """Стратегия Highest Payment"""
    
    description = """
    **Суть стратегии:** Гасим кредит с **максимальным ежемесячным платежом**.
    
    ✅ **Плюсы:**
    - Быстрое снижение месячной нагрузки
    - Высвобождаются деньги для новых целей
    - Психологически комфортно
    
    ⚠️ **Минусы:**
    - Может быть не оптимально с точки зрения переплаты
    """
    
    render_strategy(
        credits, extra_amount,
        'monthly_payment', True,
        'Highest Payment', '💸',
        description
    )


def render_comparison(credits, extra_amount):
    """Сравнение всех стратегий"""
    
    st.subheader("📊 Сравнение стратегий")
    
    st.info("Сравним все три стратегии и выберем оптимальную!")
    
    # Расчёт для каждой стратегии
    strategies = [
        ('Avalanche', 'annual_rate', True, '🔥'),
        ('Snowball', 'balance', False, '⛄'),
        ('Highest Payment', 'monthly_payment', True, '💸')
    ]
    
    strategies_data = []
    
    for name, sort_key, reverse, emoji in strategies:
        sorted_credits = sorted(
            credits,
            key=lambda x: float(x[1].get(sort_key, 0)),
            reverse=reverse
        )
        
        if sorted_credits:
            try:
                credit = create_credit_object(sorted_credits[0][1])
                result = credit.calculate_with_extra_payment(extra_amount, datetime.now())
                savings = result['savings']
                roi = result['roi']
                credit_name = credit.name
            except:
                savings = 0
                roi = 0
                credit_name = "Ошибка"
        else:
            savings = 0
            roi = 0
            credit_name = "Нет данных"
        
        strategies_data.append({
            'name': f"{emoji} {name}",
            'savings': savings,
            'roi': roi,
            'credit': credit_name
        })
    
    # График сравнения
    fig = go.Figure(data=[
        go.Bar(
            x=[s['name'] for s in strategies_data],
            y=[s['savings'] for s in strategies_data],
            text=[f"{s['savings']:,.0f} ₽" for s in strategies_data],
            textposition='auto',
            marker=dict(
                color=['#FF6B6B', '#4ECDC4', '#45B7D1']
            ),
            hovertemplate='<b>%{x}</b><br>Экономия: %{y:,.0f} ₽<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title="Экономия по стратегиям",
        xaxis_title="Стратегия",
        yaxis_title="Экономия (₽)",
        height=500,
        showlegend=False,
        yaxis=dict(tickformat=',.0f')
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Таблица сравнения
    st.subheader("📋 Детальное сравнение:")
    
    df_data = []
    
    for s in strategies_data:
        df_data.append({
            'Стратегия': s['name'],
            'Кредит': s['credit'],
            'Экономия': f"{s['savings']:,.0f} ₽",
            'ROI': f"{s['roi']:.2f}%"
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Лучшая стратегия
    if strategies_data:
        best = max(strategies_data, key=lambda x: x['savings'])
        st.success(f"🏆 **Лучшая стратегия:** {best['name']} (экономия {best['savings']:,.0f} ₽)")
        
        st.divider()
        
        # Рекомендация
        st.subheader("💡 Персональная рекомендация:")
        
        if '🔥' in best['name']:
            st.write("""
            ✅ **Рекомендуем стратегию Avalanche:**
            - Максимальная экономия на процентах
            - У вас есть кредиты с высокими ставками
            - Готовы к долгосрочной игре
            - Математически оптимальное решение
            """)
        elif '⛄' in best['name']:
            st.write("""
            ✅ **Рекомендуем стратегию Snowball:**
            - Быстро закроете первые кредиты
            - Психологически легче видеть прогресс
            - Снизится количество обязательств
            - Мотивация будет расти с каждым закрытым кредитом
            """)
        else:
            st.write("""
            ✅ **Рекомендуем стратегию Highest Payment:**
            - Быстро снизится месячная нагрузка
            - Высвободятся средства для других целей
            - Психологически комфортно
            - Улучшится финансовая гибкость
            """)
        
        # Дополнительная информация
        st.info(f"""
        **Следующий шаг:**
        Внесите {extra_amount:,.0f} ₽ досрочным платежом на кредит **"{best['credit']}"**
        
        **Ожидаемый результат:**
        - Экономия на процентах: {best['savings']:,.0f} ₽
        - ROI: {best['roi']:.2f}%
        """)
