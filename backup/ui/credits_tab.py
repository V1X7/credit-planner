import streamlit as st
from datetime import datetime, date
import plotly.graph_objects as go
import pandas as pd
from database import get_extra_payments, delete_extra_payment as db_delete_extra_payment, add_extra_payment


def render_credits_tab(credits, save_credit_func, update_credit_func, delete_credit_func):
    """Вкладка управления кредитами"""
    
    st.header("💳 Управление кредитами")
    
    # Статистика по всем кредитам
    if credits:
        total_balance = sum(credit[1].get('balance', 0) for credit in credits)
        total_monthly = sum(credit[1].get('monthly_payment', 0) for credit in credits)
        avg_rate = sum(credit[1].get('annual_rate', 0) for credit in credits) / len(credits)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 Общий долг", f"{total_balance:,.0f} ₽")
        
        with col2:
            st.metric("💳 Платежей в месяц", f"{total_monthly:,.0f} ₽")
        
        with col3:
            st.metric("📊 Средняя ставка", f"{avg_rate:.2f}%")
        
        with col4:
            st.metric("🏦 Кредитов", len(credits))
        
        st.divider()
        
        # График распределения долга
        render_credits_chart(credits)
        
        st.divider()
    
    # Tabs
    tab1, tab2 = st.tabs(["➕ Добавить кредит", "📋 Список кредитов"])
    
    # ==================== TAB 1: ДОБАВИТЬ ====================
    with tab1:
        st.subheader("Добавить новый кредит")
        
        with st.form("add_credit_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input(
                    "Название кредита *",
                    placeholder="Например: Ипотека Сбер",
                    help="Укажите название для удобной идентификации"
                )
                
                balance = st.number_input(
                    "Текущий остаток (₽) *",
                    min_value=0.0,
                    value=1000000.0,
                    step=1000.0,
                    format="%.2f",
                    help="Оставшаяся сумма долга"
                )
                
                annual_rate = st.number_input(
                    "Годовая ставка (%) *",
                    min_value=0.01,
                    max_value=100.0,
                    value=10.0,
                    step=0.1,
                    format="%.2f",
                    help="Процентная ставка по кредиту"
                )
            
            with col2:
                monthly_payment = st.number_input(
                    "Ежемесячный платёж (₽) *",
                    min_value=0.0,
                    value=30000.0,
                    step=100.0,
                    format="%.2f",
                    help="Обязательный ежемесячный платёж"
                )
                
                start_date = st.date_input(
                    "Дата начала кредита *",
                    value=datetime.now(),
                    help="Когда был оформлен кредит"
                )
                
                payment_day = st.number_input(
                    "День платежа *",
                    min_value=1,
                    max_value=31,
                    value=10,
                    help="Число месяца для обязательного платежа"
                )
            
            st.markdown("---")
            
            end_date = st.date_input(
                "Дата окончания кредита",
                value=start_date,
                help="Когда кредит будет полностью погашен"
            )
            
            st.markdown("---")
            
            submitted = st.form_submit_button("➕ Добавить кредит", type="primary", use_container_width=True)
            
            if submitted:
                # Валидация
                errors = []
                
                if not name or name.strip() == "":
                    errors.append("❌ Укажите название кредита")
                
                if balance <= 0:
                    errors.append("❌ Остаток должен быть больше 0")
                
                if annual_rate <= 0:
                    errors.append("❌ Ставка должна быть больше 0")
                
                if monthly_payment <= 0:
                    errors.append("❌ Платёж должен быть больше 0")
                
                if payment_day < 1 or payment_day > 31:
                    errors.append("❌ День платежа должен быть от 1 до 31")
                
                # Проверка: платёж покрывает проценты?
                monthly_rate = annual_rate / 12
                monthly_interest = balance * (monthly_rate / 100)
                
                if monthly_payment < monthly_interest:
                    errors.append(f"⚠️ Платёж ({monthly_payment:,.0f} ₽) меньше процентов ({monthly_interest:,.0f} ₽)! Долг будет расти.")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    result = save_credit_func(
                        name=name,
                        balance=balance,
                        annual_rate=annual_rate,
                        monthly_payment=monthly_payment,
                        start_date=start_date,
                        payment_day=payment_day,
                        end_date=end_date
                    )
                    
                    if result:
                        st.success(f"✅ Кредит '{name}' успешно добавлен!")
                        st.rerun()
    
    # ==================== TAB 2: СПИСОК ====================
    with tab2:
        st.subheader("Список всех кредитов")
        
        if not credits:
            st.info("📭 Кредиты не добавлены. Перейдите на вкладку 'Добавить кредит'.")
            return
        
        # Сортировка
        sort_by = st.selectbox(
            "Сортировать по:",
            ["По умолчанию", "По остатку (убывание)", "По остатку (возрастание)", "По ставке (убывание)", "По ставке (возрастание)"],
            key="credits_sort"
        )
        
        sorted_credits = credits.copy()
        
        if "остатку (убывание)" in sort_by:
            sorted_credits = sorted(credits, key=lambda x: x[1].get('balance', 0), reverse=True)
        elif "остатку (возрастание)" in sort_by:
            sorted_credits = sorted(credits, key=lambda x: x[1].get('balance', 0))
        elif "ставке (убывание)" in sort_by:
            sorted_credits = sorted(credits, key=lambda x: x[1].get('annual_rate', 0), reverse=True)
        elif "ставке (возрастание)" in sort_by:
            sorted_credits = sorted(credits, key=lambda x: x[1].get('annual_rate', 0))
        
        st.divider()
        
        for credit_id, credit in sorted_credits:
            credit_name = credit.get('name', 'Без названия')
            credit_balance = credit.get('balance', 0)
            credit_rate = credit.get('annual_rate', 0)
            credit_payment = credit.get('monthly_payment', 0)
            credit_day = credit.get('payment_day', 1)
            credit_start = credit.get('start_date', datetime.now())
            credit_end = credit.get('end_date')
            credit_extra = credit.get('extra_payments', {})
            
            # Расчёт процентов
            monthly_rate = credit_rate / 12
            monthly_interest = credit_balance * (monthly_rate / 100)
            
            with st.expander(f"💳 {credit_name} — {credit_balance:,.0f} ₽ @ {credit_rate}%", expanded=False):
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Остаток", f"{credit_balance:,.0f} ₽")
                    st.metric("Годовая ставка", f"{credit_rate}%")
                
                with col2:
                    st.metric("Ежемесячный платёж", f"{credit_payment:,.0f} ₽")
                    st.metric("День платежа", f"{credit_day} число")
                
                with col3:
                    st.metric("Проценты в месяц", f"{monthly_interest:,.0f} ₽")
                    
                    if credit_payment > monthly_interest:
                        months_left = credit_balance / (credit_payment - monthly_interest)
                        st.metric("Осталось месяцев", f"~{int(months_left)}")
                    else:
                        st.metric("Осталось месяцев", "∞", help="Платёж меньше процентов!")
                
                st.markdown("---")
                
                # Предупреждения
                if credit_payment < monthly_interest:
                    st.error(f"🚨 **ВНИМАНИЕ!** Платёж меньше процентов! Долг растёт на {(monthly_interest - credit_payment):,.0f} ₽/мес")
                elif credit_payment < monthly_interest * 1.5:
                    st.warning(f"⚠️ Платёж слишком маленький. Кредит будет выплачиваться очень долго.")
                
                st.markdown("---")
                
                st.write(f"**Дата начала:** {credit_start.strftime('%d.%m.%Y') if isinstance(credit_start, datetime) else credit_start}")
                if credit_end:
                    st.write(f"**Дата окончания:** {credit_end.strftime('%d.%m.%Y') if isinstance(credit_end, datetime) else credit_end}")
                else:
                    st.write(f"**Дата окончания:** не указана")
                
                st.markdown("---")
                
                st.subheader("💰 Досрочные платежи")
                
                if credit_extra:
                    st.write("**Запланированные досрочные платежи:**")
                    
                    total_extra = 0
                    
                    for payment_date, amount in sorted(credit_extra.items()):
                        total_extra += amount
                        
                        col_date, col_amount, col_delete = st.columns([2, 2, 1])
                        
                        with col_date:
                            st.write(f"📅 {payment_date}")
                        
                        with col_amount:
                            st.write(f"💵 {amount:,.0f} ₽")
                        
                        with col_delete:
                            if st.button("🗑️", key=f"del_extra_{credit_id}_{payment_date}"):
                                if db_delete_extra_payment(credit_id, payment_date):
                                    st.success("✅ Платёж удалён!")
                                    st.rerun()
                    
                    st.info(f"💰 **Итого досрочных платежей:** {total_extra:,.0f} ₽")
                    
                    # Расчёт выгоды
                    if total_extra > 0:
                        saved_interest = total_extra * (credit_rate / 100)
                        st.success(f"✅ **Экономия на процентах за год:** ~{saved_interest:,.0f} ₽")
                else:
                    st.info("Нет запланированных досрочных платежей")
                
                with st.form(f"add_extra_payment_{credit_id}"):
                    st.write("**Добавить досрочный платёж:**")
                    
                    col_date, col_amount = st.columns(2)
                    
                    with col_date:
                        extra_date = st.date_input(
                            "Дата",
                            value=datetime.now(),
                            key=f"extra_date_{credit_id}"
                        )
                    
                    with col_amount:
                        extra_amount = st.number_input(
                            "Сумма (₽)",
                            min_value=1000.0,
                            value=50000.0,
                            step=1000.0,
                            key=f"extra_amount_{credit_id}"
                        )
                    
                    if st.form_submit_button("➕ Добавить досрочный платёж"):
                        # Валидация
                        if extra_amount > credit_balance:
                            st.warning(f"⚠️ Сумма досрочного платежа ({extra_amount:,.0f} ₽) больше остатка ({credit_balance:,.0f} ₽). Будет внесено {credit_balance:,.0f} ₽.")
                            extra_amount = credit_balance
                        
                        if add_extra_payment(credit_id, extra_date, extra_amount):
                            st.success(f"✅ Досрочный платёж {extra_amount:,.0f} ₽ добавлен на {extra_date.strftime('%d.%m.%Y')}")
                            st.rerun()
                
                st.markdown("---")
                
                st.subheader("✏️ Редактировать кредит")
                
                with st.form(f"edit_credit_{credit_id}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_name = st.text_input("Название", value=credit_name, key=f"edit_name_{credit_id}")
                        edit_balance = st.number_input("Остаток (₽)", value=float(credit_balance), step=1000.0, key=f"edit_balance_{credit_id}")
                        edit_rate = st.number_input("Ставка (%)", value=float(credit_rate), step=0.1, key=f"edit_rate_{credit_id}")
                    
                    with col2:
                        edit_payment = st.number_input("Платёж (₽)", value=float(credit_payment), step=100.0, key=f"edit_payment_{credit_id}")
                        edit_start = st.date_input("Дата начала", value=credit_start if isinstance(credit_start, date) else datetime.now().date(), key=f"edit_start_{credit_id}")
                        edit_day = st.number_input("День платежа", value=credit_day, min_value=1, max_value=31, key=f"edit_day_{credit_id}")
                    
                    edit_end = st.date_input(
                        "Дата окончания",
                        value=credit_end if isinstance(credit_end, date) else edit_start,
                        key=f"edit_end_{credit_id}"
                    )
                    
                    col_save, col_delete = st.columns(2)
                    
                    with col_save:
                        if st.form_submit_button("💾 Сохранить изменения", type="primary", use_container_width=True):
                            if update_credit_func(
                                credit_id=credit_id,
                                name=edit_name,
                                balance=edit_balance,
                                annual_rate=edit_rate,
                                monthly_payment=edit_payment,
                                start_date=edit_start,
                                payment_day=edit_day,
                                end_date=edit_end
                            ):
                                st.success("✅ Кредит обновлён!")
                                st.rerun()
                    
                    with col_delete:
                        if st.form_submit_button("🗑️ Удалить кредит", type="secondary", use_container_width=True):
                            # Подтверждение удаления
                            if st.session_state.get(f'confirm_delete_{credit_id}', False):
                                if delete_credit_func(credit_id):
                                    st.success("✅ Кредит удалён!")
                                    st.session_state[f'confirm_delete_{credit_id}'] = False
                                    st.rerun()
                            else:
                                st.session_state[f'confirm_delete_{credit_id}'] = True
                                st.warning("⚠️ Нажмите ещё раз для подтверждения удаления")
                                st.rerun()


def render_credits_chart(credits):
    """График распределения долга по кредитам"""
    
    st.subheader("📊 Распределение долга")
    
    # Данные для графика
    names = [credit[1].get('name', 'Без названия') for credit in credits]
    balances = [credit[1].get('balance', 0) for credit in credits]
    rates = [credit[1].get('annual_rate', 0) for credit in credits]
    
    # Круговая диаграмма
    fig_pie = go.Figure(data=[go.Pie(
        labels=names,
        values=balances,
        textposition='inside',
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>Остаток: %{value:,.0f} ₽<br>%{percent}<extra></extra>'
    )])
    
    fig_pie.update_layout(
        title="Распределение долга по кредитам",
        height=400,
        showlegend=True
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Столбчатая диаграмма
    fig_bar = go.Figure()
    
    fig_bar.add_trace(go.Bar(
        x=names,
        y=balances,
        name='Остаток',
        marker=dict(color='#4ECDC4'),
        text=[f'{b:,.0f} ₽' for b in balances],
        textposition='auto',
        hovertemplate='<b>%{x}</b><br>Остаток: %{y:,.0f} ₽<extra></extra>'
    ))
    
    fig_bar.update_layout(
        title="Остатки по кредитам",
        xaxis_title="Кредит",
        yaxis_title="Остаток (₽)",
        height=400,
        yaxis=dict(tickformat=',.0f')
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)
