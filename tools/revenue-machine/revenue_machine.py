#!/usr/bin/env python3
"""Revenue Machine v1

Autonomous earnings loop focused on machine-verifiable freelance markets.
Primary live adapter: ClawGig REST API.
Human-market bridges: CrowdWorks via ChatGPT Work browser; Upwork via official MCP.

The machine refuses work it cannot finish end-to-end with available tools, and
never treats proposals or theoretical value as revenue. Revenue is recorded only
when a contract is platform-approved / paid.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from openai import OpenAI

BASE = "https://clawgig.ai/api/v1"
DB_PATH = Path(os.getenv("REVENUE_DB", "revenue_machine.sqlite3"))

HARD_NO = re.compile(
    r"\b(password|credential|seed phrase|private key|kyc|identity verification|"
    r"buy|purchase|send money|transfer funds|bridge|stake|gambl|casino|bet|"
    r"mass dm|mass message|fake review|review bombing|captcha bypass|"
    r"impersonat|phishing|malware|ransomware|exploit production|"
    r"medical diagnosis|legal representation)\b",
    re.I,
)

DEFAULT_CATEGORIES = {
    "content", "research", "code", "data", "writing", "marketing", "analysis"
}

@dataclass
class Gig:
    id: str
    title: str
    description: str
    category: str
    budget_usdc: float
    proposal_count: int
    max_proposals: int | None
    skills_required: list[str]
    deliverables: str = ""
    deadline: str | None = None


class Ledger:
    def __init__(self, path: Path = DB_PATH) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS events(
            ts TEXT NOT NULL,
            kind TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            detail TEXT NOT NULL,
            UNIQUE(kind, entity_id)
            )"""
        )
        self.conn.commit()

    def add(self, kind: str, entity_id: str, amount: float, detail: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO events(ts,kind,entity_id,amount,detail) VALUES(?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), kind, entity_id, amount,
             json.dumps(detail, ensure_ascii=False)),
        )
        self.conn.commit()

    def earned(self) -> float:
        row = self.conn.execute("SELECT COALESCE(SUM(amount),0) FROM events WHERE kind='paid'").fetchone()
        return float(row[0] or 0)


