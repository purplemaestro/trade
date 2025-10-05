import json
import os

def extract_and_merge(har_file, output_file="merged.json"):
    # Load HAR file
    with open(har_file, "r", encoding="utf-8") as f:
        har_data = json.load(f)

    merged_data = {}

    for entry in har_data.get("log", {}).get("entries", []):
        request_url = entry.get("request", {}).get("url", "")
        response_content = entry.get("response", {}).get("content", {})
        text = response_content.get("text", "")
        if not text:
            continue

        try:
            json_data = json.loads(text)
        except Exception:
            continue

        # ------------------ Case 1: /req → Fundamentals or Metrics ------------------
        if request_url.endswith("/req"):
            # Case 1a: data -> eq (symbols as keys)
            if isinstance(json_data.get("data"), dict) and "eq" in json_data["data"]:
                for symbol, info in json_data["data"]["eq"].items():
                    merged_data.setdefault(symbol, {}).update(info)

            # Case 1b: data is a list of metrics
            elif isinstance(json_data.get("data"), list):
                for item in json_data["data"]:
                    symbol = item.get("symbol")
                    name = item.get("name")
                    value = item.get("value")
                    if symbol and name:
                        merged_data.setdefault(symbol, {})[name] = value

        # ------------------ Case 2: /rq → Technical data ------------------
        elif request_url.endswith("/rq"):
            # Example:
            # {
            #   "AASM": [
            #       [1733914800, 7.14, 7.23, 7.14, 7.2, 5915],
            #       [1734001200, 7.47, 7.47, 7.06, 7.07, 1231]
            #   ]
            # }
            if isinstance(json_data, dict):
                for symbol, tech_data in json_data['data'].items():
                    if isinstance(tech_data, list) and all(isinstance(x, list) for x in tech_data):
                        merged_data.setdefault(symbol, {}).setdefault("technicals", []).extend(tech_data)

    # Save merged output
    with open(output_file, "w", encoding="utf-8") as out_file:
        json.dump(merged_data, out_file, indent=4, ensure_ascii=False)

    print(f"Merged data saved to {output_file}")

# Example usage
extract_and_merge("research.akdtrade.biz.har")
