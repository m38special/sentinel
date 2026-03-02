#!/usr/bin/env python3
"""
config_backup.py — Automatic backup before config changes
Creates timestamped backups of OpenClaw config and secrets
"""
import os
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path("/Users/m38special/.openclaw/backups")
CONFIG_FILE = Path("/Users/m38special/.openclaw/openclaw.json")
SECRETS_FILE = Path("/Users/m38special/.openclaw/workspace/.secrets")

# Files to backup
BACKUP_TARGETS = [
    CONFIG_FILE,
    SECRETS_FILE,
    Path("/Users/m38special/.openclaw/openclaw.json.bak"),
]

def create_backup(name: str = None) -> str:
    """Create a timestamped backup of config files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = name or f"backup_{timestamp}"
    backup_path = BACKUP_DIR / backup_name
    backup_path.mkdir(exist_ok=True)
    
    backed_up = []
    
    for target in BACKUP_TARGETS:
        if target.exists():
            dest = backup_path / target.name
            shutil.copy2(target, dest)
            backed_up.append(str(target))
            print(f"✓ Backed up: {target}")
        else:
            print(f"⚠ Skipped (not found): {target}")
    
    # Create manifest
    manifest = {
        "timestamp": timestamp,
        "name": backup_name,
        "files": backed_up,
        "checksums": {}
    }
    
    # Calculate checksums
    for target in BACKUP_TARGETS:
        if target.exists():
            with open(target, 'rb') as f:
                manifest["checksums"][target.name] = hashlib.sha256(f.read()).hexdigest()
    
    # Write manifest
    with open(backup_path / "manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n✅ Backup created: {backup_name}")
    print(f"   Location: {backup_path}")
    
    # Prune old backups (keep last 10)
    prune_old_backups()
    
    return str(backup_path)


def restore_backup(backup_name: str) -> bool:
    """Restore from a named backup."""
    backup_path = BACKUP_DIR / backup_name
    
    if not backup_path.exists():
        print(f"❌ Backup not found: {backup_name}")
        return False
    
    manifest_path = backup_path / "manifest.json"
    if not manifest_path.exists():
        print(f"❌ No manifest in backup: {backup_name}")
        return False
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    # Verify checksums
    for filename, expected_hash in manifest.get("checksums", {}).items():
        filepath = backup_path / filename
        if filepath.exists():
            with open(filepath, 'rb') as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            if actual_hash != expected_hash:
                print(f"❌ Checksum mismatch: {filename}")
                return False
    
    # Restore files
    for target in BACKUP_TARGETS:
        backup_file = backup_path / target.name
        if backup_file.exists():
            shutil.copy2(backup_file, target)
            print(f"✓ Restored: {target}")
    
    print(f"\n✅ Restored from: {backup_name}")
    return True


def list_backups():
    """List available backups."""
    if not BACKUP_DIR.exists():
        print("No backups found.")
        return
    
    backups = sorted(BACKUP_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
    
    print("Available backups:")
    for backup in backups:
        if backup.is_dir():
            manifest_path = backup / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    m = json.load(f)
                    print(f"  {m['name']} — {m['timestamp']}")
            else:
                print(f"  {backup.name}")


def prune_old_backups(keep: int = 10):
    """Remove old backups, keeping only the most recent."""
    backups = sorted(BACKUP_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if len(backups) <= keep:
        return
    
    for old in backups[keep:]:
        shutil.rmtree(old)
        print(f"🗑 Pruned: {old.name}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: config_backup.py [create|restore <name>|list]")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "create":
        create_backup()
    elif action == "restore":
        if len(sys.argv) < 3:
            print("Usage: config_backup.py restore <backup_name>")
            sys.exit(1)
        restore_backup(sys.argv[2])
    elif action == "list":
        list_backups()
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
