import os
import json
import time
import requests
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats
from sklearn.ensemble import RandomForestClassifier

# Configurazione da Secrets di GitHub
T_ID = os.getenv("TELEGRAM_CHAT_ID", "2072895073")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

TOTAL1_LEADERS = "BTC-USD,ETH-USD,USDT-USD,USDC-USD"
TOTAL2_MAJORS = "SOL-USD,BNB-USD,XRP-USD,ADA-USD,TRX-USD,DOT-USD,LINK-USD,AVAX-USD,TON-USD,SHIB-USD,SUI-USD"
TOTAL3_ALTS = (
    "MATIC-USD,LTC-USD,UNI-USD,NEAR-USD,APT-USD,ICP-USD,STX-USD,FIL-USD,ATOM-USD,"
    "IMX-USD,RNDR-USD,GRT-USD,FTM-USD,OP-USD,ARB-USD,INJ-USD,LDO-USD,TIA-USD,"
    "SEI-USD,AAVE-USD,MKR-USD,RUNE-USD,EGLD-USD,THETA-USD,ALGO-USD,XLM-USD,VET-USD,"
    "FLOW-USD,AXS-USD,SAND-USD,MANA-USD,GALA-USD,CHZ-USD,DYDX-USD,CRV-USD,ENS-USD,"
    "LRC-USD,ANKR-USD,WOO-USD,GMX-USD,JUP-USD,FET-USD,TAO-USD,WLD-USD,ONDO-USD,PYTH-USD,JTO-USD"
)

PANIERI_WEEKEND = {
    "SP500": (
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
    ),
    "NASDAQ": (
        "MDLZ,ADI,ADP,ADSK,AAL,ALGN,AMAT,AMD,AMGN,AMZN,ANSS,ASML,TEAM,ADBE,BIIB,BMRN,BKNG,AVGO,CDNS,CDW,CHTR,"
        "CHKP,CTAS,CSCO,CTSH,CMCSA,CPRT,COST,CRWD,DLTR,DXCM,EBAY,EA,EXPE,FAST,META,FISV,FOXA,FOX,GILD,GOOGL,GOOG,"
        "IDXX,ILMN,INCY,INTC,INTU,ISRG,JBHT,JD,KDP,KLAC,KHC,LRCX,MELI,MAR,MTCH,MCHP,MU,MSFT,MRNA,MNST,"
        "NTES,NFLX,NVDA,NXPI,ORLY,OKTA,ODFL,PCAR,PAYX,PYPL,PEP,PDD,REGN,ROST,SIRI,SWKS,SBUX,SNPS,TMUS,TSLA,"
        "TXN,TCOM,VRSN,VRTX,WBA,WDAY,XEL,ZM,ALAB,CRWV,RKLB,NBIS,STX,MPWR,TER"
    ),
    "FTSEMIB": (
        "A2A.MI,AMP.MI,AZM.MI,BAMI.MI,BCA.MI,BMED.MI,BPER.MI,CPR.MI,DIA.MI,ENI.MI,ERG.MI,EVO.MI,FBK.MI,G.MI,"
        "HER.MI,INW.MI,ISP.MI,LDO.MI,MB.MI,MONC.MI,NEXI.MI,PIRC.MI,PRY.MI,PST.MI,RACE.MI,REC.MI,SGO.MI,SRG.MI,"
        "STLAM.MI,STMPA.MI,TEN.MI,TRN.MI,UCG.MI,UNI.MI,YSVP.MI,BMPS.MI,BPSO.MI,BC.MI,AVIO.MI,IP.MI"
    ),
    "CRYPTO_FULL": f"{TOTAL1_LEADERS},{TOTAL2_MAJORS},{TOTAL3_ALTS}",
    "MIDCAP_US": (
        "ONDS,RGTI,AGIO,AIRS,ALG,HUBS,CLX,IREN,RIVN,MARA,JAN,LIFE,MXL,IESC,HALO,TXRH,DKS,WFR,DT,"
        "SMR,XPO,GFL,FLEX,JBL,AA,MTDR,CHX,OVV,STNG,WBS,DINO,AMR,SF,LANC,PNR,XOM,AAL,X"
    ),
    "CRYPTO_STOCKS": "COIN,MARA,IREN,CLSK,WULF,MSTR,HUT,CORZ,RIOT,CIFR,BTBT,BOOM",
    "EUROSTOXX": (
        "ADS.DE,ALV.DE,BAS.DE,BAYN.DE,BMW.DE,DB1.DE,DBK.DE,DPW.DE,DTE.DE,EOAN.DE,IFX.DE,MBG.DE,MUV2.DE,RWE.DE,SAP.DE,SIE.DE,"
        "AI.PA,AIR.PA,ALO.PA,CS.PA,BNP.PA,CA.PA,DG.PA,EL.PA,ERF.PA,OR.PA,MC.PA,ML.PA,ORAN.PA,RI.PA,RMS.PA,SAN.PA,SGO.PA,"
        "SU.PA,TTE.PA,VIE.PA,VIV.PA,ASML.AS,ADYEN.AS,INGA.AS,KPN.AS,PRX.AS,BBVA.MC,SAN.MC,ITX.MC,REP.MC,ENI.MI,ISP.MI,UCG.MI"
    )
}


