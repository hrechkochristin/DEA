from flask import Flask, request, render_template, send_file
import os
import uuid
from pymavlink import DFReader
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output_csv"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# 🔧 Обробка лог-файлу
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


# 🌐 Головна сторінка
@app.route("/")
def index():
    return render_template("index.html")


# 📤 Завантаження файлу
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")

    if not file or file.filename == "":
        return "❌ Файл не завантажено"

    # ✅ Генеруємо унікальне ім’я
    ext = os.path.splitext(file.filename)[1] or ".bin"
    filename = str(uuid.uuid4()) + ext
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    file.save(filepath)

    # 🔥 Обробка
    output_path, count = process_log_file(filepath)

    if output_path:
        return f"""
        <h3>✅ Оброблено {count} записів</h3>
        <a href="/download?path={output_path}">📥 Завантажити CSV</a>
        <br><br>
        <a href="/">⬅️ Назад</a>
        """

    return """
    ❌ Дані не знайдені<br><br>
    <a href="/">⬅️ Назад</a>
    """


# 📥 Завантаження CSV
@app.route("/download")
def download():
    path = request.args.get("path")

    if not path or not os.path.exists(path):
        return "❌ Файл не знайдено"

    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)