import pandas as pd
import requests
import os
import io

# =========================
# CONFIGURAZIONE CACCIATORE
# =========================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SOGLIA_ALLERTA = 1.50   
SOGLIA_ERRORE_MIN = 0.80 

# Province del Nord-Est (Veneto, Trentino, Friuli)
PROVINCE_NORD_EST = [
    "TV", "VE", "PD", "VI", "VR", "BL", "RO", # Veneto
    "TN", "BZ",                               # Trentino
    "TS", "UD", "PN", "GO"                    # Friuli
]

URL_IMPIANTI = "https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv"
URL_PREZZI = "https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv"

HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_type_emoji(carburante):
    c = carburante.lower()
    return "🟢" if "benzina" in c else "⚫"

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=15)

def check():
    try:
        # Scarico dati
        r_prezzi = requests.get(URL_PREZZI, headers=HEADERS, timeout=60)
        r_impianti = requests.get(URL_IMPIANTI, headers=HEADERS, timeout=60)

        df_prezzi = pd.read_csv(io.BytesIO(r_prezzi.content), sep="|", skiprows=1, on_bad_lines="skip", dtype=str)
        df_impianti = pd.read_csv(io.BytesIO(r_impianti.content), sep="|", skiprows=1, on_bad_lines="skip", dtype=str)

        df_prezzi.columns = df_prezzi.columns.str.strip()
        df_impianti.columns = df_impianti.columns.str.strip()

        df = pd.merge(df_prezzi, df_impianti, on="idImpianto")
        df["prezzo"] = pd.to_numeric(df["prezzo"].str.replace(",", "."), errors="coerce")
        
        # FILTRO REGIONALE ESTESO
        df = df[df["Provincia"].isin(PROVINCE_NORD_EST)].copy()

        # Filtro Carburanti (Benzina e Gasolio)
        mask = (df["descCarburante"].str.contains("Benzina|Gasolio|Artico|100 ottani", case=False, na=False) & 
                ~df["descCarburante"].str.contains("Metano|GPL|LPG", case=False, na=False))
        df = df[mask].copy()

        # TROVA I PREZZI BASSISSIMI
        offerte = df[(df["prezzo"] <= SOGLIA_ALLERTA) & (df["prezzo"] >= SOGLIA_ERRORE_MIN)].copy()
        offerte = offerte.sort_values("prezzo")

        if offerte.empty:
            print("Nessun prezzo anomalo trovato nel Nord-Est.")
            return

        msg = f"<b>🚨 ALLERTA PREZZO NORD-EST! 🚨</b>\n"
        msg += f"<i>(Veneto, Trentino, Friuli)</i>\n"
        msg += f"Trovati {len(offerte)} distributori sotto {SOGLIA_ALLERTA}€\n\n"
        
        for _, row in offerte.iterrows():
            emoji = get_type_emoji(row["descCarburante"])
            lat = row["Latitudine"]
            lon = row["Longitudine"]
            maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            
            msg += (f"{emoji} <b>PREZZO: {row['prezzo']}€</b>\n"
                    f"⛽ {row['descCarburante']}\n"
                    f"📍 {row.get('Nome Impianto', 'N/D')}\n"
                    f"🏙️ {row['Comune']} ({row['Provincia']})\n"
                    f"🗺️ <a href='{maps_link}'>Apri su Google Maps</a>\n"
                    f"------------------------\n")

        send_msg(msg)

    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    check()
