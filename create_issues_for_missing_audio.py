import json
import requests
import os
from time import sleep

GITHUB_REPO = "ezeanyimhenry/igbonsibidi-names"
GH_TOKEN = os.environ.get("GH_TOKEN")
JSON_FILE = "dictionary.json"
TRACKED_FILE = ".issued_words.json"

headers = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def load_issued_words():
    if os.path.exists(TRACKED_FILE):
        with open(TRACKED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_issued_words(words):
    with open(TRACKED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(words)), f, indent=2)

def search_existing_issues(word):
    """Find issues for a word with 'audio-needed' label."""
    query = f'repo:{GITHUB_REPO} is:issue in:title "{word}" label:audio-needed'
    url = f"https://api.github.com/search/issues?q={requests.utils.quote(query)}"

    resp = requests.get(url, headers=headers)
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        print("⚠️ Rate limit hit during search. Skipping...")
        return None
    elif resp.status_code != 200:
        print(f"❌ Failed to search issues: {resp.status_code} - {resp.text}")
        return None

    return resp.json().get("items", [])

def close_duplicate(issue_number, original_number):
    comment_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}/comments"
    close_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}"

    comment = {
        "body": f"This issue is a duplicate of #{original_number}. Closing it."
    }
    requests.post(comment_url, headers=headers, json=comment)

    payload = {"state": "closed"}
    resp = requests.patch(close_url, headers=headers, json=payload)

    if resp.status_code == 200:
        print(f"🗂️ Closed duplicate issue #{issue_number}")
    else:
        print(f"❌ Failed to close issue #{issue_number}: {resp.status_code}")

def create_issue(entry):
    title = f"Add Audio for: {entry['igboWord']}"
    definition = entry['definitions'][0]['definitions'][0] if entry.get("definitions") else "N/A"

    body = f"""### 🗣 Audio Needed

**Igbo Word**: `{entry['igboWord']}`  
**Definition**: {definition}

📢 Please upload an `.mp3` file for this word using a public service like **Google Drive**, **Dropbox**, or **Vocaroo**, then paste the link below in a comment.

Once approved, it will be added to the repository and linked in the dataset.
"""
    payload = {
        "title": title,
        "body": body,
        "labels": ["audio-needed"]
    }

    issue_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    resp = requests.post(issue_url, headers=headers, json=payload)

    if resp.status_code == 201:
        print(f"✅ Created issue for {entry['igboWord']}")
        return True
    elif resp.status_code == 403 and "rate limit" in resp.text.lower():
        print("⏳ Rate limit hit during creation. Aborting...")
        return "rate-limit"
    else:
        print(f"❌ Failed to create issue: {resp.status_code} - {resp.text}")
        return False

# === MAIN ===
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

issued_words = load_issued_words()

for entry in data:
    word = entry["igboWord"]

    if entry.get("audioUrl") or word in issued_words:
        continue

    issues = search_existing_issues(word)

    if issues is None:
        print(f"⏩ Skipping '{word}' due to rate limit or error.")
        continue

    if len(issues) > 1:
        issues.sort(key=lambda i: i["created_at"])
        original = issues[0]["number"]
        for dup in issues[1:]:
            close_duplicate(dup["number"], original)
        print(f"🔁 Retained issue #{original} for '{word}'")

    if issues:
        print(f"📝 Issue already exists for '{word}'")
        issued_words.add(word)
        continue

    result = create_issue(entry)
    if result == "rate-limit":
        break
    elif result:
        issued_words.add(word)

    sleep(1)  # gentle pacing

save_issued_words(issued_words)
print("✅ Done creating audio-needed issues.")
