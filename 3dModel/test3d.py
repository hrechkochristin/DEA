import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pymap3d as pm

# === ЗАВАНТАЖЕННЯ ===
df = pd.read_csv('../output_csv/combined_sensors_data.csv')

# === ВИБІР GPS ДАНИХ (найкраще) ===
df_gps = df[df['MSG_TYPE'] == 'GPS'].copy()

# якщо GPS мало — fallback на SIM
if df_gps.empty:
    df_gps = df[df['MSG_TYPE'] == 'SIM'].copy()

# прибираємо сміття
df_gps = df_gps[['TimeUS', 'Lat', 'Lng', 'Alt']].dropna()

# === ТОЧКА ВІДЛІКУ ===
lat0 = df_gps['Lat'].iloc[0]
lon0 = df_gps['Lng'].iloc[0]
alt0 = df_gps['Alt'].iloc[0]

# === ENU ===
e, n, u = pm.geodetic2enu(
    df_gps['Lat'].values,
    df_gps['Lng'].values,
    df_gps['Alt'].values,
    lat0, lon0, alt0
)

df_gps['E'] = e
df_gps['N'] = n
df_gps['U'] = u

# === ШВИДКІСТЬ ===
dt = df_gps['TimeUS'].diff() / 1_000_000
dist = np.sqrt(df_gps['E'].diff()**2 + df_gps['N'].diff()**2)

df_gps['speed'] = (dist / dt).fillna(0)

# === ГРАФІК ===
fig = go.Figure(data=[go.Scatter3d(
    x=df_gps['E'],
    y=df_gps['N'],
    z=df_gps['U'],
    mode='lines+markers',
    marker=dict(
        size=3,
        color=df_gps['speed'],
        colorscale='Plasma',
        colorbar=dict(title='Швидкість (м/с)'),
        opacity=0.8
    ),
    line=dict(
        width=5,
        color=df_gps['speed'],
        colorscale='Plasma'
    )
)])

fig.update_layout(
    title='3D траєкторія польоту',
    # scene=dict(
    #     xaxis_title='East (м)',
    #     yaxis_title='North (м)',
    #     zaxis_title='Up (м)',
    #     aspectmode='data'
    # )
    scene=dict(
        xaxis_title='East (м)',
        yaxis_title='North (м)',
        zaxis_title='Up (м)',
        aspectmode='data',
        camera=dict(
            eye=dict(x=4, y=1, z=4)
    )
)
)

# fig.show()
# fig.write_html("flight_plot.html")
fig.write_html("graphic.html", include_plotlyjs='cdn')