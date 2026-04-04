import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import pymap3d as pm
import tempfile
import os
from ai_asisstant import get_ai_analysis
from Model.test3d import draw_trajectory

# --- НАЛАШТУВАННЯ ІНТЕРФЕЙСУ ---
st.set_page_config(page_title="DEA Telemetry Analyzer", layout="wide")

# Очищення кешу ШІ при завантаженні нового файлу (щоб звіт відповідав новому польоту)
if 'last_uploaded_file' not in st.session_state:
    st.session_state['last_uploaded_file'] = None

# --- БЕЗПЕЧНИЙ ІМПОРТ БЕКЕНДУ (Захист від помилок) ---
try:
    from backend import process_log_file, calculate_metrics
    backend_ready = True
except ImportError:
    backend_ready = False
    
    # Тимчасові заглушки (Mocks), які працюють замість бекенду
    def process_log_file(filepath):
        t = np.linspace(0, 10, 500)
        df = pd.DataFrame({
            'MSG_TYPE': ['GPS'] * 500,
            'TimeUS': t * 1_000_000,
            'Lat': 49.8397 + np.cumsum(np.random.randn(500) * 0.0001),
            'Lng': 24.0297 + np.cumsum(np.random.randn(500) * 0.0001),
            'Alt': 100 + np.abs(np.cumsum(np.random.randn(500) * 2))
        })
        return df

    def calculate_metrics(df):
        return {
            'max_h_speed': 45.2,
            'max_v_speed': 12.0,
            'max_accel': 18.5,
            'total_distance': 4200.0,
            'max_altitude_gain': 120.0,
            'flight_time_sec': 870.0
        }

# --- БІЧНА ПАНЕЛЬ ---
with st.sidebar:
    st.title("🚁 DEA Telemetry")
    st.markdown("---")
    
    if not backend_ready:
        st.warning("⚠️ Увімкнено Демо-режим. Функції бекенду ще не знайдено, використовуються фейкові дані.")
    
    st.subheader("Дані польоту")
    uploaded_file = st.file_uploader("Завантажте лог-файл (.bin)", type=["bin", "log"])

    # Якщо завантажили інший файл, очищаємо старий звіт ШІ
    if uploaded_file and uploaded_file.name != st.session_state['last_uploaded_file']:
        st.session_state['last_uploaded_file'] = uploaded_file.name
        if 'ai_report_content' in st.session_state:
            del st.session_state['ai_report_content']

    analyze_btn = st.button("✦ Огляд від ШІ", use_container_width=True)

    if analyze_btn:
        if uploaded_file:
            # Ставимо прапорець, що потрібно згенерувати звіт саме зараз
            st.session_state['generate_ai_now'] = True
        else:
            st.error("Спочатку завантажте файл!")

# --- ГОЛОВНА ПАНЕЛЬ ---
st.title("Аналіз просторової траєкторії БПЛА")

if not uploaded_file:
    st.info("👈 Будь ласка, завантажте лог-файл Ardupilot у меню ліворуч, щоб розпочати аналіз.")
else:
    with st.spinner("Обробка даних... ⏳"):
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        try:
            # 1. ОТРИМАННЯ ДАНИХ
            try:
                csv_path, rows_count = process_log_file(tmp_path)
            except ValueError as e:
                st.error(f"Невалідний файл: {e}")
                st.stop()
            except Exception as e:
                st.error(f"Помилка обробки: {e}")
                st.stop()

            if csv_path is None or rows_count == 0:
                st.error("Повернуто порожній масив даних.")
            else:
                df = pd.read_csv(csv_path)

                if df.empty:
                    st.error("Повернуто порожній масив даних.")
                else:
                    metrics = calculate_metrics(df)
                mins, secs = divmod(int(metrics.get('flight_time_sec', 0)), 60)

                # --- ДАШБОРД ---
                st.subheader("Кінематичні показники місії")
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                
                with col1: st.metric("Макс. гориз. швидкість", f"{metrics.get('max_h_speed', 0):.1f} м/с")
                with col2: st.metric("Макс. верт. швидкість", f"{metrics.get('max_v_speed', 0):.1f} м/с")
                with col3: st.metric("Макс. прискорення (IMU)", f"{metrics.get('max_accel', 'N/A')} м/с²")
                with col4: st.metric("Дистанція (Haversine)", f"{metrics.get('total_distance', 0) / 1000:.2f} км")
                with col5: st.metric("Макс. набір висоти", f"{metrics.get('max_altitude_gain', 0):.1f} м")
                with col6: st.metric("Час польоту", f"{mins} хв {secs} с")

                st.markdown("---")

                # --- ТАЙМЛАЙН ТА ПОВЗУНОК ---
                st.subheader("Просторова траєкторія (система ENU)")
                
                min_time = df['TimeUS'].min()
                max_time = df['TimeUS'].max()
                duration_sec = float((max_time - min_time) / 1_000_000.0)

                selected_sec = st.slider(
                    "⏱️ Хронологія польоту (секунди)",
                    min_value=0.0,
                    max_value=duration_sec,
                    value=duration_sec, 
                    step=0.5 
                )

                selected_time_us = min_time + (selected_sec * 1_000_000.0)
                df_filtered = df[df['TimeUS'] <= selected_time_us].copy()

                valid_points = len(df_filtered[df_filtered['MSG_TYPE'].isin(['GPS', 'SIM'])])
                
                if valid_points < 2:
                    st.warning("Повзунок на самому початку: замало даних для відмальовування траєкторії.")
                else:
                    fig = draw_trajectory(df_filtered)
                    st.plotly_chart(fig, use_container_width=True)

                # Якщо кнопку щойно натиснули
                if st.session_state.get('generate_ai_now'):
                    with st.spinner("Генеруємо звіт за допомогою Gemini... 🧠"):
                        # Зберігаємо результат у пам'ять
                        st.session_state['ai_report_content'] = get_ai_analysis(metrics)
                    # Скидаємо прапорець, щоб більше не генерувати
                    st.session_state['generate_ai_now'] = False

                # Якщо звіт вже є у пам'яті (від попереднього натискання) — просто виводимо його
                if st.session_state.get('ai_report_content'):
                    st.markdown("---")
                    st.subheader("🤖 Висновок від ШІ (AI Flight Conclusion)")
                    st.info(st.session_state['ai_report_content'])

        finally:
            try:
                os.remove(tmp_path)
            except PermissionError:
                pass