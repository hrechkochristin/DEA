from pymavlink import DFReader
import pandas as pd
from collections import defaultdict
import os  # <-- для роботи з папками

logfile = r'test_task_challenge\test_task_challenge\00000001.BIN'

dfreader = DFReader.DFReader_binary(logfile)

# Папка для CSV
output_folder = "output_csv"
os.makedirs(output_folder, exist_ok=True)  # створює папку, якщо нема

# Збираємо всі дані
data = defaultdict(list)

while True:
    m = dfreader.recv_msg()
    if m is None:
        break
    msg_type = m.get_type()
    # Беремо тільки корисні повідомлення
    if msg_type in ['IMU', 'GPS', 'ATT', 'CTUN', 'SIM', 'VIBE', 'BARO', 'MODE', 'GPA', 'PARM']:
        data[msg_type].append(m.to_dict())

# Створюємо DataFrame'и
dfs = {k: pd.DataFrame(v) for k, v in data.items() if v}

# Вивід
for name, df in dfs.items():
    print(f"✅ {name:6} → {len(df):5} записів | частота ≈ {round(1_000_000 / df['TimeUS'].diff().mean(), 1)} Гц")
    print(df.columns.tolist()[:12], "...\n")  # перші 12 колонок

# Зберігаємо всі в CSV у спеціальній папці
for name, df in dfs.items():
    filepath = os.path.join(output_folder, f'{name}_data.csv')
    df.to_csv(filepath, index=False)

print(f"🎉 Всі дані збережено в папку '{output_folder}'!")