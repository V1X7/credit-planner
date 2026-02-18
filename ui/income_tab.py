import streamlit as st
from datetime import datetime, date, timedelta
from calendar import monthcalendar
from database import (
    get_all_credits,
    get_all_deposits,
    save_deposit,
    add_deposit_contribution,
    add_extra_payment,
    save_distribution_rules,
    get_distribution_rules,
    get_latest_distribution,
    check_income_deposit_done,
    check_income_extra_done,
    execute_query
)

MONTH_NAMES_RU = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
]


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_month_events(year: int, month: int) -> dict:
    incomes = execute_query(
        '''SELECT id.id, id.date, id.salary_type, id.amount,
                  idl.credits, idl.deposits, idl.extra_payments, idl.life
           FROM income_diary id
           LEFT JOIN income_distribution_log idl ON id.id = idl.income_id
           WHERE strftime('%Y', id.date)=? AND strftime('%m', id.date)=?
           ORDER BY id.date, id.id''',
        (str(year), f"{month:02d}"),
        fetch='all'
    )

    credits = get_all_credits()
    credit_days = set()
    for _, credit_dict in credits:
        payment_day = credit_dict.get('payment_day')
        if payment_day:
            credit_days.add(int(payment_day))

    return {
        'incomes': incomes or [],
        'credit_days': list(credit_days)
    }


def calculate_distribution(income_amount: float, income_date: date, income_type: str) -> dict:
    rules = get_distribution_rules()
    deposits_percent = float(rules.get('deposits_percent', 20))
    extra_percent = float(rules.get('extra_payments_percent', 30))
    life_percent = 100 - deposits_percent - extra_percent

    credits = get_all_credits()
    credits_total = sum(float(c[1].get('monthly_payment', 0)) for c in credits)

    is_salary = income_date.day == 10 and income_type == "Зарплата"

    if is_salary:
        remaining = income_amount - credits_total
        if remaining < 0:
            return {
                'total_income': income_amount, 'credits': credits_total,
                'deposits': 0, 'extra_payments': 0, 'life': 0,
                'remaining': remaining, 'deposits_percent': deposits_percent,
                'extra_percent': extra_percent, 'life_percent': life_percent,
                'deficit': abs(remaining), 'is_salary': True, 'has_deficit': True
            }
        else:
            return {
                'total_income': income_amount, 'credits': credits_total,
                'deposits': remaining * (deposits_percent / 100),
                'extra_payments': remaining * (extra_percent / 100),
                'life': remaining * (life_percent / 100),
                'remaining': remaining, 'deposits_percent': deposits_percent,
                'extra_percent': extra_percent, 'life_percent': life_percent,
                'deficit': 0, 'is_salary': True, 'has_deficit': False
            }
    else:
        return {
            'total_income': income_amount, 'credits': 0,
            'deposits': income_amount * (deposits_percent / 100),
            'extra_payments': income_amount * (extra_percent / 100),
            'life': income_amount * (life_percent / 100),
            'remaining': income_amount, 'deposits_percent': deposits_percent,
            'extra_percent': extra_percent, 'life_percent': life_percent,
            'deficit': 0, 'is_salary': False, 'has_deficit': False
        }


# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================

