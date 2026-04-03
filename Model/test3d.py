def draw_trajectory(df):
    import numpy as np
    import plotly.graph_objects as go
    import pymap3d as pm

    # Вибір джерела
    msg_types = set(df['MSG_TYPE'].unique())

    # Приорітетність: XKF1/NKF1 > SIM > GPS
    if 'XKF1' in msg_types or 'NKF1' in msg_types:
        use_mode = 'EKF'
    elif 'SIM' in msg_types:
        use_mode = 'SIM'
    else:
        use_mode = 'GPS'

    print(f"Використовується джерело: {use_mode}")

    #  ОБРОБКА
    # Якщо EKF - супер, можем так і брати
    if use_mode == 'EKF':
        df_data = df[df['MSG_TYPE'].isin(['XKF1', 'NKF1'])].copy()
        df_data = df_data[['TimeUS', 'PN', 'PE', 'PD']].dropna()

        df_data['E'] = df_data['PE']
        df_data['N'] = df_data['PN']
        df_data['U'] = -df_data['PD']

    # Якщо SIM це 50/50 - треба дивитись що є
    elif use_mode == 'SIM':
        df_data = df[df['MSG_TYPE'] == 'SIM'].copy()
        # перевірка структури
        # Якщо є точки - по ним і будуємо
        if {'X', 'Y', 'Z'}.issubset(df_data.columns):
            df_data = df_data[['TimeUS', 'X', 'Y', 'Z']].dropna()
            df_data['E'] = df_data['X']
            df_data['N'] = df_data['Y']
            df_data['U'] = -df_data['Z']

        # Якщо є тільки 'Lat', 'Lng', 'Alt' - робимо конвертацію WGS-84 -> ENU
        elif {'Lat', 'Lng', 'Alt'}.issubset(df_data.columns):
            df_data = df_data[['TimeUS', 'Lat', 'Lng', 'Alt']].dropna()

            lat0, lon0, alt0 = df_data.iloc[0][['Lat','Lng','Alt']]
            # З "широта-висота-довгота" в "east-north-up"
            e, n, u = pm.geodetic2enu(
                df_data['Lat'].values,
                df_data['Lng'].values,
                df_data['Alt'].values,
                lat0, lon0, alt0
            )

            df_data['E'], df_data['N'], df_data['U'] = e, n, u

        else:
            raise ValueError("SIM формат не підтримується")

    # Тут лишається тільки конвертація WGS-84 -> ENU
    else:
        df_data = df[df['MSG_TYPE'] == 'GPS'].copy()
        df_data = df_data[['TimeUS', 'Lat', 'Lng', 'Alt']].dropna()

        lat0, lon0, alt0 = df_data.iloc[0][['Lat','Lng','Alt']]

        e, n, u = pm.geodetic2enu(
            df_data['Lat'].values,
            df_data['Lng'].values,
            df_data['Alt'].values,
            lat0, lon0, alt0
        )

        df_data['E'], df_data['N'], df_data['U'] = e, n, u

    # ОБРОБКА ШВИДКОСТІ
    # Час
    dt = df_data['TimeUS'].diff() / 1_000_000
    # Відстань
    dist = np.sqrt(
        df_data['E'].diff()**2 +
        df_data['N'].diff()**2 +
        df_data['U'].diff()**2
    )
    # Швидкість
    df_data['speed'] = (dist / dt).fillna(0)
    df_data['speed'] = df_data['speed'].replace([np.inf, -np.inf], 0).fillna(0)

    #  ГРАФІК
    fig = go.Figure(data=[go.Scatter3d(
        x=df_data['E'],
        y=df_data['N'],
        z=df_data['U'],
        mode='lines',
        line=dict(
            width=6,
            color=df_data['speed'],
            colorscale='Plasma'
        )
    )])

    return fig