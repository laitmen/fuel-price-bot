import pandas as pd
import requests
import time

# --- CONFIGURAZIONE ---
TELEGRAM_TOKEN = "IL_TUO_TOKEN_QUI"
CHAT_ID = "IL_TUO_ID_CHAT_QUI"
SOGLIA_ERRORE = 0.90  # Prezzo sotto il quale consideriamo un errore

# URL Ufficiali MIMIT (Ministero Imprese e Made in Italy)
URL_IMPIANTI = "https://www.mimit.gov.it/images/stories/documenti/anagrafica_impianti_attivi.csv"
URL_PREZZI = "https://www.mimit.gov.it/images/stories/documenti/prezzi_alle_comunicazioni.csv"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Errore invio Telegram: {e}")

def check_fuel_prices():
    print(f"[{time.strftime('%H:%M:%S')}] Inizio scansione prezzi...")
    try:
        # 1. Scaricamento dati (usiamo sep=';' e skiprows=1 perché i CSV ministeriali hanno un header sporco)
        df_impianti = pd.read_csv(URL_IMPIANTI, sep=';', skiprows=1, on_bad_lines='skip')
        df_prezzi = pd.read_csv(URL_PREZZI, sep=';', skiprows=1, on_bad_lines='skip')

        # 2. Pulizia nomi colonne (spesso hanno spazi)
        df_impianti.columns = df_impianti.columns.str.strip()
        df_prezzi.columns = df_prezzi.columns.str.strip()

        # 3. Unione tabelle
        df = pd.merge(df_prezzi, df_impianti, on='idImpianto')

        # 4. Filtro Errori (Prezzo sotto soglia)
        # Assicuriamoci che 'prezzo' sia un numero
        df['prezzo'] = pd.to_numeric(df['prezzo'], errors='coerce')
        errori = df[df['prezzo'] < SOGLIA_ERRORE].copy()

        # 5. Notifica
        if not errori.empty:
            for _, row in errori.iterrows():
                msg = (f"⚠️ POSSIBILE ERRORE PREZZO!\n"
                       f"Benzinaio: \"{row['NomeImpianto']}\"\n"
                       f"Coordinate: {row['Latitudine']}, {row['Longitudine']}\n"
                       f"Prezzo rilevato: {row['prezzo']} €/L\n"
                       f"Carburante: {row['descCarburante']}")
                send_telegram_msg(msg)
                print(f"Segnalato: {row['NomeImpianto']}")
        else:
            print("Nessun errore di prezzo trovato.")

    except Exception as e:
        print(f"Errore durante l'elaborazione: {e}")

# --- LOOP 24h ---
# Esegue il controllo ogni ora (3600 secondi)
if __name__ == "__main__":
    send_telegram_msg("🚀 Bot Fuel-Error avviato correttamente! Monitoraggio h24 attivo.")
    while True:
        check_fuel_prices()
        time.sleep(3600)