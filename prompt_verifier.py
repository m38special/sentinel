#!/usr/bin/env python3
"""
prompt_verifier.py — Structured Prompt Verification Layer
Validates prompts against security policies before execution
"""
import json
import re
import hashlib
import os
from datetime import datetime, timezone
from typing import Optional

# Security policy definitions
class SecurityPolicy:
    """Defines what's allowed in prompts."""
    
    # Allowed tool categories (whitelist)
    ALLOWED_TOOLS = {
        "read", "write", "edit", "exec", "message",
        "web_search", "web_fetch", "browser", "memory_search",
        "sessions_spawn", "subagents", "nodes", "tts"
    }
    
    # Blocked patterns (blacklist)
    BLOCKED_PATTERNS = [
        (r"rm\s+-rf\s+/", "Destructive delete root"),
        (r"chmod\s+-R\s+777", "World-writable permissions"),
        (r"curl.*\|.*bash", "Pipe to shell (injection risk)"),
        (r"wget.*\|.*bash", "Pipe to shell (injection risk)"),
        (r"base64.*-d.*\|", "Encoded command execution"),
        (r"eval\s+\$", "Dynamic code execution"),
        (r"exec\s+\$", "Shell execution"),
        (r"sudo\s+rm", "sudo delete"),
        (r">\s*/etc/passwd", "Write to passwd"),
        (r">\s*/etc/shadow", "Write to shadow"),
    ]
    
    # Require approval for these
    APPROVAL_REQUIRED = {
        "exec": r".*rm.*",
        "exec": r".*chmod\s+777.*",
        "exec": r".*curl\s+\|.*bash.*",
        "message": r".*",  # All messages require confirmation
    }
    
    # Max file sizes (MB)
    MAX_FILE_WRITE_MB = 10
    MAX_MEMORY_SEARCH_RESULTS = 50


class VerificationResult:
    def __init__(self, allowed: bool, reason: str, severity: str = "none"):
        self.allowed = allowed
        self.reason = reason
        self.severity = severity  # none, low, medium, high, critical
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self):
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "severity": self.severity,
            "timestamp": self.timestamp,
        }
    
    def __bool__(self):
        return self.allowed


class PromptVerifier:
    """Verifies prompts against security policies."""
    
    def __init__(self, policy: Optional[SecurityPolicy] = None):
        self.policy = policy or SecurityPolicy()
        self.audit_log = []
    
    def verify(self, prompt: str, context: dict = None) -> VerificationResult:
        """
        Verify a prompt against security policies.
        
        Returns VerificationResult with allowed=True/False
        """
        context = context or {}
        
        # Check blocked patterns
        for pattern, description in self.policy.BLOCKED_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                result = VerificationResult(
                    allowed=False,
                    reason=f"Blocked pattern detected: {description}",
                    severity="critical"
                )
                self._log(prompt, result, context)
                return result
        
        # Check for credential patterns
        credential_patterns = [
            (r"ghp_[A-Za-z0-9]{36}", "GitHub token"),
            (r"sk-[A-Za-z0-9]{48,}", "OpenAI key"),
            (r"xox[baprs]-[0-9A-Za-z-]{10,}", "Slack token"),
            (r"gsk_[A-Za-z0-9]{43,}", "Groq key"),
        ]
        
        for pattern, cred_type in credential_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                result = VerificationResult(
                    allowed=False,
                    reason=f"Credential detected in prompt: {cred_type} — redacted in logs",
                    severity="critical"
                )
                self._log(prompt, result, context)
                return result
        
        # Check file write size limits
        if "file_size" in context:
            if context["file_size"] > self.policy.MAX_FILE_WRITE_MB * 1024 * 1024:
                result = VerificationResult(
                    allowed=False,
                    reason=f"File too large: {context['file_size']}MB > {self.policy.MAX_FILE_WRITE_MB}MB",
                    severity="high"
                )
                self._log(prompt, result, context)
                return result
        
        # Check memory search limits
        if "memory_results" in context:
            if context["memory_results"] > self.policy.MAX_MEMORY_SEARCH_RESULTS:
                result = VerificationResult(
                    allowed=False,
                    reason=f"Too many memory results: {context['memory_results']} > {self.policy.MAX_MEMORY_SEARCH_RESULTS}",
                    severity="medium"
                )
                self._log(prompt, result, context)
                return result
        
        # All checks passed
        result = VerificationResult(
            allowed=True,
            reason="Prompt passed security verification",
            severity="none"
        )
        self._log(prompt, result, context)
        return result
    
    def _log(self, prompt: str, result: VerificationResult, context: dict):
        """Log verification for audit trail."""
        # Truncate prompt for logging
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        
        entry = {
            "prompt_hash": prompt_hash,
            "result": result.to_dict(),
            "context": {k: str(v)[:100] for k, v in context.items()},
        }
        self.audit_log.append(entry)
    
    def get_audit_log(self):
        return self.audit_log


# CLI for testing
if __name__ == "__main__":
    import sys
    
    verifier = PromptVerifier()
    
    if len(sys.argv) < 2:
        print("Usage: prompt_verifier.py <prompt>")
        sys.exit(1)
    
    prompt = " ".join(sys.argv[1:])
    result = verifier.verify(prompt)
    
    print(json.dumps(result.to_dict(), indent=2))
    
    if not result.allowed:
        sys.exit(1)
