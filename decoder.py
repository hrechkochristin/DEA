from pymavlink import DFReader
import pandas as pd
import os

logfile = r'test_task_challenge\test_task_challenge\00000001.BIN'
output_folder = "output_csv"
os.makedirs(output_folder, exist_ok=True)

target_messages = {'GPS', 'IMU', 'BARO', 'SIM'}

# Які поля очікуємо в кожному типі повідомлень
required_attributes = {
    'GPS': ['TimeUS', 'Lat', 'Lng'],
    'IMU': ['TimeUS'],
    'BARO': ['TimeUS'],
    'SIM': ['TimeUS']
}


def validate_bin_file(filepath: str):
    # 1. Перевірка існування файлу
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Файл не знайдено: {filepath}")

    # 2. Перевірка розширення
    _, ext = os.path.splitext(filepath)
    if ext.upper() != '.BIN':
        raise ValueError(f"Неправильне розширення файлу: {ext}. Очікується .BIN")


def validate_message_attributes(msg_type: str, msg_dict: dict, required_map: dict):
    """
    Перевіряє, чи є в повідомленні всі потрібні атрибути.
    Повертає список відсутніх полів.
    """
    required_fields = required_map.get(msg_type, [])
    missing_fields = [field for field in required_fields if field not in msg_dict]
    return missing_fields


try:
    validate_bin_file(logfile)
    print("Файл пройшов перевірку розширення та існування.")

    dfreader = DFReader.DFReader_binary(logfile)

    combined_data = []
    invalid_messages = []

    print("Reading log file...")

    while True:
        m = dfreader.recv_msg()
        if m is None:
            break

        msg_type = m.get_type()

        if msg_type in target_messages:
            msg_dict = m.to_dict()

            # Перевірка атрибутів
            missing = validate_message_attributes(msg_type, msg_dict, required_attributes)

            if missing:
                invalid_messages.append({
                    'MSG_TYPE': msg_type,
                    'missing_fields': missing,
                    'raw_data': msg_dict
                })
                continue

            msg_dict['MSG_TYPE'] = msg_type
            combined_data.append(msg_dict)

    df_final = pd.DataFrame(combined_data)

    if not df_final.empty:
        if 'TimeUS' in df_final.columns:
            df_final = df_final.sort_values(by='TimeUS').reset_index(drop=True)
        else:
            print("Увага: колонка TimeUS відсутня, сортування пропущено.")

        df_final = df_final.ffill()

        cols = [c for c in ['TimeUS', 'MSG_TYPE'] if c in df_final.columns] + \
               [c for c in df_final.columns if c not in ['TimeUS', 'MSG_TYPE']]
        df_final = df_final[cols]

        output_path = os.path.join(output_folder, 'combined_sensors_data.csv')
        df_final.to_csv(output_path, index=False)

        print(f"\n✅ Готово! Збережено {len(df_final)} записів.")
        print(f"📂 Файл знаходиться тут: {output_path}")

        print("\nРозподіл повідомлень:")
        print(df_final['MSG_TYPE'].value_counts())

    else:
        print("❌ Валідних повідомлень не знайдено.")

    # Звіт про проблемні повідомлення
    if invalid_messages:
        print(f"\n⚠ Знайдено {len(invalid_messages)} повідомлень без потрібних атрибутів:")
        for i, bad_msg in enumerate(invalid_messages[:10], start=1):
            print(f"{i}. Тип: {bad_msg['MSG_TYPE']}, відсутні поля: {bad_msg['missing_fields']}")
        if len(invalid_messages) > 10:
            print(f"... і ще {len(invalid_messages) - 10} повідомлень")
    else:
        print("\nУсі оброблені повідомлення мають потрібні атрибути.")

except Exception as e:
    print(f"❌ Помилка: {e}")