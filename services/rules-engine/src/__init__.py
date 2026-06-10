"""Phase 5 rules & safety decision engine for the NHS Clinical Referral Safety Automation.

SYNTHETIC DATA ONLY. This package consumes a Phase 4 extraction result, matches
the patient against OpenMRS (or the synthetic-patient seed file for the offline
acceptance gate), applies deterministic clinical-safety rules, and produces a
fully reason-coded routing decision.

It is the layer that OWNS safety: the LLM never reaches here. Rules + human
review decide every safety-sensitive outcome. Every decision carries at least
one reason code, and any safety flag blocks auto-create (risky -> human).
"""

__version__ = "1.0.0"
