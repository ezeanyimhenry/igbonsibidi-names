import json
import requests
import os
import time

# === CONFIGURATION ===
GITHUB_REPO = "ezeanyimhenry/igbonsibidi-names"
GH_TOKEN = os.environ.get("GH_TOKEN")
JSON_FILE = "dictionary.json"
BATCH_LIMIT = 50  # Max issues to create per run
RATE_LIMIT_DELAY = 3  # seconds between issue creations

headers = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def issue_already_exists(igbo_word):
    """Check if an issue with this word already exists."""
    search_url = f"https://api.github.com/search/issues?q=repo:{GITHUB_REPO}+in:title+\"{igbo_word}\""
    resp = requests.get(search_url, headers=headers)
    if resp.status_code == 200:
        return any(igbo_word.lower() in item['title'].lower() for item in resp.json().get("items", []))
    else:
        print(f"❌ Failed to search for existing issues: {resp.status_code} - {resp.text}")
        return False

# === LOAD DATA ===
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

issues_created = 0

# === PROCESS ENTRIES ===
for entry in data:
    if entry.get("audioUrl"):
        continue

    igbo_word = entry["igboWord"]
    if issue_already_exists(igbo_word):
        print(f"🔁 Issue already exists for {igbo_word}, skipping.")
        continue

    title = f"Add Audio for: {igbo_word}"
    definition = entry.get("definitions", [{}])[0].get("definitions", ["N/A"])[0]
    body = f"""### 🗣 Audio Needed

**Igbo Word**: `{igbo_word}`  
**Definition**: {definition}

📢 Please upload an `.mp3` file as a comment below by dragging and dropping it.

Once approved, it will be added to the repository and linked in the dataset.
"""

    issue_data = {"title": title, "body": body, "labels": ["audio-needed"]}
    r = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues",
        json=issue_data,
        headers=headers
    )

    if r.status_code == 201:
        print(f"✅ Issue created for {igbo_word}")
        issues_created += 1
    else:
        print(f"❌ Failed to create issue for {igbo_word}: {r.status_code} - {r.text}")

    time.sleep(RATE_LIMIT_DELAY)

    if issues_created >= BATCH_LIMIT:
        print(f"🚫 Reached batch limit of {BATCH_LIMIT}. Stopping early.")
        break

if issues_created == 0:
    print("ℹ️ No new issues created.")
else:
    print(f"✅ Created {issues_created} issue(s) in total.")
