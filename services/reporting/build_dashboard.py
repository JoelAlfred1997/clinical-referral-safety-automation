#!/usr/bin/env python3
"""Generate the portfolio dashboard (reports/dashboard.html) from the real run.

A single self-contained HTML file — inline CSS, inline SVG charts, every figure
baked in from report_model.build_model() — so it opens offline in any browser and
screenshots cleanly. No JavaScript, no external assets, no network.

    python build_dashboard.py [--out reports/dashboard.html]

ALL DATA IS SYNTHETIC. OpenMRS is a mock EPR/EMR.
"""

from __future__ import annotations

import argparse
import html
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report_model  # noqa: E402

_REPO_ROOT = report_model._REPO_ROOT
DEFAULT_OUT = os.path.join(_REPO_ROOT, "reports", "dashboard.html")

NHS_BLUE = "#005EB8"
INK = "#212B32"
GREEN = "#007F3B"
AMBER = "#D5900A"
RED = "#D5281B"
GREY = "#768692"
OUTCOME_COLOURS = {
    "Created in OpenMRS": GREEN,
    "Rejected at review (no record)": AMBER,
    "Business exception": "#AE2573",
    "System exception": RED,
}
DECISION_COLOURS = {"APPROVE": GREEN, "AMEND": NHS_BLUE, "REJECT": AMBER}


def esc(s) -> str:
    return html.escape(str(s))


def donut(data: list[tuple[str, int, str]], size=210, thick=42) -> str:
    """SVG donut from (label, value, colour) triples."""
    total = sum(v for _, v, _ in data) or 1
    r = (size - thick) / 2
    cx = cy = size / 2
    circ = 2 * math.pi * r
    segs, offset = [], 0.0
    for label, value, colour in data:
        frac = value / total
        dash = frac * circ
        segs.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="none" stroke="{colour}" '
            f'stroke-width="{thick}" stroke-dasharray="{dash:.2f} {circ - dash:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})">'
            f'<title>{esc(label)}: {value}</title></circle>')
        offset += dash
    return (f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
            f'role="img" aria-label="outcomes donut">{"".join(segs)}'
            f'<text x="{cx}" y="{cy-4}" text-anchor="middle" font-size="34" '
            f'font-weight="700" fill="{INK}">{total}</text>'
            f'<text x="{cx}" y="{cy+18}" text-anchor="middle" font-size="12" '
            f'fill="{GREY}">referrals</text></svg>')


def hbars(data: list[tuple[str, int]], colour=NHS_BLUE, width=360, row_h=26) -> str:
    maxv = max((v for _, v in data), default=1) or 1
    rows = []
    label_w, bar_max = 168, width - 168 - 34
    for i, (label, value) in enumerate(data):
        y = i * row_h
        bw = max(2, bar_max * value / maxv)
        rows.append(
            f'<text x="0" y="{y+15}" font-size="12.5" fill="{INK}">{esc(label)}</text>'
            f'<rect x="{label_w}" y="{y+3}" width="{bw:.1f}" height="16" rx="3" fill="{colour}"/>'
            f'<text x="{label_w+bw+6:.1f}" y="{y+15}" font-size="12" font-weight="600" '
            f'fill="{INK}">{value}</text>')
    h = len(data) * row_h
    return (f'<svg viewBox="0 0 {width} {h}" width="100%" height="{h}" '
            f'role="img">{"".join(rows)}</svg>')


def legend(data: list[tuple[str, int, str]]) -> str:
    out = []
    for label, value, colour in data:
        out.append(
            f'<div class="lg"><span class="sw" style="background:{colour}"></span>'
            f'<span class="lglab">{esc(label)}</span><span class="lgval">{value}</span></div>')
    return "".join(out)


def kpi(label, value, sub="", tone="") -> str:
    cls = " kpi-" + tone if tone else ""
    subhtml = f'<div class="kpi-sub">{esc(sub)}</div>' if sub else ""
    return (f'<div class="kpi{cls}"><div class="kpi-val">{esc(value)}</div>'
            f'<div class="kpi-lab">{esc(label)}</div>{subhtml}</div>')


