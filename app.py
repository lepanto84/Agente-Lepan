import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta

# --- CONFIGURACIÓN DE LA PÁGININA ---
st.set_page_config(page_title="Agente Lepan", page_icon="📈", layout="wide")
st.title("🤖 Agente Lepan - Panel de Inversión")

# --- CREDENCIALES (Usa las de tu Testnet) ---
API_KEY = 'MDI5M4OeE9ss3Z5czc3bw7Rs8iqTgkOacnbljANl5O2KzUxZ7RB1KDgELAEwM7cr'
API_SECRET = 'c9NtfZAMrqUzbFYTYNbiRrVzdpngmoQyFITyJySvXOeYdvdB1aH9DPk9u8NMOVj3'
SYMBOL = 'BTC/USDT'
TIPO_CAMBIO_EUR = 0.93

# --- CONEXIÓN ---
@st.cache_resource # Esto evita reconectarse cada vez que tocas un botón
def iniciar_conexion():
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(True)
    return exchange

exchange = iniciar_conexion()

# --- INTERFAZ VISUAL ---
st.sidebar.header("Panel de Control")
if st.sidebar.button("🔄 Analizar Mercado Ahora"):
    
    with st.spinner("Escaneando el mercado de criptomonedas..."):
        try:
            # 1. Obtener Saldo
            balance = exchange.fetch_balance()
            saldo_eur = balance['USDT']['free'] * TIPO_CAMBIO_EUR
            btc_disponible = balance['BTC']['free']
            
            # 2. Descargar Datos
            bars = exchange.fetch_ohlcv(SYMBOL, timeframe='1m', limit=100)
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['fecha'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('fecha', inplace=True)
            
            # Convertimos a Euros
            df['Precio_EUR'] = df['close'] * TIPO_CAMBIO_EUR
            
            # 3. Calcular Indicadores
            df['SMA_5'] = df['Precio_EUR'].rolling(window=5).mean()
            df['SMA_20'] = df['Precio_EUR'].rolling(window=20).mean()
            df['RSI'] = ta.rsi(df['close'], length=14)

            # --- DIBUJAR EL PANEL ---
            
            # Tarjetas superiores
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 Saldo Disponible", f"{saldo_eur:.2f} €")
            col2.metric("₿ BTC en Cartera", f"{btc_disponible:.4f} BTC")
            col3.metric("🌡️ RSI Actual", f"{df['RSI'].iloc[-1]:.2f}")

            # Gráfico de Precios y Medias Móviles
            st.subheader("📊 Cotización y Cruce de Medias (BTC/EUR)")
            # Filtramos las filas vacías para que el eje Y se ajuste bien
            df_grafico = df.dropna()
            st.line_chart(df_grafico[['Precio_EUR', 'SMA_5', 'SMA_20']])
            # Gráfico del RSI
            st.subheader("📉 Oscilador RSI")
            st.line_chart(df[['RSI']])
            
            # Decisión del Agente
            st.divider()
            ultima_sma5 = df['SMA_5'].iloc[-1]
            ultima_sma20 = df['SMA_20'].iloc[-1]
            previa_sma5 = df['SMA_5'].iloc[-2]
            previa_sma20 = df['SMA_20'].iloc[-2]
            
            if previa_sma5 <= previa_sma20 and ultima_sma5 > ultima_sma20 and df['RSI'].iloc[-1] < 70:
                st.success("🟢 SEÑAL DE COMPRA: El Agente Lepan recomienda comprar.")
            elif previa_sma5 >= previa_sma20 and ultima_sma5 < ultima_sma20:
                st.error("🔴 SEÑAL DE VENTA: El Agente Lepan recomienda vender.")
            else:
                st.info("⚪ MERCADO ESTABLE: El Agente Lepan se mantiene a la espera.")

        except Exception as e:
            st.error(f"Error al conectar con Binance: {e}")
else:
    st.info("Haz clic en 'Analizar Mercado Ahora' en el panel lateral para iniciar.")
