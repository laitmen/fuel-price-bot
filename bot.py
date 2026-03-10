import pandas as pd
import requests
import os

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
    print("Inizio scansione...")
    try:
        # Nuovi link diretti del portale Osservaprezzi (MIMIT)
        URL_IMPIANTI = "https://www.mimit.gov.it/images/stories/documenti/anagrafica_impianti_attivi.csv"
        URL_PREZZI = "https://www.mimit.gov.it/images/stories/documenti/prezzi_alle_comunicazioni.csv"
        
        # Usiamo un "User-Agent" per far credere al sito del Ministero che siamo un browser normale
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        print("Scaricamento anagrafica...")
        r1 = requests.get(URL_IMPIANTI, headers=headers)
        print("Scaricamento prezzi...")
        r2 = requests.get(URL_PREZZI, headers=headers)
        
        # Se ancora danno 404, proviamo i link alternativi
        if r1.status_code == 404 or r2.status_code == 404:
             send_msg("❌ Il sito del Ministero ha rimosso i file o ha cambiato i link. Devo cercarli manualmente!")
             return

        # Leggiamo i file scaricati
        from io import BytesIO
        df_impianti = pd.read_csv(BytesIO(r1.content), sep=';', skiprows=1, on_bad_lines='skip')
        df_prezzi = pd.read_csv(BytesIO(r2.content), sep=';', skiprows=1, on_bad_lines='skip')
        
        df_impianti.columns = df_impianti.columns.str.strip()
        df_prezzi.columns = df_prezzi.columns.str.strip()
        
        df = pd.merge(df_prezzi, df_impianti, on='idImpianto')
        df['prezzo'] = pd.to_numeric(df['prezzo'].astype(str).str.replace(',', '.'), errors='coerce')
        
        errori = df[df['prezzo'] < SOGLIA_ERRORE].copy()
        
        if not errori.empty:
            messaggio = f"⛽ {len(errori)} PREZZI BASSI TROVATI!\n\n"
            for _, row in errori.head(5).iterrows():
                messaggio += f"📍 {row['NomeImpianto']} ({row['Comune']})\n💰 {row['prezzo']}€ - {row['descCarburante']}\n\n"
            send_msg(messaggio)
        else:
            # Mandami un messaggio così so che il bot ha lavorato bene!
            send_msg("✅ Scansione completata: nessun prezzo anomalo trovato (soglia " + str(SOGLIA_ERRORE) + "€)")
            
    except Exception as e:
        print(f"Errore: {e}")
        send_msg(f"❌ Errore tecnico durante il download: {e}")

if __name__ == "__main__":
    check()
