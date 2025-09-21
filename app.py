# app.py
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict

from flask import Flask, send_from_directory
import pandas as pd

import snscrape.modules.twitter as sntwitter
from pytrends.request import TrendReq

# Config
DATA_DIR = 'data'
MEMBERS_SEED = os.path.join(DATA_DIR, 'members_seed.txt')
OUTPUT_DIR = 'docs'
TOP_N = 10

app = Flask(__name__)

# Utility: load seed members
def load_seed_members():
    if not os.path.exists(MEMBERS_SEED):
        return []
    with open(MEMBERS_SEED, 'r', encoding='utf-8') as f:
        names = [line.strip() for line in f if line.strip()]
    return names

# Use snscrape to count mentions of a name over a timeframe (e.g., 7 days)
def twitter_mention_count(name, days=7, max_tweets=1000):
    since = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
    query = f'"{name}" since:{since}'
    count = 0
    for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
        count += 1
        if i+1 >= max_tweets:
            break
    return count

# Get Google Trends interest for a name over timeframe (e.g., 7 days)
def google_trends_interest(names, timeframe='now 7-d'):
    pytrends = TrendReq(hl='en-US', tz=0)
    results = {}
    batch_size = 5
    for i in range(0, len(names), batch_size):
        kw_list = names[i:i+batch_size]
        try:
            pytrends.build_payload(kw_list, cat=0, timeframe=timeframe, geo='JP')
            df = pytrends.interest_over_time()
            if df.empty:
                for k in kw_list:
                    results[k] = 0
                continue
            for k in kw_list:
                if k in df.columns:
                    results[k] = int(df[k].mean())
                else:
                    results[k] = 0
        except Exception:
            for k in kw_list:
                results[k] = 0
    return results

# Normalize and combine signals into a single popularity index
def compute_popularity_index(twitter_counts, trends, weight_twitter=0.6, weight_trends=0.4):
    names = list(set(list(twitter_counts.keys()) + list(trends.keys())))
    tvals = [twitter_counts.get(n, 0) for n in names]
    gvals = [trends.get(n, 0) for n in names]

    def normalize(arr):
        if not arr:
            return []
        mx = max(arr)
        mn = min(arr)
        if mx == mn:
            return [50]*len(arr)
        return [ (x - mn) / (mx - mn) * 100 for x in arr]

    tnorm = normalize(tvals)
    gnorm = normalize(gvals)
    score = {}
    for i,n in enumerate(names):
        s = weight_twitter*tnorm[i] + weight_trends*gnorm[i]
        score[n] = round(s, 3)
    return score

# Build rankings
def build_rankings():
    candidates = load_seed_members()
    if not candidates:
        raise RuntimeError('No candidates found. Please provide data/members_seed.txt.')
    candidates = candidates[:100]

    twitter_counts = {}
    for name in candidates:
        try:
            c = twitter_mention_count(name, days=7, max_tweets=2000)
        except Exception:
            c = 0
        twitter_counts[name] = c

    trends = google_trends_interest(candidates, timeframe='now 7-d')
    popularity = compute_popularity_index(twitter_counts, trends)

    top_members = sorted(popularity.items(), key=lambda x: -x[1])[:TOP_N]

    news_scores = {}
    for name in candidates:
        query = f'"{name}" since:{(datetime.utcnow()-timedelta(days=7)).strftime("%Y-%m-%d")} filter:links'
        link_count = 0
        for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
            link_count += 1
            if i+1 >= 300:
                break
        news_scores[name] = link_count

    ns_values = list(news_scores.values())
    if ns_values:
        mx = max(ns_values); mn = min(ns_values)
    else:
        mx = mn = 0
    news_index = {n: (0 if mx==mn else round((v-mn)/(mx-mn)*100,3)) for n,v in news_scores.items()}
    top_news = sorted(news_index.items(), key=lambda x: -x[1])[:TOP_N]

    summary = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'top_members': [{'name': n, 'score': s, 'twitter_mentions': twitter_counts.get(n,0), 'trend_index': trends.get(n,0)} for n,s in top_members],
        'top_news': [{'name': n, 'news_index': news_index.get(n,0), 'link_mentions': news_scores.get(n,0)} for n,_ in top_news],
        'all_popularity': sorted(popularity.items(), key=lambda x: -x[1])
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, 'data.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader('templates'))
    tpl = env.get_template('index.html')
    html = tpl.render(summary=summary)
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    return summary

@app.route('/')
def index():
    if not os.path.exists(os.path.join(OUTPUT_DIR, 'index.html')):
        try:
            build_rankings()
        except Exception as e:
            return f'<pre>Error generating site: {e}</pre>'
    return send_from_directory(OUTPUT_DIR, 'index.html')

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--build', action='store_true', help='Build site once and exit')
    args = p.parse_args()
    if args.build:
        print('Building rankings...')
        s = build_rankings()
        print('Built. Summary:')
        print(json.dumps(s, ensure_ascii=False, indent=2))
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)
