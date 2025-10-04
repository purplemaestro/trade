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
def recommend_day_trade(json_data):
    results = []
    equities = json_data.get("data", {}).get("eq", {})
    
    for symbol, details in equities.items():
        ldcp = details.get("ldcp", 0)
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
def recommend_swing_trade(json_data):
    results = []
    equities = json_data
    
    for symbol, details in equities.items():
        ldcp = details.get("ldcp", 0)
        pch = details.get("pch", 0)
        rsi = details.get("rsi", None)
        p1m = details.get("p1m", 0)
        p3m = details.get("p3m", 0)
        score = 0

        if ldcp <= 0:
            continue

        if p1m < ldcp and p3m < ldcp:
            score += 2  # uptrend
        
        if rsi and 40 < rsi < 60:
            score += 1
        
        if pch > 1:
            score += 1

        results.append({
            "symbol": symbol,
            "name": details.get("nm", ""),
            "price": ldcp,
            "pch": pch,
            "rsi": rsi if rsi and abs(rsi) < 1000 else None,
            "p1m": p1m,
            "p3m": p3m,
            "score": score
        })
    
    return sorted(results, key=lambda x: (x["score"],x["price"], x["p3m"], x["pch"]), reverse=True)

# ------------------ Long Term Strategy ------------------
# ------------------ Long Term Strategy (Extended) ------------------
def recommend_long_term(json_data):
    results = []
    equities = json_data

    for symbol, details in equities.items():
        ldcp = details.get("ldcp", 0)  # last price
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
def find_undervalued(json_data):
    results = []
    equities = json_data.get("data", {}).get("eq", {})

    for symbol, details in equities.items():
        ldcp = details.get("ldcp", 0)  # last price
        eps = details.get("eps", 0)
        roe = details.get("roe", None)
        pat = details.get("pat", 0)
        bv = details.get("bv", None)  # book value (if available)

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
    
    
    print("Choose trading strategy:")
    print("1. Day Trading")
    print("2. Swing Trading")
    print("3. Long Term Investing")
    print("4. Find Undervalued")
    choice = input("Enter choice (1/2/3/4): ").strip()
    
    if choice == "1":
        recommendations = recommend_day_trade(data)
        filename = "day_trade.csv"
        fields = ["symbol","name","price","pch","volume","rel_vol","rsi","volatility_%","near_level","score"]
    elif choice == "2":
        recommendations = recommend_swing_trade(data)
        filename = "swing_trade.csv"
        fields = ["symbol","name","price","pch","rsi","p1m","p3m","score"]
    elif choice == "3":
        recommendations = recommend_long_term(data)
        filename = "long_term.csv"
        fields = ["symbol","name","price","eps","roe","roa","pat","per","pbr","dy","debt_equity","int_cover","current_ratio","quick_ratio","fcf","score","reasons"]
    elif choice == "4":
        recommendations = find_undervalued(data)
        filename = "undervalued.csv"
        fields = ["symbol","name","price","eps","roe","pat","pe_ratio","book_value","score"]
    else:
        print("❌ Invalid choice. Please run again.")
        exit()
    
    # Save results
    save_to_csv(filename, recommendations, fields)
    print(f"\n✅ Results saved to {filename}")
