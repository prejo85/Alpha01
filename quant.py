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
import os
from dotenv import load_dotenv
from urllib.parse import quote


# Carica le chiavi dal file .env (se presente)
load_dotenv()

st.set_page_config(layout="wide", page_title="POC Scanner Pro", page_icon="📐")

import base64

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
    st.session_state["menu_navigazione_moduli"] = "📺 TradingView Interactive Canvas"
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


# Intercetta i link diretti provenienti dagli alert Telegram
params = st.query_params
if "ticker" in params and not st.session_state.get("url_gia_letto", False):
    tk_url = str(params["ticker"]).upper().strip()
    tf_url = str(params.get("tf", "Giornaliero (Daily)")).strip()
    
    st.session_state["menu_navigazione_moduli"] = "📺 TradingView Interactive Canvas"
    st.session_state["can_tk"] = tk_url
    st.session_state["can_tf"] = tf_url
    st.session_state["url_gia_letto"] = True

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

    @import url('https://googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');
    
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

st.title("📐 Dashboard Quantanalisys")

if "asset_type_index" not in st.session_state:
    st.session_state.asset_type_index = 0
# PROTEZIONE: Recupero sicuro dei dati sensibili dall'ambiente
T_ID = os.getenv("TELEGRAM_CHAT_ID", "2072895073")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TESTA_INTERNET = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
# ==============================================================================
# DATABASE INTERNO DEI PANIERI AZIONARI AGGIORNATO E AMPLIATO
# ==============================================================================
SP500_FULL = (
    "MMM,AOS,ABT,ABBV,ACN,ADBE,AMD,AES,AFL,A,APD,ABNB,AKAM,ALB,ARE,ALGN,ALLE,LNT,ALL,GOOGL,GOOG,MO,AMZN,AMCR,AEE,"
    "AEP,AXP,AIG,AMT,AWK,AMP,AME,AMGN,APH,ADI,AON,APA,APO,AAPL,AMAT,APP,APTV,ACGL,ADM,ARES,ANET,AJG,AIZ,T,ATO,ADSK,"
    "ADP,AZO,AVY,AXON,BKR,BALL,BAC,BAX,BDX,BRK-B,BBY,TECH,BIIB,BLK,BX,BE,BNY,BA,BKNG,BSX,BMY,AVGO,BR,BRO,BF-B,BG,"
    "BXP,CHRW,CDNS,CPT,COF,CAH,CCL,CARR,CVNA,CASY,CAT,CBOE,CBRE,CDW,COR,CNC,CNP,CF,CRL,SCHW,CHTR,CVX,CMG,CB,CHD,"
    "CIEN,CI,CINF,CTAS,CSCO,C,CFG,CLX,CME,CMS,KO,CTSH,COHR,COIN,CL,CMCSA,FIX,COP,ED,STZ,CEG,COO,CPRT,GLW,CPAY,CTVA,"
    "CSGP,COST,CRH,CRWD,CCI,CSX,CMI,CVS,DHR,DRI,DDOG,DVA,DECK,DE,DELL,DAL,DVN,DXCM,FANG,DLR,DG,DLTR,D,DPZ,DASH,DOV,"
    "DOW,DHI,DTE,DUK,DD,ETN,EBAY,ECHO,ECL,EIX,EW,ELV,EME,EMR,ETR,EOG,EQT,EFX,EQIX,ERIE,ESS,EL,EG,EVRG,P,ES,EXC,EXE,"
    "EXPE,EXPD,EXR,XOM,FFIV,FDS,FICO,FAST,FRT,FDX,FDXF,FERG,FIS,FITB,FSLR,FE,FISV,FLEX,F,FTNT,FTV,FOXA,FOX,BEN,FCX,"
    "GRMN,IT,GE,GEHC,GEV,GEN,GNRC,GD,GIS,GM,GPC,GILD,GPN,GL,GDDY,GS,HAL,HIG,HAS,HCA,DOC,HSIC,HSY,HPE,HLT,HD,HON,HRL,"
    "HST,HWM,HUBB,HUM,HBAN,HII,IBM,IEX,IDXX,ITW,ILMN,INCY,IR,PODD,INTC,IBKR,ICE,IFF,IP,INTU,ISRG,IVZ,INVH,IQV,"
    "IRM,JBHT,JBL,JKHY,J,JNJ,JCI,JPM,KVUE,KDP,KEY,KEYS,KMB,KIM,KMI,KKR,KLAC,KHC,KR,LHX,LH,LRCX,LVS,LDOS,LEN,LII,LLY,"
    "LIN,LYV,LMT,L,LOW,LULU,LITE,LYB,MTB,MPC,MAR,MRSH,MLM,MRVL,MAS,MA,MKC,MCD,MCK,MDT,MRK,META,MET,MTD,MGM,MCHP,MU,"
    "MSFT,MAA,MRNA,MDLZ,MPWR,MNST,MCO,MS,MOS,MSI,MSCI,NDAQ,NTAP,NFLX,NEM,NWSA,NWS,NEE,NKE,NI,NDSN,NSC,NTRS,NOC,NCLH,"
    "NRG,NUE,NVDA,NVR,NXPI,ORLY,OXY,ODFL,OMC,ON,OKE,ORCL,OTIS,PCAR,PKG,PLTR,PANW,PSKY,PH,PAYX,PYPL,PNR,PEP,PFE,PCG,"
    "PM,PSX,PNW,PNC,PPG,PPL,PFG,PG,PGR,PLD,PRU,PEG,PTC,PSA,PHM,PWR,QCOM,DGX,Q,RL,RJF,RDDT,RTX,O,REG,REGN,RF,RSG,"
    "RMD,RVTY,HOOD,ROK,ROL,ROP,ROST,RCL,SPGI,CRM,SBAC,SLB,STX,SRE,NOW,SHW,SPG,SWKS,SJM,SW,SNA,SOLV,SO,LUV,SWK,SBUX,"
    "STT,STLD,STE,SYK,SMCI,SYF,SNPS,SYY,TMUS,TROW,TTWO,TPR,TRGP,TGT,TEL,TDY,TER,TSLA,TXN,TPL,TXT,TMO,TJX,TKO,TSCO,"
    "TT,TDG,TRV,TRMB,TFC,TYL,TSN,USB,UBER,UDR,ULTA,UNP,UAL,UPS,URI,UNH,UHS,VLO,VEEV,VTR,VLTO,VRSN,VRSK,VZ,VRTX,VRT,"
    "VTRS,VICI,V,VST,VMC,WRB,GWW,WAB,WMT,DIS,WBD,WM,WAT,WEC,WFC,WELL,WST,WDC,WY,WSM,WMB,WTW,WDAY,WYNN,XEL,XYL,YUM,"
    "ZBRA,ZBH,ZTS,VYLR"
)

