import streamlit as st
from datetime import datetime, timedelta, date
import plotly.graph_objects as go
import pandas as pd
from database import (
    get_deposit_contributions, 
    delete_deposit_contribution as db_delete_deposit_contribution,
    add_deposit_contribution
)


def render_deposits_tab(deposits, save_deposit_func, update_deposit_func, delete_deposit_func):
    """Вкладка управления вкладами"""
    
    st.header("💎 Управление вкладами")
    
    # Статистика по всем вкладам
    if deposits:
        total_balance = sum(deposit[1].get('balance', 0) for deposit in deposits)
        avg_rate = sum(deposit[1].get('annual_rate', 0) for deposit in deposits) / len(deposits)
        total_yearly_income = sum(
            deposit[1].get('balance', 0) * deposit[1].get('annual_rate', 0) / 100 
            for deposit in deposits
        )
        total_monthly_income = total_yearly_income / 12
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 Общая сумма", f"{total_balance:,.0f} ₽")
        
        with col2:
            st.metric("📊 Средняя ставка", f"{avg_rate:.2f}%")
        
        with col3:
            st.metric("💵 Доход/месяц", f"{total_monthly_income:,.0f} ₽")
        
        with col4:
            st.metric("🏦 Вкладов", len(deposits))
        
        st.divider()
        
        # График распределения вкладов
        render_deposits_chart(deposits)
        
        st.divider()
    
    tab1, tab2 = st.tabs(["➕ Добавить вклад", "📋 Список вкладов"])
    
    # ==================== TAB 1: ДОБАВИТЬ ====================
    with tab1:
        st.subheader("Добавить новый вклад")
        
        with st.form("add_deposit_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input(
                    "Название вклада *",
                    placeholder="Например: Вклад Сбер Максимальный",
                    help="Укажите название для удобной идентификации"
                )
                
                balance = st.number_input(
                    "Сумма вклада (₽) *",
                    min_value=0.0,
                    value=100000.0,
                    step=1000.0,
                    format="%.2f",
                    help="Текущая сумма на вкладе"
                )
                
                annual_rate = st.number_input(
                    "Годовая ставка (%) *",
                    min_value=0.0,
                    max_value=100.0,
                    value=5.0,
                    step=0.1,
                    format="%.2f",
                    help="Процентная ставка по вкладу"
                )
            
            with col2:
                start_date = st.date_input(
                    "Дата открытия *",
                    value=datetime.now(),
                    help="Когда был открыт вклад"
                )
                
                has_end_date = st.checkbox("Указать дату закрытия", value=False)
                
                if has_end_date:
                    end_date = st.date_input(
                        "Дата закрытия",
                        value=datetime.now() + timedelta(days=365),
                        help="Когда планируется закрытие вклада"
                    )
                else:
                    end_date = None
                
                auto_renewal = st.checkbox(
                    "Автопролонгация",
                    value=False,
                    help="Автоматическое продление вклада"
                )
            
            st.markdown("---")
            
            # Предпросмотр
            if balance > 0 and annual_rate > 0:
                yearly_income = balance * (annual_rate / 100)
                monthly_income = yearly_income / 12
                
                st.info(f"💰 **Доход в месяц:** ~{monthly_income:,.0f} ₽ | **Доход в год:** ~{yearly_income:,.0f} ₽")
            
            submitted = st.form_submit_button("➕ Добавить вклад", type="primary", use_container_width=True)
            
            if submitted:
                # Валидация
                errors = []
                
                if not name or name.strip() == "":
                    errors.append("❌ Укажите название вклада")
                
                if balance < 0:
                    errors.append("❌ Сумма не может быть отрицательной")
                
                if annual_rate < 0:
                    errors.append("❌ Ставка не может быть отрицательной")
                
                if has_end_date and end_date and end_date <= start_date:
                    errors.append("❌ Дата закрытия должна быть позже даты открытия")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    result = save_deposit_func(
                        name=name,
                        balance=balance,
                        annual_rate=annual_rate,
                        start_date=start_date,
                        end_date=end_date,
                        auto_renewal=auto_renewal
                    )
                    
                    if result:
                        st.success(f"✅ Вклад '{name}' успешно добавлен!")
                        st.rerun()
    
    # ==================== TAB 2: СПИСОК ====================
    with tab2:
        st.subheader("Список всех вкладов")
        
        if not deposits:
            st.info("📭 Вклады не добавлены. Перейдите на вкладку 'Добавить вклад'.")
            return
        
        # Сортировка
        sort_by = st.selectbox(
            "Сортировать по:",
            ["По умолчанию", "По сумме (убывание)", "По сумме (возрастание)", "По доходу (убывание)", "По доходу (возрастание)"],
            key="deposits_sort"
        )
        
        sorted_deposits = deposits.copy()
        
        if "сумме (убывание)" in sort_by:
            sorted_deposits = sorted(deposits, key=lambda x: x[1].get('balance', 0), reverse=True)
        elif "сумме (возрастание)" in sort_by:
            sorted_deposits = sorted(deposits, key=lambda x: x[1].get('balance', 0))
        elif "доходу (убывание)" in sort_by:
            sorted_deposits = sorted(deposits, key=lambda x: x[1].get('balance', 0) * x[1].get('annual_rate', 0), reverse=True)
        elif "доходу (возрастание)" in sort_by:
            sorted_deposits = sorted(deposits, key=lambda x: x[1].get('balance', 0) * x[1].get('annual_rate', 0))
        
        st.divider()
        
        for deposit_id, deposit in sorted_deposits:
            # Безопасное получение значений
            deposit_name = deposit.get('name', 'Без названия')
            deposit_balance = deposit.get('balance', 0)
            deposit_rate = deposit.get('annual_rate', 0)
            deposit_start = deposit.get('start_date', datetime.now())
            deposit_end = deposit.get('end_date')
            deposit_renewal = deposit.get('auto_renewal', False)
            
            # Конвертация в datetime если нужно
            if isinstance(deposit_start, date) and not isinstance(deposit_start, datetime):
                deposit_start = datetime.combine(deposit_start, datetime.min.time())
            
            with st.expander(f"💎 {deposit_name} — {deposit_balance:,.0f} ₽ @ {deposit_rate}%", expanded=False):
                
                # Информация о вкладе
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Сумма вклада", f"{deposit_balance:,.0f} ₽")
                    st.metric("Годовая ставка", f"{deposit_rate}%")
                
                with col2:
                    monthly_income = deposit_balance * (deposit_rate / 12 / 100)
                    st.metric("Доход в месяц", f"{monthly_income:,.0f} ₽")
                    
                    yearly_income = deposit_balance * (deposit_rate / 100)
                    st.metric("Доход в год", f"{yearly_income:,.0f} ₽")
                
                with col3:
                    if deposit_end:
                        # Правильная работа с типами datetime
                        if isinstance(deposit_end, datetime):
                            days_left = (deposit_end - datetime.now()).days
                        elif isinstance(deposit_end, date):
                            days_left = (deposit_end - datetime.now().date()).days
                        else:
                            days_left = 0
                        
                        if days_left > 0:
                            st.metric("До закрытия", f"{days_left} дней")
                            
                            months_left = days_left / 30
                            total_income = monthly_income * months_left
                            st.metric("Ожидаемый доход", f"{total_income:,.0f} ₽")
                        else:
                            st.metric("До закрытия", "Просрочен", delta=f"{abs(days_left)} дней")
                            st.error("⚠️ Вклад просрочен! Обновите данные.")
                    else:
                        st.metric("Срок", "Бессрочный")
                        st.metric("Автопролонгация", "✅ Да" if deposit_renewal else "❌ Нет")
                
                st.markdown("---")
                
                # Дополнительная информация
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**📅 Дата открытия:** {deposit_start.strftime('%d.%m.%Y')}")
                
                with col2:
                    if deposit_end:
                        end_str = deposit_end.strftime('%d.%m.%Y') if isinstance(deposit_end, (datetime, date)) else str(deposit_end)
                        st.write(f"**📅 Дата закрытия:** {end_str}")
                
                st.markdown("---")
                
                # Пополнения
                st.subheader("💰 Пополнения")
                
                contributions = get_deposit_contributions(deposit_id)
                
                if contributions:
                    st.write("**История пополнений:**")
                    
                    total_contributions = sum(c['amount'] for c in contributions)
                    
                    for contrib in contributions:
                        col_date, col_amount, col_delete = st.columns([2, 2, 1])
                        
                        with col_date:
                            contrib_date = contrib['date']
                            if isinstance(contrib_date, str):
                                contrib_date = datetime.strptime(contrib_date, '%Y-%m-%d')
                            st.write(f"📅 {contrib_date.strftime('%d.%m.%Y')}")
                        
                        with col_amount:
                            st.write(f"💵 {contrib['amount']:,.0f} ₽")
                        
                        with col_delete:
                            if st.button("🗑️", key=f"del_contrib_{contrib['id']}"):
                                if db_delete_deposit_contribution(contrib['id']):
                                    st.success("✅ Пополнение удалено!")
                                    st.rerun()
                    
                    st.success(f"💰 **Всего пополнений:** {total_contributions:,.0f} ₽")
                else:
                    st.info("📭 Нет пополнений")
                
                # Добавить пополнение
                with st.form(f"add_contribution_{deposit_id}"):
                    st.write("**Добавить пополнение:**")
                    
                    col_date, col_amount = st.columns(2)
                    
                    with col_date:
                        contrib_date = st.date_input(
                            "Дата",
                            value=datetime.now(),
                            key=f"contrib_date_{deposit_id}"
                        )
                    
                    with col_amount:
                        contrib_amount = st.number_input(
                            "Сумма (₽)",
                            min_value=100.0,
                            value=10000.0,
                            step=1000.0,
                            key=f"contrib_amount_{deposit_id}"
                        )
                    
                    if st.form_submit_button("➕ Добавить пополнение"):
                        if contrib_amount > 0:
                            if add_deposit_contribution(deposit_id, contrib_date, contrib_amount):
                                st.success(f"✅ Пополнение {contrib_amount:,.0f} ₽ добавлено!")
                                st.rerun()
                        else:
                            st.error("❌ Сумма должна быть больше 0")
                
                st.markdown("---")
                
                # Редактирование
                st.subheader("✏️ Редактировать вклад")
                
                with st.form(f"edit_deposit_{deposit_id}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_name = st.text_input("Название", value=deposit_name, key=f"edit_dep_name_{deposit_id}")
                        edit_balance = st.number_input("Сумма (₽)", value=float(deposit_balance), step=1000.0, key=f"edit_dep_balance_{deposit_id}")
                        edit_rate = st.number_input("Ставка (%)", value=float(deposit_rate), step=0.1, key=f"edit_dep_rate_{deposit_id}")
                    
                    with col2:
                        edit_start = st.date_input("Дата открытия", value=deposit_start, key=f"edit_dep_start_{deposit_id}")
                        
                        edit_has_end = st.checkbox("Указать дату закрытия", value=deposit_end is not None, key=f"edit_dep_has_end_{deposit_id}")
                        
                        if edit_has_end:
                            default_end = deposit_end if deposit_end else datetime.now() + timedelta(days=365)
                            edit_end = st.date_input(
                                "Дата закрытия", 
                                value=default_end,
                                key=f"edit_dep_end_{deposit_id}"
                            )
                        else:
                            edit_end = None
                        
                        edit_renewal = st.checkbox("Автопролонгация", value=deposit_renewal, key=f"edit_dep_renewal_{deposit_id}")
                    
                    col_save, col_delete = st.columns(2)
                    
                    with col_save:
                        if st.form_submit_button("💾 Сохранить изменения", type="primary", use_container_width=True):
                            if update_deposit_func(
                                deposit_id=deposit_id,
                                name=edit_name,
                                balance=edit_balance,
                                annual_rate=edit_rate,
                                start_date=edit_start,
                                end_date=edit_end,
                                auto_renewal=edit_renewal
                            ):
                                st.success("✅ Вклад обновлён!")
                                st.rerun()
                    
                    with col_delete:
                        if st.form_submit_button("🗑️ Удалить вклад", type="secondary", use_container_width=True):
                            # Подтверждение удаления
                            if st.session_state.get(f'confirm_delete_deposit_{deposit_id}', False):
                                if delete_deposit_func(deposit_id):
                                    st.success("✅ Вклад удалён!")
                                    st.session_state[f'confirm_delete_deposit_{deposit_id}'] = False
                                    st.rerun()
                            else:
                                st.session_state[f'confirm_delete_deposit_{deposit_id}'] = True
                                st.warning("⚠️ Нажмите ещё раз для подтверждения удаления")
                                st.rerun()


def render_deposits_chart(deposits):
    """График распределения вкладов"""
    
    st.subheader("📊 Распределение вкладов")
    
    # Данные для графика
    names = [deposit[1].get('name', 'Без названия') for deposit in deposits]
    balances = [deposit[1].get('balance', 0) for deposit in deposits]
    rates = [deposit[1].get('annual_rate', 0) for deposit in deposits]
    
    # Круговая диаграмма
    fig_pie = go.Figure(data=[go.Pie(
        labels=names,
        values=balances,
        textposition='inside',
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>Сумма: %{value:,.0f} ₽<br>%{percent}<extra></extra>'
    )])
    
    fig_pie.update_layout(
        title="Распределение суммы по вкладам",
        height=400,
        showlegend=True
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Столбчатая диаграмма
    fig_bar = go.Figure()
    
    fig_bar.add_trace(go.Bar(
        x=names,
        y=balances,
        name='Сумма',
        marker=dict(color='#4ECDC4'),
        text=[f'{b:,.0f} ₽' for b in balances],
        textposition='auto',
        hovertemplate='<b>%{x}</b><br>Сумма: %{y:,.0f} ₽<extra></extra>'
    ))
    
    fig_bar.update_layout(
        title="Суммы по вкладам",
        xaxis_title="Вклад",
        yaxis_title="Сумма (₽)",
        height=400,
        yaxis=dict(tickformat=',.0f')
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)
