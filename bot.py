import pandas as pd
import requests
import os
import io
import math

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SOGLIA_PREZZO = 1.90
SOGLIA_MINIMA = 1.45  # Alzata per evitare i prezzi finti a 1€
MAX_RESULTS = 10

# Coordinate di Mareno di Piave (TV)
CASA_LAT = 45.8410
CASA_LON = 12.3469

URL_IMPIANTI = "https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv"
URL_PREZZI = "https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# FUNZIONE DISTANZA
# =========================
def calcola_distanza(lat1, lon1):
    try:
        lat1, lon1 = float(lat1), float(lon1)
        R = 6371  # Raggio della Terra in km
        dlat = math.radians(lat1 - CASA_LAT)
        dlon = math.radians(lon1 - CASA_LON)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(CASA_LAT)) * math.cos(math.radians(lat1)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 1)
    except:
        return 9999

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)

def check():
    try:
        # Download
        r_prezzi = requests.get(URL_PREZZI, headers=HEADERS, timeout=60)
        r_impianti = requests.get(URL_IMPIANTI, headers=HEADERS, timeout=60)

        df_prezzi = pd.read_csv(io.BytesIO(r_prezzi.content), sep="|", skiprows=1, on_bad_lines="skip", dtype=str)
        df_impianti = pd.read_csv(io.BytesIO(r_impianti.content), sep="|", skiprows=1, on_bad_lines="skip", dtype=str)

        df_prezzi.columns = df_prezzi.columns.str.strip()
        df_impianti.columns = df_impianti.columns.str.strip()

        # Merge
        df = pd.merge(df_prezzi, df_impianti, on="idImpianto")

        # Conversione prezzi e coordinate
        df["prezzo"] = pd.to_numeric(df["prezzo"].str.replace(",", "."), errors="coerce")
        
        # Filtro Carburanti (Benzina e Gasolio incl. Speciali)
        keywords = "Benzina|Gasolio|Artico|100 ottani|Special"
        exclude = "Metano|GPL|LPG|Perform"
        mask = (df["descCarburante"].str.contains(keywords, case=False, na=False) & 
                ~df["descCarburante"].str.contains(exclude, case=False, na=False))
        
        df = df[mask].copy()

        # Calcolo Distanza da Mareno di Piave
        df["distanza"] = df.apply(lambda x: calcola_distanza(x["Latitudine"], x["Longitudine"]), axis=1)

        # Filtro Finale: Prezzo valido + Distanza ragionevole (es. entro 50km)
        offerte = df[(df["prezzo"] < SOGLIA_PREZZO) & 
                    (df["prezzo"] > SOGLIA_MINIMA) & 
                    (df["distanza"] < 50)].copy() # Solo entro 50km da casa
        
        offerte = offerte.sort_values("prezzo")

        if offerte.empty:
            send_msg(f"✅ Nessuna offerta reale trovata nel raggio di 50km da Mareno di Piave.")
            return

        msg = f"⛽ OFFERTE VICINO A MARENO ({len(offerte)})\n\n"
        for _, row in offerte.head(MAX_RESULTS).iterrows():
            nome = row.get("Nome Impianto", row.get("nomeImpianto", "Sconosciuto"))
            comune = row.get("Comune", "N/D")
            prov = row.get("Provincia", "??")
            dist = row["distanza"]
            
            msg += (f"📍 {nome} ({comune} - {prov})\n"
                    f"📏 Distanza: {dist} km\n"
                    f"💰 {row['prezzo']}€ - {row['descCarburante']}\n\n")

        send_msg(msg)

    except Exception as e:
        send_msg(f"❌ Errore: {str(e)}")

if __name__ == "__main__":
    check()
