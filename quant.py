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

# ==============================================================================
# STRUTTURA DI NAVIGAZIONE LATERALE (SIDEBAR) CON TAB VERTICALI A SCOMPARSA
# ==============================================================================
with st.sidebar:
    st.image("logo_fmjp.png", use_container_width=True)
    st.markdown("## 📺 Seleziona l'analisi che vuoi approfondire:")
    st.markdown("🤖 **Menu Navigazione Moduli**")

    opzioni_menu = [
        "🧪 TradingView Pro",
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

        "🧪 TradingView Pro": (
        "**Scopo Operativo & Architettura:** Workstation grafica interattiva multi-timeframe (15m–1M) "
        "dotata di indicatori tecnici sovrapponibili (EMA 20/50/100/200, Bande di Bollinger, VWAP), "
        "oscillatori sincronizzati (RSI, MACD), Triple Volume Profile e strumenti di disegno "
        "con aggancio magnetico alle candele (Trendline, Livelli Orizzontali, Rettangoli, Fibonacci e Tool R:R)."
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
    
# ==============================================================================
# TAB 01: TRADINGVIEW PRO LAB (PARTE 1/4 - CONTROLLI & MENU A SCOMPARSA)
# ==============================================================================
if scelta_modulo == "🧪 TradingView Pro":

    st.subheader("🧪 TradingView Pro — Workstation Grafica Avanzata")

    # 1. BARRA SUPERIORE PULITA (SOLO TICKER, TIMEFRAME E STORICO)
    tv_c1, tv_c2, tv_c3 = st.columns(3)
    with tv_c1:
        tv_ticker = st.text_input("Simbolo / Ticker:", value="AAPL", key="tv_test_tk").strip().upper()
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
        tv_per_label = st.selectbox("Orizzonte Storico:", list(opz_per.keys()), index=min(1, len(opz_per)-1), key="tv_test_per")
        tv_per = opz_per[tv_per_label]

    # 2. MENU A SCOMPARSA: INDICATORI TECNICI, POC, SCALA LOG & OSCILLATORI
    with st.expander("📊 Indicatori Tecnici, Volume Profile, Scala & Oscillatori", expanded=False):
        ind_col1, ind_col2, ind_col3 = st.columns(3)
        with ind_col1:
            tv_log_scale = st.checkbox("📐 Scala Logaritmica", value=False, key="tv_test_log")
            tv_show_vp = st.checkbox("📊 Mostra 3 Volume Profile (POC)", value=True, key="tv_test_vp")
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
                options=["Nessuno", "RSI (14)", "MACD (12, 26, 9)", "Z-Score (±2)"],
                index=3,
                key="tv_test_osc"
            )
            tv_z_win = 50
            if tv_sub_osc == "Z-Score (±2)":
                tv_z_win = st.slider("Finestra Z-Score (Candele):", min_value=20, max_value=100, value=50, step=5, key="tv_z_win_sl")
            tv_rr_ratio = st.selectbox("Rapporto R:R per Tool Posizione:", [1.4, 2.0, 3.0, 4.0], index=1, key="tv_test_rr_mult")

    # 3. MENU A SCOMPARSA: STRUMENTI DI ANALISI GRAFICA
    with st.expander("✏️ Strumenti di Analisi Grafica", expanded=False):
        tv_tool = st.radio(
            "Seleziona strumento:",
            [
                "📐 Trendline Diagonale (2 Clic)",
                "➖ Livello Orizzontale (1 Clic)",
                "⬜ Rettangolo Zona (2 Clic)",
                "🌀 Ritracciamento Fibonacci (2 Clic: Min -> Max)",
                "🎯 Posizione Long/Short R:R (2 Clic: Entry -> Stop Loss)"
            ],
            horizontal=True,
            key="tv_test_tool"
        )

        tv_rect_extend = False
        if "Rettangolo" in tv_tool:
            tv_rect_extend = st.checkbox("➡️ Estendi Rettangolo all'infinito a destra (Zona Supply/Demand)", value=False, key="tv_rect_ext_chk")

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
    # TAB 01: TRADINGVIEW PRO LAB (PARTE 2/4 - CALCOLO & COSTRUZIONE GRAFICO)
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
        sxy.iloc[n_z-1:] = xy_c
        m_z = (n_z * sxy - sx * sy) / den_z
        q_z = (sx2 * sy - sx * sxy) / den_z
        p_teo = m_z * n_z + q_z
        mx, vx = sx / n_z, sx2 / n_z - ((sx / n_z)**2)
        my, vy = sy / n_z, sy2 / n_z - ((sy / n_z)**2)
        cov_z = sxy / n_z - (mx * my)
        std_res = np.sqrt(np.clip(vy - (2 * m_z * cov_z) + (m_z**2 * vx), 1e-5, None))
        df_tv["Z_Score"] = ((close_s - p_teo) / std_res).fillna(0.0)

    has_vol = tv_vol and vol_s.sum() > 0
    has_osc = tv_sub_osc != "Nessuno"

    if has_vol and has_osc:
        n_rows, r_heights = 3, [0.64, 0.16, 0.20]
    elif has_vol or has_osc:
        n_rows, r_heights = 2, [0.75, 0.25]
    else:
        n_rows, r_heights = 1, [1.0]

    fig_tv = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=r_heights
    )

    fig_tv.add_trace(grp.Candlestick(
        x=df_tv.index,
        open=open_s, high=high_s, low=low_s, close=close_s,
        increasing_line_color="#089981", increasing_fillcolor="#089981",
        decreasing_line_color="#f23645", decreasing_fillcolor="#f23645",
        name=tv_ticker,
        hoverinfo="none"
    ), row=1, col=1)

    step_tempo = (df_tv.index[-1] - df_tv.index[-2]) if len(df_tv) > 1 else pd.Timedelta(days=1)
    d_start = df_tv.index.min()
    d_end = df_tv.index.max()
    d_future = d_end + (step_tempo * 25)

    p_min_g, p_max_g = float(low_s.min()) * 0.90, float(high_s.max()) * 1.10
    livelli_y_liberi = np.linspace(p_min_g, p_max_g, 45)
    date_griglia = list(df_tv.index[::max(1, len(df_tv)//60)]) + [d_end + step_tempo * k for k in range(1, 24, 2)]

    xm, ym = [], []
    for dt_g in date_griglia:
        for y_g in livelli_y_liberi:
            xm.append(dt_g)
            ym.append(float(y_g))

    fig_tv.add_trace(grp.Scatter(
        x=xm, y=ym,
        mode="markers",
        marker=dict(size=16, opacity=0.01, color="#38bdf8"),
        showlegend=False,
        hovertemplate="Data: %{x}<br>Prezzo: <b>%{y:.2f} $</b><extra></extra>"
    ), row=1, col=1)

    colori_ema = {"EMA20": "#38bdf8", "EMA50": "#f59e0b", "EMA100": "#a855f7", "EMA200": "#ef4444"}
    for col_e, col_hex in colori_ema.items():
        if col_e in df_tv.columns:
            fig_tv.add_trace(grp.Scatter(
                x=df_tv.index, y=df_tv[col_e], mode="lines",
                line=dict(color=col_hex, width=1.5), name=col_e
            ), row=1, col=1)

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
            fig_tv.add_trace(grp.Scatter(
                x=df_tv.index[sh_clean],
                y=high_s.iloc[sh_clean] * 1.004,
                mode="markers+text",
                marker=dict(color="#ef4444", size=9, symbol="triangle-down"),
                text=[f"{round(float(v), 2)}" for v in high_s.iloc[sh_clean]],
                textposition="top center",
                textfont=dict(color="#ef4444", size=9),
                name="Swing High"
            ), row=1, col=1)

        if len(sl_clean) > 0:
            fig_tv.add_trace(grp.Scatter(
                x=df_tv.index[sl_clean],
                y=low_s.iloc[sl_clean] * 0.996,
                mode="markers+text",
                marker=dict(color="#22c55e", size=9, symbol="triangle-up"),
                text=[f"{round(float(v), 2)}" for v in low_s.iloc[sl_clean]],
                textposition="bottom center",
                textfont=dict(color="#22c55e", size=9),
                name="Swing Low"
            ), row=1, col=1)


    if tv_sub_osc == "Z-Score (±2)" and "Z_Score" in df_tv.columns:
        mask_z_up = df_tv["Z_Score"] >= 2.0
        mask_z_dn = df_tv["Z_Score"] <= -2.0
        if mask_z_up.any():
            fig_tv.add_trace(grp.Scatter(
                x=df_tv.index[mask_z_up], y=high_s[mask_z_up] * 1.006,
                mode="markers", marker=dict(color="#22c55e", size=8, symbol="circle", line=dict(color="white", width=1)),
                name="Z >= +2 (Prezzo)"
            ), row=1, col=1)
        if mask_z_dn.any():
            fig_tv.add_trace(grp.Scatter(
                x=df_tv.index[mask_z_dn], y=low_s[mask_z_dn] * 0.994,
                mode="markers", marker=dict(color="#ef4444", size=8, symbol="circle", line=dict(color="white", width=1)),
                name="Z <= -2 (Prezzo)"
            ), row=1, col=1)

    if tv_show_vp and len(df_tv) > 10:
        p1, _, _, _, _ = calc_vp(df_tv, div=100)
        idx_ath = high_s.idxmax()
        p2, _, _, _, _ = calc_vp(df_tv.loc[idx_ath:], div=80) if len(df_tv.loc[idx_ath:]) > 5 else (None, None, None, [], [])
        p3, _, _, _, _ = calc_vp(df_tv.tail(min(120, len(df_tv))), div=80)

        for p_val, p_col, p_lbl, p_dash in [
            (p1, "#ef4444", "POC Storico", "solid"),
            (p2, "#3b82f6", "POC ATH", "dash"),
            (p3, "#10b981", "POC Recente", "dot")
        ]:
            if p_val is not None:
                fig_tv.add_shape(type="line", x0=d_start, x1=d_end, y0=p_val, y1=p_val, line=dict(color=p_col, width=1.8, dash=p_dash), row=1, col=1)
                fig_tv.add_annotation(x=d_end, y=p_val, text=f"{p_lbl}: {round(p_val, 2)}", showarrow=False, xanchor="right", yshift=10, font=dict(color=p_col, size=10), bgcolor="rgba(15,23,42,0.8)", row=1, col=1)
    # ==========================================================================
    # TAB 01: TRADINGVIEW PRO LAB (PARTE 3/4 - DISEGNO FORME & SCATOLA R:R)
    # ==========================================================================
    t_fut_s = d_future.timestamp()
    for shp in st.session_state["tv_shapes_list"]:
        if shp["ticker"] != tv_ticker:
            continue
        st_type = shp["type"]
        if st_type == "horizontal":
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
            fig_tv.add_shape(
                type="rect",
                x0=x_left_r,
                x1=x_right_r,
                y0=min(shp["y0"], shp["y1"]),
                y1=max(shp["y0"], shp["y1"]),
                fillcolor="rgba(250, 204, 21, 0.16)",
                line=dict(color="#facc15", width=1.8),
                row=1, col=1
            )
        elif st_type == "fibo":
            y_low_f, y_high_f = shp["y0"], shp["y1"]
            diff_f = y_high_f - y_low_f
            livelli_fib = [(0.0, "#ef4444"), (0.236, "#f97316"), (0.382, "#eab308"), (0.5, "#22c55e"), (0.618, "#06b6d4"), (0.786, "#3b82f6"), (1.0, "#a855f7")]
            for lvl, c_fib in livelli_fib:
                y_lvl = y_high_f - (diff_f * lvl)
                fig_tv.add_shape(type="line", x0=shp["x0"], x1=d_future, y0=y_lvl, y1=y_lvl, line=dict(color=c_fib, width=1.2, dash="dot"), row=1, col=1)
                fig_tv.add_annotation(x=shp["x0"], y=y_lvl, text=f"Fib {round(lvl*100, 1)}% ({round(y_lvl, 2)})", showarrow=False, xanchor="left", yshift=7, font=dict(color=c_fib, size=9), row=1, col=1)
        elif st_type == "rr_tool":
            entry_p = float(shp["y0"])
            sl_p = float(shp["y1"])
            risk_u = entry_p - sl_p
            tp_p = float(shp.get("tp_custom", entry_p + (risk_u * shp["rr"])))
            rr_eff = abs(tp_p - entry_p) / abs(risk_u) if abs(risk_u) > 0 else shp["rr"]
            x_start_box = pd.to_datetime(shp["x0"])
            x_end_box = max(d_future, x_start_box + (step_tempo * 18))

            fig_tv.add_shape(
                type="rect", x0=x_start_box, x1=x_end_box,
                y0=min(entry_p, sl_p), y1=max(entry_p, sl_p),
                fillcolor="rgba(239, 68, 68, 0.25)", line=dict(color="#ef4444", width=1.5),
                row=1, col=1
            )
            fig_tv.add_shape(
                type="rect", x0=x_start_box, x1=x_end_box,
                y0=min(entry_p, tp_p), y1=max(entry_p, tp_p),
                fillcolor="rgba(34, 197, 94, 0.25)", line=dict(color="#22c55e", width=1.5),
                row=1, col=1
            )
            fig_tv.add_shape(
                type="line", x0=x_start_box, x1=x_end_box,
                y0=entry_p, y1=entry_p,
                line=dict(color="#ffffff", width=1.8, dash="dash"),
                row=1, col=1
            )
            pct_tp = ((tp_p - entry_p) / entry_p) * 100
            pct_sl = ((sl_p - entry_p) / entry_p) * 100
            fig_tv.add_annotation(x=x_end_box, y=tp_p, text=f"🎯 TP: {round(tp_p, 2)}$ ({round(pct_tp, 1)}%) | R:R 1:{round(rr_eff, 1)}", showarrow=False, xanchor="right", yshift=10, font=dict(color="#22c55e", size=10, weight="bold"), bgcolor="rgba(15,23,42,0.85)", row=1, col=1)
            fig_tv.add_annotation(x=x_end_box, y=entry_p, text=f"⚪ ENTRY: {round(entry_p, 2)}$", showarrow=False, xanchor="right", yshift=0, font=dict(color="#ffffff", size=10, weight="bold"), bgcolor="rgba(15,23,42,0.85)", row=1, col=1)
            fig_tv.add_annotation(x=x_end_box, y=sl_p, text=f"🛑 SL: {round(sl_p, 2)}$ ({round(pct_sl, 1)}%)", showarrow=False, xanchor="right", yshift=-12, font=dict(color="#ef4444", size=10, weight="bold"), bgcolor="rgba(15,23,42,0.85)", row=1, col=1)
    # ==========================================================================
    # TAB 01: TRADINGVIEW PRO LAB (PARTE 4/4 - OSCILLATORI, RENDER & CLIC)
    # ==========================================================================
    if st.session_state["tv_pt_a"] is not None:
        pa = st.session_state["tv_pt_a"]
        fig_tv.add_trace(grp.Scatter(x=[pa["x"]], y=[pa["y"]], mode="markers", marker=dict(color="#facc15", size=14, symbol="cross"), showlegend=False), row=1, col=1)

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
            fig_tv.update_yaxes(title_text="RSI", range=tuple((0, 100)), row=curr_row, col=1)
        elif tv_sub_osc == "MACD (12, 26, 9)":
            hist_cols = ["#089981" if v >= 0 else "#f23645" for v in df_tv["MACD_HIST"].fillna(0)]
            fig_tv.add_trace(grp.Bar(x=df_tv.index, y=df_tv["MACD_HIST"], marker_color=hist_cols, name="MACD Hist", showlegend=False), row=curr_row, col=1)
            fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=df_tv["MACD"], mode="lines", line=dict(color="#38bdf8", width=1.5), name="MACD"), row=curr_row, col=1)
            fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=df_tv["MACD_SIG"], mode="lines", line=dict(color="#f59e0b", width=1.5), name="Signal"), row=curr_row, col=1)
            fig_tv.update_yaxes(title_text="MACD", row=curr_row, col=1)
        elif tv_sub_osc == "Z-Score (±2)":
            z_s = df_tv["Z_Score"]
            fig_tv.add_trace(grp.Scatter(x=df_tv.index, y=z_s, mode="lines", line=dict(color="#38bdf8", width=1.6), name="Z-Score"), row=curr_row, col=1)
            fig_tv.add_hline(y=2.0, line_dash="dash", line_color="#22c55e", annotation_text="+2.0", row=curr_row, col=1)
            fig_tv.add_hline(y=0.0, line_dash="solid", line_color="rgba(255,255,255,0.2)", row=curr_row, col=1)
            fig_tv.add_hline(y=-2.0, line_dash="dash", line_color="#ef4444", annotation_text="-2.0", row=curr_row, col=1)

            m_up = z_s >= 2.0
            m_dn = z_s <= -2.0
            if m_up.any():
                fig_tv.add_trace(grp.Scatter(
                    x=df_tv.index[m_up], y=z_s[m_up], mode="markers",
                    marker=dict(color="#22c55e", size=8, symbol="circle", line=dict(color="white", width=1)),
                    name="Z >= +2", showlegend=False
                ), row=curr_row, col=1)
            if m_dn.any():
                fig_tv.add_trace(grp.Scatter(
                    x=df_tv.index[m_dn], y=z_s[m_dn], mode="markers",
                    marker=dict(color="#ef4444", size=8, symbol="circle", line=dict(color="white", width=1)),
                    name="Z <= -2", showlegend=False
                ), row=curr_row, col=1)

            fig_tv.update_yaxes(title_text="Z-Score", range=tuple((-4.5, 4.5)), row=curr_row, col=1)

    fig_tv.update_layout(
        template="plotly_dark",
        height=740,
        margin=dict(l=20, r=20, t=15, b=15),
        xaxis_rangeslider_visible=False,
        clickmode="event+select",
        dragmode="pan",
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1)
    )
    fig_tv.update_yaxes(type="log" if tv_log_scale else "linear", fixedrange=False, row=1, col=1)
    fig_tv.update_xaxes(range=tuple((d_start, d_future)), fixedrange=False)

    ev_tv = st.plotly_chart(
        fig_tv,
        use_container_width=True,
        config={"scrollZoom": True},
        key=f"tv_lab_chart_{tv_ticker}_{tv_tf}_{len(st.session_state['tv_shapes_list'])}_{st.session_state['tv_pt_a'] is not None}",
        on_select="rerun",
        selection_mode="points"
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
                else:
                    if st.session_state["tv_pt_a"] is None:
                        st.session_state["tv_pt_a"] = {"x": x_clk, "y": y_clk}
                        st.rerun()
                    else:
                        pa = st.session_state["tv_pt_a"]
                        is_pos_tool = "Posizione" in tv_tool
                        if is_pos_tool or x_clk != pa["x"]:
                            t_map = {
                                "Trendline": "trendline",
                                "Rettangolo": "rect",
                                "Fibonacci": "fibo",
                                "Posizione": "rr_tool"
                            }
                            k_type = next(v for k, v in t_map.items() if k in tv_tool)
                            st.session_state["tv_shapes_list"].append({
                                "ticker": tv_ticker, "type": k_type,
                                "x0": pa["x"], "y0": pa["y"],
                                "x1": x_clk, "y1": y_clk,
                                "rr": tv_rr_ratio,
                                "extend": tv_rect_extend
                            })
                            st.session_state["tv_pt_a"] = None
                            st.rerun()

    if "Posizione" in tv_tool:
        with st.expander("🎯 Imposta Livelli Esatti Posizione Pendente (Entry / Stop Loss / Take Profit)", expanded=True):
            p_last_tv = float(close_s.iloc[-1])
            pc1, pc2, pc3, pc4 = st.columns(4)
            with pc1:
                man_entry = st.number_input("Prezzo Entry ($):", value=round(p_last_tv, 2), step=0.10, key="tv_man_entry")
            with pc2:
                man_sl = st.number_input("Stop Loss ($):", value=round(p_last_tv * 0.96, 2), step=0.10, key="tv_man_sl")
            with pc3:
                tp_default = man_entry + ((man_entry - man_sl) * tv_rr_ratio)
                man_tp = st.number_input("Take Profit ($):", value=round(tp_default, 2), step=0.10, key="tv_man_tp")
            with pc4:
                st.markdown("<div style='padding-top:28px;'></div>", unsafe_allow_html=True)
                if st.button("➕ Disegna Posizione sul Grafico", type="primary", use_container_width=True):
                    if man_entry != man_sl:
                        st.session_state["tv_shapes_list"].append({
                            "ticker": tv_ticker, "type": "rr_tool",
                            "x0": str(d_end), "y0": man_entry,
                            "x1": str(d_future), "y1": man_sl,
                            "tp_custom": man_tp,
                            "rr": abs(man_tp - man_entry) / abs(man_entry - man_sl)
                        })
                        st.rerun()

    ctrl1, ctrl2, ctrl3 = st.columns(3)
    with ctrl1:
        if st.session_state["tv_pt_a"]:
            st.info(f"📍 Primo punto fissato a **{round(st.session_state['tv_pt_a']['y'], 2)} $** — Clicca il secondo punto.")
        else:
            st.caption("💡 Puoi cliccare liberamente ovunque sul grafico (anche nel vuoto o sul lato destro futuro).")
    with ctrl2:
        if st.button("↩️ Annulla Ultimo Disegno", use_container_width=True):
            if st.session_state["tv_pt_a"] is not None:
                st.session_state["tv_pt_a"] = None
            elif st.session_state["tv_shapes_list"]:
                st.session_state["tv_shapes_list"].pop()
            st.rerun()
    with ctrl3:
        if st.button("🗑️ Pulisci Grafico", use_container_width=True):
            st.session_state["tv_pt_a"] = None
            st.session_state["tv_shapes_list"] = [s for s in st.session_state["tv_shapes_list"] if s["ticker"] != tv_ticker]
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
