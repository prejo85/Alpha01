import os
import json
import requests
import numpy as np
import pandas as pd
import yfinance as yf

FILE_ALERTS = "alerts_geometrici_v2.json"
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "2072895073")
APP_URL = "https://streamlit.app"


def invia_telegram(testo):
    if not BOT_TOKEN:
        print("TELEGRAM_TOKEN mancante.")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": int(CHAT_ID),
        "text": testo,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=12)
        return r.status_code == 200
    except Exception as e:
        print(f"Errore invio Telegram: {e}")
        return False


def main():
    if not os.path.exists(FILE_ALERTS):
        print("Nessun file alerts_geometrici_v2.json trovato.")
        return

    with open(FILE_ALERTS, "r", encoding="utf-8") as f:
        db = json.load(f)

    if not isinstance(db, dict) or not db:
        print("Database alert vuoto.")
        return

    oggi_str = pd.Timestamp.now(tz="Europe/Rome").strftime("%Y-%m-%d")
    modificato = False

    for k_id, cfg in list(db.items()):
        if not cfg or cfg.get("Stato") != "ATTIVO":
            continue

        tk = str(cfg.get("Ticker", "")).strip().upper()
        tf = str(cfg.get("Timeframe", "1d")).strip()
        tf_lbl = str(cfg.get("Timeframe_Label", tf))
        tipo = str(cfg.get("Tipo_Geometria", "")).lower()
        regola = str(cfg.get("Regola", ""))
        soglia_corpo = float(cfg.get("Soglia_Corpo_Pct", 0.0))

        # 1. CONTROLLO ALERT TEMPORALE (LINEA VERTICALE)
        if tipo == "vertical":
            data_target = str(cfg.get("x0", ""))[:10]
            if data_target and oggi_str >= data_target:
                msg = (
                    f"⏳ <b>ALERT TEMPORALE RAGGIUNTO</b>\n\n"
                    f"🎯 <b>Asset:</b> #{tk.replace('-USD', '').replace('.MI', '')}\n"
                    f"📅 <b>Data Target:</b> {data_target}\n"
                    f"📌 <b>Nota:</b> {regola}\n\n"
                    f"🔗 <a href='{APP_URL}/?ticker={tk}'>APRI GRAFICO NELLA DASHBOARD</a>"
                )
                if invia_telegram(msg):
                    del db[k_id]
                    modificato = True
            continue

        # Download dati per controlli di prezzo e indicatori
        per_dl = "60d" if tf in ["15m", "1h", "4h"] else "2y"
        df = yf.download(tickers=tk, period=per_dl, interval=tf, auto_adjust=False, multi_level_index=False, progress=False)
        if df is None or len(df) < 30:
            continue

        df.columns = [str(c).strip() for c in df.columns]
        c_open = float(df["Open"].to_numpy()[-1])
        c_high = float(df["High"].to_numpy()[-1])
        c_low = float(df["Low"].to_numpy()[-1])
        c_close = float(df["Close"].to_numpy()[-1])
        r_tot = c_high - c_low
        pct_corpo = (abs(c_close - c_open) / r_tot * 100.0) if r_tot > 0 else 0.0

        scattato = False
        dettaglio = ""

        # 2. LIVELLO ORIZZONTALE
        if tipo == "horizontal":
            lvl = float(cfg.get("y0", 0.0))
            rottura = (c_open <= lvl < c_close) or (c_open >= lvl > c_close)
            if rottura and pct_corpo >= soglia_corpo:
                scattato = True
                direz = "RIALZISTA 🟢" if c_close > lvl else "RIBASSISTA 🔴"
                dettaglio = f"Rottura {direz} livello {lvl:.2f} $ (Corpo: {pct_corpo:.1f}%)"

        # 3. TRENDLINE DIAGONALE
        elif tipo == "line":
            t0_s = pd.to_datetime(cfg["x0"]).timestamp()
            t1_s = pd.to_datetime(cfg["x1"]).timestamp()
            t_last_s = pd.to_datetime(df.index[-1]).timestamp()
            if t1_s != t0_s:
                m = (float(cfg["y1"]) - float(cfg["y0"])) / (t1_s - t0_s)
                lvl_oggi = float(cfg["y0"]) + m * (t_last_s - t0_s)
                rottura = (c_open <= lvl_oggi < c_close) or (c_open >= lvl_oggi > c_close)
                if rottura and pct_corpo >= soglia_corpo:
                    scattato = True
                    dettaglio = f"Breakout Trendline a {lvl_oggi:.2f} $ (Corpo: {pct_corpo:.1f}%)"

        # 4. RETTANGOLO ZONA
        elif tipo == "rectangle":
            y_top = max(float(cfg["y0"]), float(cfg["y1"]))
            y_bot = min(float(cfg["y0"]), float(cfg["y1"]))
            up = (c_open <= y_top < c_close)
            dn = (c_open >= y_bot > c_close)
            if (up or dn) and pct_corpo >= soglia_corpo:
                scattato = True
                dettaglio = f"Breakout Rettangolo {'SOPRA ' + str(round(y_top, 2)) if up else 'SOTTO ' + str(round(y_bot, 2))} $"

        # 5. INDICATORI QUANTITATIVI
        elif tipo == "indicator":
            close_s = df["Close"].astype(float)
            if "Z-Score" in regola and len(close_s) >= 50:
                ma50 = close_s.rolling(50).mean()
                sd50 = close_s.rolling(50).std().replace(0, 1e-6)
                z_s = (close_s - ma50) / sd50
                z_prev, z_now = float(z_s.to_numpy()[-2]), float(z_s.to_numpy()[-1])
                if (z_prev < 2.0 <= z_now) or (z_prev > -2.0 >= z_now):
                    scattato = True
                    dettaglio = f"Z-Score Estremo raggiunto: {z_now:+.2f}"

            elif "EMA 200" in regola and len(close_s) >= 200:
                ema200 = close_s.ewm(span=200, adjust=False).mean()
                e_prev, e_now = float(ema200.to_numpy()[-2]), float(ema200.to_numpy()[-1])
                c_prev = float(close_s.to_numpy()[-2])
                if (c_prev <= e_prev and c_close > e_now) or (c_prev >= e_prev and c_close < e_now):
                    scattato = True
                    dettaglio = f"Incrocio EMA 200 ({e_now:.2f} $) — Chiusura: {c_close:.2f} $"

            elif "Forza Relativa" in regola:
                bench = "QQQ" if "QQQ" in regola else ("FTSEMIB.MI" if "FTSEMIB" in regola else "SPY")
                df_b = yf.download(tickers=bench, period=per_dl, interval=tf, auto_adjust=False, multi_level_index=False, progress=False)
                if df_b is not None and not df_b.empty:
                    df_b.columns = [str(c).strip() for c in df_b.columns]
                    b_c = df_b["Close"].astype(float).reindex(df.index).ffill().bfill()
                    rs = (close_s / b_c.replace(0, np.nan)).ffill()
                    rs_ema = rs.ewm(span=20, adjust=False).mean()
                    if float(rs.to_numpy()[-2]) <= float(rs_ema.to_numpy()[-2]) and float(rs.to_numpy()[-1]) > float(rs_ema.to_numpy()[-1]):
                        scattato = True
                        dettaglio = f"Forza Relativa (RS) sopra EMA 20 vs {bench}"

            elif "Volatility Squeeze" in regola and len(close_s) >= 120:
                bb_m = close_s.rolling(20).mean()
                bb_s = close_s.rolling(20).std()
                bb_w = (4 * bb_s) / bb_m.replace(0, np.nan)
                pct_rank = float((bb_w.rank(pct=True) * 100.0).to_numpy()[-1])
                if pct_rank <= 15.0:
                    scattato = True
                    dettaglio = f"Volatility Squeeze attivo ({pct_rank:.1f}° percentile)"

        if scattato:
            msg = (
                f"🚨 <b>TRADINGVIEW PRO: ALERT SCATTATO</b>\n\n"
                f"🎯 <b>Asset:</b> #{tk.replace('-USD', '').replace('.MI', '')} ({tf_lbl})\n"
                f"⚡ <b>Evento:</b> {dettaglio}\n"
                f"📊 <b>Chiusura Candela:</b> {c_close:.2f} $\n\n"
                f"🔗 <a href='{APP_URL}/?ticker={tk}'>APRI IL GRAFICO NELLA DASHBOARD</a>"
            )
            if invia_telegram(msg):
                del db[k_id]
                modificato = True

    if modificato:
        with open(FILE_ALERTS, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4)
        print("Database alerts_geometrici_v2.json aggiornato.")


if __name__ == "__main__":
    main()
