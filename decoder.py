from pymavlink import DFReader
import pandas as pd
from collections import defaultdict

logfile = r'E:\proj\python\PythonProject\00000001.BIN'

dfreader = DFReader.DFReader_binary(logfile)

# Збираємо всі дані
data = defaultdict(list)

while True:
    m = dfreader.recv_msg()
    if m is None:
        break
    msg_type = m.get_type()
    # Беремо тільки корисні повідомлення (можеш додати інші)
    if msg_type in ['IMU', 'GPS', 'ATT', 'CTUN', 'SIM', 'VIBE', 'BARO', 'MODE', 'GPA', 'PARM']:
        data[msg_type].append(m.to_dict())

# Створюємо DataFrame'и
dfs = {k: pd.DataFrame(v) for k, v in data.items() if v}

# Вивід
for name, df in dfs.items():
    print(f"✅ {name:6} → {len(df):5} записів | частота ≈ {round(1_000_000 / df['TimeUS'].diff().mean(), 1)} Гц")
    print(df.columns.tolist()[:12], "...\n")  # перші 12 колонок

# Зберігаємо всі в CSV (зручно для аналізу)
for name, df in dfs.items():
    df.to_csv(f'{name}_data.csv', index=False)

print("🎉 Всі дані збережено в CSV-файли!")