def render_income_tab():
    st.header("💰 Доходы и распределение")

    # ==================== НАВИГАЦИЯ ====================

    if 'current_month' not in st.session_state:
        st.session_state.current_month = datetime.now().replace(day=1)

    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("◀ Предыдущий", use_container_width=True):
            st.session_state.current_month = (
                st.session_state.current_month - timedelta(days=1)
            ).replace(day=1)
            st.rerun()
    with col2:
        current = st.session_state.current_month
        st.markdown(f"### 📅 {MONTH_NAMES_RU[current.month - 1]} {current.year}")
    with col3:
        if st.button("Следующий ▶", use_container_width=True):
            st.session_state.current_month = (
                st.session_state.current_month + timedelta(days=32)
            ).replace(day=1)
            st.rerun()

    st.divider()

    # ==================== НАСТРОЙКИ РАСПРЕДЕЛЕНИЯ ====================

    with st.expander("⚙️ Настройки распределения %"):
        rules = get_distribution_rules()
        dep_pct = float(rules.get('deposits_percent', 20))
        ext_pct = float(rules.get('extra_payments_percent', 30))
        life_pct = 100 - dep_pct - ext_pct

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💎 Вклады", f"{dep_pct:.0f}%")
        with col2:
            st.metric("💸 Досрочные", f"{ext_pct:.0f}%")
        with col3:
            st.metric("🏠 На жизнь", f"{life_pct:.0f}%")

        with st.form("rules_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_dep = st.slider("💎 Вклады (%)", 0, 100, int(dep_pct))
            with col2:
                new_ext = st.slider("💸 Досрочные (%)", 0, 100, int(ext_pct))

            new_life = 100 - new_dep - new_ext
            if new_dep + new_ext > 100:
                st.error("❌ Сумма > 100%!")
            else:
                st.info(f"🏠 На жизнь: {new_life}%")

            if st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True):
                if new_dep + new_ext <= 100:
                    if save_distribution_rules(new_dep, new_ext):
                        st.success("✅ Сохранено!")
                        st.rerun()
                else:
                    st.error("❌ Сумма > 100%!")

    st.divider()

    # ==================== КАЛЕНДАРЬ ====================

    events = get_month_events(current.year, current.month)

    income_days = {}
    for income in events['incomes']:
        day = datetime.strptime(income['date'], '%Y-%m-%d').day
        income_days[day] = {'amount': income['amount'], 'type': income['salary_type']}

    st.markdown("#### 📆 Календарь месяца")
    cal = monthcalendar(current.year, current.month)

    cols = st.columns(7)
    for i, dn in enumerate(['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']):
        cols[i].markdown(f"**{dn}**")

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].markdown("—")
            else:
                icons = []
                if day in income_days:
                    icons.append('💰')
                if day in events['credit_days']:
                    icons.append('💳')
                if icons:
                    cols[i].markdown(f"**{day}** {''.join(icons)}")
                else:
                    cols[i].markdown(f"{day}")

    st.caption("Легенда: 💰 Доход  💳 Списание кредита")
    st.divider()

    # ==================== СОБЫТИЯ МЕСЯЦА ====================

    st.markdown("#### 📋 События месяца")

    all_incomes = events['incomes']

    if not all_incomes:
        st.info("📭 Нет записей за этот месяц")
    else:
        for idx, income in enumerate(all_incomes):
            income_date = datetime.strptime(income['date'], '%Y-%m-%d').date()
            has_distribution = income['credits'] is not None
            income_id = income['id']
            today = datetime.now().date()

            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    status_icon = "✅" if has_distribution else "📝"
                    st.markdown(
                        f"### {status_icon} {income_date.strftime('%d.%m.%Y')} — "
                        f"💰 {income['salary_type']} **{income['amount']:,.0f} ₽**"
                    )
                with col2:
                    if st.button("🗑️ Удалить", key=f"del_{income_id}", use_container_width=True):
                        execute_query('DELETE FROM income_diary WHERE id=?', (income_id,))
                        execute_query('DELETE FROM income_distribution_log WHERE income_id=?', (income_id,))
                        st.rerun()

                if has_distribution:
                    # Метрики
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        val = income['credits'] or 0
                        st.metric("💳 Кредиты", f"{val:,.0f} ₽" if val > 0 else "—")
                    with col2:
                        st.metric("💎 Вклады", f"{float(income['deposits'] or 0):,.0f} ₽")
                    with col3:
                        st.metric("💸 Досрочные", f"{float(income['extra_payments'] or 0):,.0f} ₽")
                    with col4:
                        st.metric("🏠 Жизнь", f"{float(income['life'] or 0):,.0f} ₽")

                    # Проверяем статус по income_id
                    dep_done = check_income_deposit_done(income_id)
                    ext_done = check_income_extra_done(income_id)

                    col1, col2 = st.columns(2)

                    # --- ВКЛАД ---
                    with col1:
                        if dep_done > 0:
                            # ✅ Уже внесено — серая неактивная кнопка
                            st.button(
                                f"✅ Вклад пополнен  {dep_done:,.0f} ₽",
                                key=f"dep_done_{income_id}",
                                disabled=True,
                                use_container_width=True
                            )
                        else:
                            if st.button(
                                f"💎 Пополнить вклад  {float(income['deposits'] or 0):,.0f} ₽",
                                key=f"dep_btn_{income_id}",
                                use_container_width=True
                            ):
                                deposits = get_all_deposits()
                                if not deposits:
                                    st.session_state[f'create_deposit_{income_id}'] = True
                                elif len(deposits) == 1:
                                    add_deposit_contribution(
                                        deposits[0][0], today,
                                        float(income['deposits']),
                                        income_id=income_id  # ← привязка!
                                    )
                                    st.rerun()
                                else:
                                    st.session_state[f'choose_deposit_{income_id}'] = True
                                    st.rerun()

                        # Форма создания вклада
                        if st.session_state.get(f'create_deposit_{income_id}'):
                            with st.form(f"new_deposit_form_{income_id}"):
                                st.markdown("**💎 Создать вклад**")
                                dep_name = st.text_input("Название", value="Мой вклад")
                                dep_rate = st.number_input("Ставка (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.1)
                                dep_end = st.date_input("Дата окончания", value=date(today.year + 1, today.month, today.day))
                                dep_renewal = st.checkbox("Автопродление")

                                col_s, col_c = st.columns(2)
                                with col_s:
                                    if st.form_submit_button("✅ Создать", type="primary", use_container_width=True):
                                        dep_amount = float(income['deposits'] or 0)
                                        new_dep_id = save_deposit(
                                            dep_name, dep_amount, dep_rate,
                                            today, dep_end, dep_renewal
                                        )
                                        if new_dep_id:
                                            add_deposit_contribution(
                                                new_dep_id, today, dep_amount,
                                                income_id=income_id  # ← привязка!
                                            )
                                            st.session_state[f'create_deposit_{income_id}'] = False
                                            st.rerun()
                                with col_c:
                                    if st.form_submit_button("❌ Отмена", use_container_width=True):
                                        st.session_state[f'create_deposit_{income_id}'] = False
                                        st.rerun()

                        # Форма выбора вклада
                        if st.session_state.get(f'choose_deposit_{income_id}'):
                            deposits = get_all_deposits()
                            with st.form(f"choose_deposit_form_{income_id}"):
                                st.markdown("**💎 Выберите вклад**")
                                dep_options = {f"{d[1]['name']} ({d[1]['balance']:,.0f} ₽)": d[0] for d in deposits}
                                chosen = st.selectbox("Вклад", list(dep_options.keys()))

                                col_s, col_c = st.columns(2)
                                with col_s:
                                    if st.form_submit_button("✅ Пополнить", type="primary", use_container_width=True):
                                        dep_id = dep_options[chosen]
                                        add_deposit_contribution(
                                            dep_id, today,
                                            float(income['deposits']),
                                            income_id=income_id  # ← привязка!
                                        )
                                        st.session_state[f'choose_deposit_{income_id}'] = False
                                        st.rerun()
                                with col_c:
                                    if st.form_submit_button("❌ Отмена", use_container_width=True):
                                        st.session_state[f'choose_deposit_{income_id}'] = False
                                        st.rerun()

                    # --- ДОСРОЧНЫЙ ПЛАТЁЖ ---
                    with col2:
                        if ext_done > 0:
                            # ✅ Уже внесено — серая неактивная кнопка
                            st.button(
                                f"✅ Досрочный внесён  {ext_done:,.0f} ₽",
                                key=f"ext_done_{income_id}",
                                disabled=True,
                                use_container_width=True
                            )
                        else:
                            if st.button(
                                f"💸 Внести досрочный  {float(income['extra_payments'] or 0):,.0f} ₽",
                                key=f"ext_btn_{income_id}",
                                use_container_width=True
                            ):
                                st.session_state[f'choose_credit_{income_id}'] = True
                                st.rerun()

                        # Форма выбора кредита
                        if st.session_state.get(f'choose_credit_{income_id}'):
                            credits = get_all_credits()
                            with st.form(f"choose_credit_form_{income_id}"):
                                st.markdown("**💸 Выберите кредит**")
                                cr_options = {
                                    f"{c[1]['name']} (остаток {float(c[1].get('balance', 0)):,.0f} ₽)": c[0]
                                    for c in credits
                                }
                                chosen_cr = st.selectbox("Кредит", list(cr_options.keys()))
                                ext_amount = st.number_input(
                                    "Сумма (₽)",
                                    min_value=0.0,
                                    value=float(income['extra_payments'] or 0),
                                    step=1000.0,
                                    format="%.0f"
                                )

                                col_s, col_c = st.columns(2)
                                with col_s:
                                    if st.form_submit_button("✅ Внести", type="primary", use_container_width=True):
                                        cr_id = cr_options[chosen_cr]
                                        add_extra_payment(
                                            cr_id, today, ext_amount,
                                            income_id=income_id  # ← привязка!
                                        )
                                        st.session_state[f'choose_credit_{income_id}'] = False
                                        st.rerun()
                                with col_c:
                                    if st.form_submit_button("❌ Отмена", use_container_width=True):
                                        st.session_state[f'choose_credit_{income_id}'] = False
                                        st.rerun()
                else:
                    st.info("📝 Распределение не зафиксировано")

    st.divider()

    # ==================== ДОБАВЛЕНИЕ ПОСТУПЛЕНИЯ ====================

    if st.button("➕ Добавить поступление", type="primary", use_container_width=True):
        st.session_state.show_income_form = not st.session_state.get('show_income_form', False)

    if st.session_state.get('show_income_form', False):
        with st.form("add_income_form"):
            st.markdown("#### 📝 Новое поступление")

            col1, col2, col3 = st.columns(3)
            with col1:
                income_date_input = st.date_input(
                    "📅 Дата",
                    value=datetime.now().date(),
                    max_value=datetime.now().date()
                )
            with col2:
                default_type = (
                    "Зарплата" if income_date_input.day == 10
                    else "Аванс" if income_date_input.day == 25
                    else "Другое"
                )
                income_type_input = st.selectbox(
                    "📂 Тип",
                    ["Зарплата", "Аванс", "Другое"],
                    index=["Зарплата", "Аванс", "Другое"].index(default_type)
                )
            with col3:
                income_amount_input = st.number_input(
                    "💵 Сумма (₽)", min_value=0.0, value=0.0, step=1000.0, format="%.0f"
                )

            if income_amount_input > 0:
                dist_preview = calculate_distribution(income_amount_input, income_date_input, income_type_input)
                st.divider()
                st.markdown("**📊 Предпросмотр:**")
                if dist_preview['has_deficit']:
                    st.error(
                        f"⚠️ Недостаточно средств!\n\n"
                        f"Доход: **{dist_preview['total_income']:,.0f} ₽** | "
                        f"Кредиты: **{dist_preview['credits']:,.0f} ₽** | "
                        f"Не хватает: **{dist_preview['deficit']:,.0f} ₽**"
                    )
                else:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("💳 Кредиты", f"{dist_preview['credits']:,.0f} ₽" if dist_preview['credits'] > 0 else "—")
                    with col2:
                        st.metric("💎 Вклады", f"{dist_preview['deposits']:,.0f} ₽")
                    with col3:
                        st.metric("💸 Досрочные", f"{dist_preview['extra_payments']:,.0f} ₽")
                    with col4:
                        st.metric("🏠 Жизнь", f"{dist_preview['life']:,.0f} ₽")

            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("✅ Сохранить", type="primary", use_container_width=True)
            with col2:
                cancel = st.form_submit_button("❌ Отмена", use_container_width=True)

            if cancel:
                st.session_state.show_income_form = False
                st.rerun()

            if submit:
                if income_amount_input <= 0:
                    st.error("❌ Введите сумму!")
                else:
                    distribution = calculate_distribution(income_amount_input, income_date_input, income_type_input)
                    if distribution['has_deficit']:
                        st.error(f"❌ Не хватает: {distribution['deficit']:,.0f} ₽")
                    else:
                        income_id = execute_query(
                            'INSERT INTO income_diary (date, salary_type, amount) VALUES (?, ?, ?)',
                            (income_date_input.strftime('%Y-%m-%d'), income_type_input, income_amount_input),
                            fetch='lastrowid'
                        )
                        if income_id:
                            execute_query(
                                '''INSERT INTO income_distribution_log
                                   (income_id, total_income, credits, deposits, extra_payments, life)
                                   VALUES (?, ?, ?, ?, ?, ?)''',
                                (income_id, distribution['total_income'], distribution['credits'],
                                 distribution['deposits'], distribution['extra_payments'], distribution['life'])
                            )
                            st.success(f"✅ Доход {income_amount_input:,.0f} ₽ сохранён!")
                            st.session_state.show_income_form = False
                            st.rerun()
                        else:
                            st.error("❌ Ошибка сохранения!")

    st.divider()

    # ==================== ИТОГ МЕСЯЦА ====================

    st.markdown("#### 📊 Итог месяца")

    total_income = sum(float(inc['amount']) for inc in all_incomes)

    dist_logs = execute_query(
        '''SELECT SUM(credits) as credits, SUM(deposits) as deposits,
                  SUM(extra_payments) as extra, SUM(life) as life
           FROM income_distribution_log idl
           JOIN income_diary id ON idl.income_id = id.id
           WHERE strftime('%Y', id.date)=? AND strftime('%m', id.date)=?''',
        (str(current.year), f"{current.month:02d}"),
        fetch='one'
    )

    if total_income > 0:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("💵 Поступило", f"{total_income:,.0f} ₽")
        with col2:
            st.metric("💳 Кредиты", f"{float(dist_logs['credits'] or 0):,.0f} ₽" if dist_logs else "—")
        with col3:
            st.metric("💎 Вклады", f"{float(dist_logs['deposits'] or 0):,.0f} ₽" if dist_logs else "—")
        with col4:
            st.metric("💸 Досрочные", f"{float(dist_logs['extra'] or 0):,.0f} ₽" if dist_logs else "—")
        with col5:
            st.metric("🏠 Жизнь", f"{float(dist_logs['life'] or 0):,.0f} ₽" if dist_logs else "—")
    else:
        st.info("📭 Нет данных за этот месяц")

    st.divider()

    # ==================== ИСТОРИЯ ====================

    st.markdown("#### 📜 История (последние 3 месяца)")

    has_history = False
    for i in range(1, 4):
        prev_month = (st.session_state.current_month - timedelta(days=32 * i)).replace(day=1)
        month_events = get_month_events(prev_month.year, prev_month.month)

        if month_events['incomes']:
            has_history = True
            month_total = sum(float(inc['amount']) for inc in month_events['incomes'])
            st.markdown(
                f"**{MONTH_NAMES_RU[prev_month.month - 1]} {prev_month.year}** "
                f"— итого: **{month_total:,.0f} ₽**"
            )
            for income in month_events['incomes']:
                inc_date = datetime.strptime(income['date'], '%Y-%m-%d').date()
                icon = "✅" if income['credits'] is not None else "📝"
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} {inc_date.strftime('%d.%m.%y')} "
                    f"💰 {income['salary_type']} — **{income['amount']:,.0f} ₽**"
                )
            st.write("")

    if not has_history:
        st.info("📭 История за последние 3 месяца пуста")