class ClawGig:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("CLAWGIG_API_KEY", "").strip()
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "RevenueMachine/1.0"})
        if self.api_key:
            self.s.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        r = self.s.request(method, BASE + path, timeout=45, **kwargs)
        if r.status_code == 409:
            return {"_conflict": True, "status": 409, "text": r.text}
        if not r.ok:
            raise RuntimeError(f"ClawGig {method} {path}: {r.status_code} {r.text[:800]}")
        return r.json() if r.text else {}

    def gigs(self, min_budget: float, limit: int = 50) -> list[Gig]:
        payload = self._request("GET", "/gigs", params={
            "min_budget": min_budget, "sort": "newest", "limit": min(limit, 50)
        })
        out: list[Gig] = []
        for x in payload.get("data", []):
            out.append(Gig(
                id=str(x.get("id", "")), title=str(x.get("title", "")),
                description=str(x.get("description", "")), category=str(x.get("category", "")),
                budget_usdc=float(x.get("budget_usdc") or 0),
                proposal_count=int(x.get("proposal_count") or 0),
                max_proposals=(int(x["max_proposals"]) if x.get("max_proposals") is not None else None),
                skills_required=[str(v) for v in x.get("skills_required", [])],
                deliverables=str(x.get("deliverables") or ""), deadline=x.get("deadline"),
            ))
        return out

    def gig(self, gig_id: str) -> Gig:
        x = self._request("GET", f"/gigs/{gig_id}")
        return Gig(
            id=str(x.get("id", gig_id)), title=str(x.get("title", "")),
            description=str(x.get("description", "")), category=str(x.get("category", "")),
            budget_usdc=float(x.get("budget_usdc") or 0),
            proposal_count=int(x.get("proposal_count") or 0),
            max_proposals=(int(x["max_proposals"]) if x.get("max_proposals") is not None else None),
            skills_required=[str(v) for v in x.get("skills_required", [])],
            deliverables=str(x.get("deliverables") or ""), deadline=x.get("deadline"),
        )

    def readiness(self) -> dict[str, Any]:
        return self._request("GET", "/agents/me/readiness")

    def my_proposals(self) -> list[dict[str, Any]]:
        if not self.api_key:
            return []
        return self._request("GET", "/agents/me/proposals").get("data", [])

    def propose(self, gig_id: str, cover_letter: str, amount: float, hours: float) -> dict[str, Any]:
        return self._request("POST", f"/gigs/{gig_id}/proposals", json={
            "cover_letter": cover_letter[:2000],
            "proposed_amount_usdc": round(max(amount, 0.01), 2),
            "estimated_hours": max(0.1, round(hours, 1)),
        })

    def contracts(self, status: str) -> list[dict[str, Any]]:
        if not self.api_key:
            return []
        return self._request("GET", "/agents/me/contracts", params={"status": status, "limit": 50}).get("data", [])

    def messages(self, contract_id: str) -> list[dict[str, Any]]:
        try:
            payload = self._request("GET", f"/contracts/{contract_id}/messages")
        except RuntimeError:
            return []
        return payload.get("data", payload if isinstance(payload, list) else [])

    def upload_bytes(self, contract_id: str, name: str, data: bytes) -> dict[str, Any]:
        files = {"file": (name, io.BytesIO(data), "text/plain")}
        form = {"bucket": "attachments", "contract_id": contract_id}
        r = self.s.post(BASE + "/upload", files=files, data=form, timeout=90)
        if not r.ok:
            raise RuntimeError(f"ClawGig upload: {r.status_code} {r.text[:800]}")
        return r.json()

    def deliver(self, contract_id: str, notes: str, attachment: dict[str, Any] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"delivery_notes": notes[:5000]}
        if attachment:
            url = attachment.get("url") or attachment.get("public_url") or attachment.get("file_url")
            if url:
                body["attachments"] = [{
                    "url": url, "name": attachment.get("name", "deliverable.txt"),
                    "type": attachment.get("type", "text/plain"),
                    "size": int(attachment.get("size") or 0),
                }]
        return self._request("POST", f"/contracts/{contract_id}/deliver", json=body)


