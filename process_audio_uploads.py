import json
import os
import re
import requests
from slugify import slugify
from copy import deepcopy

GITHUB_REPO = "ezeanyimhenry/igbonsibidi-names"
GH_TOKEN = os.environ.get("GH_TOKEN")
AUDIO_DIR = "assets/audio"
JSON_FILE = "dictionary.json"

os.makedirs(AUDIO_DIR, exist_ok=True)

headers = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# Convert Google Drive "view" link to downloadable link
def convert_google_drive_url(url):
    match = re.search(r"drive\.google\.com/file/d/([^/]+)", url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url  # return original if not a Drive link

# Load and snapshot original data
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)
original_data = deepcopy(data)

# Get closed issues with 'audio-needed' label
issues_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues?state=closed&labels=completed&per_page=100"
issues = requests.get(issues_url, headers=headers).json()

for issue in issues:
    title = issue['title']
    if "Add Audio for:" not in title:
        continue

    word = title.split("Add Audio for:")[1].strip()
    slug = slugify(word)
    found_entry = next((item for item in data if item["igboWord"] == word and not item.get("audioUrl")), None)
    if not found_entry:
        continue

    # Get comments to find audio
    comments_url = issue['comments_url']
    comments = requests.get(comments_url, headers=headers).json()
    audio_url = None

    for comment in comments:
        body = comment.get("body", "")
        raw_urls = re.findall(r"https?://[^\s\)\"]+", body)
        urls = [convert_google_drive_url(u) for u in raw_urls]

        for url in urls:
            try:
                r = requests.get(url, allow_redirects=True, timeout=15)
                content_type = r.headers.get("Content-Type", "").lower()

                if r.status_code == 200 and content_type.startswith("audio"):
                    audio_url = url
                    audio_path = os.path.join(AUDIO_DIR, f"{slug}.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(r.content)
                    print(f"🎧 Saved audio for '{word}' from {url}")

                    # Update the dataset
                    github_raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{AUDIO_DIR}/{slug}.mp3"
                    found_entry["audioUrl"] = github_raw_url
                    break
            except Exception as e:
                print(f"⚠️ Failed to download from {url}: {e}")
        if audio_url:
            break

    if not audio_url:
        print(f"⚠️ No valid audio found in issue #{issue['number']} for '{word}'")

# Only save if something changed
if data != original_data:
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON updated with new audio URLs.")
else:
    print("ℹ️ No updates were made to JSON.")