NASDAQ_FULL = (
    "MDLZ,ADI,ADP,ADSK,AAL,ALGN,AMAT,AMD,AMGN,AMZN,ANSS,ASML,TEAM,ADBE,BIIB,BMRN,BKNG,AVGO,CDNS,CDW,CHTR,"
    "CHKP,CTAS,CSCO,CTSH,CMCSA,CPRT,COST,CRWD,DLTR,DXCM,EBAY,EA,EXPE,FAST,META,FISV,FOXA,FOX,GILD,GOOGL,GOOG,"
    "IDXX,ILMN,INCY,INTC,INTU,ISRG,JBHT,JD,KDP,KLAC,KHC,LRCX,MELI,MAR,MTCH,MCHP,MU,MSFT,MRNA,MNST,"
    "NTES,NFLX,NVDA,NXPI,ORLY,OKTA,ODFL,PCAR,PAYX,PYPL,PEP,PDD,REGN,ROST,SIRI,SWKS,SBUX,SNPS,TMUS,TSLA,"
    "TXN,TCOM,VRSN,VRTX,WBA,WDAY,XEL,ZM,ALAB,CRWV,RKLB,NBIS,STX,MPWR,TER"
)

FTSEMIB_FULL = (
    "A2A.MI,AMP.MI,AZM.MI,BAMI.MI,BCA.MI,BMED.MI,BPER.MI,CPR.MI,DIA.MI,ENI.MI,ERG.MI,EVO.MI,FBK.MI,G.MI,"
    "HER.MI,INW.MI,ISP.MI,LDO.MI,MB.MI,MONC.MI,NEXI.MI,PIRC.MI,PRY.MI,PST.MI,RACE.MI,REC.MI,SGO.MI,SRG.MI,"
    "STLAM.MI,STMPA.MI,TEN.MI,TRN.MI,UCG.MI,UNI.MI,YSVP.MI,BMPS.MI,BPSO.MI,BC.MI,AVIO.MI,IP.MI"
)
TOTAL1_LEADERS = "BTC-USD,ETH-USD,USDT-USD,USDC-USD"
TOTAL2_MAJORS = "SOL-USD,BNB-USD,XRP-USD,ADA-USD,TRX-USD,DOT-USD,LINK-USD,AVAX-USD,TON-USD,SHIB-USD,SUI-USD"
TOTAL3_ALTS = (
    "MATIC-USD,LTC-USD,UNI-USD,NEAR-USD,APT-USD,ICP-USD,STX-USD,FIL-USD,ATOM-USD,"
    "IMX-USD,RNDR-USD,GRT-USD,FTM-USD,OP-USD,ARB-USD,INJ-USD,LDO-USD,TIA-USD,"
    "SEI-USD,AAVE-USD,MKR-USD,RUNE-USD,EGLD-USD,THETA-USD,ALGO-USD,XLM-USD,VET-USD,"
    "FLOW-USD,AXS-USD,SAND-USD,MANA-USD,GALA-USD,CHZ-USD,DYDX-USD,CRV-USD,ENS-USD,"
    "LRC-USD,ANKR-USD,WOO-USD,GMX-USD,JUP-USD,FET-USD,TAO-USD,WLD-USD,ONDO-USD,PYTH-USD,JTO-USD"
)
CRYPTO_FULL = f"{TOTAL1_LEADERS},{TOTAL2_MAJORS},{TOTAL3_ALTS}"

