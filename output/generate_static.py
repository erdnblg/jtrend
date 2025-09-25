import os
import requests  # or whatever you used for scraping
from jinja2 import Template  # for HTML templating

# 1. Prepare output folder
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# 2. Fetch or generate your Jpop trends
# Replace this with your actual data fetching logic
trends = [
    {"rank": 1, "title": "Song A", "artist": "Artist A"},
    {"rank": 2, "title": "Song B", "artist": "Artist B"},
    {"rank": 3, "title": "Song C", "artist": "Artist C"},
]

# 3. HTML template (you can make it fancier)
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Jpop Trends</title>
  <style>
    body { font-family: Arial; padding: 2rem; background: #fdf6e3; }
    h1 { color: #dc322f; }
    table { border-collapse: collapse; width: 50%; }
    th, td { border: 1px solid #ccc; padding: 0.5rem; text-align: left; }
    th { background-color: #eee; }
  </style>
</head>
<body>
  <h1>Jpop Trends</h1>
  <table>
    <tr><th>Rank</th><th>Title</th><th>Artist</th></tr>
    {% for trend in trends %}
    <tr>
      <td>{{ trend.rank }}</td>
      <td>{{ trend.title }}</td>
      <td>{{ trend.artist }}</td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""

# 4. Render HTML
template = Template(html_template)
html_content = template.render(trends=trends)

# 5. Save to output folder
with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
    f.write(html_content)

print("Static HTML generated in output/index.html")
