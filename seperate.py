import json
import csv
import os

# ------------------ Merge Extra Metrics ------------------
def merge_metrics(base_data, roe_data, roa_data,bv_data):
    equities = base_data.get("data", {}).get("eq", {})

    # Build ROE map
    roe_map = {item["symbol"]: item["value"] for item in roe_data.get("data", []) if item.get("name") == "roe"}
    roa_map = {item["symbol"]: item["value"] for item in roa_data.get("data", []) if item.get("name") == "roa"}
    bv_map = {item["symbol"]: item["value"] for item in bv_data.get("data", []) if item.get("name") == "bval"}

    for symbol, details in equities.items():
        if symbol in roe_map:
            details["roe"] = roe_map[symbol]
        if symbol in roa_map:
            details["roa"] = roa_map[symbol]
        if symbol in bv_map:
            details["bv"] = bv_map[symbol]

    return base_data

# ------------------ Day Trading Strategy ------------------
def recommend_day_trade(json_data,read_previous_day_price=False):
    results = []
    equities = json_data.get("data", {}).get("eq", {})
    
    for symbol, details in equities.items():
        ldcp = read_previous_day_price and details.get("ldcp", 0) or details.get("c", 0)
        pch = details.get("pch", 0)
        v = details.get("v", 0)
        vm = details.get("vm", 0)
        rsi = details.get("rsi", None)
        uc = details.get("uc", 0)
        lc = details.get("lc", 0)
        pp_data = details.get("pp") or {}

        if ldcp <= 0:
            continue
        
        rel_vol = (v / vm) if vm else 0
        volatility = ((uc - lc) / ldcp * 100) if ldcp > 0 else 0
        
        score = 0
        near_level = None
        
        # Momentum
        if pch > 2:
            score += 2
        elif pch < -2:
            score += 1
        
        # Volume
        if rel_vol > 2:
            score += 2
        elif rel_vol > 1:
            score += 1
        
        # RSI
        if rsi and abs(rsi) < 1000:
            if rsi < 30:
                score += 2
            elif rsi > 70:
                score += 1
        
        # Volatility
        if volatility > 5:
            score += 1
        
        # Pivot proximity
        pivot_levels = {
            "Pivot": pp_data.get("pp", ldcp),
            "R1": pp_data.get("r1", 0),
            "R2": pp_data.get("r2", 0),
            "R3": pp_data.get("r3", 0),
            "S1": pp_data.get("s1", 0),
            "S2": pp_data.get("s2", 0),
            "S3": pp_data.get("s3", 0),
        }
        
        for level_name, level_value in pivot_levels.items():
            if level_value and abs(ldcp - level_value) / ldcp < 0.02:
                near_level = level_name
                score += 1
                break
        
        results.append({
            "symbol": symbol,
            "name": details.get("nm", ""),
            "price": ldcp,
            "pch": pch,
            "volume": v,
            "rel_vol": round(rel_vol, 2),
            "rsi": round(rsi, 2) if rsi and abs(rsi) < 1000 else None,
            "volatility_%": round(volatility, 2),
            "near_level": near_level,
            "score": score
        })
    
    return sorted(results, key=lambda x: (x["score"], x["rel_vol"]), reverse=True)

