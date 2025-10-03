import json

# ------------------ Day Trading Strategy ------------------
def recommend_day_trade(json_data):
    results = []
    equities = json_data.get("data", {}).get("eq", {})
    
    for symbol, details in equities.items():
        ldcp = details.get("ldcp", 0)     # last close price
        pch = details.get("pch", 0)       # % change
        v = details.get("v", 0)           # today’s volume
        vm = details.get("vm", 0)         # monthly avg volume
        rsi = details.get("rsi", None)    # relative strength index
        uc = details.get("uc", 0)         # upper circuit
        lc = details.get("lc", 0)         # lower circuit
        pp_data = details.get("pp") or {} # pivot points (safe)

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
    
    return sorted(results, key=lambda x: x["score"], reverse=True)

# ------------------ Swing Trading Strategy ------------------
def recommend_swing_trade(json_data):
    results = []
    equities = json_data.get("data", {}).get("eq", {})
    
    for symbol, details in equities.items():
        ldcp = details.get("ldcp", 0)
        pch = details.get("pch", 0)
        rsi = details.get("rsi", None)
        p1m = details.get("p1m", 0)  # 1 month price
        p3m = details.get("p3m", 0)  # 3 month price
        score = 0

        if ldcp <= 0:
            continue

        # Momentum across 1M and 3M
        if p1m < ldcp and p3m < ldcp:
            score += 2  # Uptrend
        
        # RSI (mid-term momentum)
        if rsi and 40 < rsi < 60:
            score += 1
        
        # Short-term change
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
    
    return sorted(results, key=lambda x: x["score"], reverse=True)

# ------------------ Long Term Strategy ------------------
def recommend_long_term(json_data):
    results = []
    equities = json_data.get("data", {}).get("eq", {})
    
    for symbol, details in equities.items():
        eps = details.get("eps", 0)
        roe = details.get("roe", 0)
        roa = details.get("roa", 0)
        pat = details.get("pat", 0)
        ldcp = details.get("ldcp", 0)
        score = 0

        if ldcp <= 0:
            continue

        # EPS positive = profit making
        if eps > 0:
            score += 2
        # Good ROE
        if roe and roe > 10:
            score += 2
        # ROA
        if roa and roa > 5:
            score += 1
        # Profit after tax growing
        if pat > 0:
            score += 1

        results.append({
            "symbol": symbol,
            "name": details.get("nm", ""),
            "price": ldcp,
            "eps": eps,
            "roe": roe,
            "roa": roa,
            "pat": pat,
            "score": score
        })
    
    return sorted(results, key=lambda x: (x["score"], x["roe"], x["eps"]), reverse=True)


# ------------------ Main ------------------
if __name__ == "__main__":
    with open("stocks.json", "r") as f:
        data = json.load(f)
    
    print("Choose trading strategy:")
    print("1. Day Trading")
    print("2. Swing Trading")
    print("3. Long Term Investing")
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice == "1":
        recommendations = recommend_day_trade(data)
        print("\n⚡ Day Trade Candidates:")
        for r in recommendations:
            print(f"{r['symbol']} ({r['name']}) | Price: {r['price']} | %Chg: {r['pch']}% | "
                  f"RelVol: {r['rel_vol']} | RSI: {r['rsi']} | Volatility: {r['volatility_%']}% | "
                  f"Near: {r['near_level']} | Score: {r['score']}")
    
    elif choice == "2":
        recommendations = recommend_swing_trade(data)
        print("\n📈 Swing Trade Candidates:")
        for r in recommendations:
            print(f"{r['symbol']} ({r['name']}) | Price: {r['price']} | %Chg: {r['pch']}% | "
                  f"RSI: {r['rsi']} | 1M: {r['p1m']} | 3M: {r['p3m']} | Score: {r['score']}")
    
    elif choice == "3":
        recommendations = recommend_long_term(data)
        print("\n🏦 Long Term Investment Candidates:")
        for r in recommendations:
            print(f"{r['symbol']} ({r['name']}) | Price: {r['price']} | EPS: {r['eps']} | "
                  f"ROE: {r['roe']} | ROA: {r['roa']} | PAT: {r['pat']} | Score: {r['score']}")
    
    else:
        print("❌ Invalid choice. Please run again.")
