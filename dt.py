import json

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
        pp_data = details.get("pp") or {} # ✅ safe pivot dict (handles None)

        # Skip if no meaningful price
        if ldcp <= 0:
            continue
        
        # Relative volume ratio
        rel_vol = (v / vm) if vm else 0
        
        # Volatility %
        volatility = ((uc - lc) / ldcp * 100) if ldcp > 0 else 0
        
        score = 0
        near_level = None
        
        # ✅ Momentum
        if pch > 2:   # strong upward move
            score += 2
        elif pch < -2:  # heavy drop (possible bounce)
            score += 1
        
        # ✅ Volume
        if rel_vol > 2:  # trading at 2x average volume
            score += 2
        elif rel_vol > 1:
            score += 1
        
        # ✅ RSI
        if rsi and abs(rsi) < 1000:  # ignore broken RSI values
            if rsi < 30:
                score += 2  # oversold (bounce)
            elif rsi > 70:
                score += 1  # overbought (breakout)
        
        # ✅ Volatility
        if volatility > 5:
            score += 1
        
        # ✅ Pivot Point Proximity
        pivot_levels = {
            "Pivot": pp_data.get("pp", ldcp),  # fallback to ldcp if missing
            "R1": pp_data.get("r1", 0),
            "R2": pp_data.get("r2", 0),
            "R3": pp_data.get("r3", 0),
            "S1": pp_data.get("s1", 0),
            "S2": pp_data.get("s2", 0),
            "S3": pp_data.get("s3", 0),
        }
        
        for level_name, level_value in pivot_levels.items():
            if level_value and abs(ldcp - level_value) / ldcp < 0.02:  # within 2%
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
    
    # Sort by score (higher = better trade candidate)
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return results


if __name__ == "__main__":
    with open("stocks.json", "r") as f:
        data = json.load(f)
    
    recommendations = recommend_day_trade(data)
    
    print("\n⚡ Day Trade Candidates:")
    for r in recommendations:
        print(
            f"{r['symbol']} ({r['name']}) | Price: {r['price']} | %Chg: {r['pch']}% | "
            f"RelVol: {r['rel_vol']} | RSI: {r['rsi']} | Volatility: {r['volatility_%']}% | "
            f"Near: {r['near_level']} | Score: {r['score']}"
        )
