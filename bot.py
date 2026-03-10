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

SOGLIA_PREZZO = 2.10 # Alzata per includere le 100 ottani/speciali nel calcolo
SOGLIA_MINIMA = 1.45 
MAX_RESULTS = 10

# Coordinate di Mareno di Piave (TV)
CASA_LAT = 45.8410
CASA_LON = 12.3469

URL_IMPIANTI = "https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv"
URL_PREZZI = "https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# FUNZIONI
# =========================
def calcola_distanza(lat1, lon1):
    try:
        lat1, lon1 = float(lat1), float(lon1)
        R = 6371 
        dlat = math.radians(lat1 - CASA_LAT)
        dlon = math.radians(lon1 - CASA_LON)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(CASA_LAT)) * math.cos(math.radians(lat1)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 1)
    except:
        return 999.0

def get_type_emoji(carburante):
    c = carburante.lower()
    return "🟢" if "benzina" in c else "⚫"

def get_price_color(prezzo, media):
    # Verde se risparmi più del 2% rispetto alla media
    if prezzo < media * 0.98: return "✅" 
    # Rosso se paghi più del 2% rispetto alla media
    if prezzo > media * 1.02: return "❌"
    # Giallo se sei nel mezzo
    return "⚠️"

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=15)

def check():
    try:
        r_prezzi = requests.get(URL_PREZZI, headers=HEADERS, timeout=60)
        r_impianti = requests.get(URL_IMPIANTI, headers=HEADERS, timeout=60)

        df_prezzi = pd.read_csv(io.BytesIO(r_prezzi.content), sep="|", skiprows=1, on_bad_lines="skip", dtype=str)
        df_impianti = pd.read_csv(io.BytesIO(r_impianti.content), sep="|", skiprows=1, on_bad_lines="skip", dtype=str)

        df_prezzi.columns = df_prezzi.columns.str.strip()
        df_impianti.columns = df_impianti.columns.str.strip()

        df = pd.merge(df_prezzi, df_impianti, on="idImpianto")

        df["prezzo"] = pd.to_numeric(df["prezzo"].str.replace(",", "."), errors="coerce")
        df["distanza"] = df.apply(lambda x: calcola_distanza(x["Latitudine"], x["Longitudine"]), axis=1)

        mask = (df["descCarburante"].str.contains("Benzina|Gasolio|Artico|100 ottani", case=False, na=False) & 
                ~df["descCarburante"].str.contains("Metano|GPL|LPG", case=False, na=False))
        
        df = df[mask].copy()

        # Filtro zona Mareno (40km) e prezzi sensati
        offerte = df[(df["prezzo"] < SOGLIA_PREZZO) & (df["prezzo"] > SOGLIA_MINIMA) & (df["distanza"] < 40)].copy()
        
        if offerte.empty:
            send_msg("✅ Nessun dato disponibile in zona.")
            return

        # Calcoliamo la media della zona per il confronto
        media_zona = offerte["prezzo"].mean()

        # Ordiniamo per distanza
        offerte = offerte.sort_values("distanza")

        msg = f"📊 REPORT CARBURANTI (Mareno +40km)\n"
        msg += f"Media zona: {round(media_zona, 3)}€\n"
        msg += f"(Legenda: ✅ Ottimo | ⚠️ Medio | ❌ Caro)\n\n"
        
        for _, row in offerte.head(MAX_RESULTS).iterrows():
            type_emoji = get_type_emoji(row["descCarburante"])
            price_status = get_price_color(row["prezzo"], media_zona)
            
            msg += (f"{type_emoji} {row['descCarburante']}\n"
                    f"{price_status} PREZZO: {row['prezzo']}€\n"
                    f"📏 {row['distanza']} km | {row.get('Nome Impianto', 'N/D')}\n"
                    f"🏙️ {row['Comune']} ({row.get('Provincia', '??')})\n\n")

        send_msg(msg)

    except Exception as e:
        send_msg(f"❌ Errore: {str(e)}")

if __name__ == "__main__":
    check()