# ------------------ Swing Trading Strategy ------------------
def recommend_swing_trade(json_data, config=None,read_previous_day_price=False):
    """
    Swing trade screener — enhanced logic with trend, momentum, volume, RSI, and pivots.

    Args:
        json_data: JSON data from screener (with 'data' > 'eq' structure)
        config: optional dict of scoring weights
    Returns:
        Sorted list of swing trade candidates
    """

    # --- Default weights ---
    weights = {
        "pch_positive": 2,
        "pch_negative": 1,
        "rel_vol_high": 2,
        "rel_vol_medium": 1,
        "rsi_oversold": 2,
        "rsi_overbought": 1,
        "volatility_high": 1,
        "trend_bullish": 2,
        "trend_bearish": -1,
        "momentum_week": 1,
        "momentum_month": 1,
        "pivot_near": 1,
        "pivot_support_bounce": 2,
        "pivot_resistance_reject": -1,
        "macd_bullish": 1,
    }

    if config:
        weights.update(config)

    results = []
    equities = json_data

    for symbol, details in equities.items():
        ldcp = read_previous_day_price and details.get("ldcp", 0) or details.get("c", 0)
        pch = details.get("pch", 0)
        v = details.get("v", 0)
        vm = details.get("vm", 0)
        rsi = details.get("rsi", None)
        
        
        uc = details.get("uc", 0)
        lc = details.get("lc", 0)
        pp_data = details.get("pp") or {}

        # Skip invalids / illiquid
        if not ldcp:
            continue
        technicals = details.get("technicals", [])
        rsi = calculate_rsi(technicals, 20)
        if(symbol=="SPEL"):
            print(details)
        # --- Derived Metrics ---
        rel_vol = (v / vm) if vm else 0
        volatility = ((uc - lc) / ldcp * 100) if ldcp > 0 else 0
        score = 0
        near_level = None

        # --- Momentum (Daily) ---
        if pch > 2:
            score += weights["pch_positive"]
        elif pch < -2:
            score += weights["pch_negative"]

        # --- Volume Strength ---
        if rel_vol > 2:
            score += weights["rel_vol_high"]
        elif rel_vol > 1:
            score += weights["rel_vol_medium"]

        # --- RSI ---
        if rsi and abs(rsi) < 1000:
            if rsi < 30:
                score += weights["rsi_oversold"]
            elif rsi > 70:
                score += weights["rsi_overbought"]

        # --- Volatility ---
        if volatility > 5:
            score += weights["volatility_high"]

        # --- Trend Confirmation (SMA) ---
        sma_20 = details.get("sma_20")
        
        sma_20 = calculate_sma(technicals, 20)
        sma_50 = calculate_sma(technicals, 50)
        if sma_20 and sma_50:
            if sma_20 > sma_50:
                score += weights["trend_bullish"]
            elif sma_20 < sma_50:
                score += weights["trend_bearish"]

        # --- Multi-Timeframe Momentum ---
        p1m = details.get("p1m", 0)
        p1w = details.get("p1w", 0)
        
        pch_1w = calculate_pch(ldcp, p1w)
        pch_1m = calculate_pch(ldcp, p1m)
        
        if pch_1w > 3:
            score += weights["momentum_week"]
        if pch_1m > 5:
            score += weights["momentum_month"]

        # --- Pivot Point Proximity ---
        pivot_levels = {
            "Pivot": pp_data.get("pp", ldcp),
            "R1": pp_data.get("r1", 0),
            "R2": pp_data.get("r2", 0),
            "R3": pp_data.get("r3", 0),
            "S1": pp_data.get("s1", 0),
            "S2": pp_data.get("s2", 0),
            "S3": pp_data.get("s3", 0),
        }

        for level_name, level_value in pivot_levels.items():
            if level_value and abs(ldcp - level_value) / ldcp < 0.02:
                near_level = level_name
                score += weights["pivot_near"]

                # Bounce/Reject Logic
                if level_name in ("S1", "S2") and rsi and rsi < 35:
                    score += weights["pivot_support_bounce"]
                elif level_name in ("R1", "R2") and rsi and rsi > 65:
                    score += weights["pivot_resistance_reject"]
                break

        # --- MACD Confirmation ---

        macd = calculate_macd(technicals, 12, 26, 9, 'M')  # MACD main line
        macd_signal = calculate_macd(technicals, 12, 26, 9, 'S')  # Signal line


        # macd = details.get("macd")
        # macd_signal = details.get("macd_signal")
        if macd and macd_signal and macd > macd_signal:
            score += weights["macd_bullish"]

        # --- Collect Result ---
        results.append({
            "symbol": symbol,
            "name": details.get("nm", ""),
            "price": ldcp,
            "pch": pch,
            "volume": v,
            "rel_vol": round(rel_vol, 2),
            "rsi": round(rsi, 2) if rsi and abs(rsi) < 1000 else None,
            "volatility_%": round(volatility, 2),
            "near_level": near_level,
            "score": score,
        })

    # --- Sort & Return ---
    return sorted(results, key=lambda x: (x["score"], x["rel_vol"]), reverse=True)

