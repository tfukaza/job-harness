"""Collect the user's own writing, locally, so an agent can learn their voice (see the write-answers skill).

Sources (configured in main/voice.yaml, template main/voice.example.yaml):
  - messages the user typed to coding agents (Claude Code transcripts in ~/.claude/projects)
  - prose and commit messages in their repos that they wrote themselves (no AI co-author trailer)
  - extra files they point to (past cover letters, essays, posts)
  - their resume bullets (formal register)
Output: main/voice/samples.md (gitignored). Plain parsing only, no model calls, nothing leaves the machine.
"""
import json
import subprocess
from pathlib import Path

import yaml

from . import ROOT

CFG = ROOT / "main" / "voice.yaml"
OUT = ROOT / "main" / "voice" / "samples.md"
TRANSCRIPTS = Path.home() / ".claude" / "projects"
AI_TRAILERS = ("co-authored-by: claude", "generated with [claude", "co-authored-by: codex", "co-authored-by: cursor")
SKIP_PREFIXES = ("<", "This session is being continued", "Caveat:", "[Request interrupted", "Base directory for this skill")


def _cfg() -> dict:
    d = yaml.safe_load(CFG.read_text()) if CFG.exists() else {}
    return {"transcripts": True, "repos": [], "extra_files": [], "max_chat": 300, "min_words": 6, "prose_before": "2023-01-01", "git_authors": [], **(d or {})}


def _user_texts(rec: dict) -> list[str]:
    """Text the human typed in one transcript record (not tool results, reminders, or command output)."""
    if rec.get("type") != "user" or rec.get("isMeta") or rec.get("isSidechain"):
        return []
    msg = rec.get("message") or {}
    c = msg.get("content")
    if isinstance(c, str):
        parts = [c]
    elif isinstance(c, list):
        if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
            return []
        parts = [x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"]
    else:
        return []
    out = []
    for p in parts:
        p = p.strip()
        if not p or p.startswith(SKIP_PREFIXES) or "<system-reminder>" in p or "<pasted_content" in p:
            continue
        out.append(p)
    return out


def chats(cfg: dict) -> list[tuple[str, str, str]]:
    """(timestamp, project, text), newest first, deduped."""
    seen, rows = set(), []
    if not TRANSCRIPTS.exists():
        return rows
    for f in TRANSCRIPTS.glob("*/*.jsonl"):
        project = f.parent.name.replace("-Users-", "").split("-code-")[-1]
        for line in f.open(errors="ignore"):
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            for t in _user_texts(rec):
                key = " ".join(t.split()).lower()
                if key in seen or len(t.split()) < cfg["min_words"]:
                    continue
                seen.add(key)
                rows.append((rec.get("timestamp", ""), project, t))
    rows.sort(reverse=True)
    return rows[: cfg["max_chat"]]


def _git(repo: Path, *args) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def repo_prose(repo: Path, before: str, authors: list[str]) -> list[str]:
    """Commit messages and docs from before `before` (pre AI coding tools), so the words are the user's own.
    Commits with an AI co-author trailer are excluded too. Docs are read as they were at that date."""
    out = []
    if not (repo / ".git").exists():
        return out
    log = _git(repo, "log", "--no-merges", f"--before={before}", *[f"--author={x}" for x in authors],
               "--format=%x1e%B")
    for body in log.split("\x1e"):
        body = body.strip()
        if len(body.split()) >= 4 and not any(t in body.lower() for t in AI_TRAILERS):
            out.append(f"[commit {repo.name}] {body}")
    rev = _git(repo, "rev-list", "-1", f"--before={before}", "HEAD").strip()
    if rev:
        for path in _git(repo, "ls-tree", "-r", "--name-only", rev).split("\n"):
            if path.endswith(".md") and "node_modules" not in path and path.count("/") <= 2:
                text = _git(repo, "show", f"{rev}:{path}").strip()
                if len(text.split()) >= 30:
                    out.append(f"[{repo.name}/{path} as of {before}]\n{text[:4000]}")
    return out


def resume_bullets() -> list[str]:
    main = yaml.safe_load((ROOT / "main" / "main.yaml").read_text()) or {}
    out = []

    def walk(n):
        if isinstance(n, dict):
            if "text" in n and "id" in n:
                out.append(n["text"])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(main)
    return out


def collect() -> dict:
    cfg = _cfg()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    chat = chats(cfg) if cfg["transcripts"] else []
    prose = []
    for r in cfg["repos"]:
        prose += repo_prose(Path(r).expanduser(), str(cfg["prose_before"]), cfg["git_authors"])
    extra = []
    for f in cfg["extra_files"]:
        p = Path(f).expanduser()
        if p.exists():
            extra.append(f"[{p.name}]\n{p.read_text(errors='ignore')[:6000]}")
    bullets = resume_bullets()
    lines = ["# Writing samples (local, gitignored). Source material for main/voice.md.", "",
             f"## Messages typed to coding agents ({len(chat)}, newest first)", ""]
    lines += [f"- ({ts[:10]}, {proj}) {t}" for ts, proj, t in chat]
    lines += ["", f"## Own prose: commits and docs from before {cfg['prose_before']} ({len(prose)})", ""] + prose
    lines += ["", f"## Extra files ({len(extra)})", ""] + extra
    lines += ["", f"## Resume bullets, formal register ({len(bullets)})", ""] + [f"- {b}" for b in bullets]
    OUT.write_text("\n".join(lines) + "\n")
    return {"chat": len(chat), "prose": len(prose), "extra": len(extra), "bullets": len(bullets), "out": str(OUT)}
