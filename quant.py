import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as grp
from plotly.subplots import make_subplots
import requests
import json
import matplotlib.pyplot as plt
from arch import arch_model
from scipy import stats
from scipy.signal import argrelextrema
import os
import re
import base64
from dotenv import load_dotenv
from urllib.parse import quote


# Carica le chiavi dal file .env (se presente)
load_dotenv()

st.set_page_config(layout="wide", page_title="POC Scanner Pro", page_icon="📐")


# ==============================================================================
# --- SCHERMATA DI ACCESSO (LOGIN PAGE CON SFONDO PERSONALIZZATO) ---
# ==============================================================================
if "autenticato" not in st.session_state:
    st.session_state["autenticato"] = False

# Legge eventuali parametri URL in arrivo da Telegram prima del login
params_init = st.query_params
if "ticker" in params_init and not st.session_state.get("url_gia_letto", False):
    tk_url = str(params_init["ticker"]).upper().strip()
    tf_url = str(params_init.get("tf", "Giornaliero (Daily)")).strip()
    st.session_state["menu_navigazione_moduli"] = "🧪 TradingView Pro"
    st.session_state["tv_test_tk"] = tk_url
    st.session_state["can_tk"] = tk_url
    st.session_state["can_tf"] = tf_url
    st.session_state["url_gia_letto"] = True

def _get_base64_bg(percorso_img):
    if os.path.exists(percorso_img):
        with open(percorso_img, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

if not st.session_state["autenticato"]:
    bg_b64 = _get_base64_bg("sfondo_login.png")
    bg_css = (
        f"background-image: linear-gradient(rgba(7, 8, 13, 0.45), rgba(7, 8, 13, 0.72)), url('data:image/png;base64,{bg_b64}');"
        if bg_b64
        else "background: radial-gradient(circle at top right, #111524 0%, #07080d 100%);"
    )

    st.markdown(f"""
    <style>
        /* Nasconde sidebar e header nella pagina di login */
        section[data-testid="stSidebar"] {{ display: none !important; }}
        header[data-testid="stHeader"] {{ background: transparent !important; }}

        /* Sfondo a tutto schermo con l'immagine caricata */
        .stApp {{
            {bg_css}
            background-size: cover !important;
            background-position: center center !important;
            background-attachment: fixed !important;
        }}

        /* Box vetro scuro compatto centrato per il form di login */
        div[data-testid="stForm"] {{
            background: rgba(9, 11, 17, 0.72) !important;
            backdrop-filter: blur(10px) !important;
            border: 1px solid rgba(56, 189, 248, 0.35) !important;
            border-radius: 16px !important;
            padding: 18px 20px !important;
            max-width: 350px !important;
            margin: 0 auto !important;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.8) !important;
        }}

        div[data-testid="stForm"] input {{
            background-color: rgba(15, 23, 42, 0.88) !important;
            color: #f8fafc !important;
            border: 1px solid #334155 !important;
            border-radius: 8px !important;
            padding: 6px 10px !important;
            font-size: 13px !important;
        }}

        div[data-testid="stFormSubmitButton"] > button {{
            background: linear-gradient(135deg, #2563eb 0%, #dc2626 100%) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            font-size: 13px !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.45rem 1rem !important;
            width: 100% !important;
            margin-top: 6px !important;
        }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 12vh;'></div>", unsafe_allow_html=True)

    col_sx, col_centro, col_dx = st.columns([1.4, 1.6, 1.4])
    with col_centro:
        with st.form("form_login_quant"):
            st.markdown("""
                <div style='text-align: center; margin-bottom: 18px;'>
                    <h2 style='margin:0; color:#f8fafc; font-weight:700;'>📐 QUANTANALISYS PRO</h2>
                    <p style='margin:4px 0 0 0; color:#94a3b8; font-size:14px;'>Area Riservata — Inserisci le credenziali di accesso</p>
                </div>
            """, unsafe_allow_html=True)

            user_in = st.text_input("👤 Nome Utente", placeholder="Inserisci username...")
            pass_in = st.text_input("🔑 Password", type="password", placeholder="Inserisci password...")
            submit_login = st.form_submit_button("🚀 Accedi alla Dashboard")

            if submit_login:
                user_corretto = os.getenv("APP_USERNAME", "admin")
                pass_corretta = os.getenv("APP_PASSWORD", "1234")

                if user_in.strip() == user_corretto and pass_in == pass_corretta:
                    st.session_state["autenticato"] = True
                    st.rerun()
                else:
                    st.error("❌ Credenziali non valide. Riprova.")

    st.stop()


# ==============================================================================
# STILE DARK PREMIUM DA PREVIEW GRAFICA (SIDEBAR COORDINATA)
# ==============================================================================
st.markdown("""
<style>
    
    /* Riduce leggermente il font dei valori delle metriche per evitare troncamenti */
    div[data-testid="stMetricValue"] > div {
        font-size: 1.55rem !important;
        white-space: normal !important;
        line-height: 1.2 !important;
    }

    /* Forza il puntatore standard (freccia) su tutti i grafici Plotly */
    .js-plotly-plot .plotly .cursor-crosshair,
    .js-plotly-plot .plotly .cursor-move,
    .js-plotly-plot .plotly .cursor-pointer,
    .js-plotly-plot .plotly .nsewdrag,
    .js-plotly-plot .plotly .drag,
    .js-plotly-plot .plotly svg {
        cursor: default !important;
    }

    @import url('https://googleapis.com');
    
    /* Sfondo principale con gradiente radiale scuro */
    .stApp { 
        background: radial-gradient(circle at top right, #111524 0%, #07080d 100%) !important; 
        font-family: 'Plus Jakarta Sans', sans-serif !important; 
        color: #f1f5f9 !important; 
    }
    
    /* Barra Laterale (Sidebar) Hi-Tech */
    section[data-testid="stSidebar"] {
        background-color: #090b11 !important;
        border-right: 1px solid rgba(56, 189, 248, 0.08) !important;
    }
    
    /* Nasconde il pallino nativo brutto dei radio button di Streamlit */
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label [data-testid="stWidgetBorder"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] [data-testid="stMarkdownContainer"] p {
        font-size: 14px !important;
        font-weight: 600 !important;
    }
    
    /* Trasforma i testi dei radio button in pulsanti rettangolari con icone visibili */
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        background: rgba(255, 255, 255, 0.01) !important;
        border: 1px solid rgba(255, 255, 255, 0.03) !important;
        padding: 12px 16px !important;
        border-radius: 10px !important;
        margin-bottom: 8px !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex !important;
        align-items: center !important;
        color: #94a3b8 !important;
        cursor: pointer !important;
    }
    
    /* Effetto Hover sulle voci del menu laterale */
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background: rgba(56, 189, 248, 0.04) !important;
        border-color: rgba(56, 189, 248, 0.2) !important;
        color: #38bdf8 !important;
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.05);
    }
    
    /* STATO ATTIVO SELEZIONATO: Pulsante illuminato al neon a sinistra */
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] [data-checked="true"] {
        background: linear-gradient(90deg, rgba(79, 70, 229, 0.15) 0%, rgba(59, 130, 246, 0.05) 100%) !important;
        border-color: rgba(56, 189, 248, 0.6) !important;
        color: #38bdf8 !important;
        font-weight: 700 !important;
        box-shadow: inset 3px 0px 0px #38bdf8, 0 4px 20px rgba(56, 189, 248, 0.1);
    }
    
    /* Box delle metriche finanziarie stile Frosted Glass */
    div[data-testid="stMetric"] { 
        background: rgba(13, 17, 28, 0.7) !important; 
        border: 1px solid rgba(56, 189, 248, 0.1) !important; 
        border-radius: 12px !important; 
        backdrop-filter: blur(12px);
    }
    
    /* Bottoni di azione con gradiente lineare */
    div.stButton > button:first-child { 
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important; 
        color: #ffffff !important; 
        font-weight: 600 !important; 
        border-radius: 10px !important; 
        padding: 0.7rem 2.2rem !important; 
        border: none !important;
    }
    
    /* Input e selettori a tendina coordinati scuri */
    div[data-baseweb="select"], input, textarea { 
        background-color: #0f172a !important; 
        border-color: #334155 !important; 
        color: #f8fafc !important; 
    }
