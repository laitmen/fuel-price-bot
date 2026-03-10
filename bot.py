import pandas as pd
import requests
import os

# Recupero segreti
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SOGLIA_ERRORE = 1.90 

def send_msg(text):
    if not TOKEN or not CHAT_ID:
        print("Errore: Token o Chat ID mancanti nei segreti di GitHub!")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text})
    except:
        pass

def check():
    print("Inizio scansione...")
    try:
        # Link diretti ai file CSV (aggiornati)
        URL_IMPIANTI = "https://www.mimit.gov.it/images/stories/documenti/anagrafica_impianti_attivi.csv"
        URL_PREZZI = "https://www.mimit.gov.it/images/stories/documenti/prezzi_alle_comunicazioni.csv"
        
        # Scarico i dati
        # Se il ministero dà 404, il problema è del loro server momentaneo
        df_impianti = pd.read_csv(URL_IMPIANTI, sep=';', skiprows=1, on_bad_lines='skip')
        df_prezzi = pd.read_csv(URL_PREZZI, sep=';', skiprows=1, on_bad_lines='skip')
        
        df_impianti.columns = df_impianti.columns.str.strip()
        df_prezzi.columns = df_prezzi.columns.str.strip()
        
        df = pd.merge(df_prezzi, df_impianti, on='idImpianto')
        df['prezzo'] = pd.to_numeric(df['prezzo'].astype(str).str.replace(',', '.'), errors='coerce')
        
        # Filtro
        errori = df[df['prezzo'] < SOGLIA_ERRORE].copy()
        
        if not errori.empty:
            # Invio un riepilogo invece di mille messaggi
            top_5 = errori.head(5)
            messaggio = "⛽ PREZZI BASSI TROVATI!\n\n"
            for _, row in top_5.iterrows():
                messaggio += f"📍 {row['NomeImpianto']} ({row['Comune']})\n💰 {row['prezzo']}€ - {row['descCarburante']}\n\n"
            
            send_msg(messaggio)
            print("Messaggio inviato!")
        else:
            print("Nessun prezzo sotto soglia.")
            
    except Exception as e:
        print(f"Errore durante il check: {e}")
        # Se ricevi questo su telegram, almeno sappiamo che il token è giusto!
        send_msg(f"❌ Errore tecnico: {e}")

if __name__ == "__main__":
    check()
