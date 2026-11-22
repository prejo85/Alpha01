import os
import time
import json
import requests
import numpy as np
import pandas as pd
import yfinance as yf
from urllib.parse import quote

T_ID = (os.getenv("TELEGRAM_CHAT_ID") or "2072895073").strip()
BOT_TOKEN = (os.getenv("TELEGRAM_TOKEN") or "").strip()

FILE_CANVAS = "alerts_geometrici_v2.json"
FILE_ZSCORE = "posizioni_z.json"
NAV_PORTAFOGLIO = 50000.0
SOGLIA_CORR_ALLARME = 0.75


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


def carica_json(percorso: str) -> dict:
    if os.path.exists(percorso):
        try:
            with open(percorso, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def salva_json(percorso: str, dati: dict):
    with open(percorso, "w", encoding="utf-8") as f:
        json.dump(dati, f, indent=4)


def calcola_zscore_ultimo(close_s: pd.Series, finestra: int = 50) -> tuple[float, float]:
    n = finestra
    x = np.arange(n)
    sum_x, sum_x2 = x.sum(), (x**2).sum()
    den = n * sum_x2 - (sum_x**2)

    sum_y = close_s.rolling(window=n).sum()
    sum_y2 = (close_s**2).rolling(window=n).sum()
    xy_conv = np.convolve(close_s.values, x[::-1], mode="valid")
    sum_xy = pd.Series(np.nan, index=close_s.index)
    sum_xy.iloc[n - 1 :] = xy_conv

    m_s = (n * sum_xy - sum_x * sum_y) / den
    q_s = (sum_x2 * sum_y - sum_x * sum_xy) / den
    p_teo = m_s * n + q_s

    mx, vx = sum_x / n, sum_x2 / n - ((sum_x / n) ** 2)
    my, vy = sum_y / n, sum_y2 / n - ((sum_y / n) ** 2)
    cov_xy = sum_xy / n - (mx * my)
    std_res = np.sqrt(np.clip(vy - (2 * m_s * cov_xy) + (m_s**2 * vx), 1e-5, None))

    z_series = ((close_s - p_teo) / std_res).fillna(0.0)
    return float(z_series.iloc[-2]), float(z_series.iloc[-1])
def esegui_routine_giornaliera():
    yf.set_tz_cache_location("/tmp/yf_cache")
    notifiche = []

    # ==========================================================================
    # 1. CONTROLLO LINEE & RETTANGOLI TRADINGVIEW CANVAS (alerts_geometrici_v2.json)
    # ==========================================================================
    db_canvas = carica_json(FILE_CANVAS)
    canvas_modificato = False

    for chiave, cfg in list(db_canvas.items()):
        if not isinstance(cfg, dict):
            continue
        tk = str(cfg.get("Ticker", "")).strip().upper()
        tf = str(cfg.get("Timeframe", "1d")).strip()
        if tf not in ("1d", "1wk") or not tk:
            continue

        time.sleep(0.25)
        df_c = yf.download(tk, period="6mo", interval=tf, auto_adjust=False, multi_level_index=False, threads=False, progress=False, timeout=8)
        if df_c is None or len(df_c) < 2:
            continue

        df_c.columns = [str(c).strip() for c in df_c.columns]
        c_open = float(df_c["Open"].iloc[-1])
        c_high = float(df_c["High"].iloc[-1])
        c_low = float(df_c["Low"].iloc[-1])
        c_close = float(df_c["Close"].iloc[-1])
        r_tot = c_high - c_low
        pct_corpo = (abs(c_close - c_open) / r_tot) * 100.0 if r_tot > 0 else 0.0
        soglia_corpo = float(cfg.get("Soglia_Corpo_Pct", 80.0))

        tipo_g = cfg.get("Tipo_Geometria")
        trigger = False
        desc = ""

        if tipo_g == "horizontal":
            liv = float(cfg["y0"])
            if ((c_open <= liv and c_close > liv) or (c_open >= liv and c_close < liv)) and pct_corpo >= soglia_corpo:
                trigger = True
                desc = f"Rottura Livello Orizzontale {liv:.2f}$"

        elif tipo_g == "line":
            t0 = pd.to_datetime(cfg["x0"]).timestamp()
            t1 = pd.to_datetime(cfg["x1"]).timestamp()
            t_last = df_c.index[-1].timestamp()
            if (t1 - t0) != 0:
                m = (float(cfg["y1"]) - float(cfg["y0"])) / (t1 - t0)
                q = float(cfg["y0"]) - (m * t0)
                liv_oggi = (m * t_last) + q
                if ((c_open <= liv_oggi and c_close > liv_oggi) or (c_open >= liv_oggi and c_close < liv_oggi)) and pct_corpo >= soglia_corpo:
                    trigger = True
                    desc = f"Breakout Trendline Diagonale ({liv_oggi:.2f}$)"

        elif tipo_g == "rectangle":
            y_top = max(float(cfg["y0"]), float(cfg["y1"]))
            y_bot = min(float(cfg["y0"]), float(cfg["y1"]))
            if ((c_open <= y_top and c_close > y_top) or (c_open >= y_bot and c_close < y_bot)) and pct_corpo >= soglia_corpo:
                trigger = True
                desc = f"Breakout Rettangolo ({y_bot:.2f}$ - {y_top:.2f}$)"

        if trigger:
            notifiche.append(
                f"📺 <b>CANVAS BREAKOUT #{tk}</b> ({cfg.get('Timeframe_Label', tf)})\n"
                f"   ▪️ {desc} | Chiusura: <code>{c_close:.2f}$</code> | Corpo: <code>{pct_corpo:.0f}%</code>"
            )
            del db_canvas[chiave]
            canvas_modificato = True

    if canvas_modificato:
        salva_json(FILE_CANVAS, db_canvas)

    # ==========================================================================
    # 2. CONTROLLO POSIZIONI APERTE Z-SCORE & RISCHIO PORTAFOGLIO (posizioni_z.json)
    # ==========================================================================
    db_z = carica_json(FILE_ZSCORE)
    z_modificato = False
    posizioni_aperte = []

    for chiave_z, pos in list(db_z.items()):
        if not isinstance(pos, dict) or pos.get("Direzione") not in ("LONG", "SHORT"):
            continue

        tk_puro = str(pos.get("Ticker_Puro", str(chiave_z).split("_")[0])).strip().upper()
        paniere = str(pos.get("Paniere", ""))
        tk_yf = f"{tk_puro}-USD" if paniere == "Crypto" and not tk_puro.endswith("-USD") else tk_puro
        tf_z = "1wk" if "Weekly" in str(chiave_z) else "1d"

        time.sleep(0.25)
        df_z = yf.download(tk_yf, period="2y", interval=tf_z, auto_adjust=False, multi_level_index=False, threads=False, progress=False, timeout=8)
        if df_z is None or len(df_z) < 55:
            continue

        df_z.columns = [str(c).strip() for c in df_z.columns]
        c_s = df_z["Close"].astype(float).dropna()
        p_last = float(c_s.iloc[-1])
        _, z_now = calcola_zscore_ultimo(c_s, finestra=50)
        direzione = pos["Direzione"]

        if (direzione == "LONG" and z_now <= -2.0) or (direzione == "SHORT" and z_now >= 2.0):
            notifiche.append(
                f"🏁 <b>TARGET Z-SCORE RAGGIUNTO #{tk_puro}</b>\n"
                f"   ▪️ Chiudi <b>{direzione}</b> | Prezzo: <code>{p_last:.2f}$</code> | Z-Score: <code>{z_now:+.2f}</code>"
            )
            db_z[chiave_z] = None
            z_modificato = True
        else:
            posizioni_aperte.append({
                "tk": tk_yf,
                "dir": direzione,
                "nozionale": float(pos.get("Taglia_Pz", 0.0)) * p_last
            })

    if z_modificato:
        db_z_clean = {k: v for k, v in db_z.items() if v is not None}
        salva_json(FILE_ZSCORE, db_z_clean)

    # ==========================================================================
    # 3. AUDIT ESPOSIZIONE & CORRELAZIONE PORTAFOGLIO LIVE
    # ==========================================================================
    alert_rischio = []
    if posizioni_aperte:
        long_tot = sum(p["nozionale"] for p in posizioni_aperte if p["dir"] == "LONG")
        short_tot = sum(p["nozionale"] for p in posizioni_aperte if p["dir"] == "SHORT")
        gross_pct = ((long_tot + short_tot) / NAV_PORTAFOGLIO) * 100.0
        net_pct = ((long_tot - short_tot) / NAV_PORTAFOGLIO) * 100.0

        alert_rischio.append(
            f"⚖️ <b>Portafoglio Attivo ({len(posizioni_aperte)} pos.):</b> Gross <code>{gross_pct:.1f}%</code> | Net <code>{net_pct:+.1f}%</code>"
        )

        tickers_unici = list(dict.fromkeys([p["tk"] for p in posizioni_aperte]))
        if len(tickers_unici) >= 2:
            dl_corr = yf.download(tickers_unici, period="6mo", interval="1d", auto_adjust=True, threads=False, progress=False)
            if dl_corr is not None and not dl_corr.empty and isinstance(dl_corr.columns, pd.MultiIndex):
                c_mat = dl_corr["Close"].ffill().pct_change().dropna(how="all").corr(min_periods=15)
                cols = list(c_mat.columns)
                for i in range(len(cols)):
                    for j in range(i + 1, len(cols)):
                        val_r = float(c_mat.iloc[i, j])
                        if abs(val_r) >= SOGLIA_CORR_ALLARME:
                            alert_rischio.append(f"⚠️ <b>Correlazione Alta:</b> {cols[i]} / {cols[j]} = <code>{val_r:.2f}</code>")

    # ==========================================================================
    # 4. INVIO REPORT SERALE SU TELEGRAM (SEMPRE ATTIVO)
    # ==========================================================================
    msg_finale = ["🌙 <b>REPORT SERALE GIORNALIERO QUANTANALISYS</b>\n"]
    if notifiche:
        msg_finale.append("🔔 <b>SEGNALI OPERATIVI:</b>")
        msg_finale.extend(notifiche)
        msg_finale.append("")
    else:
        msg_finale.append(f"⚪ <i>Nessun breakout rilevato sulle {len(db_canvas)} linee attive del Canvas.</i>\n")

    if alert_rischio:
        msg_finale.append("🛡️ <b>CONTROLLO RISCHIO PORTAFOGLIO:</b>")
        msg_finale.extend(alert_rischio)
    else:
        msg_finale.append("⚖️ <i>Nessuna posizione attiva in posizioni_z.json.</i>")

    invia_telegram("\n".join(msg_finale))
    print("Report serale inviato su Telegram.")


if __name__ == "__main__":
    esegui_routine_giornaliera()