# ------------------ Long Term Strategy ------------------
# ------------------ Long Term Strategy (Extended) ------------------
def recommend_long_term(json_data,read_previous_day_price=False):
    results = []
    equities = json_data

    for symbol, details in equities.items():
        ldcp = read_previous_day_price and details.get("ldcp", 0) or details.get("c", 0)
        eps = details.get("eps", 0)
        roe = details.get("roe", None)
        roa = details.get("roa", None)
        pat = details.get("pat", 0)
        bv = details.get("bval", None)
        per = details.get("per", None)  # P/E
        pbr = details.get("pbr", None)  # P/B
        psr = details.get("psr", None)  # P/S
        dy = details.get("divy", None)    # Dividend Yield %
        div_cover = details.get("divc", None)
        npm = details.get("npm", None)  # Net Profit Margin %
        opm = details.get("opm", None)  # Operating Profit Margin %
        roce = details.get("roce", None)  # Return on Capital Employed

        # --- Balance Sheet Strength ---
        # Calculate equity
        equity = (details.get("share_cap", 0) or 0) + (details.get("res", 0) or 0)
        total_debt = details.get("tr_debt", 0) or 0

        debt_equity = details.get("grat", None)  # Debt/Equity ratio
        

        if debt_equity is not None and debt_equity < 1:
            score += 2; reasons.append(f"Low Debt/Equity {round(debt_equity, 2)}")
        
        
        
        int_cover = details.get("intc", None)  # Interest Cover
        current_ratio = details.get("curr", None)
        quick_ratio = details.get(" ", None)
        fcf = details.get("fc", None)   # Free Cash Flow
        fcf = (details.get("opp", 0) or 0) - (details.get("ppeq", 0) or 0)
        sales = details.get("sales", 0)
        sales_growth = details.get("%chg1y", None)  # Approx using 1Y % Change

        if ldcp <= 0:
            continue

        score = 0
        reasons = []

        # --- Profitability ---
        if eps > 0:
            score += 2; reasons.append("EPS positive")
        if roe and roe > 12:
            score += 2; reasons.append(f"ROE {roe}% strong")
        if roa and roa > 6:
            score += 1; reasons.append(f"ROA {roa}% healthy")
        if roce and roce > 10:
            score += 1; reasons.append(f"ROCE {roce}% good")
        if pat > 0:
            score += 1; reasons.append("PAT positive")
        if npm and npm > 8:
            score += 1; reasons.append("High Net Profit Margin")
        if opm and opm > 12:
            score += 1; reasons.append("High Operating Margin")

        # --- Valuation ---
        if per and 5 < per < 15:
            score += 2; reasons.append(f"Reasonable PE {per}")
        if pbr and pbr < 2:
            score += 1; reasons.append(f"Cheap PB {pbr}")
        if psr and psr < 2:
            score += 1; reasons.append("Good PS ratio")
        if bv and ldcp < bv:
            score += 2; reasons.append("Price below Book Value")
        if dy and dy > 3:
            score += 1; reasons.append(f"Attractive Dividend Yield {dy}%")
        if div_cover and div_cover > 2:
            score += 1; reasons.append("Dividend well covered")

        # --- Balance Sheet Strength ---
        if debt_equity is not None and debt_equity < 1:
            score += 2; reasons.append("Low Debt/Equity")
        if int_cover and int_cover > 3:
            score += 1; reasons.append("Comfortable Interest Cover")
        if current_ratio and current_ratio > 1.5:
            score += 1; reasons.append("Healthy Current Ratio")
        if quick_ratio and quick_ratio > 1:
            score += 1; reasons.append("Healthy Quick Ratio")

        # --- Cash Flow ---
        if fcf and fcf > 0:
            score += 2; reasons.append("Positive Free Cash Flow")

        # --- Growth ---
        if sales and sales > 0:
            score += 1; reasons.append("Sales positive")
        if sales_growth and sales_growth > 5:
            score += 1; reasons.append(f"Sales growth {sales_growth}%")

        results.append({
            "symbol": symbol,
            "name": details.get("nm", ""),
            "price": ldcp,
            "eps": eps,
            "roe": roe,
            "roa": roa,
            "pat": pat,
            "per": per,
            "pbr": pbr,
            "dy": dy,
            "debt_equity": debt_equity,
            "int_cover": int_cover,
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
            "fcf": fcf,
            "score": score,
            "reasons": "; ".join(reasons)
        })

    # Sort by score (high to low), then by ROE, then by EPS
    return sorted(results, key=lambda x: (x["score"], x["roe"] if x["roe"] else 0, x["eps"]), reverse=True)

