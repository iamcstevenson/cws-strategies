#!/usr/bin/env python3
"""Publish the CWS Strategies one-page site to GitHub Pages.

Run from this folder on your Mac:
    python3 deploy.py                      # first run: creates repo, pushes, turns on Pages
    python3 deploy.py -m "Update services" # later runs: commit + push changes

Needs: git and the GitHub CLI (`brew install gh`, then `gh auth login`).
Edit REPO / DOMAIN below if you want something different.
"""
import argparse, json, subprocess, sys
from pathlib import Path

REPO = "cws-strategies"          # GitHub repo name (public, required for free Pages)
DOMAIN = "cherlynnstevenson.com"  # custom domain; set to "" to use <user>.github.io/cws-strategies
HERE = Path(__file__).resolve().parent


def run(*cmd, check=True, capture=False, input=None):
    r = subprocess.run(cmd, cwd=HERE, text=True, input=input,
                       capture_output=capture or input is not None)
    if check and r.returncode != 0:
        sys.exit(f"Failed: {' '.join(cmd)}\n{(r.stderr or r.stdout or '').strip()}")
    return r


def gh_api(method, path, payload=None, check=True):
    args = ["gh", "api", "-X", method, path, "-H", "Accept: application/vnd.github+json"]
    if payload is not None:
        args += ["--input", "-"]
    return run(*args, check=check, capture=True, input=json.dumps(payload) if payload is not None else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--message", default="Update site")
    msg = ap.parse_args().message

    if run("gh", "auth", "status", check=False, capture=True).returncode != 0:
        sys.exit("GitHub CLI isn't logged in. Run: gh auth login")
    user = run("gh", "api", "user", "--jq", ".login", capture=True).stdout.strip()
    full = f"{user}/{REPO}"

    # Pages files
    (HERE / ".nojekyll").touch()
    cname = HERE / "CNAME"
    if DOMAIN:
        cname.write_text(DOMAIN + "\n")
    elif cname.exists():
        cname.unlink()
    gitignore = HERE / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(".DS_Store\n__pycache__/\n")

    # Local repo
    if not (HERE / ".git").exists():
        run("git", "init", "-b", "main")
    run("git", "add", "-A")
    if run("git", "diff", "--cached", "--quiet", check=False).returncode != 0:
        run("git", "commit", "-m", msg)
        print(f"Committed: {msg}")
    else:
        print("No changes to commit.")

    # Remote repo
    if run("gh", "repo", "view", full, check=False, capture=True).returncode != 0:
        run("gh", "repo", "create", full, "--public", "--source", ".", "--remote", "origin",
            "--description", "CWS Strategies website")
        print(f"Created github.com/{full}")
    elif run("git", "remote", "get-url", "origin", check=False, capture=True).returncode != 0:
        run("git", "remote", "add", "origin", f"https://github.com/{full}.git")
    run("git", "push", "-u", "origin", "main")

    # Turn on Pages (serve from main /), then set the custom domain
    if gh_api("GET", f"repos/{full}/pages", check=False).returncode != 0:
        gh_api("POST", f"repos/{full}/pages", {"source": {"branch": "main", "path": "/"}})
        print("GitHub Pages enabled.")
    if DOMAIN:
        gh_api("PUT", f"repos/{full}/pages", {"cname": DOMAIN})
        # HTTPS can only be enforced after GitHub issues the certificate (DNS must point here first)
        if gh_api("PUT", f"repos/{full}/pages", {"cname": DOMAIN, "https_enforced": True}, check=False).returncode == 0:
            print("HTTPS enforced.")
        else:
            print("HTTPS not enforced yet: point DNS at GitHub, wait for the certificate, then re-run this script.")
        print(f"Live at: https://{DOMAIN}/  (once DNS resolves)")
    else:
        print(f"Live at: https://{user}.github.io/{REPO}/  (allow a minute or two)")


if __name__ == "__main__":
    main()
