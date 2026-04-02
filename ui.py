import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd

# 1. Налаштування сторінки (Dark Mode за замовчуванням у Streamlit)
st.set_page_config(page_title="BEST Telemetry Analyzer", layout="wide")

# 2. Бічна панель (Sidebar)
with st.sidebar:
    st.title("🚁 BEST Telemetry")
    st.markdown("---")
    
    # Завантажувач файлів
    st.subheader("Дані польоту")
    uploaded_file = st.file_uploader("Завантажте лог-файл (.bin)", type=["bin", "log"])
    
    # Налаштування візуалізації
    st.subheader("Налаштування")
    color_metric = st.selectbox("Колорувати траєкторію за:", ["Швидкість", "Висота", "Час"])
    
    st.markdown("---")
    analyze_btn = st.button("🚀 Аналізувати політ", use_container_width=True)

# 3. Головна панель (Заголовок)
st.title("Аналіз просторової траєкторії БПЛА")

# Якщо файл ще не завантажено, показуємо заглушку
if not uploaded_file and not analyze_btn:
    st.info("👈 Будь ласка, завантажте лог-файл Ardupilot у меню ліворуч, щоб розпочати аналіз.")
else:
    # 4. Дашборд з метриками (KPI Cards)
    # Згідно з вимогами, показуємо ключові кінематичні показники
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(label="Макс. гориз. швидкість", value="45 км/год")
    with col2:
        st.metric(label="Макс. верт. швидкість", value="12 м/с")
    with col3:
        st.metric(label="Макс. прискорення", value="18 м/с²")
    with col4:
        st.metric(label="Дистанція (Haversine)", value="4.2 км")
    with col5:
        st.metric(label="Час польоту", value="14 хв 30 с")

    st.markdown("---")

    # 5. Центральна частина — 3D-візуалізація
    st.subheader("Просторова траєкторія (система ENU)")
    
    # Генеруємо фейкові дані для демонстрації траєкторії (заміниш на реальні дані з pandas DataFrame)
    t = np.linspace(0, 10, 500)
    x = np.cumsum(np.random.randn(500))  # Схід (East)
    y = np.cumsum(np.random.randn(500))  # Північ (North)
    z = np.abs(np.cumsum(np.random.randn(500))) # Висота (Up)
    speed = np.gradient(x)**2 + np.gradient(y)**2 + np.gradient(z)**2 # Фейкова швидкість для кольору

    # Створення 3D-графіка Plotly
    fig = go.Figure()
    
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z,
        mode='lines',
        line=dict(
            color=speed, # Динамічне колорування залежно від швидкості
            colorscale='Turbo', # Градієнт від синього до червоного
            width=5,
            colorbar=dict(title="Швидкість")
        ),
        name='Траєкторія'
    ))

    # Налаштування осей для системи ENU
    fig.update_layout(
        scene=dict(
            xaxis_title='Схід (X, метри)',
            yaxis_title='Північ (Y, метри)',
            zaxis_title='Висота (Z, метри)'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=600
    )

    # Вивід графіка в Streamlit
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # 6. Нижня частина — AI-звіт та Теорія
    col_ai, col_docs = st.columns([2, 1])

    with col_ai:
        st.subheader("🤖 AI Flight Conclusion")
        st.success("""
        **Аналіз успішний.** Під час польоту виявлено різку втрату висоти на 8-й хвилині місії, що супроводжувалася короткочасним стрибком вертикального прискорення. Загальна траєкторія відповідає заданому маршруту. Перевищень критичної швидкості не зафіксовано.
        """)

    with col_docs:
        st.subheader("📚 Документація")
        with st.expander("Математичне обґрунтування"):
            st.write("""
            **Система координат ENU**: Локальна система, де осі спрямовані на Схід (X), Північ (Y) та Вгору (Z).
            
            **Розрахунок дистанції**: Використовується формула Haversine для врахування кривизни Землі при обчисленні відстані між точками GPS.
            
            **Похибки IMU**: Подвійне інтегрування даних акселерометра призводить до накопичення дрейфу (drift error), тому швидкості потребують фільтрації.
            """)