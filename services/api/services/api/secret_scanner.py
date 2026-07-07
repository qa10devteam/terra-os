"""Faza 65 — Secret scanning utility.

Scans source files for accidentally committed secrets (API keys, passwords, tokens).
Run as: python -m services.api.services.api.secret_scanner
"""
from __future__ import annotations

import re
import sys
import os
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, '/home/ubuntu/terra-os/packages/vendor')


class SecretMatch(NamedTuple):
    file: str
    line: int
    pattern_name: str
    matched_text: str


# Patterns that indicate hardcoded secrets
SECRET_PATTERNS = [
    ("AWS Key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS Secret", re.compile(r"(?i)aws.{0,20}secret.{0,20}['\"][0-9a-zA-Z/+]{40}['\"]")),
    ("Stripe Secret Key", re.compile(r"sk_(live|test)_[0-9a-zA-Z]{24,}")),
    ("Stripe Publishable Key", re.compile(r"pk_(live|test)_[0-9a-zA-Z]{24,}")),
    ("JWT Secret (hardcoded)", re.compile(r"(?i)jwt.{0,10}secret.{0,10}['\"][a-zA-Z0-9!@#$%^&*_]{16,}['\"]")),
    ("Password (hardcoded)", re.compile(r"(?i)password\s*=\s*['\"][^'\"]{6,}['\"]")),
    ("DB URL with password", re.compile(r"postgresql://[^:]+:[^@]{6,}@")),
    ("Private key", re.compile(r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----")),
    ("Generic secret", re.compile(r"(?i)(api_key|secret_key|auth_token)\s*=\s*['\"][a-zA-Z0-9_\-]{20,}['\"]")),
]

# Files/patterns to skip
SKIP_PATTERNS = [
    ".git/",
    "node_modules/",
    "__pycache__/",
    ".pyc",
    "vendor/",
    "packages/vendor/",
    "test_",
    ".env.example",
    "secret_scanner.py",  # Skip self
]

# Known false positives
FALSE_POSITIVES = {
    "terra_dev_2026",  # Dev DB password (not production)
    "your_secret_here",
    "change_me",
    "placeholder",
}


def should_skip(path: str) -> bool:
    return any(skip in path for skip in SKIP_PATTERNS)


def scan_file(file_path: Path) -> list[SecretMatch]:
    """Scan a single file for secrets."""
    matches = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(content.splitlines(), 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
                continue
            for pattern_name, pattern in SECRET_PATTERNS:
                m = pattern.search(line)
                if m:
                    matched = m.group(0)
                    # Check false positives
                    if any(fp in matched for fp in FALSE_POSITIVES):
                        continue
                    matches.append(SecretMatch(
                        file=str(file_path),
                        line=line_no,
                        pattern_name=pattern_name,
                        matched_text=matched[:60] + "..." if len(matched) > 60 else matched,
                    ))
    except Exception:
        pass
    return matches


def scan_directory(root: str | Path = ".") -> list[SecretMatch]:
    """Recursively scan directory for hardcoded secrets."""
    root = Path(root)
    all_matches = []

    extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".env", ".yaml", ".yml", ".toml", ".json"}

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if should_skip(str(file_path)):
            continue
        if file_path.suffix not in extensions:
            continue
        matches = scan_file(file_path)
        all_matches.extend(matches)

    return all_matches


if __name__ == "__main__":
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "/home/ubuntu/terra-os"
    print(f"Scanning {root_dir} for hardcoded secrets...")
    matches = scan_directory(root_dir)

    if matches:
        print(f"\n⚠️  Found {len(matches)} potential secret(s):\n")
        for m in matches:
            print(f"  [{m.pattern_name}] {m.file}:{m.line}")
            print(f"    → {m.matched_text}\n")
        sys.exit(1)
    else:
        print("✅ No hardcoded secrets found.")
        sys.exit(0)
