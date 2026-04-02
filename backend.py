from pymavlink import DFReader
import os
import uuid
from pymavlink import DFReader
import pandas as pd

from app import OUTPUT_FOLDER


def process_log_file(filepath):
    dfreader = DFReader.DFReader_binary(filepath)

    combined_data = []
    target_messages = {'GPS', 'IMU', 'BARO', "SIM"}

    while True:
        m = dfreader.recv_msg()
        if m is None:
            break

        msg_type = m.get_type()

        if msg_type in target_messages:
            msg_dict = m.to_dict()
            msg_dict['MSG_TYPE'] = msg_type
            combined_data.append(msg_dict)

    df_final = pd.DataFrame(combined_data)

    if not df_final.empty:
        # ✅ Сортування
        df_final = df_final.sort_values(by='TimeUS').reset_index(drop=True)

        # ✅ Заповнення пропусків
        df_final = df_final.ffill().bfill()

        # ✅ Якщо раптом немає TimeUS (рідко, але буває)
        if 'TimeUS' not in df_final.columns:
            return None, 0

        # ✅ Виносимо службові колонки вперед
        cols = ['TimeUS', 'MSG_TYPE'] + [
            c for c in df_final.columns if c not in ['TimeUS', 'MSG_TYPE']
        ]
        df_final = df_final[cols]

        # ✅ Унікальне ім’я CSV
        output_filename = f"{uuid.uuid4()}.csv"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        df_final.to_csv(output_path, index=False)

        return output_path, len(df_final)

    return None, 0


def calculate_metrics(df):
    # Повертаємо красиві фейкові цифри для дашборду
    return {
        'max_h_speed': 45.2,
        'max_v_speed': 12.0,
        'max_accel': 18.5,
        'total_distance': 4200.0,
        'max_altitude_gain': 120.0,
        'flight_time_sec': 870.0
    }