import streamlit as st
from datetime import datetime, timedelta, date
import plotly.graph_objects as go
import pandas as pd
from models import Credit, Deposit


def render_dashboard(credits, deposits):
    """Дашборд с полной статистикой"""
    
    st.header("📊 Дашборд")
    
    # Проверка на пустые данные
    if not credits and not deposits:
        st.info("📭 Добавьте кредиты или вклады для отображения статистики")
        return
    
    # ==================== БЕЗОПАСНЫЕ РАСЧЁТЫ ====================
    
    # Общий долг
    total_debt = sum(float(credit[1].get('balance', 0)) for credit in credits) if credits else 0
    
    # Общие сбережения
    total_savings = sum(float(deposit[1].get('balance', 0)) for deposit in deposits) if deposits else 0
    
    # Чистая позиция
    net_position = total_savings - total_debt
    
    # Переплата по процентам (с защитой от ошибок)
    total_interest_paid = 0
    if credits:
        for credit in credits:
            try:
                credit_obj = Credit(
                    name=credit[1].get('name', ''),
                    balance=float(credit[1].get('balance', 0)),
                    annual_rate=float(credit[1].get('annual_rate', 0)),
                    monthly_payment=float(credit[1].get('monthly_payment', 0)),
                    start_date=credit[1].get('start_date', datetime.now()),
                    payment_day=int(credit[1].get('payment_day', 10)),
                    end_date=credit[1].get('end_date')
                )
                total_interest_paid += credit_obj.get_total_interest()
            except Exception:
                pass
    
    # Годовой доход от вкладов (с защитой от ошибок)
    total_deposit_income = 0
    if deposits:
        for deposit in deposits:
            try:
                deposit_obj = Deposit(
                    name=deposit[1].get('name', ''),
                    balance=float(deposit[1].get('balance', 0)),
                    annual_rate=float(deposit[1].get('annual_rate', 0)),
                    start_date=deposit[1].get('start_date', datetime.now()),
                    end_date=deposit[1].get('end_date'),
                    auto_renewal=deposit[1].get('auto_renewal', False)
                )
                total_deposit_income += deposit_obj.calculate_yearly_income()
            except Exception:
                pass
    
    # Ежемесячные платежи
    total_monthly_payments = sum(float(credit[1].get('monthly_payment', 0)) for credit in credits) if credits else 0
    
    # Коэффициент долга
    debt_ratio = (total_debt / total_savings * 100) if total_savings > 0 else (100 if total_debt > 0 else 0)
    
    # ==================== ГЛАВНЫЕ МЕТРИКИ ====================
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💳 Общий долг", f"{total_debt:,.0f} ₽")
    
    with col2:
        st.metric("💎 Общие сбережения", f"{total_savings:,.0f} ₽")
    
    with col3:
        st.metric("💰 Чистая позиция", f"{net_position:,.0f} ₽")
    
    with col4:
        st.metric("📈 Годовой доход от вкладов", f"{total_deposit_income:,.0f} ₽")
    
    st.divider()
    
    # ==================== ДОПОЛНИТЕЛЬНЫЕ МЕТРИКИ ====================
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💸 Ежемесячные платежи", f"{total_monthly_payments:,.0f} ₽")
    
    with col2:
        st.metric("📊 Коэффициент долга", f"{debt_ratio:.1f}%")
    
    with col3:
        st.metric("💳 Переплата по процентам", f"{total_interest_paid:,.0f} ₽")
    
    with col4:
        st.metric("📅 Кредитов / Вкладов", f"{len(credits)} / {len(deposits)}")
    
    st.divider()
    
    # ==================== КРУГОВАЯ ДИАГРАММА ====================
    
    st.subheader("📊 Структура активов и пассивов")
    
    if credits or deposits:
        labels = []
        values = []
        colors = []
        
        if credits:
            for credit_id, credit_data in credits:
                name = credit_data.get('name', 'Кредит')
                balance = float(credit_data.get('balance', 0))
                if balance > 0:
                    labels.append(f"💳 {name}")
                    values.append(balance)
                    colors.append('#FF6B6B')
        
        if deposits:
            for deposit_id, deposit_data in deposits:
                name = deposit_data.get('name', 'Вклад')
                balance = float(deposit_data.get('balance', 0))
                if balance > 0:
                    labels.append(f"💎 {name}")
                    values.append(balance)
                    colors.append('#4ECDC4')
        
        if labels:
            fig_pie = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=colors),
                textposition='inside',
                textinfo='label+percent',
                hovertemplate='<b>%{label}</b><br>%{value:,.0f} ₽<br>%{percent}<extra></extra>'
            )])
            
            fig_pie.update_layout(
                title="Распределение активов и пассивов",
                height=600,
                showlegend=True,
                font=dict(size=14)
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("📭 Нет данных для отображения диаграммы")
    
    st.divider()
    
    # ==================== ИНФОРМАЦИЯ О КРЕДИТАХ ====================
    
    st.subheader("💳 Кредиты")
    
    if credits:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Количество кредитов", len(credits))
        
        with col2:
            avg_rate = sum(float(credit[1].get('annual_rate', 0)) for credit in credits) / len(credits)
            st.metric("Средняя ставка", f"{avg_rate:.2f}%")
        
        with col3:
            avg_months = 0
            count = 0
            for credit in credits:
                monthly_payment = float(credit[1].get('monthly_payment', 0))
                balance = float(credit[1].get('balance', 0))
                rate = float(credit[1].get('annual_rate', 0)) / 12 / 100
                
                if monthly_payment > balance * rate and balance > 0:
                    months = balance / (monthly_payment - balance * rate)
                    avg_months += months
                    count += 1
            
            avg_months = int(avg_months / count) if count > 0 else 0
            st.metric("Средний срок погашения", f"~{avg_months} мес.")
        
        st.divider()
        
        st.subheader("🔴 Топ кредитов по переплате")
        
        credits_with_interest = []
        for credit_id, credit_data in credits:
            try:
                credit_obj = Credit(
                    name=credit_data.get('name', ''),
                    balance=float(credit_data.get('balance', 0)),
                    annual_rate=float(credit_data.get('annual_rate', 0)),
                    monthly_payment=float(credit_data.get('monthly_payment', 0)),
                    start_date=credit_data.get('start_date', datetime.now()),
                    payment_day=int(credit_data.get('payment_day', 10)),
                    end_date=credit_data.get('end_date')
                )
                interest = credit_obj.get_total_interest()
                
                credits_with_interest.append({
                    'Кредит': credit_data.get('name', ''),
                    'Остаток': float(credit_data.get('balance', 0)),
                    'Ставка': f"{float(credit_data.get('annual_rate', 0)):.2f}%",
                    'Переплата': interest,
                    'Платёж': float(credit_data.get('monthly_payment', 0))
                })
            except Exception:
                pass
        
        if credits_with_interest:
            credits_with_interest.sort(key=lambda x: x['Переплата'], reverse=True)
            
            for item in credits_with_interest:
                item['Остаток'] = f"{item['Остаток']:,.0f} ₽"
                item['Переплата'] = f"{item['Переплата']:,.0f} ₽"
                item['Платёж'] = f"{item['Платёж']:,.0f} ₽"
            
            df_credits = pd.DataFrame(credits_with_interest)
            st.dataframe(df_credits, use_container_width=True, hide_index=True)
        else:
            st.info("📭 Нет данных о кредитах")
        
    else:
        st.info("📭 Кредиты не добавлены")
    
    st.divider()
    
    # ==================== ИНФОРМАЦИЯ О ВКЛАДАХ ====================
    
    st.subheader("💎 Вклады")
    
    if deposits:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Количество вкладов", len(deposits))
        
        with col2:
            avg_rate = sum(float(deposit[1].get('annual_rate', 0)) for deposit in deposits) / len(deposits)
            st.metric("Средняя ставка", f"{avg_rate:.2f}%")
        
        with col3:
            today = datetime.now()
            expiring_soon = 0
            
            for deposit_id, deposit_data in deposits:
                end_date = deposit_data.get('end_date')
                if end_date:
                    if isinstance(end_date, date) and not isinstance(end_date, datetime):
                        end_date = datetime.combine(end_date, datetime.min.time())
                    
                    if isinstance(end_date, datetime):
                        days_left = (end_date - today).days
                        if 0 < days_left <= 90:
                            expiring_soon += 1
            
            st.metric("⏰ Заканчиваются в течение 3 мес.", expiring_soon)
        
        st.divider()
        
        st.subheader("🟢 Топ вкладов по годовому доходу")
        
        deposits_with_income = []
        for deposit_id, deposit_data in deposits:
            try:
                deposit_obj = Deposit(
                    name=deposit_data.get('name', ''),
                    balance=float(deposit_data.get('balance', 0)),
                    annual_rate=float(deposit_data.get('annual_rate', 0)),
                    start_date=deposit_data.get('start_date', datetime.now()),
                    end_date=deposit_data.get('end_date'),
                    auto_renewal=deposit_data.get('auto_renewal', False)
                )
                yearly_income = deposit_obj.calculate_yearly_income()
                monthly_income = yearly_income / 12
                
                end_date = deposit_data.get('end_date')
                if end_date and isinstance(end_date, (datetime, date)):
                    end_date_str = end_date.strftime('%d.%m.%Y')
                else:
                    end_date_str = 'Бессрочно'
                
                deposits_with_income.append({
                    'Вклад': deposit_data.get('name', ''),
                    'Сумма': float(deposit_data.get('balance', 0)),
                    'Ставка': f"{float(deposit_data.get('annual_rate', 0)):.2f}%",
                    'Годовой доход': yearly_income,
                    'Ежемесячно': monthly_income,
                    'Дата окончания': end_date_str
                })
            except Exception:
                pass
        
        if deposits_with_income:
            deposits_with_income.sort(key=lambda x: x['Годовой доход'], reverse=True)
            
            for item in deposits_with_income:
                item['Сумма'] = f"{item['Сумма']:,.0f} ₽"
                item['Годовой доход'] = f"{item['Годовой доход']:,.0f} ₽"
                item['Ежемесячно'] = f"{item['Ежемесячно']:,.0f} ₽"
            
            df_deposits = pd.DataFrame(deposits_with_income)
            st.dataframe(df_deposits, use_container_width=True, hide_index=True)
        else:
            st.info("📭 Нет данных о вкладах")
        
        st.divider()
        
        st.subheader("⏰ Вклады, заканчивающиеся в ближайшие 3 месяца")
        
        today = datetime.now()
        expiring_deposits = []
        
        for deposit_id, deposit_data in deposits:
            end_date = deposit_data.get('end_date')
            if end_date:
                if isinstance(end_date, date) and not isinstance(end_date, datetime):
                    end_date = datetime.combine(end_date, datetime.min.time())
                
                if isinstance(end_date, datetime):
                    days_left = (end_date - today).days
                    if 0 < days_left <= 90:
                        expiring_deposits.append({
                            'Вклад': deposit_data.get('name', ''),
                            'Сумма': f"{float(deposit_data.get('balance', 0)):,.0f} ₽",
                            'Дата окончания': end_date.strftime('%d.%m.%Y'),
                            'Дней осталось': days_left,
                            'Автопродление': '✅ Да' if deposit_data.get('auto_renewal') else '❌ Нет'
                        })
        
        if expiring_deposits:
            df_expiring = pd.DataFrame(expiring_deposits)
            df_expiring = df_expiring.sort_values('Дней осталось')
            st.dataframe(df_expiring, use_container_width=True, hide_index=True)
        else:
            st.success("✅ Нет вкладов, заканчивающихся в ближайшие 3 месяца")
        
    else:
        st.info("📭 Вклады не добавлены")
    
    st.divider()
    
    # ==================== ПРОГНОЗ НА 12 МЕСЯЦЕВ ====================
    
    st.subheader("📈 Прогноз на 12 месяцев")
    
    if credits or deposits:
        months = []
        debt_forecast = []
        savings_forecast = []
        net_forecast = []
        
        current_debt = total_debt
        current_savings = total_savings
        
        for month in range(13):
            months.append(f"М{month}")
            debt_forecast.append(current_debt)
            savings_forecast.append(current_savings)
            net_forecast.append(current_savings - current_debt)
            
            if total_monthly_payments > 0 and current_debt > 0:
                debt_reduction = total_monthly_payments * 0.7
                current_debt = max(0, current_debt - debt_reduction)
            
            current_savings += total_deposit_income / 12
        
        fig_forecast = go.Figure()
        
        fig_forecast.add_trace(go.Scatter(
            x=months, y=debt_forecast,
            mode='lines+markers', name='💳 Долг',
            line=dict(color='#FF6B6B', width=3),
            marker=dict(size=8),
            hovertemplate='<b>%{x}</b><br>Долг: %{y:,.0f} ₽<extra></extra>'
        ))
        
        fig_forecast.add_trace(go.Scatter(
            x=months, y=savings_forecast,
            mode='lines+markers', name='💎 Сбережения',
            line=dict(color='#4ECDC4', width=3),
            marker=dict(size=8),
            hovertemplate='<b>%{x}</b><br>Сбережения: %{y:,.0f} ₽<extra></extra>'
        ))
        
        fig_forecast.add_trace(go.Scatter(
            x=months, y=net_forecast,
            mode='lines+markers', name='💰 Чистая позиция',
            line=dict(color='#FFD93D', width=3, dash='dash'),
            marker=dict(size=8),
            hovertemplate='<b>%{x}</b><br>Чистая позиция: %{y:,.0f} ₽<extra></extra>'
        ))
        
        fig_forecast.update_layout(
            title="Прогноз долга и сбережений на 12 месяцев",
            xaxis_title="Период",
            yaxis_title="Сумма (₽)",
            height=500,
            hovermode='x unified',
            yaxis=dict(tickformat=',.0f')
        )
        
        st.plotly_chart(fig_forecast, use_container_width=True)
    else:
        st.info("📭 Добавьте кредиты или вклады для отображения прогноза")
    
    st.divider()
    
    # ==================== РЕКОМЕНДАЦИИ ====================
    
    st.subheader("💡 Рекомендации")
    
    # ИСПРАВЛЕНО: Получаем total_income из БД
    try:
        from database import get_income_settings
        income_settings = get_income_settings()
        total_income = float(income_settings.get('salary', 0)) + float(income_settings.get('advance', 0))
    except:
        total_income = 0
    
    recommendations = []
    
    if net_position < 0:
        recommendations.append(("warning", f"⚠️ Чистая позиция отрицательная: {net_position:,.0f} ₽. Рекомендуем увеличить сбережения или снизить долги."))
    elif net_position > 0:
        recommendations.append(("success", f"✅ Отличная позиция! Чистая позиция: {net_position:,.0f} ₽"))
    
    if total_interest_paid > total_deposit_income:
        difference = total_interest_paid - total_deposit_income
        recommendations.append(("info", f"ℹ️ Вы платите больше процентов по кредитам ({total_interest_paid:,.0f} ₽), чем получаете от вкладов ({total_deposit_income:,.0f} ₽). Разница: {difference:,.0f} ₽"))
    elif total_deposit_income > total_interest_paid and total_interest_paid > 0:
        difference = total_deposit_income - total_interest_paid
        recommendations.append(("success", f"✅ Доходы от вкладов ({total_deposit_income:,.0f} ₽) покрывают проценты по кредитам ({total_interest_paid:,.0f} ₽). Профит: {difference:,.0f} ₽"))
    
    if debt_ratio > 100:
        recommendations.append(("error", f"🚨 Коэффициент долга превышает 100% ({debt_ratio:.1f}%). Долг больше сбережений!"))
    elif debt_ratio > 50:
        recommendations.append(("warning", f"⚠️ Коэффициент долга высокий ({debt_ratio:.1f}%). Рекомендуем снизить долги."))
    elif debt_ratio > 0:
        recommendations.append(("success", f"✅ Коэффициент долга в норме ({debt_ratio:.1f}%)"))
    
    # ИСПРАВЛЕНО: Проверяем наличие total_income
    if total_income > 0 and total_monthly_payments > total_income / 2:
        recommendations.append(("warning", f"⚠️ Высокая платёжная нагрузка: {total_monthly_payments:,.0f} ₽/мес"))
    
    for rec_type, message in recommendations:
        if rec_type == "error":
            st.error(message)
        elif rec_type == "warning":
            st.warning(message)
        elif rec_type == "success":
            st.success(message)
        else:
            st.info(message)
