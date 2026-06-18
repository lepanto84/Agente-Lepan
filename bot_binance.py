import ccxt
import pandas as pd
import pandas_ta as ta
import time
import os
from datetime import datetime

# --- 1. CREDENCIALES DE LA TESTNET ---
API_KEY = 'MDI5M4OeE9ss3Z5czc3bw7Rs8iqTgkOacnbljANl5O2KzUxZ7RB1KDgELAEwM7cr'
API_SECRET = 'c9NtfZAMrqUzbFYTYNbiRrVzdpngmoQyFITyJySvXOeYdvdB1aH9DPk9u8NMOVj3'

SYMBOL = 'BTC/USDT'
ORDER_SIZE = 0.01  
STOP_LOSS_PCT = 0.02  # 2% de pérdida máxima permitida

# --- TIPO DE CAMBIO (Aproximado) ---
# 1 USDT equivale a unos 0.93 Euros actualmente. 
# Si el dólar sube o baja, solo tienes que actualizar este número.
TIPO_CAMBIO_EUR = 0.93  

# --- VARIABLES DE ESTADO ---
posicion_abierta = False
precio_compra_eur = 0.0  # Ahora guardamos la memoria de compra en Euros

# --- 2. CONEXIÓN SEGURA ---
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
})
exchange.set_sandbox_mode(True) 

def registrar_operacion(accion, precio_eur, cantidad):
    """Guarda la operación en el archivo CSV usando el precio en Euros"""
    archivo = 'historial_operaciones.csv'
    fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    nueva_op = pd.DataFrame([{
        'Fecha': fecha_actual,
        'Accion': accion,
        'Activo': 'BTC/EUR (Simulado)',
        'Precio_Ejecucion_EUR': round(precio_eur, 2),
        'Cantidad': cantidad
    }])
    
    if not os.path.exists(archivo):
        nueva_op.to_csv(archivo, index=False, sep=';', encoding='utf-8')
    else:
        nueva_op.to_csv(archivo, mode='a', header=False, index=False, sep=';', encoding='utf-8')
    
    print(f"📊 Operación registrada en el historial a {precio_eur:.2f} €")

def mostrar_saldo():
    try:
        balance = exchange.fetch_balance()
        # Calculamos el saldo en euros multiplicando los USDT disponibles
        saldo_eur = balance['USDT']['free'] * TIPO_CAMBIO_EUR
        print(f"💰 Saldo: {saldo_eur:.2f} € | {balance['BTC']['free']:.4f} BTC")
    except Exception:
        pass

# --- 3. LÓGICA DE ANÁLISIS Y TOMA DE DECISIONES ---
def analizar_y_operar():
    global posicion_abierta, precio_compra_eur
    
    print(f"\n[{time.strftime('%X')}] Escaneando el mercado...")
    mostrar_saldo()
    
    try:
        bars = exchange.fetch_ohlcv(SYMBOL, timeframe='1m', limit=50)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['SMA_5'] = df['close'].rolling(window=5).mean()
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        ultima_sma5 = df['SMA_5'].iloc[-1]
        ultima_sma20 = df['SMA_20'].iloc[-1]
        previa_sma5 = df['SMA_5'].iloc[-2]
        previa_sma20 = df['SMA_20'].iloc[-2]
        rsi_actual = df['RSI'].iloc[-1]
        
        # Obtenemos el precio en dólares del mercado y lo convertimos a Euros
        precio_actual_usd = df['close'].iloc[-1]
        precio_actual_eur = precio_actual_usd * TIPO_CAMBIO_EUR

        print(f"Precio: {precio_actual_eur:.2f} € | SMA5: {(ultima_sma5 * TIPO_CAMBIO_EUR):.2f} € | SMA20: {(ultima_sma20 * TIPO_CAMBIO_EUR):.2f} € | RSI: {rsi_actual:.2f}")

        # --- PROTECCIÓN DE CAPITAL (STOP-LOSS) ---
        if posicion_abierta:
            limite_perdida_eur = precio_compra_eur * (1 - STOP_LOSS_PCT)
            if precio_actual_eur <= limite_perdida_eur:
                print(f"🚨 ¡ALERTA STOP-LOSS! El precio bajó a {precio_actual_eur:.2f} €. Vendiendo para evitar más pérdidas.")
                exchange.create_market_sell_order(SYMBOL, ORDER_SIZE)
                registrar_operacion('VENTA (Stop-Loss)', precio_actual_eur, ORDER_SIZE)
                posicion_abierta = False
                precio_compra_eur = 0.0
                return

        # --- ESTRATEGIA PRINCIPAL ---
        if not posicion_abierta:
            if previa_sma5 <= previa_sma20 and ultima_sma5 > ultima_sma20 and rsi_actual < 70:
                print("🟢 SEÑAL DE COMPRA: Tendencia alcista detectada. Ejecutando...")
                exchange.create_market_buy_order(SYMBOL, ORDER_SIZE) 
                registrar_operacion('COMPRA', precio_actual_eur, ORDER_SIZE)
                posicion_abierta = True
                precio_compra_eur = precio_actual_eur
            else:
                print("⚪ Buscando punto de entrada óptimo...")
                
        else:
            if previa_sma5 >= previa_sma20 and ultima_sma5 < ultima_sma20:
                print("🔴 SEÑAL DE VENTA: Tendencia bajista detectada. Asegurando ganancias...")
                exchange.create_market_sell_order(SYMBOL, ORDER_SIZE)
                registrar_operacion('VENTA (Toma de Ganancias)', precio_actual_eur, ORDER_SIZE)
                posicion_abierta = False
                precio_compra_eur = 0.0
            else:
                print(f"📈 Posición abierta desde {precio_compra_eur:.2f} €. Manteniendo...")

    except Exception as e:
        print(f"Error en el análisis: {e}")

# --- 4. BUCLE INFINITO ---
if __name__ == '__main__':
    print("Iniciando Agente de Inversión (Valores en Euros)...")
    while True:
        analizar_y_operar()
        time.sleep(60)