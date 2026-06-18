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
