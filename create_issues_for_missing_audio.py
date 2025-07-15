import json
import requests
import os
import time

GITHUB_REPO = "ezeanyimhenry/igbonsibidi-names"
GH_TOKEN = os.environ.get("GH_TOKEN")
JSON_FILE = "dictionary.json"

headers = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept": "application/vnd.github+json"
}

graphql_headers = {
    "Authorization": f"bearer {GH_TOKEN}"
}

def search_existing_issues(igbo_word):
    """Searches for existing issues with this word."""
    query = f'repo:{GITHUB_REPO} is:issue in:title "{igbo_word}"'
    url = f"https://api.github.com/search/issues?q={requests.utils.quote(query)}"
    
    resp = requests.get(url, headers=headers)

    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        print("⚠️ Rate limit hit during search. Skipping search for now.")
        return None
    elif resp.status_code != 200:
        print(f"❌ Failed to search issues: {resp.status_code} - {resp.text}")
        return None

    return resp.json().get("items", [])

def delete_issue(issue_node_id):
    """Delete an issue using GraphQL."""
    query = """
    mutation DeleteIssue($id:ID!) {
      deleteIssue(input:{issueId:$id}) {
        clientMutationId
      }
    }
    """
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"id": issue_node_id}},
        headers=graphql_headers
    )
    if resp.status_code == 200:
        print(f"🗑️ Deleted duplicate issue.")
    else:
        print(f"❌ Could not delete issue: {resp.status_code} - {resp.text}")

def create_issue(entry):
    title = f"Add Audio for: {entry['igboWord']}"
    body = f"""### 🗣 Audio Needed

**Igbo Word**: `{entry['igboWord']}`  
**Definition**: {entry['definitions'][0]['definitions'][0] if entry.get('definitions') else 'N/A'}

📢 Please upload an `.mp3` file for this word using a public service like **Google Drive**, **Dropbox**, or **Vocaroo**, then paste the link below in a comment.

Once approved, it will be added to the repository and linked in the dataset.
"""
    issue_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    payload = {"title": title, "body": body, "labels": ["audio-needed"]}

    resp = requests.post(issue_url, json=payload, headers=headers)

    if resp.status_code == 201:
        print(f"✅ Created issue for {entry['igboWord']}")
    elif resp.status_code == 403 and "rate limit" in resp.text.lower():
        print("⏳ Rate limit hit during issue creation. Skipping...")
    else:
        print(f"❌ Failed to create issue: {resp.status_code} - {resp.text}")

# === MAIN SCRIPT ===
with open(JSON_FILE, "r", encoding="utf-8") as f:
    entries = json.load(f)

for entry in entries:
    if entry.get("audioUrl"):
        continue

    igbo_word = entry["igboWord"]

    existing_issues = search_existing_issues(igbo_word)

    if existing_issues is None:
        print(f"⏩ Skipping {igbo_word} due to search failure or rate limit.")
        continue

    if len(existing_issues) > 1:
        # Sort and remove all but the earliest
        existing_issues.sort(key=lambda i: i["created_at"])
        for duplicate in existing_issues[1:]:
            detail = requests.get(duplicate["url"], headers=headers)
            if detail.status_code == 200 and detail.json().get("node_id"):
                delete_issue(detail.json()["node_id"])
            else:
                print(f"⚠️ Failed to fetch/delete: {duplicate['url']}")

    if existing_issues:
        print(f"🔁 Issue already exists for {igbo_word}. Skipping.")
        continue

    create_issue(entry)
