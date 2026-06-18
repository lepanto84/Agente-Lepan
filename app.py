import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import yfinance as yf
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Agente Lepan", page_icon="📈", layout="wide")
st.title("🤖 Agente Lepan - Panel de Inversión")

# --- CREDENCIALES ---
# Usamos las variables ocultas de Render si existen, o tus claves de Testnet por defecto
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
    activo_seleccionado = st.sidebar.selectbox("Elige la criptomoneda:", ["BTC", "ETH", "SOL"])
    symbol_api = f"{activo_seleccionado}/USDT" # Binance Testnet usa USDT
else:
    activo_seleccionado = st.sidebar.selectbox("Elige el activo:", ["Barril Brent", "Oro"])
    symbol_api = "BZ=F" if activo_seleccionado == "Barril Brent" else "GC=F"

# --- EJECUCIÓN DEL AGENTE ---
if st.sidebar.button("🔄 Analizar Mercado Ahora"):
    
    with st.spinner(f"Escaneando {activo_seleccionado}..."):
        try:
            # Variables base para evitar errores
            saldo_eur = 0.0
            moneda_disponible = 0.0
            
            # 1. BIFURCACIÓN DE DATOS (BINANCE vs YAHOO)
            if tipo_mercado == "Criptomonedas (Binance)":
                exchange = iniciar_conexion()
                
                # Saldo
                balance = exchange.fetch_balance()
                saldo_eur = balance.get('USDT', {}).get('free', 0.0) * TIPO_CAMBIO_EUR
                moneda_disponible = balance.get(activo_seleccionado, {}).get('free', 0.0)
                
                # Datos del mercado
                bars = exchange.fetch_ohlcv(symbol_api, timeframe='1m', limit=100)
                df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('fecha', inplace=True)
                
                # Convertimos todas las velas a Euros
                df['open'] = df['open'] * TIPO_CAMBIO_EUR
                df['high'] = df['high'] * TIPO_CAMBIO_EUR
                df['low'] = df['low'] * TIPO_CAMBIO_EUR
                df['close'] = df['close'] * TIPO_CAMBIO_EUR
                df['Precio_EUR'] = df['close']
                
            else:
                # Datos de Yahoo Finance
                ticker = yf.Ticker(symbol_api)
                df = ticker.history(period="5d", interval="5m")
                
                # Estandarizamos los nombres de las columnas para el Agente
                df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
                df.index = df.index.tz_localize(None) # Limpiamos la zona horaria
                df['Precio_EUR'] = df['close'] 

            # 2. CALCULAR INDICADORES (Común para ambos mercados)
            df['SMA_5'] = df['Precio_EUR'].rolling(window=5).mean()
            df['SMA_20'] = df['Precio_EUR'].rolling(window=20).mean()
            df['RSI'] = ta.rsi(df['close'], length=14)
            ultimo_rsi = df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 0.0

            # --- DIBUJAR EL PANEL VISUAL ---
            
            # Tarjetas superiores adaptables
            col1, col2, col3 = st.columns(3)
            if tipo_mercado == "Criptomonedas (Binance)":
                col1.metric("💰 Saldo Disponible", f"{saldo_eur:.2f} €")
                col2.metric(f"🪙 {activo_seleccionado} en Cartera", f"{moneda_disponible:.4f}")
            else:
                col1.metric("🌐 Mercado Tradicional", "Materias Primas")
                col2.metric("📦 Activo Analizado", activo_seleccionado)
                
            col3.metric("🌡️ RSI Actual", f"{ultimo_rsi:.2f}")

            # Filtramos datos para gráficos limpios
            df_grafico = df.dropna().copy()

            # 3. EL NUEVO GRÁFICO DE VELAS (PLOTLY)
            st.subheader(f"📊 Gráfico de Velas y Medias: {activo_seleccionado}")
            fig = go.Figure()

            # Capa 1: Velas Japonesas
            fig.add_trace(go.Candlestick(
                x=df_grafico.index,
                open=df_grafico['open'],
                high=df_grafico['high'],
                low=df
