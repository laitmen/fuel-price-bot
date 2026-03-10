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
    # Usiamo questi nuovi link che puntano direttamente allo storage dei dati
    URL_IMPIANTI = "https://www.mimit.gov.it/images/stories/documenti/anagrafica_impianti_attivi.csv"
    URL_PREZZI = "https://www.mimit.gov.it/images/stories/documenti/prezzi_alle_comunicazioni.csv"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/csv'
    }

    try:
        print("Tentativo scaricamento dati...")
        
        # Scarichiamo i prezzi
        r_prezzi = requests.get(URL_PREZZI, headers=headers, timeout=30)
        # Scarichiamo l'anagrafica
        r_impianti = requests.get(URL_IMPIANTI, headers=headers, timeout=30)

        if r_prezzi.status_code != 200:
            send_msg(f"⚠️ Il Ministero è in manutenzione (Errore {r_prezzi.status_code}). Riprovo tra 30 minuti.")
            return

        # Carichiamo i dati in memoria
        df_prezzi = pd.read_csv(io.BytesIO(r_prezzi.content), sep=';', skiprows=1, on_bad_lines='skip')
        df_impianti = pd.read_csv(io.BytesIO(r_impianti.content), sep=';', skiprows=1, on_bad_lines='skip')

        # Pulizia e Unione
        df_prezzi.columns = df_prezzi.columns.str.strip()
        df_impianti.columns = df_impianti.columns.str.strip()
        
        df = pd.merge(df_prezzi, df_impianti, on='idImpianto')
        
        # Convertiamo i prezzi (gestendo la virgola italiana)
        df['prezzo'] = pd.to_numeric(df['prezzo'].astype(str).str.replace(',', '.'), errors='coerce')
        
        # Filtriamo per la tua soglia
        offerte = df[df['prezzo'] < SOGLIA_ERRORE].copy()
        
        if not offerte.empty:
            msg = f"⛽ TROVATE {len(offerte)} OFFERTE!\n\n"
            # Prendiamo i primi 5 risultati
            for _, row in offerte.head(5).iterrows():
                msg += f"📍 {row['NomeImpianto']} ({row['Comune']})\n💰 {row['prezzo']}€ - {row['descCarburante']}\n\n"
            send_msg(msg)
        else:
            send_msg(f"✅ Scansione completata: nessun prezzo sotto {SOGLIA_ERRORE}€.")

    except Exception as e:
        send_msg(f"❌ Errore imprevisto: {str(e)}")

if __name__ == "__main__":
    check()