class Brain:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.worker_model = os.getenv("WORKER_MODEL", "gpt-6-astra")
        self.qa_model = os.getenv("QA_MODEL", "gpt-5.6-sol")

    def json_call(self, prompt: str, model: str | None = None) -> dict[str, Any]:
        resp = self.client.responses.create(model=model or self.worker_model, input=prompt)
        text = resp.output_text.strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Model returned non-JSON: {text[:1000]}") from e

    def score(self, gig: Gig) -> dict[str, Any]:
        prompt = f"""You are the gatekeeper of an autonomous revenue agent. Decide whether this gig can be completed end-to-end by an AI agent with Python, public web research, file generation, and code execution, without human meetings, identity tricks, account logins, purchases, payments, private credentials, social spam, or policy violations.

Gig JSON:\n{json.dumps(asdict(gig), ensure_ascii=False)}

Return ONLY JSON with keys: accept (bool), score (0-100), confidence (0-1), estimated_minutes (number), estimated_api_cost_usd (number), reason (string), proposal_angle (string), required_external_actions (array of strings), output_format (one of "text","code","data","other"). Reject if requirements are too ambiguous, private client material is necessary but absent, or the work requires legal/medical/financial decisions. Prefer objectively checkable tasks. Do not exaggerate capability."""
        return self.json_call(prompt, self.qa_model)

    def proposal(self, gig: Gig, assessment: dict[str, Any]) -> dict[str, Any]:
        prompt = f"""Draft a concise truthful proposal for this freelance gig. We use AI/automation tooling openly; do not pretend to be human or claim experience we do not have. Price for winning probability while retaining margin.

Gig: {json.dumps(asdict(gig), ensure_ascii=False)}\nAssessment: {json.dumps(assessment, ensure_ascii=False)}

Return ONLY JSON with cover_letter (20-1200 chars), proposed_amount_usdc (number <= budget), estimated_hours (number). State concrete deliverables and validation steps. Never promise off-platform contact, credentials, purchases, or work outside scope."""
        return self.json_call(prompt, self.worker_model)

    def fulfill(self, gig: Gig, messages: list[dict[str, Any]]) -> dict[str, Any]:
        prompt = f"""Complete this paid freelance task now. Produce a finished deliverable, not a plan. Return only the requested JSON. Do not invent facts requiring inaccessible private data. If the task cannot be completed from supplied information, set ready=false and explain the exact missing input. Never ask for passwords, identity documents, money transfers, or off-platform actions.

Gig: {json.dumps(asdict(gig), ensure_ascii=False)}\nContract messages: {json.dumps(messages[-12:], ensure_ascii=False)}

Return ONLY JSON: ready (bool), delivery_notes (string <=4500 chars), artifact_name (string or null), artifact_content (string or null), self_checks (array of strings), limitations (array of strings). For short prose put the complete result in delivery_notes. For code/data/long output put the complete file in artifact_content."""
        return self.json_call(prompt, self.worker_model)

    def qa(self, gig: Gig, deliverable: dict[str, Any]) -> dict[str, Any]:
        prompt = f"""Act as a strict independent reviewer. Determine if this deliverable fully satisfies the paid gig and is safe to submit. Reject hallucinated citations, missing requirements, boilerplate, placeholders, non-running code, or output depending on unavailable private facts.

Gig: {json.dumps(asdict(gig), ensure_ascii=False)}\nDeliverable: {json.dumps(deliverable, ensure_ascii=False)}

Return ONLY JSON: pass (bool), score (0-100), defects (array of strings), repair_instruction (string). Passing requires score >=90 and no material defects."""
        return self.json_call(prompt, self.qa_model)

    def repair(self, gig: Gig, deliverable: dict[str, Any], qa: dict[str, Any]) -> dict[str, Any]:
        prompt = f"""Repair this freelance deliverable to address every QA defect. Return the complete replacement output, not a diff.\nGig: {json.dumps(asdict(gig), ensure_ascii=False)}\nPrior: {json.dumps(deliverable, ensure_ascii=False)}\nQA: {json.dumps(qa, ensure_ascii=False)}\nReturn ONLY JSON with ready, delivery_notes, artifact_name, artifact_content, self_checks, limitations."""
        return self.json_call(prompt, self.worker_model)


def hard_gate(gig: Gig) -> tuple[bool, str]:
    text = f"{gig.title}\n{gig.description}\n{gig.deliverables}"
    if HARD_NO.search(text):
        return False, "hard-no keyword"
    if gig.category and gig.category.lower() not in DEFAULT_CATEGORIES:
        return False, f"unsupported category: {gig.category}"
    if gig.max_proposals is not None and gig.proposal_count >= gig.max_proposals:
        return False, "proposal cap reached"
    return True, "ok"


def scan_and_bid(live: bool) -> int:
    api, brain, ledger = ClawGig(), Brain(), Ledger()
    min_budget = float(os.getenv("MIN_BUDGET_USDC", "10"))
    max_competitors = int(os.getenv("MAX_PROPOSALS", "5"))
    min_score = int(os.getenv("MIN_SCORE", "86"))
    max_api_cost_ratio = float(os.getenv("MAX_API_COST_RATIO", "0.12"))
    undercut = float(os.getenv("BID_MULTIPLIER", "0.92"))
    proposed_ids = {str(p.get("gig_id")) for p in api.my_proposals()}
    gigs = api.gigs(min_budget=min_budget)
    print(f"scan: {len(gigs)} gigs; live={live}; already_proposed={len(proposed_ids)}")
    submitted = 0
    for gig in gigs:
        if not gig.id or gig.id in proposed_ids:
            continue
        ok, _ = hard_gate(gig)
        if not ok or gig.proposal_count > max_competitors:
            continue
        assessment = brain.score(gig)
        if not assessment.get("accept") or int(assessment.get("score", 0)) < min_score:
            continue
        api_cost = float(assessment.get("estimated_api_cost_usd") or 0)
        if gig.budget_usdc and api_cost / gig.budget_usdc > max_api_cost_ratio:
            continue
        proposal = brain.proposal(gig, assessment)
        proposal["proposed_amount_usdc"] = min(
            float(proposal.get("proposed_amount_usdc") or gig.budget_usdc * undercut),
            gig.budget_usdc * undercut,
        )
        print(json.dumps({"candidate": asdict(gig), "assessment": assessment, "proposal": proposal}, ensure_ascii=False))
        ledger.add("candidate", gig.id, 0, {"gig": asdict(gig), "assessment": assessment})
        if live:
            result = api.propose(gig.id, str(proposal.get("cover_letter", "")),
                                 float(proposal.get("proposed_amount_usdc")),
                                 float(proposal.get("estimated_hours") or 1))
            if not result.get("_conflict"):
                ledger.add("proposed", gig.id, 0, result)
                submitted += 1
    return submitted


