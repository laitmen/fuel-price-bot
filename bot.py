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
SOGLIA_MINIMA = 0.11  # <--- NUOVO: Ignora tutto ciò che costa meno di 1€ (errori)
MAX_RESULTS = 5

# URL stabili con separatore PIPE (|)
URL_IMPIANTI = "https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv"
URL_PREZZI = "https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv"

HEADERS = {"User-Agent": "Mozilla/5.0"}

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)

def check():
    try:
        # Download
        r_prezzi = requests.get(URL_PREZZI, headers=HEADERS, timeout=60)
        r_impianti = requests.get(URL_IMPIANTI, headers=HEADERS, timeout=60)

        # Caricamento con separatore corretto "|"
        df_prezzi = pd.read_csv(io.BytesIO(r_prezzi.content), sep="|", skiprows=1, on_bad_lines="skip", dtype=str)
        df_impianti = pd.read_csv(io.BytesIO(r_impianti.content), sep="|", skiprows=1, on_bad_lines="skip", dtype=str)

        # Pulizia spazi nei nomi colonne
        df_prezzi.columns = df_prezzi.columns.str.strip()
        df_impianti.columns = df_impianti.columns.str.strip()

        # Merge
        df = pd.merge(df_prezzi, df_impianti, on="idImpianto")

        # Conversione prezzo
        df["prezzo"] = pd.to_numeric(df["prezzo"].str.replace(",", "."), errors="coerce")

        # FILTRO INTELLIGENTE:
        # Prende i prezzi minori della soglia MA maggiori di 1€ (per evitare i finti prezzi a 0.01€)
        offerte = df[(df["prezzo"] < SOGLIA_PREZZO) & (df["prezzo"] > SOGLIA_MINIMA)].copy()
        offerte = offerte.sort_values("prezzo")

        if offerte.empty:
            send_msg(f"✅ Scansione completata: nessun prezzo reale trovato sotto {SOGLIA_PREZZO}€.")
            return

        msg = f"⛽ Offerte Reali Trovate ({len(offerte)})\n\n"
        for _, row in offerte.head(MAX_RESULTS).iterrows():
            # Cerchiamo di prendere i nomi corretti dalle colonne del MIMIT
            nome = row.get("Nome Impianto", row.get("nomeImpianto", "Sconosciuto"))
            comune = row.get("Comune", "N/D")
            carburante = row.get("descCarburante", "Carburante")
            
            msg += f"📍 {nome} ({comune})\n💰 {row['prezzo']}€ - {carburante}\n\n"

        send_msg(msg)

    except Exception as e:
        send_msg(f"❌ Errore: {str(e)}")

if __name__ == "__main__":
    check()