# ------------------ Undervalued Strategy ------------------
def find_undervalued(json_data,read_previous_day_price=False):
    results = []
    equities = json_data

    for symbol, details in equities.items():
        ldcp = read_previous_day_price and details.get("ldcp", 0) or details.get("c", 0)  # last price
        eps = details.get("eps", 0)
        roe = details.get("roe", None)
        pat = details.get("pat", 0)
        bv = details.get("bval", None)  # book value (if available)

        if ldcp <= 0 or eps <= 0:
            continue

        pe_ratio = ldcp / eps if eps > 0 else None
        score = 0

        # undervaluation logic
        if pe_ratio and pe_ratio < 10:  # cheap PE
            score += 2
        if roe and roe > 10:  # good return
            score += 1
        if pat > 0:
            score += 1
        if bv and ldcp < bv:  # trading below book value
            score += 2

        if score > 0:
            results.append({
                "symbol": symbol,
                "name": details.get("nm", ""),
                "price": ldcp,
                "eps": eps,
                "roe": roe,
                "pat": pat,
                "pe_ratio": round(pe_ratio, 2) if pe_ratio else None,
                "book_value": bv,
                "score": score
            })

    return sorted(results, key=lambda x: (x["score"], -x["pe_ratio"] if x["pe_ratio"] else 9999), reverse=True)

# ------------------ Fundamentally Strong & Undervalued Strategy ------------------
def find_fundamentally_strong(json_data,read_previous_day_price=False):
    """
    Identify fundamentally strong and undervalued stocks.
    Combines profitability, balance sheet health, valuation,
    and adds technical confirmation using RSI and MACD.
    """
    results = []
    equities = json_data

    for symbol, details in equities.items():
        ldcp = read_previous_day_price and details.get("ldcp", 0) or details.get("c", 0)
        eps = details.get("eps", 0)
        roe = details.get("roe")
        roa = details.get("roa")
        per = details.get("per")
        pbr = details.get("pbr")
        dy = details.get("divy")
        bv = details.get("bval")
        pat = details.get("pat", 0)
        npm = details.get("npm")
        opm = details.get("opm")
        roce = details.get("roce")
        debt_equity = details.get("grat")
        int_cover = details.get("intc")
        current_ratio = details.get("curr")
        sales_growth = details.get("%chg1y")
        technicals = details.get("technicals")  # Expect list of bars [timestamp, open, high, low, close, volume]
        rsi = details.get("rsi")  # Assume you already store RSI value in JSON

        if ldcp <= 0 or eps <= 0:
            continue

        score = 0
        reasons = []

        # --- Profitability ---
        if roe and roe > 15:
            score += 2; reasons.append(f"High ROE {roe}%")
        if roa and roa > 6:
            score += 1; reasons.append(f"Healthy ROA {roa}%")
        if npm and npm > 10:
            score += 1; reasons.append(f"Good NPM {npm}%")
        if opm and opm > 12:
            score += 1; reasons.append(f"Good OPM {opm}%")
        if roce and roce > 10:
            score += 1; reasons.append(f"Solid ROCE {roce}%")
        if pat > 0:
            score += 1; reasons.append("Positive PAT")

        # --- Valuation ---
        if per and 5 < per < 12:
            score += 2; reasons.append(f"Attractive PE {per}")
        elif per and per < 5:
            score += 1; reasons.append(f"Very Low PE {per} (possible value trap)")
        if pbr and pbr < 1.5:
            score += 1; reasons.append(f"Low PB {pbr}")
        if bv and ldcp < bv:
            score += 2; reasons.append("Price below Book Value")
        if dy and dy > 3:
            score += 1; reasons.append(f"Good Dividend Yield {dy}%")

        # --- Balance Sheet Strength ---
        if debt_equity is not None and debt_equity < 0.5:
            score += 2; reasons.append(f"Low Debt/Equity {debt_equity}")
        elif debt_equity is not None and debt_equity < 1:
            score += 1; reasons.append(f"Moderate Debt/Equity {debt_equity}")
        if int_cover and int_cover > 3:
            score += 1; reasons.append("Comfortable Interest Coverage")
        if current_ratio and current_ratio > 1.5:
            score += 1; reasons.append("Healthy Current Ratio")

        # --- Technical Indicators ---
        macd_value = None
        macd_signal = None
        macd_hist = None

        if technicals:
            try:
                macd_value = calculate_macd(technicals, mode='M')
                macd_signal = calculate_macd(technicals, mode='S')
                macd_hist = calculate_macd(technicals, mode='H')
            except Exception as e:
                macd_value = macd_signal = macd_hist = None

        # RSI Buy Zone (oversold / rising)
        if rsi:
            if rsi < 30:
                score += 1; reasons.append(f"RSI {rsi} — Oversold (Potential Reversal)")
            elif 30 <= rsi <= 45:
                score += 0.5; reasons.append(f"RSI {rsi} — Early Accumulation Zone")

        # MACD Confirmation (MACD > Signal and Histogram > 0)
        if macd_value is not None and macd_signal is not None:
            if macd_value > macd_signal and macd_hist and macd_hist > 0:
                score += 1.5; reasons.append(f"MACD Bullish Crossover ({macd_value}>{macd_signal})")
            elif macd_value < macd_signal and macd_hist and macd_hist < 0:
                reasons.append(f"MACD Bearish ({macd_value}<{macd_signal})")

        # --- Combine Undervaluation & Strength ---
        if score >= 7:
            results.append({
                "symbol": symbol,
                "name": details.get("nm", ""),
                "price": ldcp,
                "eps": eps,
                "roe": roe,
                "roa": roa,
                "per": per,
                "pbr": pbr,
                "dy": dy,
                "bv": bv,
                "rsi": rsi,
                "macd": macd_value,
                "macd_signal": macd_signal,
                "macd_hist": macd_hist,
                "debt_equity": debt_equity,
                "npm": npm,
                "roce": roce,
                "current_ratio": current_ratio,
                "sales_growth": sales_growth,
                "score": round(score, 2),
                "reasons": "; ".join(reasons)
            })

    # Sort primarily by score, then by bullish MACD and ROE
    return sorted(results, key=lambda x: (
        x["score"],
        (x["macd_hist"] if x["macd_hist"] else 0),
        (x["roe"] if x["roe"] else 0)
    ), reverse=True)


