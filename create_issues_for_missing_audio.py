import json
import requests
import os

GITHUB_REPO = "ezeanyimhenry/igbonsibidi-names"
GH_TOKEN = os.environ.get("GH_TOKEN")
JSON_FILE = "dictionary.json"

headers = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept": "application/vnd.github+json"
}

with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

for entry in data:
    if entry.get("audioUrl"):
        continue

    title = f"Add Audio for: {entry['igboWord']}"
    body = f"""### 🗣 Audio Needed

**Igbo Word**: `{entry['igboWord']}`  
**Definition**: {entry['definitions'][0]['definitions'][0] if entry.get('definitions') else 'N/A'}

📢 Please upload an `.mp3` file as a comment below by dragging and dropping it.

Once approved, it will be added to the repository and linked in the dataset.
"""

    # Check if issue already exists (you could add caching or label filtering for scale)
    search_url = f"https://api.github.com/search/issues?q=repo:{GITHUB_REPO}+in:title+\"{entry['igboWord']}\""
    resp = requests.get(search_url, headers=headers)
    if any(entry['igboWord'].lower() in i['title'].lower() for i in resp.json().get("items", [])):
        continue

    # Create the issue
    issue_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    issue_data = {"title": title, "body": body, "labels": ["audio-needed"]}
    r = requests.post(issue_url, json=issue_data, headers=headers)

    if r.status_code == 201:
        print(f"✅ Issue created for {entry['igboWord']}")
    else:
        print(f"❌ Failed to create issue for {entry['igboWord']}: {r.status_code} - {r.text}")
