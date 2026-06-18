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

# Usamos MULTISELECT para poder elegir varios a la vez
if tipo_mercado == "Criptomonedas (Binance)":
    activos_seleccionados = st.sidebar.multiselect("Elige las criptomonedas:", ["BTC", "ETH", "SOL"], default=["BTC"])
else:
    activos_seleccionados = st.sidebar.multiselect("Elige los activos:", ["Barril Brent", "Oro"], default=["Barril Brent"])

# --- EJECUCIÓN DEL AGENTE ---
if st.sidebar.button("🔄 Analizar Mercado Ahora"):
    
    # Comprobamos que el usuario ha seleccionado al menos un activo
    if not activos_seleccionados:
        st.warning("⚠️ Por favor, selecciona al menos un activo en el panel lateral.")
    else:
        # Obtenemos el saldo general de la cuenta solo una vez
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

        # INICIA EL BUCLE: Repetimos este proceso por cada activo seleccionado
        for activo in activos_seleccionados:
            st.markdown("---") # Línea divisoria entre gráficos
            
            with st.spinner(f"Escaneando {activo}..."):
                try:
                    moneda_disponible = 0.0
                    
                    # 1. BIFURCACIÓN DE DATOS
                    if tipo_mercado == "Criptomonedas (Binance)":
                        symbol_api = f"{activo}/USDT"
                        moneda_disponible = balance.get(activo, {}).get('free', 0.0)
                        
                        bars = exchange.fetch_ohlcv(symbol_api, timeframe='1m', limit=100)
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

                    # 2. CALCULAR INDICADORES
                    df['SMA_5'] = df['Precio_EUR'].rolling(window=5).mean()
                    df['SMA_20'] = df['Precio_EUR'].rolling(window=20).mean()
                    df['RSI'] = ta.rsi(df['close'], length=14)
                    ultimo_rsi = df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 0.0

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

                    # 3. EL NUEVO GRÁFICO DE VELAS (PLOTLY)
                    st.subheader(f"📊 Gráfico de Velas y Medias: {activo}")
                    fig = go.Figure()

                    fig.add_trace(go.Candlestick(
                        x=df_grafico.index,
                        open=df_grafico['open'],
                        high=df_grafico['high'],
                        low=df_grafico['low'],
                        close=df_grafico['close'],
                        name='Cotización'
                    ))

                    fig.add_trace(go.Scatter(
                        x=df_grafico.index, y=df_grafico['SMA_5'],
                        line=dict(color='#FFA500', width=1.5), name='SMA 5'
                    ))

                    fig.add_trace(go.Scatter(
                        x=df_grafico.index, y=df_grafico['SMA_20'],
                        line=dict(color='#00BFFF', width=1.5), name='SMA 20'
                    ))

                    fig.update_layout(
                        template="plotly_dark",
                        margin=dict(l=0, r=0, t=30, b=0),
                        xaxis_rangeslider_visible=False,
                        height=450
                    )

                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 4. DECISIÓN DEL AGENTE
                    ultima_sma5 = df['SMA_5'].iloc[-1]
                    ultima_sma20 = df['SMA_20'].iloc[-1]
                    previa_sma5 = df['SMA_5'].iloc[-2]
                    previa_sma20 = df['SMA_20'].iloc[-2]
                    
                    if previa_sma5 <= previa_sma20 and ultima_sma5 > ultima_sma20 and ultimo_rsi < 70:
                        st.success(f"🟢 SEÑAL DE COMPRA: El Agente Lepan recomienda comprar {activo}.")
                    elif previa_sma5 >= previa_sma20 and ultima_sma5 < ultima_sma20:
                        st.error(f"🔴 SEÑAL DE VENTA: El Agente Lepan recomienda vender {activo}.")
                    else:
                        st.info(f"⚪ MERCADO ESTABLE: El Agente Lepan vigila {activo} a la espera.")

                except Exception as e:
                    st.error(f"Error en el análisis de {activo}: {e}")
                    
else:
    st.info("👈 Configura tu mercado en el panel lateral y haz clic en 'Analizar Mercado Ahora'.")