</style>
""", unsafe_allow_html=True)

if "asset_type_index" not in st.session_state:
    st.session_state.asset_type_index = 0

# PROTEZIONE: Recupero sicuro dei dati sensibili dall'ambiente
T_ID = os.getenv("TELEGRAM_CHAT_ID", "2072895073")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TESTA_INTERNET = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
# ==============================================================================
# MOTORE UNIVERSALE PANIERI GIORNALIERI (USA, ITALIA, EUROPA, CRYPTO TOTAL 1-3)
# ==============================================================================
FALLBACK_USA = "AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,BRK-B,JPM,V,AVGO,COST,NFLX,AMD,PLTR"
FALLBACK_ITA = (
    "A2A.MI,ACE.MI,ADB.MI,AEF.MI,AMP.MI,ANIM.MI,AP.MI,ARN.MI,ASC.MI,AVIO.MI,AZM.MI,BAMI.MI,BC.MI,BDB.MI,BEC.MI,"
    "BF.MI,BFE.MI,BGN.MI,BIES.MI,BMED.MI,BMPS.MI,BND.MI,BPER.MI,BPSO.MI,BRE.MI,BSS.MI,CAI.MI,CAR.MI,CE.MI,CEM.MI,"
    "CIR.MI,CMB.MI,CPR.MI,CSP.MI,DAL.MI,DAN.MI,DBG.MI,DEA.MI,DEL.MI,DIA.MI,DLG.MI,DOV.MI,ELN.MI,EM.MI,ENAV.MI,"
    "ENEL.MI,ENI.MI,EQU.MI,ERG.MI,ETH.MI,EVO.MI,EXAI.MI,FBK.MI,FILA.MI,FIN.MI,FNM.MI,G.MI,GABET.MI,GAR.MI,GEF.MI,"
    "GPI.MI,GVS.MI,HER.MI,IG.MI,IGD.MI,ILL.MI,IND.MI,INT.MI,INW.MI,IP.MI,IRCE.MI,IRE.MI,ISP.MI,ITM.MI,IVG.MI,"
    "JUVE.MI,LDB.MI,LDO.MI,LIT.MI,LUCE.MI,LVE.MI,MAIRE.MI,MARR.MI,MB.MI,MOL.MI,MON.MI,MONC.MI,MS.MI,MT.MI,MTP.MI,"
    "NEXI.MI,NEWL.MI,NOE.MI,NR.MI,NVT.MI,OVS.MI,PHN.MI,PIA.MI,PINF.MI,PIRC.MI,PLC.MI,PLT.MI,POL.MI,PRT.MI,PRY.MI,"
    "PST.MI,RACE.MI,REC.MI,RWAY.MI,SAB.MI,SAES.MI,SAL.MI,SBS.MI,SER.MI,SES.MI,SFER.MI,SIT.MI,SL.MI,SOL.MI,SOM.MI,"
    "SPM.MI,SRG.MI,SRS.MI,SSL.MI,STAR7.MI,STLAM.MI,STMPA.MI,SWT.MI,TEN.MI,TGYM.MI,TIP.MI,TISG.MI,TPRO.MI,TRN.MI,"
    "TXT.MI,UCG.MI,UNI.MI,UNIR.MI,US.MI,VAL.MI,VLA.MI,WIIT.MI,ZIGN.MI"
)

FALLBACK_EU = (
    "ASML.AS,SAP.DE,MC.PA,OR.PA,SIE.DE,TTE.PA,SAN.MC,ALV.DE,AIR.PA,SU.PA,DTE.DE,IBE.MC,BNP.PA,CS.PA,ENEL.MI,ISP.MI,"
    "UCG.MI,ENI.MI,RACE.MI,STLAM.MI,PRX.AS,INGA.AS,AD.AS,ABI.BR,BAS.DE,BAYN.DE,BMW.DE,MBG.DE,VOW3.DE,ADS.DE,DBK.DE,"
    "CBK.DE,DPW.DE,IFX.DE,MUV2.DE,RWE.DE,EOAN.DE,HEN3.DE,MRK.DE,FRE.DE,HEI.DE,MTX.DE,SY1.DE,ZAL.DE,KER.PA,RMS.PA,"
    "EL.PA,DG.PA,AI.PA,SAF.PA,SGO.PA,CAP.PA,DSY.PA,STMPA.PA,ORA.PA,VIV.PA,ENGI.PA,GLE.PA,ACA.PA,CA.PA,ML.PA,RI.PA,"
    "BBVA.MC,ITX.MC,TEF.MC,REP.MC,AMS.MC,FER.MC,ELE.MC,CLNX.MC,AENA.MC,NOKIA.HE,NESTE.HE,KNEBV.HE,UPM.HE"
)

FALLBACK_CRYPTO = (
    "BTC-USD,ETH-USD,USDT-USD,XRP-USD,BNB-USD,SOL-USD,DOGE-USD,ADA-USD,TRX-USD,AVAX-USD,SHIB-USD,TON-USD,LINK-USD,"
    "DOT-USD,XLM-USD,BCH-USD,SUI-USD,LTC-USD,PEPE-USD,NEAR-USD,UNI-USD,APT-USD,ICP-USD,ETC-USD,POL-USD,RENDER-USD,"
    "FET-USD,VET-USD,ARB-USD,FIL-USD,ATOM-USD,OP-USD,INJ-USD,IMX-USD,STX-USD,GRT-USD,AAVE-USD,THETA-USD,ALGO-USD,"
    "FTM-USD,RUNE-USD,SAND-USD,MANA-USD,AXS-USD,EGLD-USD,FLOW-USD,XTZ-USD,EOS-USD,GALA-USD,CHZ-USD,CRV-USD,LDO-USD,"
    "MKR-USD,SNX-USD,COMP-USD,DYDX-USD,ENS-USD,1INCH-USD,ZEC-USD,DASH-USD,KAVA-USD,CELO-USD,BAT-USD,ZIL-USD,ENJ-USD"
)

GERARCHIA_MERCATI = {
    "🇺🇸 USA": {
        "S&P 500": ["Large Cap (>10B)", "Tutte (500 titoli)"],
        "NASDAQ (Tutti / Tech)": ["Large Cap (>10B)", "Mid Cap (2B–10B)", "Small Cap (300M–2B)"],
        "NASDAQ 100": ["Large Cap (>10B)"],
        "NYSE (New York Stock Exchange)": ["Large Cap (>10B)", "Mid Cap (2B–10B)", "Small Cap (300M–2B)"],
    },
    "🇮🇹 Italia (Borsa Italiana)": {
        "FTSE MIB": ["Large Cap (>10B)"],
        "FTSE Italia Mid Cap": ["Mid Cap (2B–10B)"],
        "FTSE Italia Small Cap": ["Small Cap (300M–2B)"],
        "Tutte (.MI Completo)": ["Tutte le Cap"],
    },
    "🇪🇺 Europa": {
        "EURO STOXX 50": ["Large Cap (>10B)"],
        "DAX 40 (Germania .DE)": ["Large Cap (>10B)"],
        "CAC 40 (Francia .PA)": ["Large Cap (>10B)"],
        "IBEX 35 (Spagna .MC)": ["Large Cap (>10B)"],
        "AEX 25 (Olanda .AS)": ["Large Cap (>10B)"],
        "Europa Top 300 (Combinato)": ["Large Cap (>10B)"],
    },
    "🪙 Crypto": {
        "TOTAL 1 & 2 (Top 30)": ["Large Cap (>10B)"],
        "TOTAL 3 Altcoins (Rank 31–200)": ["Mid / Small Cap"],
    }
}
def _parse_market_cap(val):
    try:
        if val is None or val == "" or str(val).upper() in ("NA", "N/A", "NONE"):
            return 0.0
        s = str(val).replace("$", "").replace(",", "").strip().upper()
        if s.endswith("T"):
            return float(s[:-1]) * 1e12
        if s.endswith("B"):
            return float(s[:-1]) * 1e9
        if s.endswith("M"):
            return float(s[:-1]) * 1e6
        return float(s)
    except Exception:
        return 0.0

@st.cache_data(ttl=86400, show_spinner=False)
def scarica_paniere_universale(macro_mercato, borsa_indice, cap_scelta):
    headers_nq = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/"
    }
    motivo_err = ""

    def _filtra_cap_usa(rows_list):
        out = []
        for r in rows_list:
            sym = str(r.get("symbol", "")).strip()
            if not sym or "^" in sym or "/" in sym or "." in sym or len(sym) > 5:
                continue
            mc = _parse_market_cap(r.get("marketCap", "0"))
            if "Large Cap" in cap_scelta and mc >= 10_000_000_000:
                out.append(sym)
            elif "Mid Cap" in cap_scelta and 2_000_000_000 <= mc < 10_000_000_000:
                out.append(sym)
            elif "Small Cap" in cap_scelta and 300_000_000 <= mc < 2_000_000_000:
                out.append(sym)
            elif "Tutte" in cap_scelta:
                out.append(sym)
        return list(dict.fromkeys(out))

    try:
        # 1. USA — Usa esclusivamente l'endpoint ufficiale NASDAQ Screener
        if "USA" in macro_mercato:
            if borsa_indice == "S&P 500":
                url_sp = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true"
                res = requests.get(url_sp, headers=headers_nq, timeout=15)
                if res.status_code == 200:
                    rows_all = res.json().get("data", {}).get("rows", [])
                    cand = []
                    for r in rows_all:
                        sym = str(r.get("symbol", "")).strip()
                        if not sym or "^" in sym or "/" in sym or "." in sym or len(sym) > 5:
                            continue
                        mc = _parse_market_cap(r.get("marketCap", "0"))
                        if mc > 0:
                            cand.append((sym, mc))
                    # Top 500 società USA per Market Cap decrescente (S&P 500)
                    cand.sort(key=lambda x: x, reverse=True)
                    top_500 = cand[:500]
                    if "Large Cap" in cap_scelta:
                        selezionati = [s for s, mc in top_500 if mc >= 10_000_000_000]
                    else:
                        selezionati = [s for s, _ in top_500]
                    if len(selezionati) > 20:
                        return ",".join(selezionati), f"🌐 Live S&P 500 ({len(selezionati)} titoli)"
                motivo_err = f"HTTP {res.status_code}"

            elif borsa_indice == "NASDAQ 100":
                url_nq100 = "https://nasdaq.com"
                res = requests.get(url_nq100, headers=headers_nq, timeout=15)
                if res.status_code == 200:
                    rows_nq = res.json().get("data", {}).get("rows", [])
                    cand_nq = []
                    for r in rows_nq:
                        sym = str(r.get("symbol", "")).strip()
                        if not sym or "^" in sym or "/" in sym or "." in sym or len(sym) > 5:
                            continue
                        mc = _parse_market_cap(r.get("marketCap", "0"))
                        if mc > 0:
                            cand_nq.append((sym, mc))
                    cand_nq.sort(key=lambda x: x, reverse=True)
                    nq_syms = [s for s, _ in cand_nq[:100]]
                    if len(nq_syms) >= 50:
                        return ",".join(nq_syms), f"🌐 Live NASDAQ 100 ({len(nq_syms)} titoli)"
                motivo_err = f"HTTP {res.status_code}"

            else:
                exch_param = "&exchange=NASDAQ" if "NASDAQ" in borsa_indice else ("&exchange=NYSE" if "NYSE" in borsa_indice else "")
                url_us = f"https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0{exch_param}&download=true"
                res = requests.get(url_us, headers=headers_nq, timeout=15)
                if res.status_code == 200:
                    selezionati = _filtra_cap_usa(res.json().get("data", {}).get("rows", []))
                    if len(selezionati) > 15:
                        return ",".join(selezionati), f"🌐 Live {borsa_indice} ({len(selezionati)} titoli)"
                motivo_err = f"HTTP {res.status_code}"

        # 2. ITALIA
        elif "Italia" in macro_mercato:
            mappa_wiki_it = {
                "FTSE MIB": ["https://wikipedia.org"],
                "FTSE Italia Mid Cap": ["https://wikipedia.org"],
                "FTSE Italia Small Cap": ["https://wikipedia.org"],
                "Tutte (.MI Completo)": [
                    "https://wikipedia.org",
                    "https://wikipedia.org",
                    "https://wikipedia.org"
                ]
            }
            tutti_it = []
            for url_w in mappa_wiki_it.get(borsa_indice, []):
                resp_w = requests.get(url_w, headers=headers_nq, timeout=10)
                if resp_w.status_code == 200:
                    tutti_it.extend(re.findall(r"\b([A-Z0-9]{2,6}\.MI)\b", resp_w.text))
            tutti_it = list(dict.fromkeys(tutti_it))
            if len(tutti_it) >= 15:
                return ",".join(tutti_it), f"🌐 Live {borsa_indice} ({len(tutti_it)} titoli .MI)"

        # 3. EUROPA
        elif "Europa" in macro_mercato:
            mappa_wiki_eu = {
                "EURO STOXX 50": ["https://wikipedia.org"],
                "DAX 40 (Germania .DE)": ["https://wikipedia.org"],
                "CAC 40 (Francia .PA)": ["https://wikipedia.org"],
                "IBEX 35 (Spagna .MC)": ["https://wikipedia.org"],
                "AEX 25 (Olanda .AS)": ["https://wikipedia.org"],
                "Europa Top 300 (Combinato)": [
                    "https://wikipedia.org",
                    "https://wikipedia.org",
                    "https://wikipedia.org",
                    "https://wikipedia.org",
                    "https://wikipedia.org"
                ]
            }
            tutti_eu = []
            for url_w in mappa_wiki_eu.get(borsa_indice, []):
                resp_w = requests.get(url_w, headers=headers_nq, timeout=10)
                if resp_w.status_code == 200:
                    tutti_eu.extend(re.findall(r"\b([A-Z0-9]{2,6}\.(?:DE|PA|AS|MC|MI|BR|HE))\b", resp_w.text))
            tutti_eu = list(dict.fromkeys(tutti_eu))
            if len(tutti_eu) >= 15:
                return ",".join(tutti_eu), f"🌐 Live {borsa_indice} ({len(tutti_eu)} titoli)"

        # 4. CRYPTO (Endpoint Ufficiale CoinPaprika Tickers — Top 2.000 per Market Cap, Zero API Key)
        elif "Crypto" in macro_mercato:
            stable = {
                "USDT", "USDC", "DAI", "FDUSD", "TUSD", "USDE", "BUSD", "USDS",
                "PYUSD", "FRAX", "USDD", "EUR", "AEUR", "EURI", "WBTC", "STETH", "WSTETH",
                "CBBTC", "USD1", "USYC", "RLUSD"
            }
            url_cp = "https://api.coinpaprika.com/v1/tickers"
            res_cp = requests.get(url_cp, headers={"Accept": "application/json"}, timeout=15)
            if res_cp.status_code == 200:
                dati_cp = res_cp.json()
                # Ordina per rank ufficiale (1 = Bitcoin, 2 = Ethereum, ecc.) ed esclude stablecoin/wrapped
                dati_cp.sort(key=lambda x: int(x.get("rank") or 999999))
                coins = []
                for c in dati_cp:
                    sym = str(c.get("symbol", "")).strip().upper()
                    if sym and sym not in stable and sym.isalnum():
                        coins.append(f"{sym}-USD")
                coins = list(dict.fromkeys(coins))

                if len(coins) >= 50:
                    if "TOTAL 1 & 2" in borsa_indice:
                        lista_c = coins[:30]
                    else:
                        # TOTAL 3: tutte le Altcoins dal rank #31 al #280
                        lista_c = coins[30:280]
                    return ",".join(lista_c), f"🌐 Live CoinPaprika API ({len(lista_c)} crypto)"
            motivo_err = f"CP HTTP {res_cp.status_code}"

    except Exception as ex:
        motivo_err = str(ex)[:40]

    info_extra = f" ({motivo_err})" if motivo_err else ""
    if "Italia" in macro_mercato:
        return FALLBACK_ITA, f"📋 Listino Italia ({len(FALLBACK_ITA.split(','))} titoli .MI){info_extra}"
    if "Europa" in macro_mercato:
        return FALLBACK_EU, f"📋 Listino Europa ({len(FALLBACK_EU.split(','))} titoli){info_extra}"
    if "Crypto" in macro_mercato:
        all_c = FALLBACK_CRYPTO.split(",")
        sub_c = all_c[:25] if "TOTAL 1 & 2" in borsa_indice else all_c[25:]
        return ",".join(sub_c), f"📋 Listino Crypto ({len(sub_c)} asset){info_extra}"
    return FALLBACK_USA, f"📋 Listino USA ({len(FALLBACK_USA.split(','))} titoli){info_extra}"


@st.cache_data(ttl=1800, show_spinner=False)
def scansiona_poc_paniere(lista_tickers, timeframe="1d", giorni_recenti=90):
    risultati = []

    def _estrai_df_singolo(df_raw, simbolo):
        if df_raw is None or df_raw.empty:
            return pd.DataFrame()
        if isinstance(df_raw.columns, pd.MultiIndex):
            if simbolo not in df_raw.columns.get_level_values(0):
                return pd.DataFrame()
            return df_raw[simbolo].dropna(subset=["Close", "High", "Low"])
        return df_raw.dropna(subset=["Close", "High", "Low"])

    for i in range(0, len(lista_tickers), 25):
        blocco = lista_tickers[i:i + 25]
        try:
            df_batch = yf.download(
                tickers=blocco,
                period="max",
                interval=timeframe,
                group_by="ticker",
                auto_adjust=False,
                threads=False,
                progress=False
            )
        except Exception:
            df_batch = pd.DataFrame()

        for tk in blocco:
            dec = 4 if "-USD" in tk else 2
            df_t = _estrai_df_singolo(df_batch, tk)

            if len(df_t) < 5:
                import time
                for per_try in ["5y", "2y"]:
                    try:
                        time.sleep(0.2)
                        df_sing = yf.download(
                            tickers=tk,
                            period=per_try,
                            interval=timeframe,
                            auto_adjust=False,
                            multi_level_index=False,
                            progress=False
                        )
                        df_t = _estrai_df_singolo(df_sing, tk)
                        if len(df_t) >= 5:
                            break
                    except Exception:
                        continue



            if len(df_t) >= 5:
                if "Volume" not in df_t.columns or df_t["Volume"].fillna(0).sum() <= 0:
                    df_t = df_t.copy()
                    df_t["Volume"] = 1.0

                p_att = float(df_t["Close"].iloc[-1])
                d_ath = df_t["High"].idxmax()
                df_ath = df_t.loc[d_ath:] if len(df_t.loc[d_ath:]) >= 5 else df_t.tail(min(15, len(df_t)))
                df_rec = df_t.tail(min(giorni_recenti, len(df_t)))

                poc_1, _, _, _, _ = calc_vp(df_t, div=100)
                poc_2, _, _, _, _ = calc_vp(df_ath, div=80)
                poc_3, _, _, _, _ = calc_vp(df_rec, div=80)

                poc_1 = poc_1 if poc_1 is not None else p_att
                poc_2 = poc_2 if poc_2 is not None else p_att
                poc_3 = poc_3 if poc_3 is not None else p_att

                d1_pct = round(((p_att - poc_1) / poc_1) * 100.0, 2) if poc_1 > 0 else 0.0
                d2_pct = round(((p_att - poc_2) / poc_2) * 100.0, 2) if poc_2 > 0 else 0.0
                d3_pct = round(((p_att - poc_3) / poc_3) * 100.0, 2) if poc_3 > 0 else 0.0

                allineamento = (
                    "🟢 FULL LONG" if (p_att >= poc_1 and p_att >= poc_2 and p_att >= poc_3)
                    else "🔴 FULL SHORT" if (p_att < poc_1 and p_att < poc_2 and p_att < poc_3)
                    else "🟡 MISTO"
                )
                risultati.append({
                    "Ticker": tk,
                    "Prezzo": round(p_att, dec),
                    "POC Storico": round(poc_1, dec),
                    "Dist. Storico %": d1_pct,
                    "POC ATH": round(poc_2, dec),
                    "Dist. ATH %": d2_pct,
                    "POC Recente": round(poc_3, dec),
                    "Dist. Recente %": d3_pct,
                    "Regime 3-POC": allineamento
                })
            else:
                risultati.append({
                    "Ticker": tk,
                    "Prezzo": None,
                    "POC Storico": None,
                    "Dist. Storico %": None,
                    "POC ATH": None,
                    "Dist. ATH %": None,
                    "POC Recente": None,
                    "Dist. Recente %": None,
                    "Regime 3-POC": "⚪ N/D (Dati non disp.)"
                })

    return pd.DataFrame(risultati)

    return pd.DataFrame(risultati)
def invia_messaggio_telegram_sbloccato(chat_id, testo_messaggio):
    if not BOT_TOKEN:
        return False
    payload = {"chat_id": int(chat_id), "text": str(testo_messaggio), "parse_mode": "HTML", "disable_web_page_preview": False}
    try:
        # PROTEZIONE: URL composto dinamicamente usando la variabile d'ambiente
        url_pulito = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        res = requests.post(url_pulito, data=json.dumps(payload), headers=TESTA_INTERNET, timeout=12)
        return res.status_code == 200
    except Exception:
        return False

def calc_vp(df, div=200):
    if df.empty: return None, None, None, [], []
    p_min, p_max = float(df['Low'].min()), float(df['High'].max())
    if p_max - p_min <= 0: return p_min, p_min, p_min, [], []
    bins = np.linspace(p_min, p_max, div + 1)
    vols = np.zeros(div)
    highs, lows, volumes = df['High'].values, df['Low'].values, df['Volume'].values
    for h, l, v in zip(highs, lows, volumes):
        if v <= 0 or h == l: continue
        mask = (bins[1:] >= l) & (bins[:-1] <= h)
        vols[mask] += v / max(1, np.sum(mask))
    prices = [float((bins[i] + bins[i+1]) / 2) for i in range(div)]
    vols_list = vols.tolist()
    poc_idx = vols_list.index(max(vols_list))
    poc = prices[poc_idx]
    v_total, v_target = sum(vols_list), sum(vols_list) * 0.70
    v_current, idx_b, idx_a = vols_list[poc_idx], poc_idx, poc_idx
    while v_current < v_target:
        v_s = vols_list[idx_b - 1] if idx_b > 0 else 0
        v_p = vols_list[idx_a + 1] if idx_a < div - 1 else 0
        if v_s == 0 and v_p == 0: break
        if v_s >= v_p: idx_b -= 1; v_current += v_s
        else: idx_a += 1; v_current += v_p
    return poc, prices[min(div - 1, idx_a)], prices[max(0, idx_b)], prices, vols_list

def rileva_wedge_e_marubozu(df_in, finestra=35, soglia_corpo_pct=75.0):
    res_default = {
        "wedge_valido": False, "breakout_marubozu": False,
        "x_dates": [], "upper_y": [], "lower_y": [],
        "upper_oggi": 0.0, "pct_corpo": 0.0,
        "marubozu_list": []
    }
    if df_in is None or len(df_in) < finestra:
        return res_default

    sub = df_in.tail(finestra).copy()
    x_idx = np.arange(len(sub))
    highs = sub["High"].astype(float).values
    lows = sub["Low"].astype(float).values
    opens = sub["Open"].astype(float).values
    closes = sub["Close"].astype(float).values

    maru_found = []
    for k in range(len(sub)):
        rng = highs[k] - lows[k]
        if rng > 0:
            body = abs(closes[k] - opens[k])
            pct = (body / rng) * 100.0
            if pct >= soglia_corpo_pct:
                is_bull = closes[k] > opens[k]
                maru_found.append({
                    "date": sub.index[k],
                    "price": highs[k] if is_bull else lows[k],
                    "is_bull": is_bull,
                    "pct": round(pct, 1)
                })
    res_default["marubozu_list"] = maru_found

    m_up, q_up = np.polyfit(x_idx[:-1], highs[:-1], 1)
    m_low, q_low = np.polyfit(x_idx[:-1], lows[:-1], 1)

    if m_up < 0 and m_low < 0 and m_up < m_low:
        upper_line = m_up * x_idx + q_up
        lower_line = m_low * x_idx + q_low

        o_last, c_last = float(opens[-1]), float(closes[-1])
        h_last, l_last = float(highs[-1]), float(lows[-1])
        pct_last = round((abs(c_last - o_last) / max(1e-6, h_last - l_last)) * 100.0, 1)
        upper_oggi = float(upper_line[-1])
        is_breakout = (c_last > o_last) and (c_last > upper_oggi) and (pct_last >= soglia_corpo_pct)

        res_default.update({
            "wedge_valido": True,
            "breakout_marubozu": is_breakout,
            "x_dates": sub.index.tolist(),
            "upper_y": upper_line.tolist(),
            "lower_y": lower_line.tolist(),
            "upper_oggi": upper_oggi,
            "pct_corpo": pct_last
        })

    return res_default


# ==============================================================================
# STRUTTURA DI NAVIGAZIONE LATERALE (SIDEBAR) CON TAB VERTICALI A SCOMPARSA
# ==============================================================================
with st.sidebar:
    if os.path.exists("logo_fmjp.png"):
        st.image("logo_fmjp.png", use_container_width=True)
    st.markdown("## 📺 Seleziona l'analisi che vuoi approfondire:")
    st.markdown("🤖 **Menu Navigazione Moduli**")

    opzioni_menu = [
        "🧪 TradingView Pro",
        "📁 Analisi Triple-POC",
        "📈 Analisi GARCH Volatilità",
    ]

    if "jump_to_modulo" in st.session_state and st.session_state["jump_to_modulo"]:
        st.session_state["menu_navigazione_moduli"] = st.session_state.pop("jump_to_modulo")

    modulo_corrente = st.session_state.get("menu_navigazione_moduli", opzioni_menu[0])
    idx_default = opzioni_menu.index(modulo_corrente) if modulo_corrente in opzioni_menu else 0

    scelta_modulo = st.radio(
        label="Seleziona Modulo Operativo:",
        options=opzioni_menu,
        index=idx_default,
        label_visibility="collapsed",
        key="menu_navigazione_moduli",
    )
    
    st.markdown("---")
    if st.button("🔒 Disconnetti (Logout)", use_container_width=True):
        st.session_state["autenticato"] = False
        st.rerun()


    st.markdown("---")
    st.caption("Quant Framework Dashboard Pro v3.0 📐")

# Configurazione del Titolo dinamico della pagina principale
st.title(f"{scelta_modulo}")

# ==============================================================================
# DISCOVERY COMPONENT: NOTE DI ARCHITETTURA E SCOPO OPERATIVO DEL MODULO SELEZIONATO
# ==============================================================================
descrizioni_moduli = {        
    
    "📁 Analisi Triple-POC": (
        "**Scopo Operativo & Architettura:** Motore istituzionale di analisi volumetrica multi-orizzonte che confronta "
        "simultaneamente tre profili di volume (**Storico Completo**, **Dall'ATH** e **Finestra Recente 3M/6M/9M**) per isolare "
        "i veri nodi di liquidità (**POC**, **VAH**, **VAL**). Integra calcolo automatico di **Entry, Stop Loss e Take Profit (R:R 1:2 su ATR 14)**, "
        "trendline dinamica sui massimi decrescenti, riconoscimento pattern **Falling Wedge + candele Marubozu** e pannelli sincronizzati "
        "di **RSI (14)**, **ATR (14)** e **Z-Score (50) con SMA 9**."
    ),


        "🧪 TradingView Pro": (
        "**Scopo Operativo & Architettura:** Workstation grafica quantitativa multi-timeframe (15m–1M) "
        "con barra contesto in tempo reale (**Esponente di Hurst**, **ATR 14**, **RVOL** e **Calendario Earnings**). "
        "Integra indicatori sovrapponibili (EMA 20/50/100/200, Bande di Bollinger, VWAP, Swing High/Low), "
        "oscillatori sincronizzati (RSI, MACD, Z-Score ±2), Triple Volume Profile, strumenti di disegno "
        "con **Position Sizing automatico** nel Tool R:R e salvataggio alert su **GitHub (`alerts_geometrici_v2.json`)**."
     ),

        "📈 Analisi GARCH Volatilità": (
        "**Scopo Operativo & Architettura:** Modellizza i fenomeni finanziari dei cluster di volatilità (*volatility clustering*) "
        "e i picchi asimmetrici generati dal panico di mercato. Sfrutta la libreria econometrica `arch` per configurare i parametri "
        "condizionali e confrontare le varianti Standard GARCH (simmetrico), GJR-GARCH (effetto leva a soglia) ed EGARCH (esponenziale), "
        "sovrapponendo la varianza annualizzata ai rendimenti logaritmici."
    ),
}

if scelta_modulo in descrizioni_moduli:
    st.markdown(f"""
    <div style='background: rgba(56, 189, 248, 0.05); padding: 16px; border-radius: 12px; margin-bottom: 25px; border: 1px solid rgba(56, 189, 248, 0.15);'>
        <p style='margin:0; font-size:14px; line-height:1.6; color:#94a3b8;'>
            💡 {descrizioni_moduli[scelta_modulo]}
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# --- TAB 1: TRE POC SCANNER (PARTE 1/6) ---
# ==========================================
if scelta_modulo == "📁 Analisi Triple-POC":

    st.subheader("📊 Analisi Grafica Avanzata Volume Profile & Indicatori")

    with st.expander("📖 Guida Operativa: Come Funziona e Come Leggere il Triple-POC Scanner", expanded=False):
        st.markdown("""
        ### 🎯 A cosa serve questo modulo?
        Il prezzo si muove da un'area di equilibrio volumetrico all'altra. Questo modulo affianca **3 orizzonti temporali**:
        1. **Profilo Generale (Storico Completo):** Mostra dove i grandi capitali hanno scambiato di più in tutta la vita del titolo (supporti/resistenze macro).
        2. **Profilo Dall'ATH (All-Time High):** Isola i volumi accumulati *dopo* il massimo assoluto, rivelando dove sono intrappolati i compratori o dove si forma la base di riaccumulo.
        3. **Profilo Recente (3 / 6 / 9 Mesi):** Fotografa l'equilibrio attuale di breve-medio periodo per calibrare l'ingresso.

        ---

        ### 🧠 Perché abbiamo inserito **Falling Wedge** e **Candele Marubozu**?
        * **📐 Falling Wedge (Cuneo Discendente):** Figura di compressione in cui massimi e minimi scendono convergendo (i venditori perdono spinta). Vicino a un **POC** o alla **VAL**, anticipa un'inversione rialzista.
        * **🔥 Candela Marubozu:** Candela impulsiva con corpo ampio e pochissime ombre: certifica l'ingresso deciso dei compratori o venditori e filtra i falsi breakout.
        """)

    st.markdown("##### ⚙️ Personalizzazione Livelli Grafici")
    
    # Riga 1 (4 colonne)
    t_col1, t_col2, t_col3, t_col4 = st.columns(4)
    with t_col1:
        mostra_poc = st.checkbox("Mostra Linea POC Entry (Rosso)", value=True, key="chk_poc")
    with t_col2:
        mostra_va = st.checkbox("Mostra Value Area & Istogrammi (VAH/VAL)", value=True, key="chk_va")
    with t_col3:
        mostra_rr = st.checkbox("Mostra Zone Target / Stop Loss Strategici (ATR 1:2)", value=True, key="chk_rr")
    with t_col4:
        mostra_bb = st.checkbox("Mostra Bande di Bollinger (Volatilità Price)", value=True, key="chk_bb")
    
    # Riga 2 (4 colonne allineate: Trendline | RSI | SL/TP | ATR)
    c_col1, c_col2, c_col3, c_col4 = st.columns(4)
    with c_col1:
        mostra_trend = st.checkbox("📐 Mostra Trendline Dinamica sui Massimi (Linea Bianca)", value=True, key="chk_trend")
    with c_col2:
        mostra_rsi = st.checkbox("📊 Mostra Indicatore RSI (14)", value=True, key="chk_rsi")
    with c_col3:
        mostra_sl_tp = st.checkbox("🎯 Mostra Linee Orizzontali SL / TP (Gialla e Azzurra)", value=True, key="chk_sltp")
    with c_col4:
        mostra_atr = st.checkbox("📈 Mostra Indicatore ATR (14)", value=True, key="chk_atr")
    
    st.markdown("---")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        macro_scelto = st.selectbox("1️⃣ Macro Mercato:", list(GERARCHIA_MERCATI.keys()), key="an_macro")
    with m_col2:
        borse_disp = list(GERARCHIA_MERCATI[macro_scelto].keys())
        borsa_scelta = st.selectbox("2️⃣ Borsa / Indice:", borse_disp, key=f"an_borsa_{macro_scelto}")
    with m_col3:
        cap_disp = GERARCHIA_MERCATI[macro_scelto][borsa_scelta]
        cap_scelta = st.selectbox("3️⃣ Capitalizzazione:", cap_disp, key=f"an_cap_{macro_scelto}_{borsa_scelta}")

    paniere_selezionato = f"{macro_scelto} — {borsa_scelta} ({cap_scelta})"
    ticker_caricati, fonte_paniere = scarica_paniere_universale(macro_scelto, borsa_scelta, cap_scelta)
    st.caption(f"📌 **{paniere_selezionato}** | {fonte_paniere}")
    st.session_state.asset_type_index = 1 if "Crypto" in macro_scelto else 0

    col2, col3, col4 = st.columns(3)
    with col2:
        tickers_input = st.text_input(
            "Ticker specifici (vuoto = tutto il paniere):",
            value="",
            placeholder="Es: AAPL, NVDA o BTC-USD",
            key=f"an_area_{paniere_selezionato}"
        )
    with col3:
        period_label = st.selectbox("Estensione Profilo Recente:", ["3 Mesi", "6 Mesi", "9 Mesi"], key="an_period")
        g3 = {"3 Mesi": 90, "6 Mesi": 180, "9 Mesi": 270}[period_label]
    with col4:
        tf_label = st.selectbox("Timeframe Candele:", ["Giornaliero (Daily)", "Settimanale (Weekly)"], key="an_timeframe")
        tf_attivo = {"Giornaliero (Daily)": "1d", "Settimanale (Weekly)": "1wk"}[tf_label]

    # Determina automaticamente il tipo asset senza bisogno del menu a tendina
    if tickers_input.strip():
        primo_tk = tickers_input.split(",").strip().upper()
        asset_type = "Criptovaluta" if primo_tk.endswith("-USD") else "Azione"
    else:
        asset_type = "Criptovaluta" if "Crypto" in macro_scelto else "Azione"



    if st.button("🌐 Scansiona Tutto il Paniere & Calcola i 3 POC", type="secondary", use_container_width=True):
        lista_target = [t.strip().upper() for t in (tickers_input if tickers_input.strip() else ticker_caricati).split(",") if t.strip()]
        with st.spinner(f"Download batch e calcolo 3 POC su tutti i {len(lista_target)} asset ({paniere_selezionato})..."):
            st.session_state["df_scan_poc_cache"] = scansiona_poc_paniere(lista_target, timeframe=tf_attivo, giorni_recenti=g3)
            st.session_state["scan_paniere_nome"] = paniere_selezionato

    if "df_scan_poc_cache" in st.session_state and not st.session_state["df_scan_poc_cache"].empty:
        df_raw_poc = st.session_state["df_scan_poc_cache"].copy()
        st.success(f"✅ Visualizzati tutti i **{len(df_raw_poc)} titoli** ({st.session_state.get('scan_paniere_nome', '')})!")

        # Protezione: se in session_state c'è ancora il formato vecchio della tabella, resetta
        if "Dist. Recente %" not in df_raw_poc.columns:
            del st.session_state["df_scan_poc_cache"]
            st.info("🔄 Aggiornamento struttura tabella: clicca di nuovo su **Scansiona Tutto il Paniere**.")
            st.stop()

        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            filtro_poc_vista = st.selectbox(
                "🎯 Quale POC vuoi visionare nella tabella:",
                [
                    "Tutti i 3 POC (Completo)",
                    "1. Solo POC Storico (Generale)",
                    "2. Solo POC Dall'ATH",
                    "3. Solo POC Recente"
                ],
                key="sel_filtro_poc_vista"
            )
        with f_col2:
            filtro_dir_poc = st.selectbox(
                "🧭 Filtra Posizione Prezzo rispetto al POC:",
                [
                    "Tutti i titoli (inclusi N/D)",
                    "🟢 Solo LONG (Prezzo sopra il POC)",
                    "🔴 Solo SHORT (Prezzo sotto il POC)"
                ],
                key="sel_filtro_dir_poc"
            )
        with f_col3:
            max_dist_pct = st.slider(
                "📏 Distanza massima dal POC (%):",
                min_value=1.0, max_value=100.0, value=15.0, step=1.0,
                key="sl_max_dist_poc"
            )

        # 1. Selezione colonne e colonna di riferimento
        if filtro_poc_vista == "1. Solo POC Storico (Generale)":
            col_dist = "Dist. Storico %"
            cols_show = ["Ticker", "Prezzo", "POC Storico", "Dist. Storico %", "Regime 3-POC"]
        elif filtro_poc_vista == "2. Solo POC Dall'ATH":
            col_dist = "Dist. ATH %"
            cols_show = ["Ticker", "Prezzo", "POC ATH", "Dist. ATH %", "Regime 3-POC"]
        elif filtro_poc_vista == "3. Solo POC Recente":
            col_dist = "Dist. Recente %"
            cols_show = ["Ticker", "Prezzo", "POC Recente", "Dist. Recente %", "Regime 3-POC"]
        else:
            col_dist = "Dist. Recente %"
            cols_show = ["Ticker", "Prezzo", "POC Storico", "Dist. Storico %", "POC ATH", "Dist. ATH %", "POC Recente", "Dist. Recente %", "Regime 3-POC"]

        # 2. Creazione df_filtrato e applicazione filtri
        df_filtrato = df_raw_poc.copy()
        if filtro_dir_poc == "🟢 Solo LONG (Prezzo sopra il POC)":
            df_filtrato = df_filtrato[df_filtrato[col_dist].notna() & (df_filtrato[col_dist] >= 0)]
        elif filtro_dir_poc == "🔴 Solo SHORT (Prezzo sotto il POC)":
            df_filtrato = df_filtrato[df_filtrato[col_dist].notna() & (df_filtrato[col_dist] < 0)]

        df_filtrato = df_filtrato[df_filtrato[col_dist].isna() | (df_filtrato[col_dist].abs() <= max_dist_pct)]

        # 3. Ordina dal titolo più VICINO al POC al più lontano
        df_filtrato["_dist_abs"] = df_filtrato[col_dist].abs()
        df_filtrato = df_filtrato.sort_values(by="_dist_abs", ascending=True, na_position="last").drop(columns=["_dist_abs"]).reset_index(drop=True)

        st.caption("💡 Clicca su una riga della tabella per inviare subito il titolo a **TradingView Pro** o ai **Grafici 3-POC**.")
        ev_tab_poc = st.dataframe(
            df_filtrato[cols_show],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="tabella_poc_interattiva"
        )

        righe_sel = ev_tab_poc.get("selection", {}).get("rows", []) if isinstance(ev_tab_poc, dict) else getattr(ev_tab_poc.selection, "rows", [])
        if len(righe_sel) > 0 and righe_sel[0] < len(df_filtrato):
            tk_scelto = str(df_filtrato.iloc[righe_sel[0]]["Ticker"])
            st.markdown(f"**🎯 Asset selezionato dalla tabella:** `{tk_scelto}`")
            act_c1, act_c2 = st.columns(2)
            with act_c1:
                def _vai_a_tv(simbolo_sel=tk_scelto):
                    st.session_state["tv_test_tk"] = simbolo_sel
                    st.session_state["menu_navigazione_moduli"] = "🧪 TradingView Pro"
                    st.session_state["jump_to_modulo"] = "🧪 TradingView Pro"

                st.button(f"🧪 Apri {tk_scelto} su TradingView Pro", type="primary", use_container_width=True, on_click=_vai_a_tv)

            with act_c2:
                def _carica_e_apri_3poc(simbolo_sel=tk_scelto, key_area=f"an_area_{paniere_selezionato}"):
                    st.session_state[key_area] = simbolo_sel
                    st.session_state["auto_run_3poc"] = True

                st.button(f"📊 Apri Grafici 3-POC per {tk_scelto}", type="primary", use_container_width=True, on_click=_carica_e_apri_3poc)




    # ==========================================
    # --- TAB 1: TRE POC SCANNER (PARTE 2/6) ---
    # ==========================================    
    
    if st.button("🔍 Avvia Analisi Grafica Nodes", type="primary") or st.session_state.pop("auto_run_3poc", False):

        if tickers_input.strip() == "":
            tickers = [t.strip().upper() for t in ticker_caricati.split(',') if t.strip()]
        else:
            tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
            
        if not tickers: 
            st.warning("Inserisci almeno un ticker valido.")
        else:
            if len(tickers) > 15:
                st.info(f"⚠️ Paniere ampio ({len(tickers)} titoli): elaborazione limitata ai primi **15 ticker** per evitare blocchi API di Yahoo Finance.")
                tickers = tickers[:15]

            st.success("Generazione fogli ticker...")
            fogli_ticker = st.tabs([t.replace("-USD", "") for t in tickers])
            for ticker, foglio_attivo in zip(tickers, fogli_ticker):
                with foglio_attivo:
                    tk_yf = ticker + "-USD" if asset_type == "Criptovaluta" and not ticker.endswith("-USD") else ticker
                    df_c = yf.download(tickers=tk_yf, period="max", interval=tf_attivo, auto_adjust=False, multi_level_index=False, progress=False)
                    if df_c is not None and len(df_c) > 50:
                        df_c.columns = [str(c).strip() for c in df_c.columns]
                        close_series = df_c["Close"].astype(float)
                        high_series = df_c["High"].astype(float)
                        low_series = df_c["Low"].astype(float)
                        d_ath = high_series.idxmax()
                        p_att = float(close_series.iloc[-1])
                        
                        df_c["EMA200"] = close_series.ewm(span=200, min_periods=20, adjust=False).mean()
                        ema200_att = float(df_c["EMA200"].iloc[-1])
                        delta = close_series.diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        df_c["RSI"] = 100 - (100 / (1 + (gain / np.where(loss == 0, 0.00001, loss))))
                        
                        tr = pd.concat([high_series-low_series, (high_series-close_series.shift(1)).abs(), (low_series-close_series.shift(1)).abs()], axis=1).max(axis=1)
                        df_c["ATR"] = tr.rolling(window=14).mean().bfill()
                        atr_att = float(df_c["ATR"].iloc[-1])

                        # Calcolo Z-Score (50) + SMA 9
                        n_z = min(50, max(10, len(close_series) // 2))
                        x_z = np.arange(n_z)
                        sx, sx2 = x_z.sum(), (x_z**2).sum()
                        den_z = n_z * sx2 - (sx**2)
                        sy = close_series.rolling(window=n_z).sum()
                        sy2 = (close_series**2).rolling(window=n_z).sum()
                        xy_c = np.convolve(close_series.values, x_z[::-1], mode="valid")
                        sxy = pd.Series(np.nan, index=close_series.index)
                        sxy.iloc[n_z - 1:] = xy_c
                        m_z = (n_z * sxy - sx * sy) / den_z
                        q_z = (sx2 * sy - sx * sxy) / den_z
                        p_teo = m_z * n_z + q_z
                        mx, vx = sx / n_z, sx2 / n_z - ((sx / n_z)**2)
                        my, vy = sy / n_z, sy2 / n_z - ((sy / n_z)**2)
                        cov_z = sxy / n_z - (mx * my)
                        std_res = np.sqrt(np.clip(vy - (2 * m_z * cov_z) + (m_z**2 * vx), 1e-5, None))
                        df_c["Z_Score"] = ((close_series - p_teo) / std_res).fillna(0.0)
                        df_c["Z_Score_MA9"] = df_c["Z_Score"].rolling(9).mean()
                        
                        df_ath_raw = df_c.loc[d_ath:].copy()
                        df2 = df_ath_raw if len(df_ath_raw) >= 15 else df_c.tail(15).copy()
                        df1, df3 = df_c.copy(), df_c.tail(g3).copy()
                        
                        p1, vh1, vl1, prz1, vl_v1 = calc_vp(df1)
                        p2, vh2, vl2, prz2, vl_v2 = calc_vp(df2)
                        p3, vh3, vl3, prz3, vl_v3 = calc_vp(df3)
                        
                        if None in [p1, vh1, vl1, p2, vh2, vl2, p3, vh3, vl3]:
                            st.warning(f"Impossibile calcolare il Volume Profile per {ticker}.")
                            continue
                        
                        is_long_1 = p_att >= p1
                        is_long_2 = p_att >= p2
                        is_long_3 = p_att >= p3
                        
                        sl_1 = p_att - (1.5 * atr_att) if is_long_1 else p_att + (1.5 * atr_att)
                        tp_1 = p_att + (3.0 * atr_att) if is_long_1 else p_att - (3.0 * atr_att)
                        sl_2 = p_att - (1.5 * atr_att) if is_long_2 else p_att + (1.5 * atr_att)
                        tp_2 = p_att + (3.0 * atr_att) if is_long_2 else p_att - (3.0 * atr_att)
                        sl_3 = p_att - (1.5 * atr_att) if is_long_3 else p_att + (1.5 * atr_att)
                        tp_3 = p_att + (3.0 * atr_att) if is_long_3 else p_att - (3.0 * atr_att)
                        
                        dec_f = 4 if asset_type == "Criptovaluta" else 2
                        st.markdown(f"""
                        <div style='background: rgba(15, 23, 42, 0.6); padding: 15px; border-radius: 14px; margin-bottom: 25px; border: 1px solid rgba(56, 189, 248, 0.2);'>
                            <h4 style='margin-top:0; color:#38bdf8; font-family: "Plus Jakarta Sans", sans-serif;'>🎯 Riepilogo Ingressi Operativi & Risk Management</h4>
                            <p style='margin-bottom:6px; font-size:15px;'>📈 <b>1. Profilo Generale (Storico):</b> <span style='color:{"#22c55e" if is_long_1 else "#ef4444"}; font-weight:bold;'>{'LONG 🟢' if is_long_1 else 'SHORT 🔴'}</span> | Entry: <b>{round(p_att, dec_f)}</b> | POC: <b>{round(p1, dec_f)}</b> | <span style='color:#f59e0b;'>SL: {round(sl_1, dec_f)}</span> | <span style='color:#06b6d4;'>TP: {round(tp_1, dec_f)}</span></p>
                            <p style='margin-bottom:6px; font-size:15px;'>🏛️ <b>2. Profilo Dall'ATH:</b> <span style='color:{"#22c55e" if is_long_2 else "#ef4444"}; font-weight:bold;'>{'LONG 🟢' if is_long_2 else 'SHORT 🔴'}</span> | Entry: <b>{round(p_att, dec_f)}</b> | POC: <b>{round(p2, dec_f)}</b> | <span style='color:#f59e0b;'>SL: {round(sl_2, dec_f)}</span> | <span style='color:#06b6d4;'>TP: {round(tp_2, dec_f)}</span></p>
                            <p style='margin-bottom:0; font-size:15px;'>⚡ <b>3. Profilo Recente ({period_label}):</b> <span style='color:{"#22c55e" if is_long_3 else "#ef4444"}; font-weight:bold;'>{'LONG 🟢' if is_long_3 else 'SHORT 🔴'}</span> | Entry: <b>{round(p_att, dec_f)}</b> | POC: <b>{round(p3, dec_f)}</b> | <span style='color:#f59e0b;'>SL: {round(sl_3, dec_f)}</span> | <span style='color:#06b6d4;'>TP: {round(tp_3, dec_f)}</span></p>
                        </div>
                        """, unsafe_allow_html=True)
                        # ==========================================
                        # --- TAB 1: TRE POC SCANNER (PARTE 3/6) ---
                        # ==========================================
                        sub_titles = [
                            f"1. STORICO COMPLETO ({ticker}) — {'LONG 🟢' if is_long_1 else 'SHORT 🔴'} Entry: {round(p_att, dec_f)} | POC: {round(p1, dec_f)} | EMA200: {round(ema200_att, dec_f)}", 
                            f"2. DALL'ATH ({d_ath.strftime('%d/%m/%Y')}) — {'LONG 🟢' if is_long_2 else 'SHORT 🔴'} Entry: {round(p_att, dec_f)} | POC: {round(p2, dec_f)}", 
                            f"3. PROFILO RECENTE {period_label.upper()} — {'LONG 🟢' if is_long_3 else 'SHORT 🔴'} Entry: {round(p_att, dec_f)} | POC: {round(p3, dec_f)}"
                        ]
                        r_heights = [0.22, 0.22, 0.24]
                        if mostra_rsi:
                            sub_titles.append("📊 RSI (14) — Momentum di Filtro")
                            r_heights.append(0.11)
                        if mostra_atr:
                            sub_titles.append("📈 ATR (14) — Volatilità Dinamica")
                            r_heights.append(0.11)
                        sub_titles.append("🌀 Z-SCORE (50) & SMA 9 (Arancione) — Deviazione Statistica")
                        r_heights.append(0.14)

                        n_tot_rows = len(sub_titles)
                        fig = make_subplots(rows=n_tot_rows, cols=1, vertical_spacing=0.045, row_heights=r_heights, subplot_titles=tuple(sub_titles))

                        cfg = [(1, df1, prz1, vl_v1, p1, vh1, vl1, "Generale"), (2, df2, prz2, vl_v2, p2, vh2, vl2, "ATH"), (3, df3, prz3, vl_v3, p3, vh3, vl3, f"{g3}D")]
                        for r_idx, df_s, p_vp, v_vp, p_poc, p_vh, p_vl, nm in cfg:
                            if df_s.empty:
                                continue
                            fig.add_trace(grp.Candlestick(x=df_s.index, open=df_s["Open"].astype(float), high=df_s["High"].astype(float), low=df_s["Low"].astype(float), close=df_s["Close"].astype(float), name=nm), row=r_idx, col=1)
                            fig.add_trace(grp.Scatter(x=df_s.index, y=df_s["EMA200"], mode="lines", name="EMA 200", line=dict(color="#f43f5e", width=1.5)), row=r_idx, col=1)
                            
                            if mostra_bb and len(df_s) > 20:
                                b_m = df_s["Close"].rolling(20).mean()
                                b_s = df_s["Close"].rolling(20).std()
                                fig.add_trace(grp.Scatter(x=df_s.index, y=b_m+(b_s*2), mode="lines", line=dict(color="rgba(56,189,248,0.25)", width=1, dash="dash")), row=r_idx, col=1)
                                fig.add_trace(grp.Scatter(x=df_s.index, y=b_m-(b_s*2), mode="lines", line=dict(color="rgba(56,189,248,0.25)", width=1, dash="dash")), row=r_idx, col=1)
                            
                            if mostra_va and v_vp and max(v_vp) > 0:
                                m_v, d_i, d_f = max(v_vp), df_s.index.min(), df_s.index.max()
                                ext = max(1, (d_f - d_i).days)
                                step_k = max(1, len(v_vp) // 50)
                                for i in range(0, len(v_vp), step_k):
                                    idx_f = min(i + step_k, len(v_vp) - 1)
                                    y0_v, y1_v = float(p_vp[i]), float(p_vp[idx_f])
                                    if y0_v == y1_v:
                                        sp_m = max(1e-5, (max(p_vp) - min(p_vp)) * 0.005)
                                        y0_v -= sp_m
                                        y1_v += sp_m
                                    w = (float(v_vp[i]) / m_v) * (ext * 0.18) if m_v > 0 else 0
                                    fig.add_shape(type="rect", x0=d_i, x1=d_i + pd.Timedelta(days=int(w) if w > 0 else 1), y0=y0_v, y1=y1_v, fillcolor="rgba(242,142,43,0.20)" if p_vl <= p_vp[i] <= p_vh else "rgba(0,165,181,0.06)", line=dict(width=0), row=r_idx, col=1)
                            
                            is_long = p_att >= p_poc
                            sl = p_att - (1.5 * atr_att) if is_long else p_att + (1.5 * atr_att)
                            tp = p_att + (3.0 * atr_att) if is_long else p_att - (3.0 * atr_att)
                            col_z = "rgba(34, 197, 94, 0.08)" if is_long else "rgba(239, 68, 68, 0.08)"
                            ic, dir_n = ("🟢", "LONG") if is_long else ("🔴", "SHORT")
                            
                            d_lf = df_s.index[-1]
                            d_li_rischio = df_s.index[-8] if len(df_s) > 8 else df_s.index
                                
                            if mostra_rr and not np.isnan(atr_att):
                                fig.add_shape(type="rect", x0=d_li_rischio, x1=d_lf, y0=min(p_att, tp), y1=max(p_att, tp), fillcolor=col_z, line=dict(width=0), row=r_idx, col=1)
                            
                            if mostra_poc:
                                fig.add_shape(type="line", x0=df_s.index.min(), x1=d_lf, y0=p_poc, y1=p_poc, line=dict(color="#ef4444", width=2.5), row=r_idx, col=1)
                            
                            fig.add_shape(type="line", x0=df_s.index.min(), x1=d_lf, y0=p_att, y1=p_att, line=dict(color="#a855f7", width=2, dash="dot"), row=r_idx, col=1)
                            
                            if mostra_sl_tp and not np.isnan(atr_att):
                                fig.add_shape(type="line", x0=d_li_rischio, x1=d_lf, y0=sl, y1=sl, line=dict(color="#f59e0b", width=2, dash="dash"), row=r_idx, col=1)
                                fig.add_shape(type="line", x0=d_li_rischio, x1=d_lf, y0=tp, y1=tp, line=dict(color="#06b6d4", width=2, dash="solid"), row=r_idx, col=1)
                            # ==========================================
                            # --- TAB 1: TRE POC SCANNER (PARTE 4/6) ---
                            # ==========================================
                            if mostra_trend and r_idx == 3 and len(df_s) > 20:
                                idx_max_assoluto = df_s["High"].idxmax()
                                val_max_assoluto = float(df_s["High"].max())
                                date_max_assoluto = pd.to_datetime(idx_max_assoluto)
                                df_successivo = df_s.loc[date_max_assoluto:]
                                
                                if len(df_successivo) > 5:
                                    punti_swing_lh = []
                                    k_finestra = 3  
                                    for i in range(k_finestra, len(df_successivo) - k_finestra):
                                        data_corrente = df_successivo.index[i]
                                        val_corrente = float(df_successivo["High"].iloc[i])
                                        max_sinistro = df_successivo["High"].iloc[i - k_finestra : i].max()
                                        max_destro = df_successivo["High"].iloc[i + 1 : i + k_finestra + 1].max()
                                        if val_corrente >= max_sinistro and val_corrente >= max_destro and val_corrente < val_max_assoluto:
                                            punti_swing_lh.append((data_corrente, val_corrente))
                                                
                                    if not punti_swing_lh:
                                        for d_c, r_c in df_successivo.iloc[2:].iterrows():
                                            if float(r_c["High"]) < val_max_assoluto:
                                                punti_swing_lh.append((d_c, float(r_c["High"])))
                                                
                                    miglior_data_swing = None
                                    pendenza_ottimale = -999999.0
                                    for data_sw, val_sw in punti_swing_lh:
                                        dist_giorni = (data_sw - date_max_assoluto).days
                                        if dist_giorni > 0:
                                            m_trend = (val_sw - val_max_assoluto) / dist_giorni
                                            intersezione_rilevata = False
                                            for verif_idx in range(1, len(df_successivo)):
                                                giorni_check = (df_successivo.index[verif_idx] - date_max_assoluto).days
                                                if float(df_successivo["High"].iloc[verif_idx]) > val_max_assoluto + (m_trend * giorni_check) + 0.01:
                                                    intersezione_rilevata = True
                                                    break
                                            if not intersezione_rilevata and m_trend > pendenza_ottimale:
                                                pendenza_ottimale = m_trend
                                                miglior_data_swing = data_sw
                                                
                                    if miglior_data_swing is None and len(punti_swing_lh) > 0:
                                        punti_swing_lh.sort(key=lambda item: item, reverse=True)
                                        primo_sw = punti_swing_lh
                                        miglior_data_swing = primo_sw
                                        dist_giorni = (miglior_data_swing - date_max_assoluto).days
                                        if dist_giorni > 0:
                                            pendenza_ottimale = (primo_sw - val_max_assoluto) / dist_giorni
                                            
                                    if miglior_data_swing is not None:
                                        giorni_tot = (df_s.index[-1] - date_max_assoluto).days
                                        val_proj = val_max_assoluto + (pendenza_ottimale * giorni_tot)
                                        fig.add_trace(grp.Scatter(x=[date_max_assoluto, df_s.index[-1]], y=[val_max_assoluto, val_proj], mode="lines", line=dict(color="#ffffff", width=2.5), showlegend=False), row=r_idx, col=1)
                            # ==========================================
                            # --- TAB 1: TRE POC SCANNER (PARTE 5/6) ---
                            # ==========================================
                            if r_idx == 3 and len(df_s) >= 15:
                                res_wedge = rileva_wedge_e_marubozu(df_s, finestra=45, soglia_corpo_pct=68.0)
                                maru_list = res_wedge.get("marubozu_list", [])
                                if maru_list:
                                    bull_m = [m for m in maru_list if m.get("is_bull")]
                                    bear_m = [m for m in maru_list if not m.get("is_bull")]
                                    if bull_m:
                                        fig.add_trace(grp.Scatter(
                                            x=[m["date"] for m in bull_m],
                                            y=[m["price"] * 1.008 for m in bull_m],
                                            mode="markers+text",
                                            marker=dict(color="#22c55e", size=11, symbol="triangle-up"),
                                            text=[f"🔥M {m['pct']}%" for m in bull_m],
                                            textposition="top center",
                                            textfont=dict(color="#22c55e", size=9),
                                            showlegend=False
                                        ), row=r_idx, col=1)
                                    if bear_m:
                                        fig.add_trace(grp.Scatter(
                                            x=[m["date"] for m in bear_m],
                                            y=[m["price"] * 0.992 for m in bear_m],
                                            mode="markers+text",
                                            marker=dict(color="#ef4444", size=11, symbol="triangle-down"),
                                            text=[f"🔻M {m['pct']}%" for m in bear_m],
                                            textposition="bottom center",
                                            textfont=dict(color="#ef4444", size=9),
                                            showlegend=False
                                        ), row=r_idx, col=1)

                                if res_wedge.get("wedge_valido", False):
                                    is_brk = res_wedge.get("breakout_marubozu", False)
                                    colore_w = "#22c55e" if is_brk else "#38bdf8"
                                    fig.add_trace(grp.Scatter(x=res_wedge.get("x_dates", []), y=res_wedge.get("upper_y", []), mode="lines", line=dict(color=colore_w, width=2.2, dash="dashdot"), showlegend=False), row=r_idx, col=1)
                                    fig.add_trace(grp.Scatter(x=res_wedge.get("x_dates", []), y=res_wedge.get("lower_y", []), mode="lines", line=dict(color=colore_w, width=2.2, dash="dashdot"), showlegend=False), row=r_idx, col=1)
                                    if is_brk and res_wedge.get("x_dates"):
                                        fig.add_annotation(
                                            x=res_wedge["x_dates"][-1], y=res_wedge.get("upper_oggi", 0.0),
                                            text=f"🚀 WEDGE BREAKOUT ({res_wedge.get('pct_corpo', 0)}% Marubozu)",
                                            showarrow=True, arrowhead=2, arrowcolor="#22c55e", ax=-50, ay=-40,
                                            bgcolor="#22c55e", font=dict(color="white", size=10, weight="bold"),
                                            row=r_idx, col=1
                                        )
                            
                            txt_label_grafico = f"📊 ENTRY {dir_n} {round(p_att, dec_f)}<br>🔸 SL: {round(sl, dec_f)}<br>🔹 TP: {round(tp, dec_f)}"
                            fig.add_annotation(x=d_lf, y=p_att, text=txt_label_grafico, showarrow=True, arrowhead=2, arrowcolor="#22c55e" if is_long else "#ef4444", ax=-65, ay=-45 if is_long else 45, align="left", font=dict(color="white", size=9), bgcolor="#22c55e" if is_long else "#ef4444", bordercolor="white", borderwidth=1, borderpad=5, row=r_idx, col=1)

                            y_pos_leg = {1: 0.99, 2: 0.77, 3: 0.55}[r_idx]
                            txt_leg = f"<b>📊 PROFILO {nm.upper()}</b><br>Setup: {ic} {dir_n}<br>🟣 ENTRY: {round(p_att, dec_f)}<br>🔴 POC: {round(p_poc, dec_f)}<br>🟠 VAH: {round(p_vh, dec_f)}<br>🔵 VAL: {round(p_vl, dec_f)}"
                            fig.add_annotation(xref="paper", yref="paper", x=0.01, y=y_pos_leg, text=txt_leg, showarrow=False, align="left", bgcolor="rgba(20,24,33,0.95)", bordercolor="rgba(242,142,43,0.4)", borderwidth=1.5, borderpad=8, font=dict(color="white", size=10))
                        # ==========================================
                        # --- TAB 1: TRE POC SCANNER (PARTE 6/6) ---
                        # ==========================================
                        df_recent_ind = df3.copy()
                        curr_r = 4

                        if mostra_rsi:
                            fig.add_trace(grp.Scatter(x=df_recent_ind.index, y=df_recent_ind["RSI"], mode="lines", name="RSI", line=dict(color="#a855f7", width=2)), row=curr_r, col=1)
                            fig.add_shape(type="line", x0=df_recent_ind.index.min(), x1=df_recent_ind.index[-1], y0=75, y1=75, line=dict(color="rgba(239, 68, 68, 0.4)", width=1.5, dash="dot"), row=curr_r, col=1)
                            fig.add_shape(type="line", x0=df_recent_ind.index.min(), x1=df_recent_ind.index[-1], y0=25, y1=25, line=dict(color="rgba(34, 197, 94, 0.4)", width=1.5, dash="dot"), row=curr_r, col=1)
                            fig.update_xaxes(matches="x3", row=curr_r, col=1)
                            curr_r += 1

                        if mostra_atr:
                            fig.add_trace(grp.Scatter(x=df_recent_ind.index, y=df_recent_ind["ATR"], mode="lines", name="ATR", line=dict(color="#10b981", width=2)), row=curr_r, col=1)
                            fig.update_xaxes(matches="x3", row=curr_r, col=1)
                            curr_r += 1

                        # Pannello Z-Score + SMA 9 Arancione
                        fig.add_trace(grp.Scatter(x=df_recent_ind.index, y=df_recent_ind["Z_Score"], mode="lines", name="Z-Score", line=dict(color="#38bdf8", width=1.8)), row=curr_r, col=1)
                        fig.add_trace(grp.Scatter(x=df_recent_ind.index, y=df_recent_ind["Z_Score_MA9"], mode="lines", name="SMA 9 Z-Score", line=dict(color="#f59e0b", width=1.6)), row=curr_r, col=1)
                        fig.add_shape(type="line", x0=df_recent_ind.index.min(), x1=df_recent_ind.index[-1], y0=2.0, y1=2.0, line=dict(color="#22c55e", width=1.2, dash="dash"), row=curr_r, col=1)
                        fig.add_shape(type="line", x0=df_recent_ind.index.min(), x1=df_recent_ind.index[-1], y0=0.0, y1=0.0, line=dict(color="rgba(255, 255, 255, 0.25)", width=1), row=curr_r, col=1)
                        fig.add_shape(type="line", x0=df_recent_ind.index.min(), x1=df_recent_ind.index[-1], y0=-2.0, y1=-2.0, line=dict(color="#ef4444", width=1.2, dash="dash"), row=curr_r, col=1)
                        fig.update_xaxes(matches="x3", row=curr_r, col=1)

                        fig.update_layout(
                            template="plotly_dark",
                            dragmode="pan",
                            height=1750 + (220 * (n_tot_rows - 4)),
                            showlegend=False
                        )
                        fig.update_xaxes(rangeslider_visible=False, fixedrange=False)
                        fig.update_yaxes(fixedrange=False)
                        st.plotly_chart(
                            fig,
                            use_container_width=True,
                            key=f"chart_{ticker}",
                            config={"scrollZoom": True, "displayModeBar": True}
                        )

                    else: 
                        st.warning(f"Dati storici insufficienti per {ticker}.")

# ==============================================================================
# TAB 19: TRADINGVIEW PRO QUANTITATIVO (PARTE 1/5 - CONTROLLI & STRUMENTI)
# ==============================================================================
if scelta_modulo == "🧪 TradingView Pro":

    st.subheader("🧪 TradingView Pro — Workstation Grafica & Alert Prezzo/Tempo")

    # 1. BARRA SUPERIORE (TICKER, TIMEFRAME, STORICO E RISK MANAGEMENT)
    tv_c1, tv_c2, tv_c3, tv_c4, tv_c5 = st.columns([1.1, 1.2, 1.1, 1.0, 0.9])
    with tv_c1:
        tv_ticker = st.text_input("Simbolo / Ticker:", value="NVDA", key="tv_test_tk").strip().upper()
    with tv_c2:
        tv_tf_map = {
            "15 Minuti (15m)": "15m",
            "1 Ora (1h)": "1h",
            "4 Ore (4h)": "4h",
            "Giornaliero (1D)": "1d",
            "Settimanale (1W)": "1wk",
            "Mensile (1M)": "1mo",
        }
        tv_tf_label = st.selectbox("Timeframe:", list(tv_tf_map.keys()), index=3, key="tv_test_tf")
        tv_tf = tv_tf_map[tv_tf_label]
    with tv_c3:
        if tv_tf == "15m":
            opz_per = {"5 Giorni": "5d", "1 Mese": "1mo", "2 Mesi": "60d"}
        elif tv_tf in ["1h", "4h"]:
            opz_per = {"1 Mese": "1mo", "3 Mesi": "3mo", "6 Mesi": "6mo", "1 Anno": "1y", "2 Anni": "2y"}
        else:
            opz_per = {"6 Mesi": "6mo", "1 Anno": "1y", "2 Anni": "2y", "5 Anni": "5y", "Massimo": "max"}
        tv_per_label = st.selectbox("Orizzonte Storico:", list(opz_per.keys()), index=min(1, len(opz_per) - 1), key="tv_test_per")
        tv_per = opz_per[tv_per_label]
    with tv_c4:
        tv_capitale = st.number_input("Capitale ($):", min_value=500, value=10000, step=500, key="tv_test_cap")
    with tv_c5:
        tv_rischio_pct = st.number_input("Rischio %:", min_value=0.1, max_value=10.0, value=1.0, step=0.25, key="tv_test_risk")

    # 2. MENU A SCOMPARSA: INDICATORI TECNICI, POC, HTF & OSCILLATORI
    with st.expander("📊 Indicatori Tecnici, Livelli HTF, Forza Relativa & Oscillatori", expanded=False):
        ind_col1, ind_col2, ind_col3 = st.columns(3)
        with ind_col1:
            tv_log_scale = st.checkbox("📐 Scala Logaritmica", value=False, key="tv_test_log")
            tv_show_vp = st.checkbox("📊 Mostra 3 Volume Profile (POC)", value=True, key="tv_test_vp")
            tv_show_htf = st.checkbox("🏛️ Livelli Istituzionali (Prev. Week / Month High-Low)", value=True, key="tv_test_htf")
            tv_ema_scelte = st.multiselect(
                "Medie Mobili Esponenziali (EMA):",
                options=["EMA 20", "EMA 50", "EMA 100", "EMA 200"],
                default=["EMA 20", "EMA 50", "EMA 200"],
                key="tv_test_emas"
            )
            tv_bb = st.checkbox("Bande di Bollinger (20, 2)", value=False, key="tv_test_bb")
        with ind_col2:
            tv_vwap = st.checkbox("VWAP Ancorato al Periodo", value=False, key="tv_test_vwap")
            tv_vol = st.checkbox("Istogramma Volumi", value=True, key="tv_test_vol")
            tv_swings = st.checkbox("🔺🔻 Mostra Swing High / Low", value=False, key="tv_test_swings")
            tv_swing_order = st.slider(
                "Sensibilità Swing (Candele dx/sx):",
                min_value=2, max_value=15, value=5, step=1,
                disabled=not tv_swings,
                key="tv_swing_ord"
            )
        with ind_col3:
            tv_sub_osc = st.radio(
                "Oscillatore Inferiore:",
                options=["Nessuno", "Forza Relativa vs Benchmark (RS)", "RSI (14)", "MACD (12, 26, 9)", "Z-Score (±2)"],
                index=1,
                key="tv_test_osc"
            )
            tv_bench_rs = "SPY"
            if tv_sub_osc == "Forza Relativa vs Benchmark (RS)":
                tv_bench_rs = st.selectbox("Benchmark RS:", ["SPY", "QQQ", "FTSEMIB.MI", "BTC-USD"], index=0, key="tv_rs_bench_sel")
            tv_z_win = 50
            if tv_sub_osc == "Z-Score (±2)":
                tv_z_win = st.slider("Finestra Z-Score (Candele):", min_value=20, max_value=100, value=50, step=5, key="tv_z_win_sl")
            tv_rr_ratio = st.selectbox("Rapporto R:R Default:", [1.5, 2.0, 2.5, 3.0, 4.0], index=2, key="tv_test_rr_mult")

    # 3. MENU A SCOMPARSA: STRUMENTI DI ANALISI GRAFICA (PREZZO & TEMPO)
    with st.expander("✏️ Strumenti di Disegno (Prezzo & Alert Temporali)", expanded=True):
        tv_tool = st.radio(
            "Seleziona strumento:",
            [
                "📐 Trendline Diagonale (2 Clic)",
                "➖ Livello Orizzontale Prezzo (1 Clic)",
                "⏳ Linea Verticale Temporale (1 Clic sulla Data)",
                "⬜ Rettangolo Zona (2 Clic)",
                "🌀 Ritracciamento Fibonacci (2 Clic: Min -> Max)",
                "🎯 Posizione Long/Short R:R + Size (2 Clic: Entry -> Stop Loss)"
            ],
            horizontal=True,
            key="tv_test_tool"
        )

        tv_rect_extend = False
        if "Rettangolo" in tv_tool:
            tv_rect_extend = st.checkbox("➡️ Estendi Rettangolo all'infinito a destra (Zona Supply/Demand)", value=True, key="tv_rect_ext_chk")

    if "tv_shapes_list" not in st.session_state:
        st.session_state["tv_shapes_list"] = []
    if "tv_pt_a" not in st.session_state:
        st.session_state["tv_pt_a"] = None
    if "tv_last_tool" not in st.session_state:
        st.session_state["tv_last_tool"] = tv_tool

    if st.session_state["tv_last_tool"] != tv_tool:
        st.session_state["tv_pt_a"] = None
        st.session_state["tv_last_tool"] = tv_tool
    # ==========================================================================
    # TAB 19: PARTE 2/5 - DOWNLOAD, CONTEXT METRICS & OSCILLATORI
    # ==========================================================================
    df_tv = yf.download(tickers=tv_ticker, period=tv_per, interval=tv_tf, auto_adjust=False, multi_level_index=False, progress=False)

    if df_tv is None or df_tv.empty:
        st.error("❌ Impossibile caricare i dati per il ticker/timeframe selezionato.")
        st.stop()

    df_tv.columns = [str(c).strip() for c in df_tv.columns]
    close_s = df_tv["Close"].astype(float)
    high_s = df_tv["High"].astype(float)
    low_s = df_tv["Low"].astype(float)
    open_s = df_tv["Open"].astype(float)
    vol_s = df_tv["Volume"].astype(float)

    # Calcolo ATR(14) e RVOL(20)
    tr_tv = pd.concat([
        high_s - low_s,
        (high_s - close_s.shift(1)).abs(),
        (low_s - close_s.shift(1)).abs()
    ], axis=1).max(axis=1)
    df_tv["ATR"] = tr_tv.rolling(14).mean().bfill()
    atr_now_tv = float(df_tv["ATR"].to_numpy()[-1])
    p_now_tv = float(close_s.to_numpy()[-1])
    atr_pct_tv = (atr_now_tv / p_now_tv * 100.0) if p_now_tv > 0 else 0.0

    vol_sma20_tv = vol_s.rolling(20).mean()
    v_last_tv = float(vol_s.to_numpy()[-1])
    v_sma_last_tv = float(vol_sma20_tv.to_numpy()[-1]) if len(vol_sma20_tv) >= 20 else 0.0
    rvol_now_tv = (v_last_tv / v_sma_last_tv) if (v_sma_last_tv > 0 and not np.isnan(v_sma_last_tv)) else 1.0

    # Calcolo Esponente di Hurst
    log_c_tv = np.log(close_s.dropna().to_numpy())
    if len(log_c_tv) >= 50:
        sub_h = log_c_tv[-min(126, len(log_c_tv)):]
        lags_tv = range(10, min(35, len(sub_h) // 2))
        tau_tv = [max(1e-8, float(np.std(sub_h[lg:] - sub_h[:-lg]))) for lg in lags_tv]
        if len(tau_tv) >= 5:
            poly_h_tv = np.polyfit(np.log(list(lags_tv)), np.log(tau_tv), 1)
            hurst_tv = float(np.clip(float(poly_h_tv.item(0)) * 2.0, 0.05, 0.95))
        else:
            hurst_tv = 0.50
    else:
        hurst_tv = 0.50

    if hurst_tv > 0.55:
        regime_tv_lbl = "🚀 Trend-Following"
    elif hurst_tv < 0.45:
        regime_tv_lbl = "🔄 Mean-Reversion"
    else:
        regime_tv_lbl = "🎲 Random Walk"

    # Controllo Calendario Earnings
    earn_lbl_tv = "⚪ N/A"
    earn_delta_tv = "Asset non azionario"
    if not any(x in tv_ticker for x in ["-USD", "=F", "=X", "^"]):
        try:
            ed_tv = yf.Ticker(tv_ticker).get_earnings_dates(limit=6)
            if ed_tv is not None and not ed_tv.empty:
                ed_idx = pd.to_datetime(ed_tv.index).tz_localize(None)
                oggi_tv = pd.Timestamp.now().tz_localize(None)
                fut_tv = ed_idx[ed_idx >= oggi_tv]
                if len(fut_tv) > 0:
                    gg_manc = int((fut_tv.min() - oggi_tv).days)
                    data_e_str = fut_tv.min().strftime("%d/%m/%Y")
                    if gg_manc <= 12:
                        earn_lbl_tv = f"🚨 TRA {gg_manc} GG"
                        earn_delta_tv = f"Rischio Gap ({data_e_str})"
                    else:
                        earn_lbl_tv = f"✅ Tra {gg_manc} gg"
                        earn_delta_tv = f"Data: {data_e_str}"
                else:
                    earn_lbl_tv = "⚪ N/D"
                    earn_delta_tv = "Nessuna data futura"
        except Exception:
            earn_lbl_tv = "⚪ N/D"
            earn_delta_tv = "Calendario non disp."

    # BARRA KPI QUANTITATIVA IN TESTA AL GRAFICO
    q_k1, q_k2, q_k3, q_k4 = st.columns(4)
    with q_k1:
        st.metric("🧭 Regime Hurst", f"H = {hurst_tv:.2f}", regime_tv_lbl)
    with q_k2:
        st.metric("📏 ATR (14) & Stop Minimo", f"{atr_now_tv:.2f} $ ({atr_pct_tv:.2f}%)", f"1.5x ATR = {1.5 * atr_now_tv:.2f} $")
    with q_k3:
        st.metric("📊 Volumi Relativi (RVOL)", f"{rvol_now_tv:.2f}x", "🔥 Sopra media" if rvol_now_tv >= 1.25 else "Nella norma")
    with q_k4:
        st.metric("📅 Prossimi Earnings", earn_lbl_tv, earn_delta_tv)

    # Indicatori Overlay
    if "EMA 20" in tv_ema_scelte:
        df_tv["EMA20"] = close_s.ewm(span=20, adjust=False).mean()
    if "EMA 50" in tv_ema_scelte:
        df_tv["EMA50"] = close_s.ewm(span=50, adjust=False).mean()
    if "EMA 100" in tv_ema_scelte:
        df_tv["EMA100"] = close_s.ewm(span=100, adjust=False).mean()
    if "EMA 200" in tv_ema_scelte:
        df_tv["EMA200"] = close_s.ewm(span=200, adjust=False).mean()

    if tv_bb:
        bb_mid = close_s.rolling(20).mean()
        bb_std = close_s.rolling(20).std()
        df_tv["BB_UP"] = bb_mid + 2 * bb_std
        df_tv["BB_LOW"] = bb_mid - 2 * bb_std

    if tv_vwap and vol_s.sum() > 0:
        tp = (high_s + low_s + close_s) / 3.0
        df_tv["VWAP"] = (tp * vol_s).cumsum() / vol_s.cumsum().replace(0, np.nan)

    # Oscillatori Inferiori
    if tv_sub_osc == "RSI (14)":
        delta = close_s.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df_tv["RSI"] = 100 - (100 / (1 + (gain / loss.replace(0, 1e-5))))
    elif tv_sub_osc == "MACD (12, 26, 9)":
        ema12 = close_s.ewm(span=12, adjust=False).mean()
        ema26 = close_s.ewm(span=26, adjust=False).mean()
        df_tv["MACD"] = ema12 - ema26
        df_tv["MACD_SIG"] = df_tv["MACD"].ewm(span=9, adjust=False).mean()
        df_tv["MACD_HIST"] = df_tv["MACD"] - df_tv["MACD_SIG"]
    elif tv_sub_osc == "Z-Score (±2)":
        n_z = min(tv_z_win, max(10, len(close_s) // 2))
        x_z = np.arange(n_z)
        sx, sx2 = x_z.sum(), (x_z**2).sum()
        den_z = n_z * sx2 - (sx**2)
        sy = close_s.rolling(window=n_z).sum()
        sy2 = (close_s**2).rolling(window=n_z).sum()
        xy_c = np.convolve(close_s.values, x_z[::-1], mode="valid")
        sxy = pd.Series(np.nan, index=close_s.index)
        sxy.iloc[n_z - 1:] = xy_c
        m_z = (n_z * sxy - sx * sy) / den_z
        q_z = (sx2 * sy - sx * sxy) / den_z
        p_teo = m_z * n_z + q_z
        mx, vx = sx / n_z, sx2 / n_z - ((sx / n_z)**2)
        my, vy = sy / n_z, sy2 / n_z - ((sy / n_z)**2)
        cov_z = sxy / n_z - (mx * my)
        std_res = np.sqrt(np.clip(vy - (2 * m_z * cov_z) + (m_z**2 * vx), 1e-5, None))
        df_tv["Z_Score"] = ((close_s - p_teo) / std_res).fillna(0.0)
        df_tv["Z_Score_MA9"] = df_tv["Z_Score"].rolling(9).mean()
    elif tv_sub_osc == "Forza Relativa vs Benchmark (RS)":
        df_b_rs = yf.download(tickers=tv_bench_rs, period=tv_per, interval=tv_tf, auto_adjust=False, multi_level_index=False, progress=False)
        if df_b_rs is not None and not df_b_rs.empty:
            df_b_rs.columns = [str(c).strip() for c in df_b_rs.columns]
            b_close = df_b_rs["Close"].astype(float).reindex(df_tv.index).ffill().bfill()
            rs_raw = (close_s / b_close.replace(0, np.nan)).ffill().bfill()
            primo_val = float(rs_raw.to_numpy().item(0)) if len(rs_raw) > 0 else 1.0
            rs_norm = (rs_raw / primo_val) * 100.0 if primo_val > 0 else rs_raw
            df_tv["RS_Line"] = rs_norm
            df_tv["RS_EMA20"] = rs_norm.ewm(span=20, adjust=False).mean()
        else:
            df_tv["RS_Line"] = 100.0
            df_tv["RS_EMA20"] = 100.0
    # ==========================================================================
    # TAB 19: PARTE 3A - STRUTTURA GRAFICO, CANDELE & INDICATORI OVERLAY
    # ==========================================================================
    has_vol = tv_vol and vol_s.sum() > 0
    has_osc = tv_sub_osc != "Nessuno"

    if has_vol and has_osc:
        n_rows, r_heights = 3, [0.64, 0.16, 0.20]
    elif has_vol or has_osc:
        n_rows, r_heights = 2, [0.75, 0.25]
    else:
        n_rows, r_heights = 1, [1.0]

    fig_tv = make_subplots(rows=n_rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=r_heights)

    fig_tv.add_trace(grp.Candlestick(
        x=df_tv.index, open=open_s, high=high_s, low=low_s, close=close_s,
        increasing_line_color="#089981", increasing_fillcolor="#089981",
        decreasing_line_color="#f23645", decreasing_fillcolor="#f23645",
        name=tv_ticker, hoverinfo="none"
    ), row=1, col=1)

    step_tempo = (df_tv.index[-1] - df_tv.index[-2]) if len(df_tv) > 1 else pd.Timedelta(days=1)
    d_start = df_tv.index.min()
    d_end = df_tv.index.max()
    d_future = d_end + (step_tempo * 30)

    p_min_g, p_max_g = float(low_s.min()) * 0.90, float(high_s.max()) * 1.10
    livelli_y_liberi = np.linspace(p_min_g, p_max_g, 45)
    date_griglia = list(df_tv.index[::max(1, len(df_tv) // 60)]) + [d_end + step_tempo * k for k in range(1, 29, 1)]

    xm, ym = [], []
    for dt_g in date_griglia:
        for y_g in livelli_y_liberi:
            xm.append(dt_g)
            ym.append(float(y_g))

    fig_tv.add_trace(grp.Scatter(
        x=xm, y=ym, mode="markers",
        marker=dict(size=16, opacity=0.01, color="#38bdf8"),
        showlegend=False,
        hovertemplate="Data: %{x|%Y-%m-%d}<br>Prezzo: <b>%{y:.2f} $</b><extra></extra>"
    ), row=1, col=1)

    colori_ema = {"EMA20": "#38bdf8", "EMA50": "#f59e0b", "EMA100": "#a855f7", "EMA200": "#ef4444"}
    for col_e, col_hex in colori_ema.items():
        if col_e in df_tv.columns:
            fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=df_tv[col_e], mode="lines", line=dict(color=col_hex, width=1.5), name=col_e), row=1, col=1)

    if tv_bb and "BB_UP" in df_tv.columns:
        fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=df_tv["BB_UP"], mode="lines", line=dict(color="rgba(56,189,248,0.4)", width=1), name="BB Upper"), row=1, col=1)
        fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=df_tv["BB_LOW"], mode="lines", line=dict(color="rgba(56,189,248,0.4)", width=1), fill="tonexty", fillcolor="rgba(56,189,248,0.06)", name="BB Lower"), row=1, col=1)

    if tv_vwap and "VWAP" in df_tv.columns:
        fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=df_tv["VWAP"], mode="lines", line=dict(color="#eab308", width=1.8, dash="dash"), name="VWAP"), row=1, col=1)

    if tv_swings and len(df_tv) > (tv_swing_order * 2 + 1):
        sh_raw = argrelextrema(high_s.values, np.greater_equal, order=tv_swing_order)[0]
        sl_raw = argrelextrema(low_s.values, np.less_equal, order=tv_swing_order)[0]
        sh_clean = [int(i) for k, i in enumerate(sh_raw) if k == 0 or (i - sh_raw[k - 1]) >= tv_swing_order]
        sl_clean = [int(i) for k, i in enumerate(sl_raw) if k == 0 or (i - sl_raw[k - 1]) >= tv_swing_order]

        if len(sh_clean) > 0:
            fig_tv.add_trace(grp.Scatter(x=df_tv.index[sh_clean], y=high_s.iloc[sh_clean] * 1.004, mode="markers+text", marker=dict(color="#ef4444", size=9, symbol="triangle-down"), text=[f"{round(float(v), 2)}" for v in high_s.iloc[sh_clean]], textposition="top center", textfont=dict(color="#ef4444", size=9), name="Swing High"), row=1, col=1)
        if len(sl_clean) > 0:
            fig_tv.add_trace(grp.Scatter(x=df_tv.index[sl_clean], y=low_s.iloc[sl_clean] * 0.996, mode="markers+text", marker=dict(color="#22c55e", size=9, symbol="triangle-up"), text=[f"{round(float(v), 2)}" for v in low_s.iloc[sl_clean]], textposition="bottom center", textfont=dict(color="#22c55e", size=9), name="Swing Low"), row=1, col=1)

    if tv_show_vp and len(df_tv) > 10:
        p1, _, _, _, _ = calc_vp(df_tv, div=100)
        idx_ath = high_s.idxmax()
        p2, _, _, _, _ = calc_vp(df_tv.loc[idx_ath:], div=80) if len(df_tv.loc[idx_ath:]) > 5 else (None, None, None, [], [])
        p3, _, _, _, _ = calc_vp(df_tv.tail(min(120, len(df_tv))), div=80)

        for p_val, p_col, p_lbl, p_dash in [(p1, "#ef4444", "POC Storico", "solid"), (p2, "#3b82f6", "POC ATH", "dash"), (p3, "#10b981", "POC Recente", "dot")]:
            if p_val is not None:
                fig_tv.add_shape(type="line", x0=d_start, x1=d_end, y0=p_val, y1=p_val, line=dict(color=p_col, width=1.8, dash=p_dash), row=1, col=1)
                fig_tv.add_annotation(x=d_end, y=p_val, text=f"{p_lbl}: {round(p_val, 2)}", showarrow=False, xanchor="right", yshift=10, font=dict(color=p_col, size=10), bgcolor="rgba(15,23,42,0.8)", row=1, col=1)
    # ==========================================================================
    # TAB 19: PARTE 3B - LIVELLI HTF & ALERT GIÀ ARMATI SUL CLOUD
    # ==========================================================================
    if tv_show_htf and tv_tf in ["15m", "1h", "4h", "1d"]:
        try:
            df_htf = yf.download(tickers=tv_ticker, period="6mo", interval="1d", auto_adjust=False, multi_level_index=False, progress=False)
            if df_htf is not None and len(df_htf) >= 25:
                df_htf.columns = [str(c).strip() for c in df_htf.columns]
                df_w_htf = df_htf.resample("W-FRI").agg({"High": "max", "Low": "min"}).dropna()
                df_m_htf = df_htf.resample("ME").agg({"High": "max", "Low": "min"}).dropna()
                if len(df_w_htf) >= 2:
                    pwh, pwl = float(df_w_htf["High"].iloc[-2]), float(df_w_htf["Low"].iloc[-2])
                    fig_tv.add_shape(type="line", x0=d_start, x1=d_future, y0=pwh, y1=pwh, line=dict(color="rgba(56, 189, 248, 0.55)", width=1.3, dash="dashdot"), row=1, col=1)
                    fig_tv.add_annotation(x=d_start, y=pwh, text=f"PWH: {pwh:.2f}", showarrow=False, xanchor="left", yshift=8, font=dict(color="#38bdf8", size=9), row=1, col=1)
                    fig_tv.add_shape(type="line", x0=d_start, x1=d_future, y0=pwl, y1=pwl, line=dict(color="rgba(56, 189, 248, 0.55)", width=1.3, dash="dashdot"), row=1, col=1)
                    fig_tv.add_annotation(x=d_start, y=pwl, text=f"PWL: {pwl:.2f}", showarrow=False, xanchor="left", yshift=-10, font=dict(color="#38bdf8", size=9), row=1, col=1)
                if len(df_m_htf) >= 2:
                    pmh, pml = float(df_m_htf["High"].iloc[-2]), float(df_m_htf["Low"].iloc[-2])
                    fig_tv.add_shape(type="line", x0=d_start, x1=d_future, y0=pmh, y1=pmh, line=dict(color="rgba(245, 158, 11, 0.65)", width=1.5, dash="longdash"), row=1, col=1)
                    fig_tv.add_annotation(x=d_start, y=pmh, text=f"PMH: {pmh:.2f}", showarrow=False, xanchor="left", yshift=8, font=dict(color="#f59e0b", size=9), row=1, col=1)
                    fig_tv.add_shape(type="line", x0=d_start, x1=d_future, y0=pml, y1=pml, line=dict(color="rgba(245, 158, 11, 0.65)", width=1.5, dash="longdash"), row=1, col=1)
                    fig_tv.add_annotation(x=d_start, y=pml, text=f"PML: {pml:.2f}", showarrow=False, xanchor="left", yshift=-10, font=dict(color="#f59e0b", size=9), row=1, col=1)
        except Exception:
            pass

    FILE_GEO_TV_VIEW = "alerts_geometrici_v2.json"
    db_geo_view = {}
    if os.path.exists(FILE_GEO_TV_VIEW):
        try:
            with open(FILE_GEO_TV_VIEW, "r") as f_gv:
                db_geo_view = json.load(f_gv)
            if not isinstance(db_geo_view, dict):
                db_geo_view = {}
        except Exception:
            db_geo_view = {}

    t_fut_s = d_future.timestamp()
    rischio_usd_tv = float(tv_capitale) * (float(tv_rischio_pct) / 100.0)

    for k_gv, cfg_gv in db_geo_view.items():
        if cfg_gv and cfg_gv.get("Ticker") == tv_ticker:
            tg_v = cfg_gv.get("Tipo_Geometria")
            if tg_v == "vertical":
                xv_str = str(cfg_gv["x0"])[:10]
                fig_tv.add_shape(type="line", x0=cfg_gv["x0"], x1=cfg_gv["x0"], y0=p_min_g, y1=p_max_g, line=dict(color="#a855f7", width=2.2, dash="dashdot"), row=1, col=1)
                fig_tv.add_annotation(x=cfg_gv["x0"], y=float(high_s.max()), text=f"⏳ TIME ALERT: {xv_str}", showarrow=False, xanchor="left", yshift=14, font=dict(color="#e9d5ff", size=9, weight="bold"), bgcolor="rgba(88, 28, 135, 0.85)", row=1, col=1)
            elif cfg_gv.get("Timeframe") == tv_tf and tg_v == "horizontal":
                yv = float(cfg_gv["y0"])
                fig_tv.add_shape(type="line", x0=d_start, x1=d_future, y0=yv, y1=yv, line=dict(color="#22c55e", width=2.0), row=1, col=1)
                fig_tv.add_annotation(x=d_future, y=yv, text=f"🔔 ALERT: {yv:.2f}$", showarrow=False, xanchor="right", yshift=9, font=dict(color="#22c55e", size=9, weight="bold"), bgcolor="rgba(15,23,42,0.85)", row=1, col=1)
            elif cfg_gv.get("Timeframe") == tv_tf and tg_v == "line":
                try:
                    t0_v, t1_v = pd.to_datetime(cfg_gv["x0"]).timestamp(), pd.to_datetime(cfg_gv["x1"]).timestamp()
                    if t1_v != t0_v:
                        m_v = (float(cfg_gv["y1"]) - float(cfg_gv["y0"])) / (t1_v - t0_v)
                        y_f_v = float(cfg_gv["y0"]) + m_v * (t_fut_s - t0_v)
                        fig_tv.add_trace(grp.Scatter(x=[cfg_gv["x0"], d_future], y=[float(cfg_gv["y0"]), y_f_v], mode="lines", line=dict(color="#22c55e", width=2.2), showlegend=False), row=1, col=1)
                except Exception:
                    pass
    # ==========================================================================
    # TAB 19: PARTE 3C - DISEGNO NUOVE FORME IN BOZZA & SCATOLA R:R CON SIZE
    # ==========================================================================
    for shp in st.session_state["tv_shapes_list"]:
        if shp["ticker"] != tv_ticker:
            continue
        st_type = shp["type"]
        if st_type == "vertical":
            fig_tv.add_shape(type="line", x0=shp["x0"], x1=shp["x0"], y0=p_min_g, y1=p_max_g, line=dict(color="#c084fc", width=2.4, dash="dash"), row=1, col=1)
            fig_tv.add_annotation(x=shp["x0"], y=float(high_s.max()), text=f"⏳ {str(shp['x0'])[:10]}", showarrow=False, xanchor="left", yshift=12, font=dict(color="#c084fc", size=10, weight="bold"), bgcolor="rgba(15,23,42,0.85)", row=1, col=1)
        elif st_type == "horizontal":
            fig_tv.add_shape(type="line", x0=shp["x0"], x1=d_future, y0=shp["y0"], y1=shp["y0"], line=dict(color="#06b6d4", width=2.2), row=1, col=1)
        elif st_type == "trendline":
            t0_s, t1_s = pd.to_datetime(shp["x0"]).timestamp(), pd.to_datetime(shp["x1"]).timestamp()
            if t1_s != t0_s:
                m = (shp["y1"] - shp["y0"]) / (t1_s - t0_s)
                y_proj = shp["y0"] + m * (t_fut_s - t0_s)
                fig_tv.add_trace(grp.Scatter(x=[shp["x0"], d_future], y=[shp["y0"], y_proj], mode="lines", line=dict(color="#d946ef", width=2.2), showlegend=False), row=1, col=1)
        elif st_type == "rect":
            x_left_r = min(pd.to_datetime(shp["x0"]), pd.to_datetime(shp["x1"]))
            x_right_r = d_future if shp.get("extend", False) else max(pd.to_datetime(shp["x0"]), pd.to_datetime(shp["x1"]))
            fig_tv.add_shape(type="rect", x0=x_left_r, x1=x_right_r, y0=min(shp["y0"], shp["y1"]), y1=max(shp["y0"], shp["y1"]), fillcolor="rgba(250, 204, 21, 0.16)", line=dict(color="#facc15", width=1.8), row=1, col=1)
        elif st_type == "fibo":
            y_low_f, y_high_f = shp["y0"], shp["y1"]
            diff_f = y_high_f - y_low_f
            for lvl, c_fib in [(0.0, "#ef4444"), (0.236, "#f97316"), (0.382, "#eab308"), (0.5, "#22c55e"), (0.618, "#06b6d4"), (0.786, "#3b82f6"), (1.0, "#a855f7")]:
                y_lvl = y_high_f - (diff_f * lvl)
                fig_tv.add_shape(type="line", x0=shp["x0"], x1=d_future, y0=y_lvl, y1=y_lvl, line=dict(color=c_fib, width=1.2, dash="dot"), row=1, col=1)
                fig_tv.add_annotation(x=shp["x0"], y=y_lvl, text=f"Fib {round(lvl*100, 1)}% ({round(y_lvl, 2)})", showarrow=False, xanchor="left", yshift=7, font=dict(color=c_fib, size=9), row=1, col=1)
        elif st_type == "rr_tool":
            entry_p, sl_p = float(shp["y0"]), float(shp["y1"])
            risk_u = entry_p - sl_p
            tp_p = float(shp.get("tp_custom", entry_p + (risk_u * shp["rr"])))
            abs_risk = abs(risk_u)
            rr_eff = abs(tp_p - entry_p) / abs_risk if abs_risk > 0 else shp["rr"]
            pezzi_rr = (rischio_usd_tv / abs_risk) if abs_risk > 0 else 0.0
            nozionale_rr = pezzi_rr * entry_p
            atr_mult_sl = abs_risk / atr_now_tv if atr_now_tv > 0 else 0.0
            x_start_box = pd.to_datetime(shp["x0"])
            x_end_box = max(d_future, x_start_box + (step_tempo * 18))

            fig_tv.add_shape(type="rect", x0=x_start_box, x1=x_end_box, y0=min(entry_p, sl_p), y1=max(entry_p, sl_p), fillcolor="rgba(239, 68, 68, 0.25)", line=dict(color="#ef4444", width=1.5), row=1, col=1)
            fig_tv.add_shape(type="rect", x0=x_start_box, x1=x_end_box, y0=min(entry_p, tp_p), y1=max(entry_p, tp_p), fillcolor="rgba(34, 197, 94, 0.25)", line=dict(color="#22c55e", width=1.5), row=1, col=1)
            fig_tv.add_shape(type="line", x0=x_start_box, x1=x_end_box, y0=entry_p, y1=entry_p, line=dict(color="#ffffff", width=1.8, dash="dash"), row=1, col=1)

            pct_tp, pct_sl = ((tp_p - entry_p) / entry_p) * 100, ((sl_p - entry_p) / entry_p) * 100
            fig_tv.add_annotation(x=x_end_box, y=tp_p, text=f"🎯 TP: {round(tp_p, 2)}$ ({round(pct_tp, 1)}%) | R:R 1:{round(rr_eff, 1)}", showarrow=False, xanchor="right", yshift=10, font=dict(color="#22c55e", size=10, weight="bold"), bgcolor="rgba(15,23,42,0.88)", row=1, col=1)
            fig_tv.add_annotation(x=x_end_box, y=entry_p, text=f"⚪ ENTRY: {round(entry_p, 2)}$ | SIZE: {round(pezzi_rr, 2)} Pz (${round(nozionale_rr, 0)})", showarrow=False, xanchor="right", yshift=0, font=dict(color="#38bdf8", size=10, weight="bold"), bgcolor="rgba(15,23,42,0.92)", row=1, col=1)
            fig_tv.add_annotation(x=x_end_box, y=sl_p, text=f"🛑 SL: {round(sl_p, 2)}$ ({round(pct_sl, 1)}% | {round(atr_mult_sl, 1)}x ATR)", showarrow=False, xanchor="right", yshift=-12, font=dict(color="#ef4444", size=10, weight="bold"), bgcolor="rgba(15,23,42,0.88)", row=1, col=1)

    if st.session_state["tv_pt_a"] is not None:
        pa = st.session_state["tv_pt_a"]
        fig_tv.add_trace(grp.Scatter(x=[pa["x"]], y=[pa["y"]], mode="markers", marker=dict(color="#facc15", size=14, symbol="cross"), showlegend=False), row=1, col=1)
    # ==========================================================================
    # TAB 19: PARTE 4/5 - OSCILLATORI, RENDER & GESTIONE CLIC PREZZO/TEMPO
    # ==========================================================================
    curr_row = 2
    if has_vol:
        vol_colors = ["#089981" if c >= o else "#f23645" for c, o in zip(close_s, open_s)]
        fig_tv.add_trace(grp.Bar(x=df_tv.index, y=vol_s, marker_color=vol_colors, opacity=0.5, name="Volume", showlegend=False), row=curr_row, col=1)
        fig_tv.update_yaxes(title_text="Vol", row=curr_row, col=1)
        curr_row += 1

    if has_osc:
        if tv_sub_osc == "RSI (14)":
            fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=df_tv["RSI"], mode="lines", line=dict(color="#a855f7", width=1.6), name="RSI 14"), row=curr_row, col=1)
            fig_tv.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=curr_row, col=1)
            fig_tv.add_hline(y=30, line_dash="dot", line_color="#22c55e", row=curr_row, col=1)
            fig_tv.update_yaxes(title_text="RSI", range=(0, 100), row=curr_row, col=1)
        elif tv_sub_osc == "MACD (12, 26, 9)":
            hist_cols = ["#089981" if v >= 0 else "#f23645" for v in df_tv["MACD_HIST"].fillna(0)]
            fig_tv.add_trace(grp.Bar(x=df_tv.index, y=df_tv["MACD_HIST"], marker_color=hist_cols, name="MACD Hist", showlegend=False), row=curr_row, col=1)
            fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=df_tv["MACD"], mode="lines", line=dict(color="#38bdf8", width=1.5), name="MACD"), row=curr_row, col=1)
            fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=df_tv["MACD_SIG"], mode="lines", line=dict(color="#f59e0b", width=1.5), name="Signal"), row=curr_row, col=1)
            fig_tv.update_yaxes(title_text="MACD", row=curr_row, col=1)
        elif tv_sub_osc == "Z-Score (±2)":
            z_s = df_tv["Z_Score"]
            fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=z_s, mode="lines", line=dict(color="#38bdf8", width=1.6), name="Z-Score"), row=curr_row, col=1)
            fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=df_tv["Z_Score_MA9"], mode="lines", line=dict(color="#f59e0b", width=1.5), name="SMA 9 Z-Score"), row=curr_row, col=1)
            fig_tv.add_hline(y=2.0, line_dash="dash", line_color="#22c55e", annotation_text="+2.0", row=curr_row, col=1)
            fig_tv.add_hline(y=0.0, line_dash="solid", line_color="rgba(255,255,255,0.2)", row=curr_row, col=1)
            fig_tv.add_hline(y=-2.0, line_dash="dash", line_color="#ef4444", annotation_text="-2.0", row=curr_row, col=1)
            fig_tv.update_yaxes(title_text="Z-Score", range=(-4.5, 4.5), row=curr_row, col=1)
        elif tv_sub_osc == "Forza Relativa vs Benchmark (RS)" and "RS_Line" in df_tv.columns:
            fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=df_tv["RS_Line"], mode="lines", line=dict(color="#22c55e", width=1.8), name=f"RS vs {tv_bench_rs}"), row=curr_row, col=1)
            fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=df_tv["RS_EMA20"], mode="lines", line=dict(color="#f59e0b", width=1.3, dash="dash"), name="EMA 20 RS"), row=curr_row, col=1)
            fig_tv.add_hline(y=100.0, line_dash="dot", line_color="rgba(255,255,255,0.25)", row=curr_row, col=1)
            fig_tv.update_yaxes(title_text=f"RS ({tv_bench_rs})", row=curr_row, col=1)

    fig_tv.update_layout(
        template="plotly_dark", height=720, margin=dict(l=20, r=20, t=15, b=15),
        xaxis_rangeslider_visible=False, clickmode="event+select", dragmode="pan", hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1)
    )
    fig_tv.update_yaxes(type="log" if tv_log_scale else "linear", fixedrange=False, row=1, col=1)
    fig_tv.update_xaxes(range=(d_start, d_future), fixedrange=False)

    ev_tv = st.plotly_chart(
        fig_tv, use_container_width=True, config={"scrollZoom": True},
        key=f"tv_lab_chart_{tv_ticker}_{tv_tf}_{len(st.session_state['tv_shapes_list'])}_{st.session_state['tv_pt_a'] is not None}",
        on_select="rerun", selection_mode="points"
    )

    if ev_tv is not None:
        sel_tv = ev_tv.get("selection", {}) if isinstance(ev_tv, dict) else getattr(ev_tv, "selection", {})
        pts_tv = sel_tv.get("points", []) if isinstance(sel_tv, dict) else getattr(sel_tv, "points", [])
        if len(pts_tv) > 0:
            pt_click = pts_tv[-1]
            x_clk = str(pt_click.get("x", ""))
            y_clk = float(pt_click.get("y", 0.0))

            if x_clk and y_clk > 0:
                if "Orizzontale" in tv_tool:
                    st.session_state["tv_shapes_list"].append({"ticker": tv_ticker, "type": "horizontal", "x0": x_clk, "y0": y_clk})
                    st.rerun()
                elif "Verticale" in tv_tool:
                    st.session_state["tv_shapes_list"].append({"ticker": tv_ticker, "type": "vertical", "x0": x_clk, "y0": y_clk})
                    st.rerun()
                else:
                    if st.session_state["tv_pt_a"] is None:
                        st.session_state["tv_pt_a"] = {"x": x_clk, "y": y_clk}
                        st.rerun()
                    else:
                        pa = st.session_state["tv_pt_a"]
                        is_pos_tool = "Posizione" in tv_tool
                        if is_pos_tool or x_clk != pa["x"]:
                            t_map = {"Trendline": "trendline", "Rettangolo": "rect", "Fibonacci": "fibo", "Posizione": "rr_tool"}
                            k_type = next(v for k, v in t_map.items() if k in tv_tool)
                            st.session_state["tv_shapes_list"].append({
                                "ticker": tv_ticker, "type": k_type,
                                "x0": pa["x"], "y0": pa["y"],
                                "x1": x_clk, "y1": y_clk,
                                "rr": tv_rr_ratio, "extend": tv_rect_extend
                            })
                            st.session_state["tv_pt_a"] = None
                            st.rerun()
    # ==========================================================================
    # TAB 19: PARTE 5A - SYNC GITHUB, SIZING & PULSANTI CONTROLLO
    # ==========================================================================
    def _sync_github_prolab(percorso_file, contenuto_dict, messaggio_commit):
        gh_token = os.getenv("GITHUB_TOKEN")
        gh_repo = os.getenv("GITHUB_REPO")
        if not gh_token or not gh_repo:
            return False, "Variabili GITHUB_TOKEN o GITHUB_REPO mancanti nei Secrets/env."

        url_api = f"https://github.com{gh_repo.strip('/')}/contents/{percorso_file}"
        headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}

        sha_esistente = None
        try:
            res_get = requests.get(url_api, headers=headers, timeout=10)
            if res_get.status_code == 200:
                sha_esistente = res_get.json().get("sha")
        except Exception:
            pass

        testo_json = json.dumps(contenuto_dict, indent=4)
        contenuto_b64 = base64.b64encode(testo_json.encode("utf-8")).decode("utf-8")
        payload = {"message": messaggio_commit, "content": contenuto_b64}
        if sha_esistente:
            payload["sha"] = sha_esistente

        try:
            res_put = requests.put(url_api, headers=headers, json=payload, timeout=10)
            if res_put.status_code in (200, 201):
                return True, "Sincronizzato su GitHub con successo!"
            return False, f"Errore API GitHub: {res_put.status_code}"
        except Exception as ex_gh:
            return False, f"Errore connessione GitHub: {ex_gh}"

    if "Posizione" in tv_tool:
        with st.expander("🎯 Calcolatore Esatto Posizione & Size (Entry / Stop Loss / Take Profit)", expanded=True):
            pc1, pc2, pc3, pc4 = st.columns(4)
            with pc1:
                man_entry = st.number_input("Prezzo Entry ($):", value=round(p_now_tv, 2), step=0.10, key="tv_man_entry")
            with pc2:
                man_sl = st.number_input("Stop Loss ($):", value=round(p_now_tv - (1.5 * atr_now_tv), 2), step=0.10, key="tv_man_sl")
            with pc3:
                tp_default = man_entry + ((man_entry - man_sl) * tv_rr_ratio)
                man_tp = st.number_input("Take Profit ($):", value=round(tp_default, 2), step=0.10, key="tv_man_tp")
            with pc4:
                dist_man = abs(man_entry - man_sl)
                pz_man = (rischio_usd_tv / dist_man) if dist_man > 0 else 0.0
                st.metric("Taglia Calcolata", f"{pz_man:.2f} Pz", f"Noz: ${pz_man * man_entry:,.0f} | Rischio: ${rischio_usd_tv:.0f}")

            b_rr1, b_rr2 = st.columns(2)
            with b_rr1:
                if st.button("➕ Disegna Posizione con Size sul Grafico", type="secondary", use_container_width=True):
                    if man_entry != man_sl:
                        st.session_state["tv_shapes_list"].append({
                            "ticker": tv_ticker, "type": "rr_tool",
                            "x0": str(d_end), "y0": man_entry,
                            "x1": str(d_future), "y1": man_sl,
                            "tp_custom": man_tp,
                            "rr": abs(man_tp - man_entry) / abs(man_entry - man_sl)
                        })
                        st.rerun()
            with b_rr2:
                def _cb_prolab_to_finecox():
                    st.session_state["t40_oms_tk_in"] = tv_ticker
                    st.session_state["t40_oms_side_sel"] = "BUY (Long)" if man_entry > man_sl else "SELL (Short - Marginazione)"
                    st.session_state["t40_oms_qty_in"] = max(0.01, round(pz_man, 2))
                    st.session_state["t40_oms_ent_in"] = max(0.01, float(man_entry))
                    st.session_state["t40_oms_sl_in"] = max(0.01, float(man_sl))
                    st.session_state["t40_oms_tp_in"] = max(0.01, float(man_tp))
                    st.session_state["t40_oms_type_sel"] = "LIMIT (A Limite)"
                    st.session_state["menu_navigazione_moduli"] = "🤖 Esecuzione OMS / EMS (Bracket API)"
                    st.session_state["jump_to_modulo"] = "🤖 Esecuzione OMS / EMS (Bracket API)"

                st.button("🇮🇹 Invia a Ticket FinecoX / OMS (Tab 40)", use_container_width=True, key="tv_pro_to_oms", on_click=_cb_prolab_to_finecox)

    ctrl1, ctrl2, ctrl3 = st.columns(3)
    with ctrl1:
        if st.session_state["tv_pt_a"]:
            st.info(f"📍 Primo punto fissato a **{round(st.session_state['tv_pt_a']['y'], 2)} $** — Clicca il secondo punto.")
        else:
            st.caption("💡 Verde = Alert Prezzo attivi | Viola = Alert Temporali attivi.")
    with ctrl2:
        if st.button("↩️ Annulla Ultimo Disegno", use_container_width=True):
            if st.session_state["tv_pt_a"] is not None:
                st.session_state["tv_pt_a"] = None
            elif st.session_state["tv_shapes_list"]:
                st.session_state["tv_shapes_list"].pop()
            st.rerun()
    with ctrl3:
        if st.button("🗑️ Pulisci Nuovi Disegni", use_container_width=True):
            st.session_state["tv_pt_a"] = None
            st.session_state["tv_shapes_list"] = [s for s in st.session_state["tv_shapes_list"] if s["ticker"] != tv_ticker]
            st.rerun()
    # ==========================================================================
    # TAB 19: PARTE 5B - ARMATURA ALERT DA DISEGNI (PREZZO + TEMPO)
    # ==========================================================================
    st.markdown("---")
    st.markdown("##### 🔔 1. Arma Alert da Disegni (Prezzo & Linee Temporali Verticali)")

    forme_ticker_corrente = [s for s in st.session_state["tv_shapes_list"] if s["ticker"] == tv_ticker and s["type"] in ["horizontal", "vertical", "trendline", "rect", "rr_tool"]]

    gh_c1, gh_c2, gh_c3 = st.columns([1.4, 1.3, 1.3])
    with gh_c1:
        filtro_maru_tv = st.selectbox(
            "Filtro Candela di Conferma (solo linee prezzo):",
            ["80% Corpo Minimo (Standard)", "100% Marubozu Piena", "Qualsiasi Chiusura (0% - Immediato)"],
            index=0,
            key="tv_lab_maru_sel"
        )
        soglia_maru_tv = 80.0 if "80%" in filtro_maru_tv else (98.0 if "100%" in filtro_maru_tv else 0.0)
    with gh_c2:
        st.markdown("<div style='padding-top:28px;'></div>", unsafe_allow_html=True)
        st.write(f"📐 Disegni pronti per **{tv_ticker}**: **{len(forme_ticker_corrente)}**")
    with gh_c3:
        st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
        if st.button("💾 Arma Disegni & Salva su GitHub", type="primary", use_container_width=True, disabled=(len(forme_ticker_corrente) == 0), key="tv_lab_save_gh"):
            FILE_GEO_TV = "alerts_geometrici_v2.json"
            try:
                with open(FILE_GEO_TV, "r") as f_r:
                    db_alerts_tv = json.load(f_r)
                if not isinstance(db_alerts_tv, dict):
                    db_alerts_tv = {}
            except Exception:
                db_alerts_tv = {}

            aggiunti_tv = 0
            for shp in forme_ticker_corrente:
                st_t = shp["type"]
                if st_t == "vertical":
                    data_target_str = str(shp["x0"])[:10]
                    k_id = f"{tv_ticker}_{tv_tf}_vertical_{len(db_alerts_tv) + aggiunti_tv}"
                    db_alerts_tv[k_id] = {
                        "Ticker": tv_ticker, "Timeframe_Label": tv_tf_label, "Timeframe": tv_tf,
                        "Tipo_Geometria": "vertical", "x0": data_target_str, "x1": data_target_str,
                        "y0": float(shp["y0"]), "y1": float(shp["y0"]),
                        "Regola": f"⏳ Scadenza Temporale ({data_target_str})",
                        "Soglia_Corpo_Pct": 0.0, "Stato": "ATTIVO"
                    }
                    aggiunti_tv += 1
                elif st_t == "horizontal":
                    k_id = f"{tv_ticker}_{tv_tf}_horizontal_{len(db_alerts_tv) + aggiunti_tv}"
                    db_alerts_tv[k_id] = {
                        "Ticker": tv_ticker, "Timeframe_Label": tv_tf_label, "Timeframe": tv_tf,
                        "Tipo_Geometria": "horizontal", "x0": shp["x0"], "x1": str(d_end),
                        "y0": float(shp["y0"]), "y1": float(shp["y0"]),
                        "Regola": f"Rottura Livello Orizzontale ({round(float(shp['y0']), 2)}$)",
                        "Soglia_Corpo_Pct": soglia_maru_tv, "Stato": "ATTIVO"
                    }
                    aggiunti_tv += 1
                elif st_t == "trendline":
                    x_a, x_b = shp["x0"], shp["x1"]
                    y_a, y_b = float(shp["y0"]), float(shp["y1"])
                    if pd.to_datetime(x_a) > pd.to_datetime(x_b):
                        x_a, x_b, y_a, y_b = x_b, x_a, y_b, y_a
                    k_id = f"{tv_ticker}_{tv_tf}_line_{len(db_alerts_tv) + aggiunti_tv}"
                    db_alerts_tv[k_id] = {
                        "Ticker": tv_ticker, "Timeframe_Label": tv_tf_label, "Timeframe": tv_tf,
                        "Tipo_Geometria": "line", "x0": x_a, "x1": x_b, "y0": y_a, "y1": y_b,
                        "Regola": "Breakout Trendline Diagonale (Pro Lab)",
                        "Soglia_Corpo_Pct": soglia_maru_tv, "Stato": "ATTIVO"
                    }
                    aggiunti_tv += 1
                elif st_t == "rect":
                    y_top = max(float(shp["y0"]), float(shp["y1"]))
                    y_bot = min(float(shp["y0"]), float(shp["y1"]))
                    x_s = shp["x0"] if pd.to_datetime(shp["x0"]) <= pd.to_datetime(shp["x1"]) else shp["x1"]
                    k_id = f"{tv_ticker}_{tv_tf}_rectangle_{len(db_alerts_tv) + aggiunti_tv}"
                    db_alerts_tv[k_id] = {
                        "Ticker": tv_ticker, "Timeframe_Label": tv_tf_label, "Timeframe": tv_tf,
                        "Tipo_Geometria": "rectangle", "x0": x_s, "x1": str(d_end),
                        "y0": y_top, "y1": y_bot,
                        "Regola": f"Breakout Rettangolo ({round(y_bot, 2)}$ - {round(y_top, 2)}$)",
                        "Soglia_Corpo_Pct": soglia_maru_tv, "Stato": "ATTIVO"
                    }
                    aggiunti_tv += 1
                elif st_t == "rr_tool":
                    for lbl_lvl, val_lvl in [("Entry R:R", float(shp["y0"])), ("Stop Loss R:R", float(shp["y1"]))]:
                        k_id = f"{tv_ticker}_{tv_tf}_horizontal_{len(db_alerts_tv) + aggiunti_tv}"
                        db_alerts_tv[k_id] = {
                            "Ticker": tv_ticker, "Timeframe_Label": tv_tf_label, "Timeframe": tv_tf,
                            "Tipo_Geometria": "horizontal", "x0": str(d_end), "x1": str(d_end),
                            "y0": val_lvl, "y1": val_lvl,
                            "Regola": f"Alert {lbl_lvl} ({round(val_lvl, 2)}$)",
                            "Soglia_Corpo_Pct": 0.0, "Stato": "ATTIVO"
                        }
                        aggiunti_tv += 1

            with open(FILE_GEO_TV, "w") as f_w:
                json.dump(db_alerts_tv, f_w, indent=4)

            st.session_state["tv_shapes_list"] = [s for s in st.session_state["tv_shapes_list"] if s["ticker"] != tv_ticker]
            ok_gh_tv, msg_gh_tv = _sync_github_prolab(FILE_GEO_TV, db_alerts_tv, f"Nuovi alert {tv_ticker} da Pro Lab")
            if ok_gh_tv:
                st.success(f"✅ {aggiunti_tv} alert armati e sincronizzati su GitHub!")
            else:
                st.warning(f"⚠️ Salvati in locale ({aggiunti_tv} alert), ma sync GitHub non riuscito: {msg_gh_tv}")
            st.rerun()
    # ==========================================================================
    # TAB 19: PARTE 5C - ALERT SU INDICATORI & REGISTRO GESTIONE CLOUD
    # ==========================================================================
    st.markdown("##### 🧠 2. Arma Alert su Indicatori & Regimi (Senza Disegnare Linee)")
    ind_a1, ind_a2 = st.columns([2.2, 1.3])
    with ind_a1:
        cond_ind_scelta = st.selectbox(
            "Seleziona condizione quantitativa da monitorare:",
            [
                "📉 Z-Score Estremo (Incrocio ±2.0)",
                f"🚀 Forza Relativa (RS incrocia al rialzo EMA 20 vs {tv_bench_rs})",
                "🏛️ Trend Strutturale (Chiusura sopra/sotto EMA 200)",
                "🌀 Volatility Squeeze (Compressione Bande Bollinger < 15° pct)"
            ],
            key="tv_ind_alert_sel"
        )
    with ind_a2:
        st.markdown("<div style='padding-top:28px;'></div>", unsafe_allow_html=True)
        if st.button("⚡ Arma Alert Indicatore su GitHub", use_container_width=True, key="tv_btn_ind_alert"):
            FILE_GEO_TV = "alerts_geometrici_v2.json"
            try:
                with open(FILE_GEO_TV, "r") as f_r:
                    db_alerts_tv = json.load(f_r)
                if not isinstance(db_alerts_tv, dict):
                    db_alerts_tv = {}
            except Exception:
                db_alerts_tv = {}

            k_ind = f"{tv_ticker}_{tv_tf}_indicator_{len(db_alerts_tv)}"
            db_alerts_tv[k_ind] = {
                "Ticker": tv_ticker, "Timeframe_Label": tv_tf_label, "Timeframe": tv_tf,
                "Tipo_Geometria": "indicator", "x0": str(d_end)[:10], "x1": str(d_end)[:10],
                "y0": p_now_tv, "y1": p_now_tv,
                "Regola": cond_ind_scelta,
                "Soglia_Corpo_Pct": 0.0, "Stato": "ATTIVO"
            }
            with open(FILE_GEO_TV, "w") as f_w:
                json.dump(db_alerts_tv, f_w, indent=4)
            ok_gh_i, msg_gh_i = _sync_github_prolab(FILE_GEO_TV, db_alerts_tv, f"Alert indicatore {tv_ticker}")
            if ok_gh_i:
                st.success("✅ Alert indicatore armato e sincronizzato su GitHub!")
            else:
                st.warning(f"⚠️ Salvato in locale, ma sync GitHub non riuscito: {msg_gh_i}")
            st.rerun()

    # Registro Gestione Alert già armati sul Cloud
    if db_geo_view:
        righe_alert_tv = []
        chiavi_alert_tv = []
        for k_al, v_al in db_geo_view.items():
            if v_al:
                chiavi_alert_tv.append(k_al)
                t_g_str = str(v_al.get("Tipo_Geometria", "")).upper()
                rif_str = str(v_al.get("x0", ""))[:10] if t_g_str == "VERTICAL" else f"{round(float(v_al.get('y0', 0.0)), 2)} $"
                righe_alert_tv.append({
                    "ID": k_al,
                    "Ticker": v_al.get("Ticker"),
                    "Timeframe": v_al.get("Timeframe_Label"),
                    "Tipo": t_g_str,
                    "Target (Prezzo / Data)": rif_str,
                    "Regola": v_al.get("Regola", ""),
                    "Corpo %": f"{int(v_al.get('Soglia_Corpo_Pct', 0))}%"
                })
        if righe_alert_tv:
            st.markdown("##### 📋 Registro Alert Attivi sul Cloud (Prezzo, Tempo & Indicatori)")
            st.dataframe(pd.DataFrame(righe_alert_tv), use_container_width=True, hide_index=True)

            del_c1, del_c2 = st.columns([2.5, 1.5])
            with del_c1:
                id_del_tv = st.selectbox(
                    "Seleziona alert da disarmare:",
                    options=chiavi_alert_tv,
                    format_func=lambda x: f"{db_geo_view[x]['Ticker']} — {db_geo_view[x]['Regola']} ({db_geo_view[x]['Timeframe_Label']})",
                    label_visibility="collapsed",
                    key="tv_lab_sel_del"
                )
            with del_c2:
                if st.button("❌ Disarma & Elimina Alert Selezionato", use_container_width=True, key="tv_lab_btn_del"):
                    if id_del_tv in db_geo_view:
                        tk_rem = db_geo_view[id_del_tv]["Ticker"]
                        del db_geo_view[id_del_tv]
                        with open("alerts_geometrici_v2.json", "w") as f_del:
                            json.dump(db_geo_view, f_del, indent=4)
                        _sync_github_prolab("alerts_geometrici_v2.json", db_geo_view, f"Eliminato alert {tk_rem} da Pro Lab")
                        st.rerun()