MIDCAP_US = (
    "ONDS,RGTI,AGIO,AIRS,ALG,HUBS,CLX,IREN,RIVN,MARA,JAN,LIFE,MXL,IESC,HALO,TXRH,DKS,WFR,DT,"
    "SMR,XPO,GFL,FLEX,JBL,AA,MTDR,CHX,OVV,STNG,WBS,DINO,AMR,SF,LANC,PNR,XOM,AAL,X"
)
CRYPTO_STOCKS = "COIN,MARA,IREN,CLSK,WULF,MSTR,HUT,CORZ,RIOT,CIFR,BTBT,BOOM"
EUROSTOXX_FULL = (
    "ADS.DE,ALV.DE,BAS.DE,BAYN.DE,BMW.DE,DB1.DE,DBK.DE,DPW.DE,DTE.DE,EOAN.DE,IFX.DE,MBG.DE,MUV2.DE,RWE.DE,SAP.DE,SIE.DE,"
    "AI.PA,AIR.PA,ALO.PA,CS.PA,BNP.PA,CA.PA,DG.PA,EL.PA,ERF.PA,OR.PA,MC.PA,ML.PA,ORAN.PA,RI.PA,RMS.PA,SAN.PA,SGO.PA,"
    "SU.PA,TTE.PA,VIE.PA,VIV.PA,ASML.AS,ADYEN.AS,INGA.AS,KPN.AS,PRX.AS,BBVA.MC,SAN.MC,ITX.MC,REP.MC,ENI.MI,ISP.MI,UCG.MI"
)

ELENCO_PANIERI = [
    "S&P 500", 
    "NASDAQ 100", 
    "FTSE MIB (FIB)", 
    "Crypto", 
    "US Mid-Caps", 
    "Crypto & AI Stocks", 
    "Euro Stoxx 50"
]
def ottieni_paniere(nome_paniere):
    if nome_paniere == "S&P 500": return SP500_FULL
    elif nome_paniere == "NASDAQ 100": return NASDAQ_FULL
    elif nome_paniere == "FTSE MIB (FIB)": return FTSEMIB_FULL
    elif nome_paniere == "Crypto": return CRYPTO_FULL
    elif nome_paniere == "US Mid-Caps": return MIDCAP_US
    elif nome_paniere == "Crypto & AI Stocks": return CRYPTO_STOCKS
    elif nome_paniere == "Euro Stoxx 50": return EUROSTOXX_FULL
    return "AAPL,MSFT"

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