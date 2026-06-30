# code-reviewer-tool

A small Python tool that uses Claude to review the diff of a GitHub pull request and if the changes adhere to standard coding practices, then post a formatted PR review comment with the findings.

## What it does

- Fetches changed files from a GitHub pull request
- Builds a diff-based review prompt for the Claude model
- Parses the model response as structured JSON
- Prints a readable summary locally
- Posts the review back to the pull request as a GitHub review comment

## Requirements

- Python 3.10+
- `requests`
- `python-dotenv`
- `anthropic`

## Setup

1. Clone the repository.
2. Create a `.env` file in the project root with the following values:

```env
GITHUB_TOKEN=your_github_token
ANTHROPIC_API_KEY=your_anthropic_api_key
```
You can find out how to obtain these keys in the following documentation:
GitHub Token: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
Anthropic API Key: https://platform.claude.com/docs/en/api/admin/api_keys/retrieve

3. Install dependencies:

```bash
python3 -m pip install requests python-dotenv anthropic
```

4. Update the configuration in `code-reviewer.py`:

- `GITHUB_OWNER`
- `GITHUB_REPO`
- `PR_NUMBER`

## Usage

Run the tool from the project root:

```bash
python3 code-reviewer.py
```

The script will:

- fetch the pull request diff from GitHub
- ask Claude to review it
- parse the returned JSON review
- print a human-readable summary
- post a GitHub review comment on the pull request

## Notes

- The script currently posts a single summary review comment rather than inline line-by-line comments.
- If the model output includes markdown fences, the script strips them before parsing JSON.
- Ensure the GitHub token has permission to read the repository and post PR reviews.
