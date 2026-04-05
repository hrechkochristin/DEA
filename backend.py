from pymavlink import DFReader
import os
import uuid
import pandas as pd

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output_csv"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Які поля очікуємо в кожному типі повідомлень
required_attributes = {
    'GPS': ['TimeUS', 'Lat', 'Lng'],
    'IMU': ['TimeUS'],
    'BARO': ['TimeUS'],
    'SIM': ['TimeUS']
}

def validate_bin_file(filepath):
    # перевірка існування
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Файл не знайдено: {filepath}")

    # перевірка розширення файлу
    _, ext = os.path.splitext(filepath)
    if ext.lower() != '.bin':
        raise ValueError(f"Очікується .bin файл, отримано: {ext}")

    # спроба відкрити файл
    try:
        reader = DFReader.DFReader_binary(filepath)
        msg = reader.recv_msg()
        if msg is None:
            raise ValueError("Файл порожній або не містить валідних повідомлень")
    except Exception as e:
        raise ValueError(f"Файл не є валідним Ardupilot BIN: {str(e)}")


def validate_message_attributes(msg_type: str, msg_dict: dict, required_map: dict):
    # Перевіряє, чи є в повідомленні всі потрібні атрибути.
    # Повертає список відсутніх полів.
    required_fields = required_map.get(msg_type, [])
    missing_fields = [field for field in required_fields if field not in msg_dict]
    return missing_fields

# обробка отриманого файлу
def process_log_file(filepath):
    validate_bin_file(filepath)

    dfreader = DFReader.DFReader_binary(filepath)

    combined_data = []
    # збираємо тільки потрібну інформацію
    target_messages = {'GPS', 'IMU', 'BARO', 'SIM'}

    while True:
        m = dfreader.recv_msg()
        if m is None:
            break

        msg_type = m.get_type()

        if msg_type in target_messages:
            msg_dict = m.to_dict()

            # перевірка полів
            missing = validate_message_attributes(
                msg_type, msg_dict, required_attributes
            )

            if missing:
                continue

            msg_dict['MSG_TYPE'] = msg_type
            combined_data.append(msg_dict)

    # якщо взагалі нічого валідного
    if not combined_data:
        raise ValueError("Не знайдено жодного валідного повідомлення")

    df_final = pd.DataFrame(combined_data)

    # перевірка присутності ключового поля
    if 'TimeUS' not in df_final.columns:
        raise ValueError("Відсутній TimeUS у даних")

    # сортування по часовому штампу
    df_final = df_final.sort_values(by='TimeUS').reset_index(drop=True)

    # збір даних в кучу
    df_final = df_final.ffill().bfill()

    # створення файлу CSV для збереження отриманих даних
    output_filename = f"{uuid.uuid4()}.csv"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    df_final.to_csv(output_path, index=False)

    return output_path, len(df_final)

# функція з математ. обрахунками
def calculate_metrics(df):
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    import pymap3d as pm

    # зчитування файлу
    if isinstance(df, str):
        df = pd.read_csv(df)

    # якщо пусто - по нулям
    if df is None or df.empty:
        return {
            'max_h_speed': 0,
            'max_v_speed': 0,
            'max_accel': 0,
            'total_distance': 0,
            'max_altitude_gain': 0,
            'flight_time_sec': 0
        }

    # витаскуємо інформацію з GPS
    df_gps = df[df['MSG_TYPE'] == 'GPS'].copy()
    # якщо немає - берем з SIM
    if df_gps.empty:
        df_gps = df[df['MSG_TYPE'] == 'SIM'].copy()
    # якщо взагалі нічого немає - по нулям
    if df_gps.empty:
        return {
            'max_h_speed': 0,
            'max_v_speed': 0,
            'max_accel': 0,
            'total_distance': 0,
            'max_altitude_gain': 0,
            'flight_time_sec': 0
        }

    df_gps = df_gps[['TimeUS', 'Lat', 'Lng', 'Alt']].dropna().copy()
    df_gps = df_gps.sort_values('TimeUS').reset_index(drop=True)

    # якщо даних недостатньо для обрахунку - по нулям
    if len(df_gps) < 2:
        return {
            'max_h_speed': 0,
            'max_v_speed': 0,
            'max_accel': 0,
            'total_distance': 0,
            'max_altitude_gain': 0,
            'flight_time_sec': 0
        }

    # ТОЧКА ВІДЛІКУ
    lat0 = df_gps.loc[0, 'Lat']
    lon0 = df_gps.loc[0, 'Lng']
    alt0 = df_gps.loc[0, 'Alt']
    # ENU
    e, n, u = pm.geodetic2enu(
        df_gps['Lat'].to_numpy(),
        df_gps['Lng'].to_numpy(),
        df_gps['Alt'].to_numpy(),
        lat0, lon0, alt0
    )

    df_gps['E'] = e
    df_gps['N'] = n
    df_gps['U'] = u

    # ЧАС
    dt = df_gps['TimeUS'].diff() / 1_000_000.0
    dt = dt.replace(0, np.nan)

    # ВІДСТАНІ
    dE = df_gps['E'].diff()
    dN = df_gps['N'].diff()
    dU = df_gps['U'].diff()

    horizontal_dist = np.sqrt(dE**2 + dN**2)
    total_dist = np.sqrt(dE**2 + dN**2 + dU**2)

    # ШВИДКОСТІ
    df_gps['h_speed'] = (horizontal_dist / dt).fillna(0)
    df_gps['v_speed'] = (dU / dt).fillna(0)
    df_gps['speed'] = (total_dist / dt).fillna(0)

    # ПРИСКОРЕННЯ
    df_gps['accel'] = df_gps['speed'].diff() / dt
    df_gps['accel'] = df_gps['accel'].fillna(0)

    #  МЕТРИКИ 
    max_h_speed = float(df_gps['h_speed'].max())
    max_v_speed = float(df_gps['v_speed'].abs().max())
    max_accel = float(df_gps['accel'].abs().max())

    total_distance = float(total_dist.fillna(0).sum())

    altitude_gain = df_gps['U'].max() - df_gps['U'].min()
    max_altitude_gain = float(altitude_gain)

    flight_time_sec = float(
        (df_gps['TimeUS'].iloc[-1] - df_gps['TimeUS'].iloc[0]) / 1_000_000.0
    )
    
    #  Результат
    return {
        'max_h_speed': round(max_h_speed, 2),
        'max_v_speed': round(max_v_speed, 2),
        'max_accel': round(max_accel, 2),
        'total_distance': round(total_distance, 2),
        'max_altitude_gain': round(max_altitude_gain, 2),
        'flight_time_sec': round(flight_time_sec, 2)
    }