def process_funded(live: bool) -> int:
    api, brain, ledger = ClawGig(), Brain(), Ledger()
    contracts = api.contracts("funded")
    print(f"funded contracts: {len(contracts)}; live={live}")
    delivered = 0
    for c in contracts:
        cid, gid = str(c.get("id", "")), str(c.get("gig_id", ""))
        if not cid or not gid:
            continue
        gig = api.gig(gid)
        ok, why = hard_gate(gig)
        if not ok:
            print(f"hold {cid}: {why}")
            continue
        out = brain.fulfill(gig, api.messages(cid))
        if not out.get("ready"):
            print(f"hold {cid}: missing input: {out.get('limitations')}")
            continue
        qa = brain.qa(gig, out)
        if not qa.get("pass") or int(qa.get("score", 0)) < 90:
            out = brain.repair(gig, out, qa)
            qa = brain.qa(gig, out)
        if not qa.get("pass") or int(qa.get("score", 0)) < 90:
            print(f"hold {cid}: QA failed: {qa.get('defects')}")
            continue
        attachment = None
        if out.get("artifact_content"):
            name = str(out.get("artifact_name") or f"deliverable-{cid}.txt")
            data = str(out["artifact_content"]).encode("utf-8")
            if live:
                attachment = api.upload_bytes(cid, name, data)
                attachment.setdefault("name", name)
                attachment.setdefault("size", len(data))
            else:
                print(f"dry artifact {name}: {len(data)} bytes")
        print(json.dumps({"contract": cid, "gig": gig.title, "qa": qa, "delivery": out}, ensure_ascii=False))
        if live:
            result = api.deliver(cid, str(out.get("delivery_notes") or "Completed."), attachment)
            ledger.add("delivered", cid, 0, result)
            delivered += 1
    return delivered


def sync_paid() -> float:
    api, ledger = ClawGig(), Ledger()
    for c in api.contracts("approved"):
        cid = str(c.get("id", ""))
        gross = float(c.get("amount_usdc") or 0)
        net = round(gross * 0.90, 6)
        if cid:
            ledger.add("paid", cid, net, c)
    total = ledger.earned()
    print(f"confirmed earned (net est., approved contracts): ${total:.6f} USDC")
    return total


def status() -> int:
    api = ClawGig()
    if not api.api_key:
        print("CLAWGIG_API_KEY missing")
        return 2
    ready = api.readiness()
    print(json.dumps(ready, ensure_ascii=False, indent=2))
    return 0 if ready.get("ready") else 3


def cycle(live_bid: bool, live_delivery: bool) -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required")
    if not os.getenv("CLAWGIG_API_KEY"):
        raise SystemExit("CLAWGIG_API_KEY is required")
    sync_paid()
    scan_and_bid(live_bid)
    process_funded(live_delivery)
    sync_paid()


def main() -> int:
    p = argparse.ArgumentParser(description="Autonomous revenue machine")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status"); sub.add_parser("scan"); sub.add_parser("fulfill"); sub.add_parser("paid")
    cyc = sub.add_parser("cycle")
    cyc.add_argument("--live-bid", action="store_true")
    cyc.add_argument("--live-delivery", action="store_true")
    args = p.parse_args()
    if args.cmd == "status": return status()
    if args.cmd == "scan": scan_and_bid(False)
    elif args.cmd == "fulfill": process_funded(False)
    elif args.cmd == "paid": sync_paid()
    elif args.cmd == "cycle": cycle(args.live_bid, args.live_delivery)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
