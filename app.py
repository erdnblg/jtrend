import json
import os
import snscrape.modules.twitter as sntwitter
from pytrends.request import TrendReq
from flask import Flask, render_template

app = Flask(__name__)


# Load seed members list
def load_members():
    members_file = os.path.join("data", "members_seed.txt")
    with open(members_file, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


# Get trending score using pytrends
def get_trending_index(name):
    pytrends = TrendReq(hl='ja-JP', tz=540)
    try:
        pytrends.build_payload([name], timeframe='now 7-d', geo='JP')
        interest = pytrends.interest_over_time()
        if not interest.empty:
            return int(interest[name].mean())
    except Exception:
        pass
    return 0


# Collect top members
@app.route("/update")
def update_data():
    members = load_members()
    results = []
    for member in members:
        score = get_trending_index(member)
        results.append({"name": member, "score": score})
    results = sorted(results, key=lambda x: x["score"], reverse=True)[:10]

    # Collect top trending news via snscrape
    news_results = []
    for i, tweet in enumerate(sntwitter.TwitterSearchScraper("JPOP since:2023-01-01").get_items()):
        if i >= 100:
            break
        news_results.append({"title": tweet.content[:80], "score": tweet.likeCount + tweet.retweetCount})
    news_results = sorted(news_results, key=lambda x: x["score"], reverse=True)[:10]

    data = {"members": results, "news": news_results}

    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"status": "updated", "data": data}


@app.route("/")
def index():
    with open("docs/data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return render_template("index.html", data=data)


if __name__ == "__main__":
    app.run(debug=True)

