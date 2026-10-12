#!/usr/bin/env python3
import argparse
import os
import sys
import fnmatch
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------
# EXCLUSION RULES
# ---------------------------------------------------------

EXCLUDE_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".pytest_cache", "dist", "build",
    ".idea", ".vscode", ".tox", ".eggs", "logs", ".turbo", ".playwright"
}

EXCLUDE_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".ico", ".pdf", ".zip", ".gz", ".tar", ".rar",
    ".mp3", ".wav", ".mp4", ".mkv", ".ttf", ".woff",
    ".gitignore", ".pem", ".pyc"
}

EXCLUDE_NAMES = {
    "repo_text_dump.py",
    "repo_dump.txt",
    "instruct_copilot.txt",
    "poetry.lock",
    "LICENSE.md",
    ".gitignore",
    "README.md",
    "package-lock.json",
    "problems.txt",
    "temp_test_result.txt", "lighthouse-report.json"
}

EXCLUDE_GLOBS = {
    "*.min.js",
    "*.bin",
    "*.lockb"
}

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def is_binary(path):
    """Detect binary files safely."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(2048)
            if b"\x00" in chunk:
                return True
    except:
        return True
    return False


def should_skip(dirpath, filename):
    """Determine whether to skip a given file based on extension/name/glob."""
    if filename in EXCLUDE_NAMES:
        return True

    lower = filename.lower()
    if any(fnmatch.fnmatch(lower, g) for g in EXCLUDE_GLOBS):
        return True

    ext = os.path.splitext(lower)[1]
    if ext in EXCLUDE_EXTS:
        return True

    return False


# ---------------------------------------------------------
# FILE PROCESSOR
# ---------------------------------------------------------

def dump_file(task):
    """Read and format a single file for inclusion in the repo dump."""
    dirpath, filename = task
    path = os.path.join(dirpath, filename)

    if is_binary(path):
        return None

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except:
        return None

    rel = os.path.relpath(path)

    # IMPORTANT FIX:
    # Use safe comment boundaries that DO NOT appear inside file content.
    return (
        f"\n# ==== FILE START: {rel} ====\n"
        f"{content}\n"
        f"# ==== FILE END: {rel} ====\n"
    )


# ---------------------------------------------------------
# REPO DUMP ENGINE
# ---------------------------------------------------------

def dump_repo(root, output):
    tasks = []

    # Walk the directory tree
    for dirpath, dirnames, filenames in os.walk(root):
        # Remove excluded dirs
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for f in filenames:
            if should_skip(dirpath, f):
                continue
            tasks.append((dirpath, f))

    results = []

    # Process files concurrently
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(dump_file, t): t for t in tasks}
        for future in as_completed(futures):
            block = future.result()
            if block:
                results.append(block)

    # Write the final dump
    with open(output, "w", encoding="utf-8") as out:
        out.writelines(results)

    print(f"Done. Output: {output}")


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="repo_dump.txt")
    args = parser.parse_args()

    dump_repo(args.root, args.output)


if __name__ == "__main__":
    main()
    
# Test 4