CAPITALE_OPERATIVO = 10000.0
RISCHIO_PCT = 1.0
MIN_PROB_AI = 55.0
RR_MINIMO = 2.0


def invia_telegram(testo: str) -> bool:
    if not BOT_TOKEN:
        print("TELEGRAM_TOKEN mancante.")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": int(T_ID),
        "text": testo,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    res = requests.post(url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=15)
    return res.status_code == 200


def calc_poc(df: pd.DataFrame, div: int = 80):
    if df.empty:
        return None
    p_min, p_max = float(df["Low"].min()), float(df["High"].max())
    if p_max - p_min <= 0:
        return p_min
    bins = np.linspace(p_min, p_max, div + 1)
    vols = np.zeros(div)
    for h, l, v in zip(df["High"].values, df["Low"].values, df["Volume"].values):
        if v <= 0 or h == l:
            continue
        mask = (bins[1:] >= l) & (bins[:-1] <= h)
        vols[mask] += v / max(1, np.sum(mask))
    prices = [float((bins[i] + bins[i + 1]) / 2) for i in range(div)]
    return prices[int(np.argmax(vols))]


def check_earnings_gap(tk: str) -> tuple[int, str]:
    if tk.endswith("-USD"):
        return 999, "N/A"
    try:
        ed = yf.Ticker(tk).get_earnings_dates(limit=6)
        if ed is None or ed.empty:
            return 999, "N/D"
        ed_idx = pd.to_datetime(ed.index).tz_localize(None)
        oggi = pd.Timestamp.now().tz_localize(None)
        fut = ed_idx[ed_idx >= oggi]
        if len(fut) > 0:
            gg = int((fut.min() - oggi).days)
            return gg, f"Tra {gg}g ({fut.min().strftime('%d/%m')})"
    except Exception:
        pass
    return 999, "N/D"

