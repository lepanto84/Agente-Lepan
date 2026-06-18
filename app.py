import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import yfinance as yf
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Agente Lepan", page_icon="📈", layout="wide")
st.title("🤖 Agente Lepan - Panel de Inversión Múltiple")

# --- CREDENCIALES ---
API_KEY = os.environ.get('API_KEY', 'MDI5M4OeE9ss3Z5czc3bw7Rs8iqTgkOacnbljANl5O2KzUxZ7RB1KDgELAEwM7cr')
API_SECRET = os.environ.get('API_SECRET', 'c9NtfZAMrqUzbFYTYNbiRrVzdpngmoQyFITyJySvXOeYdvdB1aH9DPk9u8NMOVj3')
TIPO_CAMBIO_EUR = 0.93

# --- CONEXIÓN BINANCE ---
@st.cache_resource 
def iniciar_conexion():
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(True)
    return exchange

# --- MENÚ LATERAL INTERACTIVO ---
st.sidebar.header("⚙️ Configuración del Mercado")
tipo_mercado = st.sidebar.radio("Fuente de datos:", ["Criptomonedas (Binance)", "Materias Primas (Yahoo)"])

if tipo_mercado == "Criptomonedas (Binance)":
    activos_seleccionados = st.sidebar.multiselect("Elige las criptomonedas:", ["BTC", "ETH", "SOL"], default=["BTC"])
else:
    activos_seleccionados = st.sidebar.multiselect("Elige los activos:", ["Barril Brent", "Oro"], default=["Barril Brent"])

