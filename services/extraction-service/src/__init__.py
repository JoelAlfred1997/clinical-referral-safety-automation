"""Phase 4 extraction service for the NHS Clinical Referral Safety Automation.

SYNTHETIC DATA ONLY. This package turns a referral document (TXT/PDF) into a
schema-validated extraction JSON: structured fields, completeness, and
confidence. It performs NO patient matching and makes NO clinical/routing
decision -- those are deterministic rules (Phase 5) against OpenMRS (Phase 6).
"""

__version__ = "1.0.0"