def stima_prob_ai(df_in: pd.DataFrame, tipo_setup: str, macro_bull: bool) -> float:
    c_s = df_in["Close"].astype(float)
    h_s = df_in["High"].astype(float)
    l_s = df_in["Low"].astype(float)
    if len(c_s) < 350:
        return 50.0

    tr = pd.concat([h_s - l_s, (h_s - c_s.shift(1)).abs(), (l_s - c_s.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    sma200 = c_s.rolling(200).mean()
    dist_sma = ((c_s - sma200) / sma200) * 100.0
    ma50 = c_s.rolling(50).mean()
    sd50 = c_s.rolling(50).std().replace(0, 1e-6)
    z_sc = (c_s - ma50) / sd50
    dc = c_s.diff()
    rsi = 100.0 - (100.0 / (1.0 + dc.where(dc > 0, 0).rolling(14).mean() / (-dc.where(dc < 0, 0)).rolling(14).mean().replace(0, 1e-5)))
    vol30 = np.log(c_s / c_s.shift(1)).rolling(30).std() * np.sqrt(252) * 100.0

    if "BREAKOUT" in tipo_setup:
        sig = (c_s > h_s.rolling(20).max().shift(1)).astype(int).to_numpy()
    else:
        sig = ((z_sc <= -1.5) & (z_sc.shift(1) > -1.5)).astype(int).to_numpy()

    c_a, h_a, l_a, atr_a = c_s.to_numpy(), h_s.to_numpy(), l_s.to_numpy(), atr.to_numpy()
    d_a, z_a, r_a, v_a = dist_sma.to_numpy(), z_sc.to_numpy(), rsi.to_numpy(), vol30.to_numpy()

    X_rows, y_rows = [], []
    for i in range(205, len(c_a) - 20):
        if sig[i] == 1:
            ep, at = float(c_a[i]), float(atr_a[i])
            if np.isnan(at) or at <= 0 or np.isnan(d_a[i]):
                continue
            sl_l = ep - 1.5 * at
            tp_l = ep + (1.5 * RR_MINIMO) * at
            lbl = 0
            for stp in range(1, 21):
                if float(l_a[i + stp]) <= sl_l:
                    lbl = 0
                    break
                if float(h_a[i + stp]) >= tp_l:
                    lbl = 1
                    break
            X_rows.append([float(d_a[i]), float(z_a[i]), float(r_a[i]), float(v_a[i])])
            y_rows.append(lbl)

    if len(X_rows) < 25 or len(set(y_rows)) < 2:
        return 50.0

    clf = RandomForestClassifier(n_estimators=120, max_depth=3, min_samples_leaf=4, random_state=42, class_weight="balanced")
    clf.fit(np.array(X_rows), np.array(y_rows))
    x_now = np.array([[float(d_a[-1]), float(z_a[-1]), float(r_a[-1]), float(v_a[-1])]])
    prob_win = float(clf.predict_proba(x_now)[0, -1]) * 100.0
    if not macro_bull:
        prob_win *= 0.90
    return round(prob_win, 1)


def esegui_routine_settimanale():
    df_mac = yf.download(["^GSPC", "^VIX"], period="1y", interval="1d", auto_adjust=True, progress=False)
    macro_bull, vix_now = True, 18.0
    if df_mac is not None and not df_mac.empty and isinstance(df_mac.columns, pd.MultiIndex):
        c_mac = df_mac["Close"].dropna()
        if "^GSPC" in c_mac.columns and len(c_mac["^GSPC"]) >= 200:
            spx_now = float(c_mac["^GSPC"].iloc[-1])
            macro_bull = spx_now >= float(c_mac["^GSPC"].rolling(200).mean().iloc[-1])
        if "^VIX" in c_mac.columns:
            vix_now = float(c_mac["^VIX"].iloc[-1])

    stato_macro_txt = "🟢 RISK-ON (S&P > SMA200)" if macro_bull else "🔴 RISK-OFF (Difensivo)"
    rischio_usd = CAPITALE_OPERATIVO * (RISCHIO_PCT / 100.0)

    messaggio = [
        "📅 <b>ROUTINE SETTIMANALE QUANTANALISYS PRO</b>",
        f"🌐 <b>Regime Macro:</b> {stato_macro_txt} | VIX: <code>{vix_now:.1f}</code>\n"
    ]

    for nome_pan, stringa_tk in PANIERI_WEEKEND.items():
        tickers = [t.strip() for t in stringa_tk.split(",") if t.strip()]
        candidati = []

        for tk in tickers:
            time.sleep(0.25)
            try:
                gg_earn, lbl_earn = check_earnings_gap(tk)
                if gg_earn <= 12:
                    continue

                df_t = yf.download(tk, period="5y", interval="1d", auto_adjust=False, multi_level_index=False, progress=False, timeout=8)
                if df_t is None or len(df_t) < 260:
                    continue

                df_t.columns = [str(c).strip() for c in df_t.columns]
                c_s = df_t["Close"].astype(float).dropna()
                h_s = df_t["High"].astype(float).dropna()
                l_s = df_t["Low"].astype(float).dropna()
                p_now = float(c_s.iloc[-1])

                lr = np.log(c_s / c_s.shift(1)).dropna().values
                cagr = ((p_now / float(c_s.iloc[0])) ** (252.0 / len(lr)) - 1.0) * 100.0
                _, pv_d = stats.ttest_1samp(lr, 0.0)

                lp_126 = np.log(c_s.tail(126).values)
                lgs = range(10, 40)
                tau = [max(1e-8, np.std(lp_126[lg:] - lp_126[:-lg])) for lg in lgs]
                hurst_v = float(np.clip(np.polyfit(np.log(list(lgs)), np.log(tau), 1)[0] * 2.0, 0.05, 0.95))

                sma200_now = float(c_s.rolling(200).mean().iloc[-1])
                dist_sma_now = ((p_now - sma200_now) / sma200_now) * 100.0
                poc_90 = calc_poc(df_t.tail(90), div=60)

                tr = pd.concat([h_s - l_s, (h_s - c_s.shift(1)).abs(), (l_s - c_s.shift(1)).abs()], axis=1).max(axis=1)
                atr_now = float(tr.rolling(14).mean().iloc[-1])

                sc_brk = (25 if (cagr > 0 and pv_d < 0.05) else 0) + (20 if hurst_v >= 0.52 else 0) + (30 if (p_now > sma200_now and poc_90 and p_now >= poc_90) else 0)
                sc_bot = (35 if dist_sma_now <= -15.0 else 0) + (25 if hurst_v <= 0.48 else 0) + (15 if p_now > float(c_s.iloc[-2]) else 0)

                tipo_setup = "🚀 BREAKOUT" if sc_brk >= sc_bot else "🔄 BOTTOM"
                prob_ai = stima_prob_ai(df_t, tipo_setup, macro_bull)
                if prob_ai < MIN_PROB_AI:
                    continue

                score_tot = min(100, max(sc_brk, sc_bot) + (20 if prob_ai >= 65 else 10))
                if score_tot < 65:
                    continue

                if tipo_setup == "🚀 BREAKOUT":
                    entry_p = round(float(h_s.tail(20).max()) * 1.001, 2)
                else:
                    entry_p = round(float(h_s.iloc[-1]) * 1.001, 2)

                sl_p = round(entry_p - 1.5 * atr_now, 2)
                tp_p = round(entry_p + RR_MINIMO * (entry_p - sl_p), 2)
                taglia_pz = round(rischio_usd / max(0.01, entry_p - sl_p), 2)

                candidati.append({
                    "tk": tk, "setup": tipo_setup, "score": score_tot, "ai": prob_ai,
                    "entry": entry_p, "sl": sl_p, "tp": tp_p, "pz": taglia_pz, "earn": lbl_earn
                })
            except Exception:
                continue

        candidati.sort(key=lambda x: (x["score"], x["ai"]), reverse=True)
        top3 = candidati[:3]

        messaggio.append(f"🏆 <b>TOP SETUP {nome_pan}:</b>")
        if not top3:
            messaggio.append("   ⚪ <i>Nessun titolo supera i filtri AI/Score questa settimana.</i>\n")
        else:
            for c in top3:
                tk_clean = c["tk"].replace(".MI", "")
                messaggio.append(
                    f"{c['setup']} <b>#{tk_clean}</b> (Score: {c['score']}/100 | AI: {c['ai']}%)\n"
                    f"   ▪️ Entry: <code>{c['entry']}</code> | SL: <code>{c['sl']}</code> | TP: <code>{c['tp']}</code>\n"
                    f"   ▪️ Taglia: <b>{c['pz']} Pz</b> | Earnings: {c['earn']}\n"
                )

    invia_telegram("\n".join(messaggio))
    print("Routine settimanale completata.")


if __name__ == "__main__":
    esegui_routine_settimanale()
