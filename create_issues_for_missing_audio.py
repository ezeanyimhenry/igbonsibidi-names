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
    """Returns all matching open issues for a given igbo_word"""
    query = f'repo:{GITHUB_REPO} is:issue in:title "{igbo_word}"'
    search_url = f"https://api.github.com/search/issues?q={requests.utils.quote(query)}"
    resp = requests.get(search_url, headers=headers)
    if resp.status_code == 200:
        return resp.json().get("items", [])
    else:
        print(f"❌ Failed to search for issues: {resp.status_code} - {resp.text}")
        return []

def delete_issue(issue_node_id):
    """Delete a GitHub issue using GraphQL"""
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
        print(f"🗑️  Deleted duplicate issue")
    else:
        print(f"❌ Failed to delete issue: {resp.status_code} - {resp.text}")

def create_issue(entry):
    title = f"Add Audio for: {entry['igboWord']}"
    body = f"""### 🗣 Audio Needed

**Igbo Word**: `{entry['igboWord']}`  
**Definition**: {entry['definitions'][0]['definitions'][0] if entry.get('definitions') else 'N/A'}

📢 Please upload an `.mp3` file as a comment below by dragging and dropping it.

Once approved, it will be added to the repository and linked in the dataset.
"""
    issue_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    issue_data = {"title": title, "body": body, "labels": ["audio-needed"]}
    r = requests.post(issue_url, json=issue_data, headers=headers)

    if r.status_code == 201:
        print(f"✅ Issue created for {entry['igboWord']}")
    elif r.status_code == 403 and "rate limit" in r.text.lower():
        print("⚠️ Rate limited. Sleeping for 60 seconds...")
        time.sleep(60)
        create_issue(entry)
    else:
        print(f"❌ Failed to create issue for {entry['igboWord']}: {r.status_code} - {r.text}")

# === MAIN SCRIPT ===
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

for entry in data:
    if entry.get("audioUrl"):
        continue

    igbo_word = entry["igboWord"]
    existing_issues = search_existing_issues(igbo_word)

    # Remove duplicates, keep the earliest
    if len(existing_issues) > 1:
        # Sort by creation date
        existing_issues.sort(key=lambda x: x["created_at"])
        to_delete = existing_issues[1:]  # All but the first

        for issue in to_delete:
            # Fetch node_id to delete via GraphQL
            issue_detail = requests.get(issue["url"], headers=headers).json()
            node_id = issue_detail.get("node_id")
            if node_id:
                delete_issue(node_id)
            else:
                print(f"⚠️ Could not find node_id for issue: {issue['html_url']}")

    if not existing_issues:
        create_issue(entry)
