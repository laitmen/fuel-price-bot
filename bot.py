import pandas as pd
import requests
import os
import io

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SOGLIA_PREZZO = 1.90
SOGLIA_MINIMA = 0.11  # Ignora errori sotto 1€
MAX_RESULTS = 10      # Alziamo un po' il limite visto che filtriamo i tipi

URL_IMPIANTI = "https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv"
URL_PREZZI = "https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv"

HEADERS = {"User-Agent": "Mozilla/5.0"}

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)

def check():
    try:
        # Download dati
        r_prezzi = requests.get(URL_PREZZI, headers=HEADERS, timeout=60)
        r_impianti = requests.get(URL_IMPIANTI, headers=HEADERS, timeout=60)

        df_prezzi = pd.read_csv(io.BytesIO(r_prezzi.content), sep="|", skiprows=1, on_bad_lines="skip", dtype=str)
        df_impianti = pd.read_csv(io.BytesIO(r_impianti.content), sep="|", skiprows=1, on_bad_lines="skip", dtype=str)

        df_prezzi.columns = df_prezzi.columns.str.strip()
        df_impianti.columns = df_impianti.columns.str.strip()

        # Merge
        df = pd.merge(df_prezzi, df_impianti, on="idImpianto")

        # Conversione prezzo
        df["prezzo"] = pd.to_numeric(df["prezzo"].str.replace(",", "."), errors="coerce")

        # ==========================================================
        # NUOVO FILTRO CARBURANTI
        # Includiamo: Benzina, Gasolio (normale e artico), 100 ottani
        # Escludiamo: Metano, GPL, HiQ Perform+, ecc.
        # ==========================================================
        
        # Parole chiave ammesse
        keywords = "Benzina|Gasolio|Artico|100 ottani|Special"
        # Parole da escludere assolutamente (per sicurezza)
        exclude = "Metano|GPL|LPG|Perform"

        mask = (
            df["descCarburante"].str.contains(keywords, case=False, na=False) & 
            ~df["descCarburante"].str.contains(exclude, case=False, na=False)
        )
        
        df_filtrato = df[mask].copy()

        # Filtro prezzo
        offerte = df_filtrato[(df_filtrato["prezzo"] < SOGLIA_PREZZO) & (df_filtrato["prezzo"] > SOGLIA_MINIMA)].copy()
        offerte = offerte.sort_values("prezzo")

        if offerte.empty:
            send_msg(f"✅ Nessuna offerta per Benzina/Gasolio sotto {SOGLIA_PREZZO}€.")
            return

        msg = f"⛽ Offerte Carburante ({len(offerte)})\n"
        msg += "Focus: Benzina, Gasolio (Artico/100 oct)\n\n"

        for _, row in offerte.head(MAX_RESULTS).iterrows():
            nome = row.get("Nome Impianto", row.get("nomeImpianto", "Sconosciuto"))
            comune = row.get("Comune", "N/D")
            prezzo = row["prezzo"]
            tipo = row["descCarburante"]
            
            msg += f"📍 {nome} ({comune})\n💰 {prezzo}€ - {tipo}\n\n"

        send_msg(msg)

    except Exception as e:
        send_msg(f"❌ Errore bot: {str(e)}")

if __name__ == "__main__":
    check()
