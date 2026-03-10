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
MAX_RESULTS = 5

URL_IMPIANTI = "https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv"
URL_PREZZI = "https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/csv"
}


# =========================
# TELEGRAM
# =========================

def send_msg(text):

    if not TOKEN or not CHAT_ID:
        print("Token o ChatID mancanti")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }

    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Errore Telegram:", e)


# =========================
# DOWNLOAD DATASET
# =========================

def download_csv(url):

    r = requests.get(url, headers=HEADERS, timeout=60)

    if r.status_code != 200:
        raise Exception(f"Errore download {url} -> {r.status_code}")

    return r.content


# =========================
# LOAD DATA
# =========================

def load_data():

    print("Scaricamento dataset MIMIT...")

    prezzi_raw = download_csv(URL_PREZZI)
    impianti_raw = download_csv(URL_IMPIANTI)

    print("Parsing CSV...")

    df_prezzi = pd.read_csv(
        io.BytesIO(prezzi_raw),
        sep="|",
        skiprows=1,
        on_bad_lines="skip",
        dtype=str
    )

    df_impianti = pd.read_csv(
        io.BytesIO(impianti_raw),
        sep="|",
        skiprows=1,
        on_bad_lines="skip",
        dtype=str
    )

    return df_prezzi, df_impianti


# =========================
# PROCESS DATA
# =========================

def process_data(df_prezzi, df_impianti):

    print("Pulizia dati...")

    df_prezzi.columns = df_prezzi.columns.str.strip()
    df_impianti.columns = df_impianti.columns.str.strip()

    print("Merge dataset...")

    df = pd.merge(
        df_prezzi,
        df_impianti,
        on="idImpianto",
        how="inner"
    )

    print("Conversione prezzi...")

    df["prezzo"] = (
        df["prezzo"]
        .astype(str)
        .str.replace(",", ".")
    )

    df["prezzo"] = pd.to_numeric(
        df["prezzo"],
        errors="coerce"
    )

    return df


# =========================
# TROVA OFFERTE
# =========================

def find_offers(df):

    offerte = df[df["prezzo"] < SOGLIA_PREZZO].copy()

    offerte = offerte.sort_values("prezzo")

    return offerte


# =========================
# FORMAT MESSAGGIO
# =========================

def build_message(offerte):

    if offerte.empty:
        return f"✅ Nessun prezzo sotto {SOGLIA_PREZZO}€"

    msg = f"⛽ Offerte trovate ({len(offerte)})\n\n"

    for _, row in offerte.head(MAX_RESULTS).iterrows():

        nome = row.get("NomeImpianto", "N/D")
        comune = row.get("Comune", "N/D")
        carburante = row.get("descCarburante", "Carburante")
        prezzo = row.get("prezzo", "N/D")

        msg += (
            f"📍 {nome} ({comune})\n"
            f"💰 {prezzo}€ - {carburante}\n\n"
        )

    return msg


# =========================
# MAIN
# =========================

def check():

    try:

        df_prezzi, df_impianti = load_data()

        df = process_data(df_prezzi, df_impianti)

        offerte = find_offers(df)

        msg = build_message(offerte)

        send_msg(msg)

        print("Completato")

    except Exception as e:

        err = f"❌ Errore bot carburanti:\n{str(e)}"

        print(err)

        send_msg(err)


# =========================

if __name__ == "__main__":
    check()