# ------------------ SMA Calculator ------------------
def calculate_sma(technicals, period):
    """
    Calculate Simple Moving Average (SMA) for the given period
    from the 'technicals' array (each bar = [timestamp, open, high, low, close, volume]).

    Args:
        technicals (list): List of bar arrays
        period (int): Number of bars to include in the average

    Returns:
        float: SMA value (rounded to 2 decimals) or None if insufficient data
    """
    if not technicals or len(technicals) < period:
        return None

    # Get the last `period` bars
    recent_bars = technicals[-period:]

    # Extract closing prices safely (index 4)
    closes = [bar[4] for bar in recent_bars if len(bar) > 4 and isinstance(bar[4], (int, float))]

    if not closes:
        return None

    sma = sum(closes) / len(closes)
    return round(sma, 2)

def calculate_pch(e,t):
        return (e - t) / t if t != 0 else 0

def calculate_rsi(data, period):
    n = int(period)
    if len(data) < n + 1:
        return None

    avg_gain = 0
    avg_loss = 0

    for o in range(len(data)):
        if o == 0:
            continue

        gain = 0
        loss = 0
        diff = data[o][4] - data[o - 1][4]  # assuming close price is at index 4

        if diff > 0:
            gain = diff
        elif diff < 0:
            loss = abs(diff)

        if o <= n:
            avg_gain += gain
            avg_loss += loss

        if o == n:
            avg_gain /= n
            avg_loss /= n

        if o > n:
            avg_gain = (avg_gain * (n - 1) + gain) / n
            avg_loss = (avg_loss * (n - 1) + loss) / n

    if avg_loss == 0:
        return 100  # prevent division by zero

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(technicals, short_period=12, long_period=26, signal_period=9, mode='M'):
    """
    Calculate MACD (Moving Average Convergence Divergence)
    for a list of technical bars (each bar = [timestamp, open, high, low, close, volume]).

    Args:
        technicals (list): List of bars
        short_period (int): Short-term SMA period (default 12)
        long_period (int): Long-term SMA period (default 26)
        signal_period (int): Signal line SMA period (default 9)
        mode (str): 'M' = MACD line, 'S' = Signal line, 'H' = Histogram

    Returns:
        float or None: Calculated MACD value based on mode
    """
    if not technicals:
        return None

    max_period = max(short_period, long_period)
    required_bars = max_period + signal_period

    # Keep only the last `required_bars`
    data = technicals[-required_bars:]

    if len(data) < required_bars:
        return None

    closes = [bar[4] for bar in data if len(bar) > 4 and isinstance(bar[4], (int, float))]
    if len(closes) < required_bars:
        return None

    # Compute MACD values for last `signal_period` bars
    macd_values = []
    for i in range(len(closes) - signal_period, len(closes)):
        if i - short_period + 1 < 0 or i - long_period + 1 < 0:
            continue

        short_sma = sum(closes[i - short_period + 1 : i + 1]) / short_period
        long_sma = sum(closes[i - long_period + 1 : i + 1]) / long_period
        macd_values.append(short_sma - long_sma)

    if not macd_values:
        return None

    macd_last = macd_values[-1]
    signal_avg = sum(macd_values) / len(macd_values)

    if mode == 'M':
        return round(macd_last, 2)
    elif mode == 'S':
        return round(signal_avg, 2)
    elif mode == 'H':
        return round(macd_last - signal_avg, 2)
    else:
        return None