# --- EJECUCIÓN DEL AGENTE ---
if st.sidebar.button("🔄 Analizar Mercado Ahora"):
    
    if not activos_seleccionados:
        st.warning("⚠️ Por favor, selecciona al menos un activo en el panel lateral.")
    else:
        saldo_eur = 0.0
        exchange = None
        balance = {}
        
        if tipo_mercado == "Criptomonedas (Binance)":
            exchange = iniciar_conexion()
            try:
                balance = exchange.fetch_balance()
                saldo_eur = balance.get('USDT', {}).get('free', 0.0) * TIPO_CAMBIO_EUR
            except Exception as e:
                st.error(f"Error al conectar con la cuenta: {e}")

        for activo in activos_seleccionados:
            st.markdown("---") 
            
            with st.spinner(f"Escaneando {activo}..."):
                try:
                    moneda_disponible = 0.0
                    
                    # 1. BIFURCACIÓN DE DATOS
                    if tipo_mercado == "Criptomonedas (Binance)":
                        symbol_api = f"{activo}/USDT"
                        moneda_disponible = balance.get(activo, {}).get('free', 0.0)
                        
                        # IMPORTANTE: Subimos el límite a 200 para poder calcular la SMA de 100
                        bars = exchange.fetch_ohlcv(symbol_api, timeframe='1m', limit=200)
                        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df.set_index('fecha', inplace=True)
                        
                        df['open'] = df['open'] * TIPO_CAMBIO_EUR
                        df['high'] = df['high'] * TIPO_CAMBIO_EUR
                        df['low'] = df['low'] * TIPO_CAMBIO_EUR
                        df['close'] = df['close'] * TIPO_CAMBIO_EUR
                        df['Precio_EUR'] = df['close']
                        
                    else:
                        symbol_api = "BZ=F" if activo == "Barril Brent" else "GC=F"
                        ticker = yf.Ticker(symbol_api)
                        df = ticker.history(period="5d", interval="5m")
                        
                        df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
                        df.index = df.index.tz_localize(None) 
                        df['Precio_EUR'] = df['close'] 

                    # 2. CEREBRO QUANT: CÁLCULO DE INDICADORES AVANZADOS
                    # Medias Móviles Clásicas
                    df['SMA_5'] = df['Precio_EUR'].rolling(window=5).mean()
                    df['SMA_20'] = df['Precio_EUR'].rolling(window=20).mean()
                    # Filtro 1: Tendencia Principal
                    df['SMA_100'] = df['Precio_EUR'].rolling(window=100).mean() 
                    
                    # Filtro 2: Fuerza Relativa
                    df['RSI'] = ta.rsi(df['close'], length=14)
                    ultimo_rsi = df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 0.0
                    
                    # Filtro 3: Anatomía de la Vela y Volumen
                    df['Vela_Verde'] = df['close'] > df['open']
                    df['Volumen_Promedio'] = df['volume'].rolling(window=20).mean()

                    # --- DIBUJAR EL PANEL VISUAL ---
                    col1, col2, col3 = st.columns(3)
                    if tipo_mercado == "Criptomonedas (Binance)":
                        col1.metric("💰 Saldo Total", f"{saldo_eur:.2f} €")
                        col2.metric(f"🪙 {activo} en Cartera", f"{moneda_disponible:.4f}")
                    else:
                        col1.metric("🌐 Mercado Tradicional", "Materias Primas")
                        col2.metric("📦 Activo Analizado", activo)
                        
                    col3.metric("🌡️ RSI Actual", f"{ultimo_rsi:.2f}")

                    df_grafico = df.dropna().copy()

                    # 3. EL NUEVO GRÁFICO DE VELAS CON TENDENCIA MACRO
                    st.subheader(f"📊 Análisis Técnico: {activo}")
                    fig = go.Figure()

                    # Capa 1: Velas
                    fig.add_trace(go.Candlestick(
                        x=df_grafico.index,
                        open=df_grafico['open'], high=df_grafico['high'], low=df_grafico['low'], close=df_grafico['close'],
                        name='Cotización'
                    ))

                    # Capa 2: Media Rápida
                    fig.add_trace(go.Scatter(
                        x=df_grafico.index, y=df_grafico['SMA_5'],
                        line=dict(color='#FFA500', width=1.5), name='SMA 5'
                    ))

                    # Capa 3: Media Lenta
                    fig.add_trace(go.Scatter(
                        x=df_grafico.index, y=df_grafico['SMA_20'],
                        line=dict(color='#00BFFF', width=1.5), name='SMA 20'
                    ))
                    
                    # Capa 4: La Gran Tendencia (SMA 100)
                    fig.add_trace(go.Scatter(
                        x=df_grafico.index, y=df_grafico['SMA_100'],
                        line=dict(color='#8A2BE2', width=2.5, dash='dot'), name='SMA 100 (Tendencia)'
                    ))

                    fig.update_layout(
                        template="plotly_dark",
                        margin=dict(l=0, r=0, t=30, b=0),
                        xaxis_rangeslider_visible=False,
                        height=450
                    )

                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 4. DECISIÓN DEL AGENTE (DOBLE CONFIRMACIÓN)
                    # Extracción de los datos del último minuto
                    precio_actual = df['Precio_EUR'].iloc[-1]
                    sma100_actual = df['SMA_100'].iloc[-1]
                    vela_es_verde = df['Vela_Verde'].iloc[-1]
                    volumen_actual = df['volume'].iloc[-1]
                    volumen_promedio = df['Volumen_Promedio'].iloc[-1]
                    
                    ultima_sma5 = df['SMA_5'].iloc[-1]
                    ultima_sma20 = df['SMA_20'].iloc[-1]
                    previa_sma5 = df['SMA_5'].iloc[-2]
                    previa_sma20 = df['SMA_20'].iloc[-2]
                    
                    # Lógica estricta
                    cruce_alcista = previa_sma5 <= previa_sma20 and ultima_sma5 > ultima_sma20
                    cruce_bajista = previa_sma5 >= previa_sma20 and ultima_sma5 < ultima_sma20
                    tendencia_alcista = precio_actual > sma100_actual
                    hay_volumen = volumen_actual > volumen_promedio
                    
                    if cruce_alcista and ultimo_rsi < 70 and vela_es_verde and hay_volumen and tendencia_alcista:
                        st.success(f"🟢 SEÑAL DE COMPRA FUERTE: {activo}. Cruce alcista validado por vela verde, alto volumen y a favor de la tendencia principal.")
                    elif cruce_bajista:
                        st.error(f"🔴 SEÑAL DE VENTA: El Agente Lepan recomienda vender {activo} por cruce bajista.")
                    else:
                        st.info(f"⚪ MERCADO SIN CONFIRMACIÓN: El Agente Lepan exige más pruebas antes de operar {activo}.")

                except Exception as e:
                    st.error(f"Error en el análisis de {activo}: {e}")
                    
else:
    st.info("👈 Configura tu mercado en el panel lateral y haz clic en 'Analizar Mercado Ahora'.")
