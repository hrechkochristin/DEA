import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import pymap3d as pm
import tempfile
import os
from ai_asisstant import get_ai_analysis

# --- НАЛАШТУВАННЯ ІНТЕРФЕЙСУ ---
st.set_page_config(page_title="BEST Telemetry Analyzer", layout="wide")

# --- БЕЗПЕЧНИЙ ІМПОРТ БЕКЕНДУ (Захист від помилок) ---
try:
    from backend import process_log_file, calculate_metrics
    backend_ready = True
except ImportError:
    backend_ready = False
    
    def process_log_file(filepath):
        # 1. Створюємо фейкові дані
        t = np.linspace(0, 10, 500)
        df = pd.DataFrame({
            'MSG_TYPE': ['GPS'] * 500,
            'TimeUS': t * 1_000_000,
            'Lat': 49.8397 + np.cumsum(np.random.randn(500) * 0.0001),
            'Lng': 24.0297 + np.cumsum(np.random.randn(500) * 0.0001),
            'Alt': 100 + np.abs(np.cumsum(np.random.randn(500) * 2))
        })
        
        # 2. Імітуємо збереження в CSV (як це робитиме реальний бекенд)
        temp_csv = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        df.to_csv(temp_csv.name, index=False)
        
        # 3. ПОВЕРТАЄМО 2 ЗНАЧЕННЯ, як очікує рядок 74
        return temp_csv.name, len(df)

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
    st.title("🚁 BEST Telemetry")
    st.markdown("---")
    
    if not backend_ready:
        st.warning("⚠️ Увімкнено Демо-режим. Функції бекенду ще не знайдено, використовуються фейкові дані.")
    
    st.subheader("Дані польоту")
    uploaded_file = st.file_uploader("Завантажте лог-файл (.bin)", type=["bin", "log"])

    analyze_btn = st.button("✦ Огляд від ШІ", use_container_width=True)

    if analyze_btn:
        if uploaded_file:
            st.session_state['run_ai'] = True
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

                # --- ПІДГОТОВКА ДАНИХ ДЛЯ 3D ГРАФІКА ---
                df_gps = df[df['MSG_TYPE'] == 'GPS'].copy()
                if df_gps.empty:
                    df_gps = df[df['MSG_TYPE'] == 'SIM'].copy()
                    df_gps = df_gps[['TimeUS', 'Lat', 'Lng', 'Alt']].dropna()
                if not df_gps.empty:
                    lat0, lon0, alt0 = df_gps['Lat'].iloc[0], df_gps['Lng'].iloc[0], df_gps['Alt'].iloc[0]
                    e, n, u = pm.geodetic2enu(
                        df_gps['Lat'].values, df_gps['Lng'].values, df_gps['Alt'].values,
                        lat0, lon0, alt0
                    )
                    df_gps['E'], df_gps['N'], df_gps['U'] = e, n, u

                    dt = df_gps['TimeUS'].diff() / 1_000_000
                    dist = np.sqrt(df_gps['E'].diff()**2 + df_gps['N'].diff()**2)
                    df_gps['speed'] = (dist / dt).fillna(0)

                    # --- 3D ВІЗУАЛІЗАЦІЯ ---
                    st.subheader("Просторова траєкторія (система ENU)")
                    
                    fig = go.Figure(data=[go.Scatter3d(
                        x=df_gps['E'], y=df_gps['N'], z=df_gps['U'],
                        mode='lines+markers',
                        marker=dict(
                            size=3, color=df_gps['speed'], colorscale='Plasma',
                            colorbar=dict(title='Швидкість (м/с)'), opacity=0.8
                        ),
                        line=dict(
                            width=5, color=df_gps['speed'], colorscale='Plasma'
                        )
                    )])

                    fig.update_layout(
                        scene=dict(
                            xaxis_title='East (Схід, м)', yaxis_title='North (Північ, м)', zaxis_title='Up (Висота, м)',
                            aspectmode='data', camera=dict(eye=dict(x=4, y=1, z=4))
                        ),
                        margin=dict(l=0, r=0, b=0, t=0), height=600
                    )

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Не знайдено GPS або SIM даних для побудови траєкторії.")

                # --- СЕКЦІЯ AI АНАЛІЗУ ---
                # Перевіряємо, чи була натиснута кнопка в сайдбарі
                if st.session_state.get('run_ai'):
                    st.markdown("---")
                    st.subheader("✦ Висновок від ШІ")
                    
                    # Створюємо контейнер для гарного візуального виділення
                    with st.container():
                        with st.spinner("ШІ аналізує телеметрію та шукає аномалії..."):
                            # Тут ми готуємо текст для асистента на основі реальних метрик
                            # (Це закриває вимогу про інтеграцію LLM для аналізу )
                            
                            # Поки бекенд ще в розробці, зробимо змістовну заглушку:
                            #ai_report = f"""
                            #**Аналіз місії:**
                            #* **Динаміка:** Максимальна швидкість ({metrics.get('max_h_speed')} м/с) стабільна. 
                            #* **Аномалії:** Різких втрат висоти або критичних перевантажень не зафіксовано.
                            #* **Рекомендація:** Політ пройшов успішно. Всі системи працювали в штатному режимі.
                            #"""
                            
                            ai_report = get_ai_analysis(metrics)
                            st.info(ai_report)

        finally:
            try:
                os.remove(tmp_path)
            except PermissionError:
                pass