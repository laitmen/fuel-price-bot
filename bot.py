import pandas as pd
import requests
import os

# GitHub recupera i segreti che hai appena salvato
TOKEN = os.getenv('8787419769:AAG7MWbjonEPF4E-xvueht5uD8-aoGeQw5M')
CHAT_ID = os.getenv('6416960636')
SOGLIA_ERRORE = 0.90 

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, json=payload)

def check():
    try:
        # URL ufficiali Ministero
        URL_IMPIANTI = "https://www.mimit.gov.it/images/stories/documenti/anagrafica_impianti_attivi.csv"
        URL_PREZZI = "https://www.mimit.gov.it/images/stories/documenti/prezzi_alle_comunicazioni.csv"
        
        # Scarico i dati
        df_impianti = pd.read_csv(URL_IMPIANTI, sep=';', skiprows=1, on_bad_lines='skip')
        df_prezzi = pd.read_csv(URL_PREZZI, sep=';', skiprows=1, on_bad_lines='skip')
        
        # Pulizia colonne e unione
        df_impianti.columns = df_impianti.columns.str.strip()
        df_prezzi.columns = df_prezzi.columns.str.strip()
        df = pd.merge(df_prezzi, df_impianti, on='idImpianto')
        
        df['prezzo'] = pd.to_numeric(df['prezzo'], errors='coerce')
        
        # Cerchiamo gli errori
        errori = df[df['prezzo'] < SOGLIA_ERRORE]
        
        if not errori.empty:
            for _, row in errori.iterrows():
                msg = (f"⚠️ POSSIBILE ERRORE PREZZO!\n"
                       f"Benzinaio: {row['NomeImpianto']}\n"
                       f"Coordinate: {row['Latitudine']}, {row['Longitudine']}\n"
                       f"Prezzo: {row['prezzo']} €/L")
                send_msg(msg)
    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    check()
