import ccxt
import pandas as pd
import pandas_ta as ta
import time
import os
from datetime import datetime

# --- CONFIGURACIÓN DEL BOT ---
API_KEY = os.environ.get('API_KEY', 'MDI5M4OeE9ss3Z5czc3bw7Rs8iqTgkOacnbljANl5O2KzUxZ7RB1KDgELAEwM7cr')
API_SECRET = os.environ.get('API_SECRET', 'c9NtfZAMrqUzbFYTYNbiRrVzdpngmoQyFITyJySvXOeYdvdB1aH9DPk9u8NMOVj3')

# Parámetros de Operación
SIMBOLO = 'BTC/USDT'     # El mercado que vamos a operar
MONEDA = 'BTC'           # La moneda que acumulamos
CANTIDAD_COMPRA = 0.05   # Cuántos BTC comprará en cada señal (Ajusta según tu saldo de Testnet)

print("="*50)
print(f"🤖 AGENTE LEPAN [MOTOR DE EJECUCIÓN] INICIADO")
print(f"🌐 Mercado: {SIMBOLO} | Sandbox: ACTIVADO")
print("="*50)

# --- INICIAR CONEXIÓN ---
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
})
exchange.set_sandbox_mode(True) # ¡VITAL! Nos asegura que es dinero de mentira

# --- BUCLE INFINITO DE VIGILANCIA ---
while True:
    try:
        ahora = datetime.now().strftime("%H:%M:%S")
        
        # 1. Consultar el saldo actual para saber si ya hemos comprado
        balance = exchange.fetch_balance()
        saldo_usdt = balance.get('USDT', {}).get('free', 0.0)
        saldo_cripto = balance.get(MONEDA, {}).get('free', 0.0)
        
        # Consideramos que estamos "dentro" si tenemos más de 0.001 BTC
        en_posicion = saldo_cripto > 0.001 

        # 2. Descargar datos y calcular la inteligencia del Agente
        bars = exchange.fetch_ohlcv(SIMBOLO, timeframe='1m', limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['SMA_5'] = df['close'].rolling(window=5).mean()
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_100'] = df['close'].rolling(window=100).mean()
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['Vela_Verde'] = df['close'] > df['open']
        df['Volumen_Promedio'] = df['volume'].rolling(window=20).mean()

        # 3. Extraer valores del último minuto cerrado (evitamos la vela actual que aún se mueve)
        # Usamos .iloc[-2] para la vela anterior, ya que .iloc[-1] es la vela de este mismo segundo
        precio = df['close'].iloc[-2]
        sma100 = df['SMA_100'].iloc[-2]
        vela_verde = df['Vela_Verde'].iloc[-2]
        volumen = df['volume'].iloc[-2]
        volumen_prom = df['Volumen_Promedio'].iloc[-2]
        rsi = df['RSI'].iloc[-2]
        
        ultima_sma5 = df['SMA_5'].iloc[-2]
        ultima_sma20 = df['SMA_20'].iloc[-2]
        previa_sma5 = df['SMA_5'].iloc[-3]
        previa_sma20 = df['SMA_20'].iloc[-3]

        # 4. Lógica Cuantitativa Estricta
        cruce_alcista = previa_sma5 <= previa_sma20 and ultima_sma5 > ultima_sma20
        cruce_bajista = previa_sma5 >= previa_sma20 and ultima_sma5 < ultima_sma20
        tendencia_alcista = precio > sma100
        hay_volumen = volumen > volumen_prom

        print(f"[{ahora}] Precio: {precio:.2f} | RSI: {rsi:.1f} | Estado: {'CON BTC' if en_posicion else 'BUSCANDO COMPRA'}")

        # 5. EJECUCIÓN DE ÓRDENES EN BINANCE
        if cruce_alcista and rsi < 70 and vela_verde and hay_volumen and tendencia_alcista:
            if not en_posicion:
                print(f"\n🚀 [SEÑAL CONFIRMADA] Lanzando orden de COMPRA de {CANTIDAD_COMPRA} {MONEDA}...")
                orden = exchange.create_market_buy_order(SIMBOLO, CANTIDAD_COMPRA)
                print(f"✅ Compra ejecutada a {orden['average']} USDT\n")
            else:
                print("   -> Señal de compra ignorada: Ya tienes saldo en cartera.")

        elif cruce_bajista:
            if en_posicion:
                print(f"\n🚨 [SEÑAL DE VENTA] Lanzando orden de VENTA de todo el {MONEDA}...")
                orden = exchange.create_market_sell_order(SIMBOLO, saldo_cripto)
                print(f"✅ Venta ejecutada a {orden['average']} USDT\n")

    except Exception as e:
        print(f"❌ Error en el bucle: {e}")

    # Dormir el programa durante 60 segundos hasta la siguiente vela
    time.sleep(60)