def referral_rows(referrals) -> str:
    out = []
    for r in referrals:
        tone = ("ok" if r["in_openmrs"] else
                "warn" if r["final_status"] == "REVIEW_REJECTED_NO_RECORD" else "err")
        rev = r["reviewer_decision"] or "&mdash;"
        out.append(
            f'<tr><td class="mono">{esc(r["referral_id"])}</td>'
            f'<td>{esc(r["patient_name"])}</td>'
            f'<td>{esc(r["match_result"].replace("_"," ").title())}</td>'
            f'<td>{esc(r["bot_decision"].replace("_"," ").title())}</td>'
            f'<td>{rev}</td>'
            f'<td><span class="pill {tone}">{esc(r["final_label"])}</span></td></tr>')
    return "".join(out)


def build_html(m) -> str:
    k = m["kpis"]
    outcomes = [(lab, val, OUTCOME_COLOURS.get(lab, GREY))
                for lab, val in m["final_status_counts"].items()]
    reviews = [(d, m["review_outcome_counts"].get(d, 0)) for d in ("APPROVE", "AMEND", "REJECT")
               if m["review_outcome_counts"].get(d)]
    safety = sorted(m["safety_catches"].items(), key=lambda x: -x[1])

    cards = (
        kpi("Referrals processed", k["total_referrals"]) +
        kpi("Created in OpenMRS", k["created_in_openmrs"],
            f'{k["auto_created"]} automated + {k["human_approved_created"]} human-approved', "ok") +
        kpi("Routed to human review", k["routed_to_human_review"],
            f'{k["human_in_loop_pct"]}% of all referrals') +
        kpi("Rejected at review", k["rejected_no_record"], "no record created", "warn") +
        kpi("Exceptions", k["exceptions"], "1 business + 1 system", "err") +
        kpi("Unsafe auto-creates", k["auto_created_with_safety_flag"],
            "referrals auto-created despite a safety flag", "ok"))

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clinical Referral Safety Automation - Run Dashboard</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: {INK};
         margin: 0; background: #F0F4F5; }}
  .wrap {{ max-width: 1080px; margin: 0 auto; padding: 28px 24px 48px; }}
  header {{ border-left: 6px solid {NHS_BLUE}; padding: 4px 0 4px 16px; margin-bottom: 6px; }}
  h1 {{ font-size: 23px; margin: 0 0 4px; }}
  .muted {{ color: {GREY}; font-size: 13px; margin: 2px 0; }}
  .banner {{ background: #FFF4D6; border: 1px solid #E8C75A; color: #6B5300; font-size: 12.5px;
            padding: 8px 12px; border-radius: 6px; margin: 14px 0 22px; }}
  .grid-kpi {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
  .kpi {{ background: #fff; border: 1px solid #E1E6E8; border-top: 4px solid {NHS_BLUE};
         border-radius: 8px; padding: 14px 16px; }}
  .kpi-ok {{ border-top-color: {GREEN}; }} .kpi-warn {{ border-top-color: {AMBER}; }}
  .kpi-err {{ border-top-color: {RED}; }}
  .kpi-val {{ font-size: 32px; font-weight: 700; line-height: 1; }}
  .kpi-lab {{ font-size: 13px; color: {INK}; margin-top: 6px; font-weight: 600; }}
  .kpi-sub {{ font-size: 11.5px; color: {GREY}; margin-top: 3px; }}
  .cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 22px; }}
  .card {{ background: #fff; border: 1px solid #E1E6E8; border-radius: 8px; padding: 18px 20px; }}
  .card h2 {{ font-size: 14px; margin: 0 0 14px; text-transform: uppercase;
             letter-spacing: .04em; color: {NHS_BLUE}; }}
  .donut-row {{ display: flex; align-items: center; gap: 18px; }}
  .lg {{ display: flex; align-items: center; gap: 8px; font-size: 12.5px; margin: 5px 0; }}
  .sw {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; }}
  .lglab {{ flex: 1; }} .lgval {{ font-weight: 700; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 22px; background: #fff;
          border: 1px solid #E1E6E8; border-radius: 8px; overflow: hidden; font-size: 12.5px; }}
  th {{ background: {NHS_BLUE}; color: #fff; text-align: left; padding: 9px 11px; font-weight: 600; }}
  td {{ padding: 8px 11px; border-top: 1px solid #EDF1F2; }}
  tr:nth-child(even) td {{ background: #F8FAFB; }}
  .mono {{ font-family: "Cascadia Code", Consolas, monospace; }}
  .pill {{ padding: 2px 9px; border-radius: 11px; font-size: 11px; font-weight: 600;
          color: #fff; white-space: nowrap; }}
  .pill.ok {{ background: {GREEN}; }} .pill.warn {{ background: {AMBER}; }}
  .pill.err {{ background: {RED}; }}
  .foot {{ color: {GREY}; font-size: 11.5px; margin-top: 22px; text-align: center; }}
  @media (max-width: 760px) {{ .cols, .grid-kpi {{ grid-template-columns: 1fr; }} }}
</style></head>
<body><div class="wrap">
  <header>
    <h1>Clinical Referral Safety Automation</h1>
    <div class="muted">End-to-end run report &middot; UiPath REFramework &middot; OpenMRS EMR &middot;
      AI-assisted extraction &middot; human-in-the-loop review</div>
  </header>
  <div class="banner"><strong>Synthetic data only.</strong> OpenMRS is a mock EPR/EMR.
    Figures are generated from the real Phase 8 + Phase 9 run artifacts &mdash; not a live NHS system.</div>

  <div class="grid-kpi">{cards}</div>

  <div class="cols">
    <div class="card"><h2>Final outcomes</h2>
      <div class="donut-row">{donut(outcomes)}<div style="flex:1">{legend(outcomes)}</div></div>
    </div>
    <div class="card"><h2>Human-review decisions ({k["routed_to_human_review"]})</h2>
      {hbars(reviews, colour=NHS_BLUE)}
      <div class="muted" style="margin-top:10px">A clinician&rsquo;s decision changed the outcome of
      every one of these &mdash; {k["human_approved_created"]} approved/amended into OpenMRS,
      {k["rejected_no_record"]} rejected with no record.</div>
    </div>
  </div>

  <div class="card" style="margin-top:18px"><h2>Safety hazards caught &amp; routed to a human</h2>
    {hbars(safety, colour=AMBER, width=520)}
    <div class="muted" style="margin-top:10px"><strong>{k["auto_created_with_safety_flag"]}</strong>
    referrals were auto-created while carrying a safety flag: the bot never makes a risky
    clinical decision &mdash; it routes every flagged case to a human.</div>
  </div>

  <table>
    <thead><tr><th>Referral</th><th>Patient (synthetic)</th><th>Match</th>
      <th>Bot decision</th><th>Reviewer</th><th>Final outcome</th></tr></thead>
    <tbody>{referral_rows(m["referrals"])}</tbody>
  </table>

  <div class="foot">{k["audit_rows"]} append-only audit rows underpin this report
    (who / what / before-after / when / why). Generated by services/reporting/build_dashboard.py.</div>
</div></body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the portfolio dashboard (Phase 10).")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    m = report_model.build_model()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(build_html(m))
    print(f"Wrote {args.out}  ({k_summary(m)})")
    return 0


def k_summary(m) -> str:
    k = m["kpis"]
    return (f'{k["total_referrals"]} referrals, {k["created_in_openmrs"]} created, '
            f'{k["rejected_no_record"]} rejected, {k["exceptions"]} exceptions')


if __name__ == "__main__":
    raise SystemExit(main())
