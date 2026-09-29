#!/usr/bin/env python3
"""
ICVC SNS proposal -> Slack notifier.

Checks the ICVC SNS for proposals newer than the last one we saw and posts
each new one to a Slack channel (via an Incoming Webhook), mentioning the
people listed in SLACK_MENTION_IDS.

Environment variables:
  SLACK_WEBHOOK_URL   (required unless --dry-run)  Slack Incoming Webhook URL
  SLACK_MENTION_IDS   (optional) comma-separated Slack member IDs, e.g. "U01ABC,U02XYZ"

Usage:
  python notify.py             # normal run: post new proposals, update state file
  python notify.py --test      # post the latest proposal once, to check the Slack setup
  python notify.py --dry-run   # print what would be sent, post nothing
No third-party packages needed (Python 3.8+ standard library only).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SNS_ROOT = "nuywj-oaaaa-aaaaq-aadta-cai"  # ICVC root canister
API = f"https://sns-api.internetcomputer.org/api/v1/snses/{SNS_ROOT}/proposals"
NNS_LINK = "https://nns.ic0.app/proposal/?u=" + SNS_ROOT + "&proposal={id}"
STATE_FILE = Path(__file__).parent / "state" / "last_seen.json"
MAX_PER_RUN = 20  # safety cap so a bad state file can't spam the channel


def http_json(url, data=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json", "User-Agent": "icvc-proposal-bot"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode()
        return json.loads(body) if body.strip().startswith(("{", "[")) else body


def fetch_latest(limit=MAX_PER_RUN):
    return http_json(f"{API}?limit={limit}")["data"]  # newest first


def load_last_seen():
    if STATE_FILE.exists():
        return int(json.loads(STATE_FILE.read_text())["last_seen_id"])
    return None


def save_last_seen(pid):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps({"last_seen_id": int(pid)}, indent=2) + "\n")


def fmt_time(ts):
    if not ts:
        return "n/a"
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%a %d %b %Y, %H:%M UTC")


def build_message(p):
    pid = p["id"]
    link = NNS_LINK.format(id=pid)
    title = p.get("proposal_title") or "(no title)"
    kind = (p.get("nervous_system_function") or {}).get("name") or p.get("proposal_action_type", "")
    topic = (p.get("topic_info") or {}).get("name", "")
    deadline = fmt_time(p.get("wait_for_quiet_state_current_deadline_timestamp_seconds"))
    proposer = p.get("proposer", "")
    proposer_short = f"{proposer[:5]}...{proposer[-5:]}" if len(proposer) > 12 else proposer
    summary = (p.get("summary") or "").strip().replace("<br>", "")
    if len(summary) > 500:
        summary = summary[:500].rsplit(" ", 1)[0] + " …"

    ids = [i.strip() for i in os.environ.get("SLACK_MENTION_IDS", "").split(",") if i.strip()]
    mentions = " ".join(f"<@{i}>" for i in ids)

    headline = f"New ICVC proposal #{pid}: {title}"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"{mentions + ' ' if mentions else ''}:ballot_box_with_ballot: *New ICVC proposal*\n*<{link}|#{pid} · {title}>*"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Type*\n{kind}"},
            {"type": "mrkdwn", "text": f"*Topic*\n{topic or 'n/a'}"},
            {"type": "mrkdwn", "text": f"*Voting deadline*\n{deadline}"},
            {"type": "mrkdwn", "text": f"*Proposer neuron*\n`{proposer_short}`"},
        ]},
    ]
    if summary:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f">{summary.replace(chr(10), chr(10) + '>')}"}})
    blocks.append({"type": "actions", "elements": [
        {"type": "button", "text": {"type": "plain_text", "text": "Open in NNS dapp"}, "url": link, "style": "primary"}]})
    return {"text": f"{mentions} {headline} {link}".strip(), "blocks": blocks}


def post(msg, dry_run):
    if dry_run:
        print(json.dumps(msg, indent=2, ensure_ascii=False))
        return
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        sys.exit("ERROR: SLACK_WEBHOOK_URL is not set.")
    resp = http_json(url, msg)
    if resp != "ok":
        sys.exit(f"ERROR: Slack answered: {resp}")


def main():
    dry_run = "--dry-run" in sys.argv
    test = "--test" in sys.argv
    proposals = fetch_latest()
    if not proposals:
        print("No proposals returned by the API.")
        return

    if test:
        post(build_message(proposals[0]), dry_run)
        print(f"Test message sent for proposal #{proposals[0]['id']}.")
        return

    newest_id = int(proposals[0]["id"])
    last_seen = load_last_seen()
    if last_seen is None:
        # First run: remember where we are, don't flood the channel with history.
        save_last_seen(newest_id)
        print(f"Initialised: last_seen_id = {newest_id}. Future proposals will be posted.")
        return

    new = sorted((p for p in proposals if int(p["id"]) > last_seen), key=lambda p: int(p["id"]))
    if not new:
        print(f"No new proposals (latest is #{newest_id}).")
        return

    for p in new:
        post(build_message(p), dry_run)
        print(f"Posted proposal #{p['id']}: {p.get('proposal_title')}")
        if not dry_run:
            save_last_seen(p["id"])  # save after each post so a crash never re-posts


if __name__ == "__main__":
    main()
