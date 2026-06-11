"""Phase 6 OpenMRS referral workflow for the NHS Clinical Referral Safety Automation.

SYNTHETIC DATA ONLY. This package is the concrete, executable OpenMRS update path
the bot uses once a referral has been DECIDED (Phase 5):

  * ensure the `Referral` encounter type + referral obs concepts exist (idempotent);
  * for an AUTO_CREATE decision, write a Referral encounter + observations via REST
    and verify it by re-reading the record (no log-message-only steps);
  * query a patient's active referrals to drive the live duplicate check;
  * seed pre-existing referrals (e.g. Arthur Reed's active Cardiology referral).

Writes are idempotent (keyed on the referral_id observation), so re-running never
creates a duplicate OpenMRS record.
"""

__version__ = "1.0.0"
