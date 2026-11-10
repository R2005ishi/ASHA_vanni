"""Measure accuracy end to end against a running server.

    python eval/run_eval.py                       # uses eval/audio/<id>.wav and <id>__noisy.wav
    python eval/run_eval.py --text                # skip audio: tests extraction + rules only (no STT credits)
    python eval/run_eval.py --server http://localhost:8000

Prints: field-level accuracy, danger-flag recall/precision, average latency,
split by language and clean vs noisy. Writes eval/report.csv.
These are the numbers for your post: measure, don't guess.
"""
import argparse
import csv
import json
import time
from collections import defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent


def close(a, b):
    if isinstance(b, float) or isinstance(a, float):
        return a is not None and abs(float(a) - float(b)) < 0.05
    if isinstance(b, list):
        return sorted(a or []) == sorted(b)
    return a == b


def run(server: str, text_only: bool):
    cases = [json.loads(l) for l in (ROOT / "testset.jsonl").read_text().splitlines() if l.strip()]
    rows, agg = [], defaultdict(lambda: {"fields": 0, "correct": 0, "tp": 0, "fn": 0, "fp": 0, "n": 0, "secs": 0.0})
    with httpx.Client(timeout=120) as c:
        for case in cases:
            variants = [("typed", None)] if text_only else [
                (v, ROOT / "audio" / f"{case['id']}{suffix}.wav")
                for v, suffix in (("clean", ""), ("noisy", "__noisy"))]
            for variant, path in variants:
                if path is not None and not path.exists():
                    continue
                data = {"visit_type": case["visit_type"], "lang": case["lang"],
                        "asha_id": f"asha_{case['lang']}_01"}
                files = None
                if path is None:
                    data["mock_text"] = case["text"]
                else:
                    files = {"audio": (path.name, path.read_bytes(), "audio/wav")}
                t0 = time.time()
                r = c.post(f"{server}/api/visits", data=data, files=files)
                secs = time.time() - t0
                r.raise_for_status()
                body = r.json()
                v = body["visit"]
                c.post(f"{server}/api/visits/{v['id']}/discard")   # keep eval runs out of the dashboard
                rec, got_flags = v["record"], {f["code"] for f in v["flags"]}
                want_flags = set(case.get("expected_flags", []))
                wrong = {k: (rec.get(k), exp) for k, exp in case["expected"].items() if not close(rec.get(k), exp)}
                key = f"{case['lang']}/{variant}"
                a = agg[key]
                a["n"] += 1
                a["fields"] += len(case["expected"])
                a["correct"] += len(case["expected"]) - len(wrong)
                a["tp"] += len(got_flags & want_flags)
                a["fn"] += len(want_flags - got_flags)
                a["fp"] += len(got_flags - want_flags)
                a["secs"] += secs
                rows.append({"id": case["id"], "variant": variant, "transcript": v["transcript"],
                             "wrong_fields": json.dumps(wrong, ensure_ascii=False),
                             "missed_flags": ",".join(want_flags - got_flags),
                             "extra_flags": ",".join(got_flags - want_flags),
                             "engine": v["engine"], "seconds": round(secs, 2)})

    print(f"\n{'group':<14}{'clips':>6}{'field acc':>11}{'flag recall':>13}{'flag prec':>11}{'avg s':>8}")
    for k, a in sorted(agg.items()):
        rec = a["tp"] / (a["tp"] + a["fn"]) if a["tp"] + a["fn"] else 1
        prec = a["tp"] / (a["tp"] + a["fp"]) if a["tp"] + a["fp"] else 1
        print(f"{k:<14}{a['n']:>6}{a['correct'] / a['fields']:>10.0%}{rec:>13.0%}{prec:>11.0%}{a['secs'] / a['n']:>8.2f}")
    with (ROOT / "report.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nPer-clip details: {ROOT / 'report.csv'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://localhost:8000")
    ap.add_argument("--text", action="store_true", help="send the text instead of audio")
    args = ap.parse_args()
    run(args.server, args.text)
