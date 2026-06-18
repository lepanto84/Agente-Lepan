import ccxt
import pandas as pd
import pandas_ta as ta
import time
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
API_KEY = os.environ.get('API_KEY', 'MDI5M4OeE9ss3Z5czc3bw7Rs8iqTgkOacnbljANl5O2KzUxZ7RB1KDgELAEwM7cr')
API_SECRET = os.environ.get('API_SECRET', 'c9NtfZAMrqUzbFYTYNbiRrVzdpngmoQyFITyJySvXOeYdvdB1aH9DPk9u8NMOVj3')
SIMBOLO = 'BTC/USDT'
MONEDA = 'BTC'
CANTIDAD_COMPRA = 0.05 

# --- FUNCIÓN DE LOGS (DIARIO) ---
def registrar_evento(mensaje):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entrada = f"[{timestamp}] {mensaje}\n"
    print(log_entrada.strip()) 
    # Cambiamos esta línea añadiendo encoding='utf-8'
    with open("historial_operaciones.txt", "a", encoding='utf-8') as f:
        f.write(log_entrada)

# --- CONEXIÓN ---
exchange = ccxt.binance({'apiKey': API_KEY, 'secret': API_SECRET, 'enableRateLimit': True})
exchange.set_sandbox_mode(True)

registrar_evento("🤖 AGENTE LEPAN [MOTOR] INICIADO. Registrando actividad en historial_operaciones.txt")

# --- BUCLE ---
while True:
    try:
        balance = exchange.fetch_balance()
        saldo_cripto = balance.get(MONEDA, {}).get('free', 0.0)
        en_posicion = saldo_cripto > 0.001 

        bars = exchange.fetch_ohlcv(SIMBOLO, timeframe='1m', limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Cálculos de Inteligencia
        df['SMA_5'] = df['close'].rolling(window=5).mean()
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_100'] = df['close'].rolling(window=100).mean()
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        # Último minuto cerrado
        precio = df['close'].iloc[-2]
        rsi = df['RSI'].iloc[-2]
        
        # Reglas
        cruce_alcista = df['SMA_5'].iloc[-3] <= df['SMA_20'].iloc[-3] and df['SMA_5'].iloc[-2] > df['SMA_20'].iloc[-2]
        cruce_bajista = df['SMA_5'].iloc[-3] >= df['SMA_20'].iloc[-3] and df['SMA_5'].iloc[-2] < df['SMA_20'].iloc[-2]
        
        # Ejecución con LOGS
        if cruce_alcista and rsi < 70 and precio > df['SMA_100'].iloc[-2] and not en_posicion:
            orden = exchange.create_market_buy_order(SIMBOLO, CANTIDAD_COMPRA)
            registrar_evento(f"🚀 COMPRA EJECUTADA: {CANTIDAD_COMPRA} BTC a {orden['average']} USDT")

        elif cruce_bajista and en_posicion:
            orden = exchange.create_market_sell_order(SIMBOLO, saldo_cripto)
            registrar_evento(f"🚨 VENTA EJECUTADA: Se vendió todo el {MONEDA} a {orden['average']} USDT")

    except Exception as e:
        registrar_evento(f"❌ ERROR: {e}")

    time.sleep(60)
