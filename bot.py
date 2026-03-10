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
SOGLIA_MINIMA = 1.45  # Per scartare i prezzi finti a 1 euro
MAX_RESULTS = 10

# Coordinate di Mareno di Piave (TV)
CASA_LAT = 45.8410
CASA_LON = 12.3469

URL_IMPIANTI = "https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv"
URL_PREZZI = "https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# FUNZIONI AUSILIARIE
# =========================
def calcola_distanza(lat1, lon1):
    try:
        lat1, lon1 = float(lat1), float(lon1)
        R = 6371  # Raggio Terra km
        dlat = math.radians(lat1 - CASA_LAT)
        dlon = math.radians(lon1 - CASA_LON)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(CASA_LAT)) * math.cos(math.radians(lat1)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 1)
    except:
        return 999.0

def get_emoji(carburante):
    c = carburante.lower()
    if "benzina" in c:
        return "🟢" # Verde per Benzina
    elif "gasolio" in c or "diesel" in c:
        return "⚫" # Nero per Gasolio
    return "⛽"

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

        # Conversione dati
        df["prezzo"] = pd.to_numeric(df["prezzo"].str.replace(",", "."), errors="coerce")
        df["distanza"] = df.apply(lambda x: calcola_distanza(x["Latitudine"], x["Longitudine"]), axis=1)

        # Filtro Tipi (Benzina e Gasolio)
        mask = (df["descCarburante"].str.contains("Benzina|Gasolio|Artico|100 ottani", case=False, na=False) & 
                ~df["descCarburante"].str.contains("Metano|GPL|LPG", case=False, na=False))
        
        df = df[mask].copy()

        # Filtro Finale (Entro 40km e prezzo realistico)
        offerte = df[(df["prezzo"] < SOGLIA_PREZZO) & 
                    (df["prezzo"] > SOGLIA_MINIMA) & 
                    (df["distanza"] < 40)].copy()
        
        # ORDINAMENTO PER DISTANZA (i più vicini a Mareno per primi)
        offerte = offerte.sort_values("distanza")

        if offerte.empty:
            send_msg(f"✅ Nessuna offerta rilevata entro 40km da Mareno di Piave.")
            return

        msg = f"📍 DISTRIBUTORI VICINI A TE\n(Ordinati per distanza)\n\n"
        
        for _, row in offerte.head(MAX_RESULTS).iterrows():
            emoji = get_emoji(row["descCarburante"])
            nome = row.get("Nome Impianto", row.get("nomeImpianto", "Sconosciuto"))
            comune = row.get("Comune", "N/D")
            dist = row["distanza"]
            prezzo = row["prezzo"]
            tipo = row["descCarburante"]
            
            msg += (f"{emoji} {prezzo}€ - {tipo}\n"
                    f"📏 {dist} km | {nome}\n"
                    f"🏙️ {comune} ({row.get('Provincia', '??')})\n\n")

        send_msg(msg)

    except Exception as e:
        send_msg(f"❌ Errore: {str(e)}")

if __name__ == "__main__":
    check()
