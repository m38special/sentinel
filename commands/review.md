# /review - Code Review

Trigger 3-AI code review on PR.

## Usage
/review [pr_number]

## Reviewers
- Codex — Logic & edge cases
- Gemini — Security & scale
- Claude — Architecture

## Process
1. Fetch PR diff
2. Route to 3 AI reviewers
3. Post summary to PR
4. Human merge decision

## Examples
/review
/review 42
