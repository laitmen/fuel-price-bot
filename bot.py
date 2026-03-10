import pandas as pd
import requests
import os
import io

# =========================
# CONFIGURAZIONE CACCIATORE
# =========================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SOGLIA_ALLERTA = 1.50   # Ti avvisa solo se il prezzo è clamoroso (sotto 1.50)
SOGLIA_ERRORE_MIN = 0.05 # Per evitare i finti 0.01€, ma beccare i 0.90€ o 1.10€

# Province del Veneto
PROVINCE_VENETO = ["TV", "VE", "PD", "VI", "VR", "BL", "RO"]

URL_IMPIANTI = "https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv"
URL_PREZZI = "https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv"

HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_type_emoji(carburante):
    c = carburante.lower()
    return "🟢" if "benzina" in c else "⚫"

def send_msg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=15)

def check():
    try:
        # Scarico dati dal Ministero
        r_prezzi = requests.get(URL_PREZZI, headers=HEADERS, timeout=60)
        r_impianti = requests.get(URL_IMPIANTI, headers=HEADERS, timeout=60)

        df_prezzi = pd.read_csv(io.BytesIO(r_prezzi.content), sep="|", skiprows=1, on_bad_lines="skip", dtype=str)
        df_impianti = pd.read_csv(io.BytesIO(r_impianti.content), sep="|", skiprows=1, on_bad_lines="skip", dtype=str)

        df_prezzi.columns = df_prezzi.columns.str.strip()
        df_impianti.columns = df_impianti.columns.str.strip()

        # Unione dati
        df = pd.merge(df_prezzi, df_impianti, on="idImpianto")

        # Conversione prezzi
        df["prezzo"] = pd.to_numeric(df["prezzo"].str.replace(",", "."), errors="coerce")
        
        # Filtro per le province del Veneto
        df = df[df["Provincia"].isin(PROVINCE_VENETO)].copy()

        # Filtro Carburanti (solo Benzina e Gasolio)
        mask = (df["descCarburante"].str.contains("Benzina|Gasolio|Artico|100 ottani", case=False, na=False) & 
                ~df["descCarburante"].str.contains("Metano|GPL|LPG", case=False, na=False))
        df = df[mask].copy()

        # TROVA I PREZZI BASSISSIMI (Sotto 1.50)
        offerte = df[(df["prezzo"] <= SOGLIA_ALLERTA) & (df["prezzo"] >= SOGLIA_ERRORE_MIN)].copy()
        offerte = offerte.sort_values("prezzo")

        if offerte.empty:
            # Opzionale: decommenta la riga sotto se vuoi un messaggio di conferma ogni 30 min anche se non trova nulla
            # send_msg("✅ Scansione Veneto completata: nessun prezzo sotto 1.50€.")
            print("Nessuna anomalia trovata.")
            return

        msg = f"🚨 ALLERTA PREZZO VENETO! 🚨\n"
        msg += f"Trovati {len(offerte)} distributori sotto {SOGLIA_ALLERTA}€\n\n"
        
        for _, row in offerte.iterrows():
            emoji = get_type_emoji(row["descCarburante"])
            msg += (f"{emoji} PREZZO: {row['prezzo']}€\n"
                    f"⛽ {row['descCarburante']}\n"
                    f"📍 {row.get('Nome Impianto', 'N/D')}\n"
                    f"🏙️ {row['Comune']} ({row['Provincia']})\n"
                    f"------------------------\n")

        send_msg(msg)

    except Exception as e:
        print(f"Errore: {e}")
        # Non inviamo l'errore su telegram ogni volta per non spammare se il MIMIT è giù
        # send_msg(f"❌ Errore tecnico: {str(e)}")

if __name__ == "__main__":
    check()
