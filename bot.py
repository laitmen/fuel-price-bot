import pandas as pd
import requests
import os
import io

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SOGLIA_ERRORE = 1.90 

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except:
        pass

def check():
    send_msg("📡 Connessione riuscita! Provo a scaricare i dati con il nuovo metodo...")
    
    try:
        # Nuovi link dinamici (indirizzi diretti del portale Open Data)
        URL_IMPIANTI = "https://www.mimit.gov.it/images/stories/documenti/anagrafica_impianti_attivi.csv"
        URL_PREZZI = "https://www.mimit.gov.it/images/stories/documenti/prezzi_alle_comunicazioni.csv"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Scarichiamo i file come flussi di dati per evitare il blocco 404
        with requests.Session() as s:
            print("Scarico impianti...")
            r1 = s.get(URL_IMPIANTI, headers=headers, verify=False)
            print("Scarico prezzi...")
            r2 = s.get(URL_PREZZI, headers=headers, verify=False)

        if r1.status_code != 200 or r2.status_code != 200:
            send_msg(f"❌ Il Ministero risponde ancora con errore {r1.status_code}. Riproverò tra 30 minuti.")
            return

        # Elaborazione dati
        df_impianti = pd.read_csv(io.BytesIO(r1.content), sep=';', skiprows=1, on_bad_lines='skip')
        df_prezzi = pd.read_csv(io.BytesIO(r2.content), sep=';', skiprows=1, on_bad_lines='skip')
        
        df_impianti.columns = df_impianti.columns.str.strip()
        df_prezzi.columns = df_prezzi.columns.str.strip()
        
        df = pd.merge(df_prezzi, df_impianti, on='idImpianto')
        df['prezzo'] = pd.to_numeric(df['prezzo'].astype(str).str.replace(',', '.'), errors='coerce')
        
        errori = df[df['prezzo'] < SOGLIA_ERRORE].copy()
        
        if not errori.empty:
            messaggio = f"⛽ TROVATE {len(errori)} OFFERTE!\n\n"
            for _, row in errori.head(5).iterrows():
                messaggio += f"📍 {row['NomeImpianto']} ({row['Comune']})\n💰 {row['prezzo']}€ - {row['descCarburante']}\n\n"
            send_msg(messaggio)
        else:
            send_msg("✅ Scansione completata: nessun prezzo sotto " + str(SOGLIA_ERRORE) + "€ trovato.")
            
    except Exception as e:
        send_msg(f"❌ Errore durante l'analisi: {str(e)}")

if __name__ == "__main__":
    check()
