import streamlit as st
from datetime import datetime
from database import (
    init_db,
    get_all_credits,
    save_credit,
    update_credit,
    delete_credit,
    get_all_deposits,
    save_deposit,
    update_deposit,
    delete_deposit
)
from ui.dashboard import render_dashboard
from ui.credits_tab import render_credits_tab
from ui.deposits_tab import render_deposits_tab
from ui.calendar_tab import render_calendar_tab
from ui.strategies_tab import render_strategies_tab
from ui.heatmap_tab import render_heatmap_tab
from ui.forecast_chart import render_forecast_chart
from ui.income_tab import render_income_tab


# ==================== КОНСТАНТЫ ====================

APP_TITLE = "Финансовый планировщик"
APP_VERSION = "v1.1"
APP_ICON = "🔥"


# ==================== НАСТРОЙКА СТРАНИЦЫ ====================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': f"{APP_TITLE} {APP_VERSION} - Управление кредитами и вкладами"
    }
)


# ==================== КАСТОМНЫЕ СТИЛИ ====================

st.markdown("""
<style>
    /* Скрываем основное меню Streamlit */
    #MainMenu {visibility: hidden;}
    
    /* Скрываем футер */
    footer {visibility: hidden;}
    
    /* Улучшаем отступы */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Стиль для метрик */
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.1);
        border: 1px solid rgba(28, 131, 225, 0.2);
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


# ==================== ИНИЦИАЛИЗАЦИЯ ====================

@st.cache_resource
def initialize_database():
    """Инициализация БД (кэшируется)"""
    return init_db()


# Инициализируем БД
if not initialize_database():
    st.error("❌ Не удалось инициализировать базу данных!")
    st.stop()


# ==================== ЗАГРУЗКА ДАННЫХ ====================

@st.cache_data(ttl=10)  # Кэш на 10 секунд
def load_credits():
    """Загрузка кредитов с кэшированием"""
    return get_all_credits()


@st.cache_data(ttl=10)  # Кэш на 10 секунд
def load_deposits():
    """Загрузка вкладов с кэшированием"""
    return get_all_deposits()


# Загружаем данные
try:
    credits = load_credits()
    deposits = load_deposits()
except Exception as e:
    st.error(f"❌ Ошибка загрузки данных: {str(e)}")
    credits = []
    deposits = []


# ==================== БОКОВАЯ ПАНЕЛЬ ====================

def render_sidebar():
    """Рендер боковой панели"""
    
    with st.sidebar:
        st.title(f"{APP_ICON} {APP_TITLE}")
        st.caption(APP_VERSION)
        
        st.divider()
        
        # Быстрая статистика
        st.subheader("📊 Сводка")
        
        total_debt = sum(float(credit[1].get('balance', 0)) for credit in credits)
        total_savings = sum(float(deposit[1].get('balance', 0)) for deposit in deposits)
        net_position = total_savings - total_debt
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("💳 Кредитов", len(credits))
            st.metric("💰 Долг", f"{total_debt:,.0f} ₽")
        
        with col2:
            st.metric("💎 Вкладов", len(deposits))
            st.metric("💵 Сбережения", f"{total_savings:,.0f} ₽")
        
        # Чистая позиция с цветом
        if net_position >= 0:
            st.success(f"✅ Чистая позиция: **+{net_position:,.0f} ₽**")
        else:
            st.error(f"⚠️ Чистая позиция: **{net_position:,.0f} ₽**")
        
        st.divider()
        
        # Быстрые действия
        st.subheader("⚡ Быстрые действия")
        
        if st.button("🔄 Обновить данные", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        if st.button("📥 Экспорт данных", use_container_width=True):
            st.info("🚧 Функция в разработке")
        
        st.divider()
        
        # Информация
        st.caption(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        st.caption(f"🔥 {APP_TITLE} {APP_VERSION}")
        st.caption("💻 Создано с помощью Streamlit")


# Рендерим сайдбар
render_sidebar()


# ==================== ГЛАВНАЯ ОБЛАСТЬ ====================

# Заголовок
st.title(f"{APP_ICON} {APP_TITLE}")
st.caption("Управление кредитами, вкладами и финансовым планированием")

st.divider()


# ==================== ВКЛАДКИ ====================

tabs = st.tabs([
    "📊 Дашборд",
    "💳 Кредиты",
    "💎 Вклады",
    "💰 Доход",
    "📅 Календарь",
    "🎯 Стратегии",
    "🔥 Температурная карта",
    "📈 Прогноз"
])


# TAB 1: ДАШБОРД
with tabs[0]:
    try:
        render_dashboard(credits, deposits)
    except Exception as e:
        st.error(f"❌ Ошибка отображения дашборда: {str(e)}")


# TAB 2: КРЕДИТЫ
with tabs[1]:
    try:
        render_credits_tab(
            credits=credits,
            save_credit_func=save_credit,
            update_credit_func=update_credit,
            delete_credit_func=delete_credit
        )
    except Exception as e:
        st.error(f"❌ Ошибка отображения кредитов: {str(e)}")


# TAB 3: ВКЛАДЫ
with tabs[2]:
    try:
        render_deposits_tab(
            deposits=deposits,
            save_deposit_func=save_deposit,
            update_deposit_func=update_deposit,
            delete_deposit_func=delete_deposit
        )
    except Exception as e:
        st.error(f"❌ Ошибка отображения вкладов: {str(e)}")


# TAB 4: ДОХОД
with tabs[3]:
    try:
        render_income_tab()
    except Exception as e:
        st.error(f"❌ Ошибка отображения доходов: {str(e)}")


# TAB 5: КАЛЕНДАРЬ
with tabs[4]:
    try:
        render_calendar_tab(credits, deposits)
    except Exception as e:
        st.error(f"❌ Ошибка отображения календаря: {str(e)}")


# TAB 6: СТРАТЕГИИ
with tabs[5]:
    try:
        render_strategies_tab(credits, deposits)
    except Exception as e:
        st.error(f"❌ Ошибка отображения стратегий: {str(e)}")


# TAB 7: ТЕМПЕРАТУРНАЯ КАРТА
with tabs[6]:
    try:
        render_heatmap_tab(credits, deposits)
    except Exception as e:
        st.error(f"❌ Ошибка отображения карты: {str(e)}")


# TAB 8: ПРОГНОЗ
with tabs[7]:
    try:
        render_forecast_chart(credits, deposits)
    except Exception as e:
        st.error(f"❌ Ошибка отображения прогноза: {str(e)}")


# ==================== ФУТЕР ====================

st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption("📊 **Всего данных:**")
    st.caption(f"Кредитов: {len(credits)} | Вкладов: {len(deposits)}")

with footer_col2:
    st.caption("⏱️ **Последнее обновление:**")
    st.caption(datetime.now().strftime('%d.%m.%Y %H:%M:%S'))

with footer_col3:
    st.caption("🔥 **Версия:**")
    st.caption(f"{APP_TITLE} {APP_VERSION}")