# ==========================================
# TAB 02: ANALISI GARCH Volatilità (PARTE 1/3)
# ==========================================
if scelta_modulo == "📈 Analisi GARCH Volatilità":

    st.subheader("📈 Studio Quantitativo della Volatilità (GARCH) & Anticipo Cambio Trend")

    with st.expander("📖 Guida Dettagliata all'Utilizzo: Come Configurare, Leggere e Anticipare il Trend", expanded=True):
        st.markdown("""
        ### 🎯 Cosa fa questo modulo e perché anticipa i cambi di trend?
        I modelli **GARCH** (*Generalized Autoregressive Conditional Heteroskedasticity*) non prevedono direttamente se il prezzo salirà o scenderà, ma **prevedono l'energia e il nervosismo del mercato**. Nei mercati finanziari, **la volatilità cambia regime prima che il trend del prezzo diventi evidente a tutti**:
        * **Prima di un grande rialzo:** La volatilità si comprime ai minimi (*Volatility Squeeze*). Il mercato sembra "addormentato", ma sta accumulando energia.
        * **Alla fine di un crollo:** La volatilità esplode verso un picco di panico (*Climax*). Nel momento esatto in cui la curva GARCH smette di salire e inizia a piegare verso il basso, il trend ribassista è spesso già finito.
        * **All'inizio di un crollo:** La volatilità inizia a salire bruscamente mentre il prezzo perde la sua media di breve periodo (EMA 21).

        ---

        ### ⚙️ Come si usa (Configurazione Parametri)
        1. **Ticker & Orizzonte:** Inserisci il simbolo (es. `AAPL`, `NVDA`, `^GSPC`, `BTC-USD`). Usa **3 Anni** o **5 Anni** per avere abbastanza cicli di mercato.
        2. **Parametri (p, q):**
           * **`p = 1, q = 1`** è lo standard istituzionale più stabile e affidabile.
           * Aumenta **`p` (es. 2 o 3)** se vuoi che il modello reagisca più velocemente agli shock degli ultimi giorni.
        3. **Variante Modello:**
           * **GJR-GARCH (Consigliato per Azioni e Indici):** Cattura l'*effetto leva* (i crolli generano più panico dei rialzi) ed è il più efficace per individuare i minimi di panico.
           * **EGARCH:** Ideale per Crypto e asset molto esplosivi, perché modella la volatilità in scala logaritmica.
           * **Standard GARCH:** Modello simmetrico di base.

        ---

        ### 🚦 Come leggere i Segnali Anticipatori sul Grafico
        Il motore incrocia la **Volatilità Condizionale GARCH** con la **EMA 21** e i **Percentili Storici (252 giorni)** per generare 3 segnali visivi direttamente sul grafico:
        * **🟣 Rombo Viola — SQUEEZE (Compressione Estrema):** La volatilità GARCH è scesa sotto il **15° percentile** dell'ultimo anno. Indica calma piatta prima di un movimento direzionale violento (prepara ordini in breakout).
        * **🟢 Triangolo Verde — INVERSIONE DA PANICO (Climax Bottom):** La volatilità GARCH ha superato l'**85° percentile** (panico estremo) e sta **iniziando a scendere**, mentre il prezzo recupera forza. Spesso anticipa l'inversione rialzista prima degli oscillatori tradizionali.
        * **🔴 Triangolo Rosso — ESPANSIONE RIBASSISTA (Trend Break):** La volatilità GARCH accelera sopra la sua media (+15%) mentre il prezzo rompe al ribasso la **EMA 21**. Segnala l'avvio di una fase distributiva o ribassista.
        """)

    g_col1, g_col2, g_col3 = st.columns(3)
    with g_col1:
        garch_ticker = st.text_input("Inserisci Ticker da analizzare (es. AAPL, BTC-USD, ^GSPC):", value="AAPL", key="garch_tk_input")
        garch_periodo = st.selectbox("Orizzonte storico dati:", ["1 Anno", "3 Anni", "5 Anni", "10 Anni", "Storico Massimo"], index=1, key="garch_per_sel")
        mappa_periodi_garch = {"1 Anno": "1y", "3 Anni": "3y", "5 Anni": "5y", "10 Anni": "10y", "Storico Massimo": "max"}
    with g_col2:
        param_p = st.slider("Ordine Autoregressivo - Shock Recenti (p):", min_value=1, max_value=5, value=1, key="garch_p")
        param_q = st.slider("Ordine Media Mobile - Persistenza Volatilità (q):", min_value=1, max_value=5, value=1, key="garch_q")
    with g_col3:
        mod_type = st.selectbox("Variante Modello GARCH:", ["GJR-GARCH (Asimmetrico)", "EGARCH", "Standard GARCH"], index=0, key="garch_type")
        finestra_regime = st.slider("Finestra Regimi Volatilità (Giorni):", min_value=60, max_value=504, value=252, step=21, key="garch_win_reg")

    st.markdown("---")
    if mod_type == "Standard GARCH":
        st.info(f"ℹ️ **Standard GARCH ({param_p}, {param_q}) [Simmetrico]:** Un rialzo del +5% e un crollo del -5% hanno lo stesso identico impatto sulla volatilità futura.")
    elif mod_type == "GJR-GARCH (Asimmetrico)":
        st.info(f"ℹ️ **GJR-GARCH ({param_p}, {param_q}) [Asimmetrico a Soglia]:** Attiva un fattore extra (*Gamma*) quando i rendimenti sono negativi, catturando il panico da crollo.")
    elif mod_type == "EGARCH":
        st.info(f"ℹ️ **EGARCH ({param_p}, {param_q}) [Esponenziale]:** Modella il logaritmo della volatilità, adattandosi rapidamente a shock estremi senza distorsioni.")
    st.markdown("---")

    # ==========================================
    # TAB 02: MOTORE ECONOMETRICO & KPI (PARTE 2/3)
    # ==========================================
    if st.button("📊 Elabora Modello Volatilità & Segnali Trend", type="primary", key="garch_btn_start"):
        st.info(f"Recupero dati storici e calcolo regimi GARCH per {garch_ticker}...")
        df_g = yf.download(tickers=garch_ticker, period=mappa_periodi_garch[garch_periodo], interval="1d", auto_adjust=False, multi_level_index=False, progress=False)
        
        if df_g is not None and len(df_g) > 100:
            df_g.columns = [str(c).strip() for c in df_g.columns]
            df_g["Close_F"] = df_g["Close"].astype(float)
            df_g["Returns"] = 100 * np.log(df_g["Close_F"] / df_g["Close_F"].shift(1))
            df_g = df_g.dropna().copy()
            
            with st.spinner("Stima econometrica GARCH e rilevamento cambi di regime..."):
                try:
                    if mod_type == "Standard GARCH":
                        mod = arch_model(df_g["Returns"], p=param_p, q=param_q, vol="GARCH", dist="normal")
                    elif mod_type == "GJR-GARCH (Asimmetrico)":
                        mod = arch_model(df_g["Returns"], p=param_p, o=1, q=param_q, vol="GARCH", dist="normal")
                    elif mod_type == "EGARCH":
                        mod = arch_model(df_g["Returns"], p=param_p, q=param_q, vol="EGARCH", dist="normal")
                        
                    res_garch = mod.fit(disp="off")
                    
                    df_g["Cond_Vol"] = res_garch.conditional_volatility * np.sqrt(252)
                    df_g["EMA21"] = df_g["Close_F"].ewm(span=21, adjust=False).mean()
                    
                    win_eff = min(finestra_regime, max(30, len(df_g) // 2))
                    df_g["Vol_Rank"] = df_g["Cond_Vol"].rolling(win_eff).rank(pct=True) * 100.0
                    df_g["Vol_SMA10"] = df_g["Cond_Vol"].rolling(10).mean()
                    df_g["Vol_Diff"] = df_g["Cond_Vol"].diff()

                    cond_squeeze = (df_g["Vol_Rank"] <= 15.0) & (df_g["Vol_Rank"].shift(1) > 15.0)
                    
                    cond_panic_rev = (
                        (df_g["Vol_Rank"].shift(1) >= 85.0) &
                        (df_g["Vol_Diff"] < 0) &
                        (df_g["Vol_Diff"].shift(1) >= 0) &
                        (df_g["Close_F"] > df_g["Close_F"].shift(1))
                    )
                    
                    cond_bear_break = (
                        (df_g["Cond_Vol"] > df_g["Vol_SMA10"] * 1.15) &
                        (df_g["Close_F"] < df_g["EMA21"]) &
                        (df_g["Close_F"].shift(1) >= df_g["EMA21"].shift(1))
                    )

                    vol_attuale = float(df_g["Cond_Vol"].iloc[-1])
                    rank_attuale = float(df_g["Vol_Rank"].iloc[-1]) if not np.isnan(df_g["Vol_Rank"].iloc[-1]) else 50.0
                    prezzo_last = float(df_g["Close_F"].iloc[-1])
                    ema21_last = float(df_g["EMA21"].iloc[-1])
                    var_vol_1d = float(df_g["Vol_Diff"].iloc[-1])

                    if rank_attuale <= 15.0:
                        regime_txt = "🟣 COMPRESSIONE (Squeeze)"
                        azione_txt = "Energia accumulata: attendi breakout"
                    elif rank_attuale >= 85.0 and var_vol_1d < 0:
                        regime_txt = "🟢 PICCO PANICO IN CALO"
                        azione_txt = "Possibile inversione rialzista"
                    elif rank_attuale >= 85.0 and var_vol_1d >= 0:
                        regime_txt = "🚨 PANICO IN ESPANSIONE"
                        azione_txt = "Alta turbolenza: attendi stabilizzazione"
                    elif prezzo_last > ema21_last and var_vol_1d <= 0:
                        regime_txt = "🔵 TREND RIALZISTA ORDINATO"
                        azione_txt = "Volatilità sotto controllo"
                    else:
                        regime_txt = "🟡 TRANSIZIONE / NEUTRALE"
                        azione_txt = "Monitora incrocio EMA 21"

                    k1, k2, k3, k4 = st.columns(4)
                    with k1:
                        st.metric("Volatilità GARCH Attuale", f"{round(vol_attuale, 2)} %", f"{round(var_vol_1d, 2)}% vs ieri")
                    with k2:
                        st.metric("Percentile Storico Volatilità", f"{round(rank_attuale, 1)}° pct", f"Finestra {win_eff}g")
                    with k3:
                        st.metric("Prezzo vs EMA 21", f"$ {round(prezzo_last, 2)}", f"EMA21: $ {round(ema21_last, 2)}")
                    with k4:
                        st.metric("Regime & Segnale Trend", regime_txt, azione_txt)
                    # ==========================================
                    # TAB 02: GRAFICI E REGISTRO SEGNALI (PARTE 3/3)
                    # ==========================================
                    st.markdown("##### 📊 Correlazione Prezzo, EMA 21, Segnali Anticipatori e Volatilità GARCH")
                    fig_combined = grp.Figure()

                    fig_combined.add_trace(grp.Scatter(
                        x=df_g.index, y=df_g["Close_F"], mode="lines",
                        name=f"Prezzo ({garch_ticker})", line=dict(color="#38bdf8", width=2)
                    ))
                    fig_combined.add_trace(grp.Scatter(
                        x=df_g.index, y=df_g["EMA21"], mode="lines",
                        name="EMA 21 (Trend Breve)", line=dict(color="#facc15", width=1.4, dash="dot")
                    ))
                    fig_combined.add_trace(grp.Scatter(
                        x=df_g.index, y=df_g["Cond_Vol"], mode="lines",
                        name=f"Volatilità {mod_type} (%)", line=dict(color="#f43f5e", width=1.7),
                        yaxis="y2"
                    ))

                    df_sq = df_g[cond_squeeze]
                    if not df_sq.empty:
                        fig_combined.add_trace(grp.Scatter(
                            x=df_sq.index, y=df_sq["Close_F"], mode="markers",
                            marker=dict(color="#a855f7", size=10, symbol="diamond"),
                            name="🟣 Squeeze (Compressione)"
                        ))

                    df_pr = df_g[cond_panic_rev]
                    if not df_pr.empty:
                        fig_combined.add_trace(grp.Scatter(
                            x=df_pr.index, y=df_pr["Close_F"], mode="markers",
                            marker=dict(color="#22c55e", size=13, symbol="triangle-up"),
                            name="🟢 Inversione da Panico"
                        ))

                    df_bb = df_g[cond_bear_break]
                    if not df_bb.empty:
                        fig_combined.add_trace(grp.Scatter(
                            x=df_bb.index, y=df_bb["Close_F"], mode="markers",
                            marker=dict(color="#ef4444", size=13, symbol="triangle-down"),
                            name="🔴 Espansione Ribassista"
                        ))

                    fig_combined.update_layout(
                        template="plotly_dark",
                        height=500,
                        margin=dict(l=20, r=20, t=15, b=20),
                        xaxis_rangeslider_visible=False,
                        dragmode="pan",
                        hovermode="x unified",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        xaxis=dict(gridcolor="rgba(51, 65, 85, 0.25)", fixedrange=False),
                        yaxis=dict(
                            title=dict(text=f"Prezzo {garch_ticker} (USD)", font=dict(color="#38bdf8")),
                            tickfont=dict(color="#38bdf8"),
                            gridcolor="rgba(51, 65, 85, 0.25)",
                            fixedrange=False
                        ),
                        yaxis2=dict(
                            title=dict(text="Volatilità Annualizzata GARCH (%)", font=dict(color="#f43f5e")),
                            tickfont=dict(color="#f43f5e"),
                            anchor="x",
                            overlaying="y",
                            side="right",
                            gridcolor="rgba(0, 0, 0, 0)",
                            fixedrange=False
                        )
                    )
                    st.plotly_chart(fig_combined, use_container_width=True, key="garch_combined_chart", config={"scrollZoom": True})

                    st.markdown("##### 🌡️ Termometro Regime di Volatilità (Percentile Rolling 0–100%)")
                    fig_rank = grp.Figure()
                    fig_rank.add_trace(grp.Scatter(
                        x=df_g.index, y=df_g["Vol_Rank"], mode="lines",
                        name="Percentile Volatilità", line=dict(color="#f59e0b", width=1.8),
                        fill="tozeroy", fillcolor="rgba(245, 158, 11, 0.12)"
                    ))
                    fig_rank.add_hline(y=85, line_dash="dash", line_color="#ef4444", annotation_text="Zona Panico (85°)")
                    fig_rank.add_hline(y=15, line_dash="dash", line_color="#a855f7", annotation_text="Zona Squeeze (15°)")
                    fig_rank.update_layout(
                        template="plotly_dark",
                        height=260,
                        margin=dict(l=20, r=20, t=15, b=20),
                        dragmode="pan",
                        yaxis=dict(title="Percentile (%)", range=[0, 100], fixedrange=False),
                        xaxis=dict(fixedrange=False),
                        showlegend=False
                    )
                    st.plotly_chart(fig_rank, use_container_width=True, key="garch_rank_chart", config={"scrollZoom": True})

                    st.markdown("##### 📋 Registro Ultimi Segnali Anticipatori Rilevati")
                    eventi_garch = []
                    for idx_dt, row_g in df_g.iterrows():
                        if cond_squeeze.loc[idx_dt]:
                            eventi_garch.append({"Data": idx_dt.strftime("%d/%m/%Y"), "Segnale": "🟣 SQUEEZE (Compressione)", "Prezzo ($)": round(row_g["Close_F"], 2), "Volatilità GARCH (%)": round(row_g["Cond_Vol"], 2)})
                        if cond_panic_rev.loc[idx_dt]:
                            eventi_garch.append({"Data": idx_dt.strftime("%d/%m/%Y"), "Segnale": "🟢 INVERSIONE DA PANICO", "Prezzo ($)": round(row_g["Close_F"], 2), "Volatilità GARCH (%)": round(row_g["Cond_Vol"], 2)})
                        if cond_bear_break.loc[idx_dt]:
                            eventi_garch.append({"Data": idx_dt.strftime("%d/%m/%Y"), "Segnale": "🔴 ESPANSIONE RIBASSISTA", "Prezzo ($)": round(row_g["Close_F"], 2), "Volatilità GARCH (%)": round(row_g["Cond_Vol"], 2)})

                    if eventi_garch:
                        df_ev_garch = pd.DataFrame(eventi_garch).iloc[::-1].head(15)
                        st.dataframe(df_ev_garch, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nessun segnale estremo rilevato nella finestra selezionata.")

                except Exception as ex:
                    st.error(f"Errore durante la convergenza del modello GARCH: {ex}")
        else:
            st.warning("Dati storici insufficienti. Prova ad estendere l'orizzonte temporale o verifica il ticker.")
