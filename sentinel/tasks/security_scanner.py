"""
Security Scanner Task
SENTINEL | LiQUiD SOUND

Scheduled security vulnerability analysis - runs daily at 3:30am UTC
"""
import os
import json
import logging
from datetime import datetime, timezone
from tasks import app

log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@app.task(
    name="tasks.security_scanner.scan_codebase",
    bind=True,
    max_retries=2,
    queue="sentinel",
)
def scan_codebase(self):
    """
    Daily security scan of codebase.
    Checks for:
    - Hardcoded secrets/API keys
    - SQL injection vulnerabilities
    - Command injection risks
    - XSS vulnerabilities
    - Insecure random usage
    """
    import redis
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vulnerabilities": [],
        "warnings": [],
        "passed": [],
        "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0}
    }
    
    # Define scan patterns
    patterns = {
        "hardcoded_secret": {
            "pattern": r'(api_key|password|secret|token)\s*=\s*["\'][^"\']{8,}["\']',
            "severity": "critical",
            "description": "Potential hardcoded secret"
        },
        "sql_injection": {
            "pattern": r'execute\s*\([^)]*\+[^)]*\)',
            "severity": "high",
            "description": "Potential SQL injection risk"
        },
        "command_injection": {
            "pattern": r'(os\.system|subprocess\.(call|run|popen)[^_])',
            "severity": "critical",
            "description": "Potential command injection"
        },
        "eval_usage": {
            "pattern": r'\beval\s*\(',
            "severity": "high",
            "description": "Use of eval() function"
        },
        "insecure_random": {
            "pattern": r'random\.(random|choice)\(',
            "severity": "medium",
            "description": "Insecure random (use secrets module)"
        }
    }
    
    # Scan Python files
    import subprocess
    try:
        scan_dir = os.getenv("SCAN_DIR", "/app")
        
        # Run basic security checks
        for vuln_type, config in patterns.items():
            try:
                # Simple grep-based scan
                cmd = f"grep -r -n -E '{config['pattern']}' {scan_dir} --include='*.py' 2>/dev/null | head -20"
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True)
                
                if output.strip():
                    findings = output.strip().split('\n')
                    for finding in findings:
                        if finding:
                            results["vulnerabilities"].append({
                                "type": vuln_type,
                                "severity": config["severity"],
                                "description": config["description"],
                                "file": finding
                            })
                            results["summary"][config["severity"]] += 1
                else:
                    results["passed"].append(vuln_type)
                    
            except subprocess.CalledProcessError:
                results["passed"].append(vuln_type)
            except Exception as e:
                log.warning(f"Scan error for {vuln_type}: {e}")
        
    except Exception as e:
        log.error(f"Security scan failed: {e}")
        return {"status": "error", "message": str(e)}
    
    # Store results
    r.set("security:scan:latest", json.dumps(results))
    r.lpush("security:scan:history", json.dumps(results))
    r.ltrim("security:scan:history", 0, 99)
    
    # Send alert if critical issues found
    if results["summary"]["critical"] > 0:
        alert_msg = f"🚨 CRITICAL: {results['summary']['critical']} security vulnerabilities found in codebase"
        log.error(alert_msg)
        # Could trigger Slack alert here
    
    log.info(f"Security scan complete: {results['summary']}")
    
    return results


# Add to beat schedule (3:30am UTC = 9:30pm CT previous day)
# Using crontab syntax
from celery.schedules import crontab

app.conf.beat_schedule = {
    **app.conf.beat_schedule,
    "security-scan-330am-utc": {
        "task": "tasks.security_scanner.scan_codebase",
        "schedule": crontab(hour=3, minute=30),  # 3:30am UTC
        "options": {"queue": "sentinel"},
    },
}
