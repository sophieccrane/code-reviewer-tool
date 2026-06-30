import json
import os
import requests
from dotenv import load_dotenv
import anthropic

# -----------------------------
# Configuration
# -----------------------------

load_dotenv()

GITHUB_OWNER = "GITHUB_OWNER"
GITHUB_REPO = "test-code-reviewer-tool"
PR_NUMBER = 123

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN not found")

if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY not found")

MODEL = "claude-sonnet-4-5-20250929"

# -----------------------------
# GitHub
# -----------------------------

github_headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls/{PR_NUMBER}/files"

r = requests.get(url, headers=github_headers)
r.raise_for_status()

files = r.json()

# -----------------------------
# Build diff prompt
# -----------------------------

diff = []

for f in files:
    diff.append(f"# File: {f['filename']}")

    if f.get("status"):
        diff.append(f"Status: {f['status']}")

    if "patch" in f:
        diff.append(f["patch"])
    else:
        diff.append("(No textual diff available.)")

    diff.append("")

combined_diff = "\n".join(diff)

system_prompt = """
You are an experienced staff software engineer.

Review this GitHub pull request.

Focus on:
- correctness
- bugs
- edge cases
- security
- maintainability
- performance

Return ONLY valid JSON. 
Use double quotes for all keys and strings.

Schema:

{
  "summary": "...",
  "issues": [
    {
      "severity": "low|medium|high",
      "file": "...",
      "title": "...",
      "description": "...",
      "suggestion": "..."
    }
  ]
}
"""

user_prompt = f"""
Review the following pull request.

{combined_diff}
"""

# -----------------------------
# Claude API
# -----------------------------
client = anthropic.Anthropic()

headers = {
    "x-api-key": ANTHROPIC_API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}

body = {
    "model": MODEL,
    "max_tokens": 4000,
    "system": system_prompt,
    "messages": [
        {
            "role": "user",
            "content": user_prompt,
        }
    ],
}

response = client.messages.create(
    model=MODEL,
    max_tokens=4000,
    system=system_prompt,
    messages=[
        {"role": "user", "content": user_prompt}
    ]
)

text = response.content[0].text.strip()

# -----------------------------
# Translate JSON into readable format
# -----------------------------

# Strip markdown fences and language identifiers if the model wrapped the JSON in a code block.
if text.startswith("```"):
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    text = "\n".join(lines).strip()

# Extract the first JSON object in case the model returned extra text before/after it.
start = text.find("{")
end = text.rfind("}")
if start != -1 and end != -1 and start < end:
    text = text[start:end + 1]

parsed = json.loads(text)

print("\nJSON parsed successfully.\n")
print(json.dumps(parsed, indent=2))

print("\nReadable review summary:\n")
print(parsed.get("summary", "(no summary returned)").strip())
print("\nIssues:")
for issue in parsed.get("issues", []):
    print(f"- [{issue.get('severity', 'unknown').upper()}] {issue.get('file', '(no file)')}: {issue.get('title', '(no title)')}")
    description = issue.get("description", "").strip()
    suggestion = issue.get("suggestion", "").strip()
    if description:
        print(f"  Description: {description}")
    if suggestion:
        print(f"  Suggestion: {suggestion}")
    print()


def build_pull_request_review_body(parsed_review):
    lines = ["### Automated Code Review Results", ""]
    summary = parsed_review.get("summary", "(no summary returned)").strip()
    lines.append("**Summary:**")
    lines.append(summary)
    lines.append("")

    issues = parsed_review.get("issues", [])
    if not issues:
        lines.append("No issues found.")
        return "\n".join(lines)

    lines.append("**Issues:**")
    for issue in issues:
        severity = issue.get("severity", "unknown").upper()
        file_path = issue.get("file", "(no file)")
        title = issue.get("title", "(no title)")
        description = issue.get("description", "").strip()
        suggestion = issue.get("suggestion", "").strip()

        lines.append(f"- **{severity}** `{file_path}`: {title}")
        if description:
            lines.append(f"  - Description: {description}")
        if suggestion:
            lines.append(f"  - Suggestion: {suggestion}")
        lines.append("")

    return "\n".join(lines).strip()


def post_pull_request_review(body_text):
    pr_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls/{PR_NUMBER}"
    pr_response = requests.get(pr_url, headers=github_headers)
    pr_response.raise_for_status()
    head_sha = pr_response.json()["head"]["sha"]

    review_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls/{PR_NUMBER}/reviews"
    payload = {
        "commit_id": head_sha,
        "body": body_text,
        "event": "COMMENT",
    }
    review_response = requests.post(review_url, headers=github_headers, json=payload)
    review_response.raise_for_status()
    return review_response.json()


review_body = build_pull_request_review_body(parsed)
print("Posting GitHub pull request review comment...")
review_result = post_pull_request_review(review_body)
print("GitHub review created:", review_result.get("html_url", "(no URL returned)"))