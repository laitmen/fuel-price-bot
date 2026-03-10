import pandas as pd
import requests
import os

# --- CORREZIONE QUI ---
# Qui dobbiamo scrivere i NOMI dei segreti che hai messo su GitHub, non i numeri!
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SOGLIA_ERRORE = 1.90 

def send_msg(text):
    if not TOKEN or not CHAT_ID:
        print("Errore: Token o Chat ID mancanti nei segreti di GitHub!")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Errore invio messaggio: {e}")

def check():
    # Questo messaggio ti conferma che il bot è connesso a Telegram
    send_msg("📡 Il bot è partito! Inizio scaricamento dati dal Ministero...")
    
    print("Scarico i dati...")
    try:
        # URL ufficiali MIMIT
        URL_IMPIANTI = "https://www.mimit.gov.it/images/stories/documenti/anagrafica_impianti_attivi.csv"
        URL_PREZZI = "https://www.mimit.gov.it/images/stories/documenti/prezzi_alle_comunicazioni.csv"
        
        # Scarico i dati con gestione della virgola italiana
        df_impianti = pd.read_csv(URL_IMPIANTI, sep=';', skiprows=1, on_bad_lines='skip')
        df_prezzi = pd.read_csv(URL_PREZZI, sep=';', skiprows=1, on_bad_lines='skip')
        
        # Pulizia colonne
        df_impianti.columns = df_impianti.columns.str.strip()
        df_prezzi.columns = df_prezzi.columns.str.strip()
        
        # Unione dati
        df = pd.merge(df_prezzi, df_impianti, on='idImpianto')
        
        # Trasformiamo il prezzo (gestendo se il file usa la virgola invece del punto)
        df['prezzo'] = pd.to_numeric(df['prezzo'].astype(str).str.replace(',', '.'), errors='coerce')
        
        # Filtriamo per la tua soglia
        errori = df[df['prezzo'] < SOGLIA_ERRORE].copy()
        
        if not errori.empty:
            # Inviamo solo i primi 5 per evitare di bloccare il bot se ci sono troppi risultati
            for _, row in errori.head(5).iterrows():
                msg = (f"⚠️ PREZZO RILEVATO!\n"
                       f"Benzinaio: {row['NomeImpianto']}\n"
                       f"Comune: {row['Comune']}\n"
                       f"Prezzo: {row['prezzo']} €/L\n"
                       f"Carburante: {row['descCarburante']}")
                send_msg(msg)
            
            send_msg(f"✅ Scansione completata. Trovati {len(errori)} distributori sotto soglia.")
        else:
            send_msg("ℹ️ Scansione completata: nessun prezzo sotto soglia trovato.")
            
    except Exception as e:
        error_info = f"❌ Errore durante il check: {str(e)}"
        print(error_info)
        send_msg(error_info)

if __name__ == "__main__":
    check()
