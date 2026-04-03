import google.generativeai as genai
from config import API_KEY

def get_ai_analysis(metrics):
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = f"""
    Ти — експертний асистент з аналізу телеметрії БПЛА. 
    Проаналізуй наступні метрики польоту Ardupilot та надай короткий технічний висновок (до 5 речень).
    
    Метрики:
    - Макс. гориз. швидкість: {metrics['max_h_speed']} м/с
    - Макс. верт. швидкість: {metrics['max_v_speed']} м/с
    - Макс. прискорення: {metrics['max_accel']} м/с²
    - Загальна дистанція: {metrics['total_distance']} м
    - Макс. набір висоти: {metrics['max_altitude_gain']} м
    - Тривалість: {metrics['flight_time_sec']} сек
    
    Зверни особливу увагу на:
    1. Виявлення різких втрат висоти або перевищення швидкості.
    2. Аномальні показники прискорення.
    3. Загальну оцінку стабільності місії.
    
    Пиши українською мовою, лаконічно та професійно.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Помилка ШІ-аналізу: {str(e)}"