# ------------------ Save to CSV ------------------
def save_to_csv(filename, results, fieldnames):
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)


# ------------------ Main ------------------
if __name__ == "__main__":
    with open("stocks.json", "r") as f:
        data = json.load(f)
    
    read_previous_day_price = False
    print("Choose trading strategy:")
    print("1. Day Trading")
    print("2. Swing Trading")
    print("3. Long Term Investing")
    print("4. Find Undervalued")
    print("5. Fundamentally Strong & Undervalued")
    choice = input("Enter choice (1/2/3/4): ").strip()
    
    if choice == "1":
        recommendations = recommend_day_trade(data,read_previous_day_price)
        filename = "day_trade.csv"
        fields = ["symbol","name","price","pch","volume","rel_vol","rsi","volatility_%","near_level","score"]
    elif choice == "2":
        custom_weights = {
            "rsi_oversold": 3,
            "trend_bullish": 3,
            "pivot_support_bounce": 3,
            "pch_positive": 1,  # reduce daily momentum importance
        }
        recommendations = recommend_swing_trade(data, config=custom_weights,read_previous_day_price =read_previous_day_price)
        #recommendations = recommend_swing_trade(data,read_previous_day_price)
        filename = "swing_trade.csv"
        fields = ["symbol","name","price","pch","volume","rel_vol","rsi","volatility_%","near_level","score"]
    elif choice == "3":
        recommendations = recommend_long_term(data,read_previous_day_price)
        filename = "long_term.csv"
        fields = ["symbol","name","price","eps","roe","roa","pat","per","pbr","dy","debt_equity","int_cover","current_ratio","quick_ratio","fcf","score","reasons"]
    elif choice == "4":
        recommendations = find_undervalued(data,read_previous_day_price)
        filename = "undervalued.csv"
        fields = ["symbol","name","price","eps","roe","pat","pe_ratio","book_value","score"]
    elif choice == "5":
        recommendations = find_fundamentally_strong(data,read_previous_day_price)
        filename = "fundamentally_strong.csv"
        fields = [
            "symbol", "name", "price", "eps", "roe", "roa", "per", "pbr", "dy",
            "bv", "debt_equity", "npm", "roce", "current_ratio", "sales_growth",
            "score", "reasons","rsi","macd","macd_signal","macd_hist"
        ]

    
    else:
        print("❌ Invalid choice. Please run again.")
        exit()
    
    # Save results
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(filename):
        filename = f"{base}_{counter}{ext}"
        counter += 1
    
    save_to_csv(filename, recommendations, fields)
    print(f"\n✅ Results saved to {filename}")
    # ...existing code...    print(f"\n✅ Results saved to {filename}")
