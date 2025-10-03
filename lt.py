import json

def recommend_long_term(json_data):
    results = []
    
    # Extract stock data
    equities = json_data.get("data", {}).get("eq", {})
    
    for symbol, details in equities.items():
        eps = details.get("eps", 0)
        pat = details.get("pat", 0)
        ldcp = details.get("ldcp", 0)  # last close price
        sh = details.get("sh", 0)      # shares outstanding
        dps = details.get("dps", 0)
        di = details.get("di", 0)
        assets = details.get("as", 0)

        # Basic filters
        if eps > 0 and pat > 0:
            per = ldcp / eps if eps > 0 else None
            market_cap = ldcp * sh
            pb_ratio = (market_cap / assets) if assets > 0 else None

            score = 0
            if 5 <= per <= 20:  # good PE range
                score += 2
            if pb_ratio and pb_ratio < 3:
                score += 2
            if dps > 0 or di > 0:
                score += 1
            if pat > 0:
                score += 1

            results.append({
                "symbol": symbol,
                "name": details.get("nm", ""),
                "eps": eps,
                "pat": pat,
                "per": round(per, 2) if per else None,
                "pb_ratio": round(pb_ratio, 2) if pb_ratio else None,
                "dividend": dps,
                "score": score
            })

    # Rank by score (higher = better)
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return results


if __name__ == "__main__":
    # Read JSON from file
    with open("stocks.json", "r") as f:
        data = json.load(f)
    
    recommendations = recommend_long_term(data)
    
    print("\n📊 Long-Term Investment Recommendations:")
    for r in recommendations:
        print(
            f"{r['symbol']} ({r['name']}) | EPS: {r['eps']} | PER: {r['per']} | "
            f"P/B: {r['pb_ratio']} | Dividend: {r['dividend']} | Score: {r['score']}"
        )
