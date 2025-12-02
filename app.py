from flask import Flask, render_template, request
import json
from strategies import (
    recommend_day_trade,
    recommend_swing_trade,
    recommend_long_term,
    find_undervalued
)

app = Flask(__name__)

def load_data():
    with open("stocks.json", "r") as f:
        raw = json.load(f)
        return raw

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        choice = request.form.get("choice")

        data = load_data()

        if choice == "day":
            results = recommend_day_trade(data)
            title = "Day Trading Recommendations"
        elif choice == "swing":
            results = recommend_swing_trade(data)
            title = "Swing Trading Recommendations"
        elif choice == "long":
            results = recommend_long_term(data)
            title = "Long Term Investing Recommendations"
        elif choice == "undervalued":
            results = find_undervalued(data)
            title = "Undervalued Stocks"
        else:
            results = []
            title = "Unknown Selection"

        return render_template("table.html", results=results, title=title)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
