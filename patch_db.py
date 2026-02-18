# Читаем database.py
with open('database.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Патч 1: add_deposit_contribution — сигнатура
for i, line in enumerate(lines):
    if 'def add_deposit_contribution(deposit_id: int, date, amount: float) -> bool:' in line:
        lines[i] = lines[i].replace(
            'def add_deposit_contribution(deposit_id: int, date, amount: float) -> bool:',
            'def add_deposit_contribution(deposit_id: int, date, amount: float, income_id: int = None) -> bool:'
        )
        print(f"✅ Патч 1 применён (строка {i+1})")
        break

# Патч 2: INSERT в deposit_contributions
for i, line in enumerate(lines):
    if 'INSERT INTO deposit_contributions (deposit_id, amount, date) VALUES (?, ?, ?)' in line:
        lines[i] = lines[i].replace(
            'INSERT INTO deposit_contributions (deposit_id, amount, date) VALUES (?, ?, ?)',
            'INSERT INTO deposit_contributions (deposit_id, amount, date, income_id) VALUES (?, ?, ?, ?)'
        )
        print(f"✅ Патч 2а применён (строка {i+1})")
        break

# Патч 3: аргументы INSERT deposit_contributions
for i, line in enumerate(lines):
    if '(deposit_id, amount, date_str)' in line:
        lines[i] = lines[i].replace(
            '(deposit_id, amount, date_str)',
            '(deposit_id, amount, date_str, income_id)'
        )
        print(f"✅ Патч 2б применён (строка {i+1})")
        break

# Патч 4: add_extra_payment — сигнатура
for i, line in enumerate(lines):
    if 'def add_extra_payment(credit_id: int, date, amount: float) -> bool:' in line:
        lines[i] = lines[i].replace(
            'def add_extra_payment(credit_id: int, date, amount: float) -> bool:',
            'def add_extra_payment(credit_id: int, date, amount: float, income_id: int = None) -> bool:'
        )
        print(f"✅ Патч 3 применён (строка {i+1})")
        break

# Патч 5: после log_history в add_extra_payment вставляем запись в extra_payments_log
for i, line in enumerate(lines):
    if 'ADD_EXTRA_PAYMENT' in line and 'log_history' in line:
        # Ищем строку со st.success после этого места
        for j in range(i, min(i+10, len(lines))):
            if 'st.success' in lines[j] and 'досрочный' in lines[j].lower() or 'st.success' in lines[j] and 'payment' in lines[j].lower() or ('st.success' in lines[j] and j > i):
                insert_line = (
                    '        execute_query(\n'
                    "            'INSERT INTO extra_payments_log (income_id, credit_id, amount, date) VALUES (?, ?, ?, ?)',\n"
                    '            (income_id, credit_id, amount, date_str)\n'
                    '        )\n'
                )
                lines.insert(j, insert_line)
                print(f"✅ Патч 4 применён (строка {j+1})")
                break
        break

# Добавляем новые функции в конец
new_functions = '''

def check_income_deposit_done(income_id: int) -> float:
    """Сумма пополнений вклада привязанных к доходу"""
    row = execute_query(
        "SELECT SUM(amount) as total FROM deposit_contributions WHERE income_id=?",
        (income_id,),
        fetch='one'
    )
    return float(row['total']) if row and row['total'] else 0.0


def check_income_extra_done(income_id: int) -> float:
    """Сумма досрочных платежей привязанных к доходу"""
    row = execute_query(
        "SELECT SUM(amount) as total FROM extra_payments_log WHERE income_id=?",
        (income_id,),
        fetch='one'
    )
    return float(row['total']) if row and row['total'] else 0.0
'''

lines.append(new_functions)
print("✅ Новые функции добавлены")

# Сохраняем
with open('database.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✅ Все патчи применены!")