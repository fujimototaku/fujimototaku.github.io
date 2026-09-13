#!/usr/bin/env python3
"""Credential-free public scout for Revenue Machine.

Purpose: keep the machine productive even before private API credentials exist.
It only reads public marketplace data, filters for low-competition/high-budget gigs,
and emits a machine-readable shortlist. It never submits proposals or counts
potential value as revenue.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://clawgig.ai/api/v1"
OUT = Path(os.getenv("SCOUT_OUT", "latest_public_scout.json"))
MIN_BUDGET = float(os.getenv("MIN_BUDGET_USDC", "10"))
MAX_COMPETITORS = int(os.getenv("MAX_PROPOSALS", "5"))

HARD_NO = re.compile(
    r"\b(password|credential|seed phrase|private key|kyc|identity verification|"
    r"buy|purchase|send money|transfer funds|bridge|stake|gambl|casino|bet|"
    r"mass dm|mass message|fake review|review bombing|captcha bypass|"
    r"impersonat|phishing|malware|ransomware|exploit production|"
    r"medical diagnosis|legal representation)\b",
    re.I,
)
GOOD_CATS = {"content", "research", "code", "data", "writing", "marketing", "analysis"}


def fetch_gigs() -> list[dict]:
    r = requests.get(
        BASE + "/gigs",
        params={"min_budget": MIN_BUDGET, "sort": "newest", "limit": 50},
        timeout=45,
        headers={"User-Agent": "RevenueMachine-PublicScout/1.0"},
    )
    r.raise_for_status()
    payload = r.json()
    return payload.get("data", []) if isinstance(payload, dict) else []


def score(x: dict) -> tuple[int, list[str]]:
    title = str(x.get("title") or "")
    desc = str(x.get("description") or "")
    deliverables = str(x.get("deliverables") or "")
    text = f"{title}\n{desc}\n{deliverables}"
    budget = float(x.get("budget_usdc") or 0)
    competitors = int(x.get("proposal_count") or 0)
    category = str(x.get("category") or "").lower()
    reasons: list[str] = []
    if HARD_NO.search(text):
        return 0, ["hard-no keyword"]
    if category and category not in GOOD_CATS:
        return 0, [f"unsupported category:{category}"]
    if competitors > MAX_COMPETITORS:
        return 0, [f"competition:{competitors}"]

    s = 55
    if budget >= 100:
        s += 25; reasons.append("budget>=100")
    elif budget >= 50:
        s += 18; reasons.append("budget>=50")
    elif budget >= 25:
        s += 12; reasons.append("budget>=25")
    else:
        s += 5
    if competitors == 0:
        s += 18; reasons.append("0 proposals")
    elif competitors <= 2:
        s += 12; reasons.append("<=2 proposals")
    else:
        s += 5
    if any(k in text.lower() for k in ["api", "python", "script", "research", "analysis", "report", "csv", "json", "automation"]):
        s += 7; reasons.append("AI-friendly deliverable")
    return min(s, 100), reasons


def main() -> None:
    gigs = fetch_gigs()
    rows = []
    for x in gigs:
        s, reasons = score(x)
        if s < 75:
            continue
        rows.append({
            "id": x.get("id"),
            "title": x.get("title"),
            "category": x.get("category"),
            "budget_usdc": float(x.get("budget_usdc") or 0),
            "proposal_count": int(x.get("proposal_count") or 0),
            "max_proposals": x.get("max_proposals"),
            "deadline": x.get("deadline"),
            "score": s,
            "reasons": reasons,
            "description": str(x.get("description") or "")[:1200],
            "deliverables": str(x.get("deliverables") or "")[:1200],
        })
    rows.sort(key=lambda r: (r["score"], r["budget_usdc"], -r["proposal_count"]), reverse=True)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "revenue_usdc": 0,
        "note": "Public scout only. Candidates are not revenue until accepted/paid.",
        "candidate_count": len(rows),
        "top": rows[:15],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
