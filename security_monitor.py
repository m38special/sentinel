#!/usr/bin/env python3
"""
security_monitor.py — Behavioral Monitoring for OpenClaw
Detects suspicious patterns: base64 encoded commands, curl | bash, token exfiltration
"""
import re
import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger(__name__)

# Suspicious patterns to detect
SUSPICIOUS_PATTERNS = [
    # Command injection
    (r"curl\s+\|\s*bash", "curl_pipe_bash"),
    (r"wget\s+\|\s*bash", "wget_pipe_bash"),
    (r"sh\s+<\s*\(?http", "shell_redirect_http"),
    
    # Base64 encoded commands
    (r"base64\s+-d\s+", "base64_decode"),
    (r"echo\s+['\"][A-Za-z0-9+/=]{20,}['\"]\s*\|", "base64_pipe"),
    (r"from\s+base64\s+import", "base64_import"),
    
    # Token/credential exfiltration
    (r"Authorization:\s*Bearer\s*[A-Za-z0-9_-]{20,}", "token_in_header"),
    (r"ghp_[A-Za-z0-9]{36}", "github_token"),
    (r"gho_[A-Za-z0-9]{36}", "github_token"),
    (r"sk-[A-Za-z0-9]{48,}", "openai_key"),
    (r"xox[baprs]-[0-9A-Za-z-]{10,}", "slack_token"),
    (r"AIza[0-9A-Za-z_-]{35}", "google_api_key"),
    (r"gsk_[A-Za-z0-9]{43,}", "groq_key"),
    
    # File exfiltration
    (r"scp\s+.*\$HOME", "scp_exfil"),
    (r"rsync\s+.*://", "rsync_exfil"),
    
    # Reverse shell patterns
    (r"/dev/tcp/", "reverse_shell_tcp"),
    (r"bash\s+-i\s+.*>/dev/tcp", "reverse_shell_bash"),
    (r"python\s+-c\s+.*socket", "python_reverse_shell"),
    
    # Privilege escalation
    (r"sudo\s+su", "sudo_su"),
    (r"chmod\s+777\s+/etc", "chmod_777_etc"),
]

# Whitelist patterns (false positives to ignore)
WHITELIST = [
    r"^# .*",  # Comments
    r"^// .*",  # Code comments
    r"example\.com",  # Example domains
    r"test.*token",  # Test tokens
    r"your_token_here",  # Placeholders
]


def is_whitelisted(text: str) -> bool:
    """Check if text matches whitelist patterns."""
    for pattern in WHITELIST:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def scan_text(text: str) -> list[dict]:
    """Scan text for suspicious patterns."""
    if is_whitelisted(text):
        return []
    
    findings = []
    for pattern, name in SUSPICIOUS_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            findings.append({
                "pattern": name,
                "match": match.group()[:100],  # Truncate long matches
                "position": match.start(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    return findings


def scan_command(command: str) -> list[dict]:
    """Scan a shell command for suspicious patterns."""
    return scan_text(command)


def scan_file(filepath: str) -> list[dict]:
    """Scan a file for suspicious patterns."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return scan_text(content)
    except Exception as e:
        log.error(f"Failed to scan file {filepath}: {e}")
        return []


def alert_security_event(findings: list[dict], context: str = ""):
    """Alert on security findings. Logs and could trigger notifications."""
    if not findings:
        return
    
    log.warning(f"🚨 SECURITY ALERT — {len(findings)} findings in: {context}")
    for finding in findings:
        log.warning(f"  [{finding['pattern']}] {finding['match'][:50]}...")
    
    # Could extend to send to Slack/Discord/PagerDuty
    # For now, just log


# CLI entry point
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: security_monitor.py <command> [args]")
        print("  scan-text <text>     — Scan text for patterns")
        print("  scan-file <path>    — Scan file for patterns")
        print("  scan-command <cmd>   — Scan command for patterns")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "scan-text":
        text = " ".join(sys.argv[2:])
        findings = scan_text(text)
        if findings:
            print(json.dumps(findings, indent=2))
        else:
            print("No suspicious patterns found")
    
    elif action == "scan-file":
        filepath = sys.argv[2]
        findings = scan_file(filepath)
        if findings:
            print(json.dumps(findings, indent=2))
        else:
            print("No suspicious patterns found")
    
    elif action == "scan-command":
        cmd = " ".join(sys.argv[2:])
        findings = scan_command(cmd)
        if findings:
            print(json.dumps(findings, indent=2))
        else:
            print("No suspicious patterns found")
    
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
