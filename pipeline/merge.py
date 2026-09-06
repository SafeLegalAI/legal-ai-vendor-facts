"""Merge the agents' fact rows into the dataset and patch the SafeLegalAI tool records.

    .venv/bin/python pipeline/merge.py                 # work/agents/*.jsonl → data/facts.jsonl + data/by-tool/<id>.json + CSV/Parquet
    .venv/bin/python pipeline/merge.py --site <path-to-safelegalai-site>   # …and patch src/content/tools/<id>.yaml

Site-patch rules (the record stays the editor's):
- a documented yes/no only ever replaces "unknown"; an existing yes/no is never overwritten (conflicts are listed, not applied)
- lists (dataResidency, models) are filled only when empty
- URLs (trustUrl, privacyUrl, termsUrl, dpaUrl, subprocessorsUrl, pricing.url) are filled only when missing
- `factsAudited` is set to the audit date and one provenance source is appended pointing at the per-tool JSON in this repo
- `verified` is never touched here; validate-content decides that on the site
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work" / "agents"
DATA = ROOT / "data"
GH_RAW = "https://github.com/SafeLegalAI/legal-ai-vendor-facts/blob/main/data/by-tool"

TRI = {"yes": "yes", "no": "no", "true": "yes", "false": "no", True: "yes", False: "no"}
TRI_FIELDS = {
    "security.soc2": ("security", "soc2"),
    "security.iso27001": ("security", "iso27001"),
    "security.iso42001": ("security", "iso42001"),
    "security.hipaa": ("security", "hipaa"),
    "security.no_training_on_customer_data": ("security", "noTrainingOnCustomerData"),
    "security.zero_retention": ("security", "zeroRetention"),
    "security.private_deployment": ("security", "privateDeployment"),
    "security.encryption_at_rest": ("security", "encryptionAtRest"),
    "security.sso_saml": ("security", "sso"),
    "contract.dpa_available": ("security", "dpa"),
    "pricing.free_trial": ("pricing", "freeTrial"),
    "pricing.published": ("pricing", "published"),
}
URL_FIELDS = {  # fact field → where its source_url may fill a missing site URL
    "security.soc2": ("security", "trustUrl"),
    "security.no_training_on_customer_data": ("security", "trustUrl"),
    "contract.dpa_available": ("security", "dpaUrl"),
    "contract.subprocessors_published": ("security", "subprocessorsUrl"),
    "contract.terms_last_updated": ("security", "termsUrl"),
    "contract.privacy_last_updated": ("security", "privacyUrl"),
    "pricing.published": ("pricing", "url"),
}
PRICING_MODEL = {"per-seat": "per-seat", "enterprise": "enterprise", "usage": "usage", "freemium": "freemium", "free": "free", "tiered": "tiered", "not-published": "unknown"}


def read_jsonl(p: Path):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def collect():
    rows = []
    for f in sorted(WORK.glob("b*.jsonl")):
        for r in read_jsonl(f):
            r["_batch"] = f.stem
            rows.append(r)
    by_id = {}
    for r in rows:
        if r["tool_id"] == "legalai-space":  # affiliated product: never audited or compared, by policy
            continue
        by_id[r["fact_id"]] = r
    out = sorted(by_id.values(), key=lambda r: (r["tool_id"], r["field"]))
    for r in out:
        r.pop("_batch", None)
    return out


def write_outputs(rows):
    DATA.mkdir(exist_ok=True)
    (DATA / "by-tool").mkdir(exist_ok=True)
    with (DATA / "facts.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    cols = ["fact_id", "tool_id", "tool_name", "vendor", "field", "value", "status", "quote", "source_url", "archive_url", "fetched_at", "page_dated", "pages_checked", "note"]
    with (DATA / "facts.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: (json.dumps(r.get(c), ensure_ascii=False) if isinstance(r.get(c), (list, dict)) else r.get(c)) for c in cols})
    by_tool = defaultdict(list)
    for r in rows:
        by_tool[r["tool_id"]].append(r)
    for tid, rs in by_tool.items():
        (DATA / "by-tool" / f"{tid}.json").write_text(json.dumps({"tool_id": tid, "tool_name": rs[0]["tool_name"], "vendor": rs[0]["vendor"], "audited": max(r["fetched_at"] for r in rs), "facts": rs}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        import pyarrow as pa, pyarrow.parquet as pq

        simple = [{c: (json.dumps(r.get(c), ensure_ascii=False) if isinstance(r.get(c), (list, dict)) else (None if r.get(c) is None else str(r.get(c)) if c == "value" else r.get(c))) for c in cols} for r in rows]
        pq.write_table(pa.Table.from_pylist(simple), DATA / "facts.parquet", compression="zstd")
    except ImportError:
        pass
    return by_tool


def patch_site(site: Path, by_tool):
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    tools_dir = site / "src" / "content" / "tools"
    report = {"patched": 0, "fields_set": 0, "conflicts": [], "missing_tool": []}
    for tid, facts in sorted(by_tool.items()):
        path = tools_dir / f"{tid}.yaml"
        if not path.exists():
            report["missing_tool"].append(tid)
            continue
        doc = yaml.load(path.read_text(encoding="utf-8"))
        doc.setdefault("security", {})
        doc.setdefault("pricing", {})
        sec, pr = doc["security"], doc["pricing"]
        changed = 0
        audited = max(f["fetched_at"] for f in facts)
        for f in facts:
            field, val, status = f["field"], f.get("value"), f["status"]
            asserted = status in ("stated", "implied") and val not in (None, "", "unknown")
            if field in TRI_FIELDS and asserted:
                block, key = TRI_FIELDS[field]
                new = TRI.get(val.lower() if isinstance(val, str) else val)
                if new:
                    cur = doc[block].get(key, "unknown")
                    if cur == "unknown":
                        doc[block][key] = new
                        changed += 1
                    elif cur != new:
                        report["conflicts"].append({"tool": tid, "field": field, "site": cur, "audit": new, "source": f["source_url"]})
            if field in URL_FIELDS and asserted and f.get("source_url"):
                block, key = URL_FIELDS[field]
                if not doc[block].get(key):
                    doc[block][key] = f["source_url"]
                    changed += 1
            if field == "pricing.model" and asserted and isinstance(val, str):
                m = PRICING_MODEL.get(val.lower())
                if m and pr.get("model", "unknown") == "unknown" and m != "unknown":
                    pr["model"] = m
                    changed += 1
            if field == "pricing.list_price" and asserted and isinstance(val, str) and not pr.get("public"):
                pr["public"] = val
                changed += 1
            if field == "pricing.seat_minimum" and asserted and isinstance(val, str) and not pr.get("seatMinimum"):
                pr["seatMinimum"] = val
                changed += 1
            if field == "pricing.minimum_term" and asserted and isinstance(val, str) and not pr.get("minimumTerm"):
                pr["minimumTerm"] = val
                changed += 1
            if field == "security.data_residency" and asserted and isinstance(val, list) and not sec.get("dataResidency"):
                sec["dataResidency"] = [str(x) for x in val]
                changed += 1
            if field == "contract.model_providers" and asserted and isinstance(val, list) and not doc.get("models"):
                doc["models"] = [str(x) for x in val]
                changed += 1
            if field == "security.breach_notification_hours" and asserted and sec.get("breachNotificationHours") is None:
                digits = re.sub(r"\D", "", str(val))
                if digits:
                    sec["breachNotificationHours"] = int(digits)
                    changed += 1
            for fld, key in (("contract.terms_last_updated", "termsUpdated"), ("contract.privacy_last_updated", "privacyUpdated")):
                if field == fld and asserted and isinstance(val, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", val) and not sec.get(key):
                    sec[key] = val
                    changed += 1
        doc["factsAudited"] = audited
        label = f"SafeLegalAI documentation audit, {audited}: every fact with its quote, source page and archived copy"
        url = f"{GH_RAW}/{tid}.json"
        if not any(s.get("url") == url for s in doc.get("sources", [])):
            doc.setdefault("sources", []).append({"label": label, "url": url})
            changed += 1
        if changed:
            with path.open("w", encoding="utf-8") as fh:
                yaml.dump(doc, fh)
            report["patched"] += 1
            report["fields_set"] += changed
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", type=Path)
    a = ap.parse_args()
    rows = collect()
    by_tool = write_outputs(rows)
    st = defaultdict(int)
    for r in rows:
        st[r["status"]] += 1
    print(json.dumps({"facts": len(rows), "tools": len(by_tool), "by_status": dict(st)}))
    if a.site:
        rep = patch_site(a.site, by_tool)
        print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in rep.items()}))
        (ROOT / "work" / "site-patch-report.json").write_text(json.dumps(rep, indent=1) + "\n")


if __name__ == "__main__":
    main()
