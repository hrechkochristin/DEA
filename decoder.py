from pymavlink import DFReader
import pandas as pd
import os

logfile = r'test_task_challenge\test_task_challenge\00000001.BIN'
output_folder = "output_csv"
os.makedirs(output_folder, exist_ok=True)

dfreader = DFReader.DFReader_binary(logfile)

# Список для зберігання всіх повідомлень разом
combined_data = []

# Визначаємо, які саме типи повідомлень нам потрібні
target_messages = {'GPS', 'IMU', 'BARO', "SIM"}

print("Reading log file...")

while True:
    m = dfreader.recv_msg()
    if m is None:
        break

    msg_type = m.get_type()

    if msg_type in target_messages:
        # Отримуємо словник даних повідомлення
        msg_dict = m.to_dict()
        # Додаємо тип повідомлення в колонку, щоб розуміти, звідки дані
        msg_dict['MSG_TYPE'] = msg_type
        combined_data.append(msg_dict)

# Створюємо один загальний DataFrame
df_final = pd.DataFrame(combined_data)

# Перевіряємо, чи є дані
if not df_final.empty:
    # 1. Сортуємо за часом
    df_final = df_final.sort_values(by='TimeUS').reset_index(drop=True)

    # 2. Заповнюємо пропуски останніми значеннями
    df_final = df_final.ffill()

    # 2. Виносимо службові колонки на початок для зручності
    cols = ['TimeUS', 'MSG_TYPE'] + [c for c in df_final.columns if c not in ['TimeUS', 'MSG_TYPE']]
    df_final = df_final[cols]

    # Збереження
    output_path = os.path.join(output_folder, 'combined_sensors_data.csv')
    df_final.to_csv(output_path, index=False)

    print(f"✅ Готово! Збережено {len(df_final)} записів.")
    print(f"📂 Файл знаходиться тут: {output_path}")

    # Вивід статистики по датчиках
    print("\nРозподіл повідомлень:")
    print(df_final['MSG_TYPE'].value_counts())
else:
    print("❌ Повідомлень вказаних типів не знайдено.")