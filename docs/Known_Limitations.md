# Known Limitations & What Still Requires Organizational Action

This build is a **functional, working core** of the system described in the
spec — it is deliberately honest about what is fully implemented, what is
architected-for-but-not-wired, and what is intentionally left to your
organization because only you can own it.

## Fully implemented and tested this pass
- AD-pluggable authentication (local demo provider verified end-to-end;
  LDAP/AD provider written with real bind logic, untestable from this
  environment since it needs a live domain controller)
- RBAC with 4 configurable roles / 14 permissions, enforced server-side
- Full storage hierarchy with automatic location-code generation
- Document Master + Copies + prominent location card (Section 13 mock-up)
- Issue / Return / Transfer with immutable history and status guards
- Append-only audit trail with a single write path, verified writing on
  every login, create, issue, return, and transfer
- Dashboard statistics, overdue detection, multi-criteria search
- Full SQL Server DDL for all 25+ tables in the spec, with GRANT/DENY
  guidance for append-only audit protection

## Architected but not yet wired into a UI (straightforward next increment)
- **Excel/CSV data import wizard** (Section 36) — the underlying unique
  constraints and validation model exist; the guided import screen with
  pre-import error preview does not.
- **Report export to Excel/PDF/CSV** (Section 21/37) — `reportlab` and
  `openpyxl` are already dependencies; no export routes are wired yet.
- **QR/barcode generation and scanning** (Section 22) — every location and
  document already has a stable unique code suitable for encoding into a
  QR image; the generation/scanning screens are not built.
- **Account lockout after N failed logins** — failed logins are already
  captured in the audit trail; the lockout counter/threshold enforcement
  is not yet active.
- **Email notifications for overdue documents** — the `Notifications` table
  exists; actual SMTP delivery needs your mail relay details.
- **GMP change-control gate on critical config changes** (Section 27) —
  `ConfigChangeLog` table exists in the schema; the UI workflow requiring
  reason + approval before a critical setting changes is not built.

## Explicitly organizational, not software (Section 31/44)
Per the original spec's own instruction: *"Do not claim that the software
is automatically GMP validated."* The following are yours to own:
- **Computer System Validation** — URS/FRS are provided as a starting
  point; Risk Assessment, IQ/OQ/PQ protocols, and a Traceability Matrix
  still need to be authored and executed against your specific intended
  use, by your validation team, per your CSV SOP.
- **21 CFR Part 11 / Annex 11 applicability determination** — a legal/QA
  risk assessment specific to your regulatory environment, not a software
  feature.
- **Periodic audit-trail review procedure** — the system stores the data;
  the SOP defining who reviews it, how often, and what triggers escalation
  is a QA governance decision.
- **Backup/restore drills, DR runbook execution** — infrastructure/IT
  operational responsibility; a strategy is documented, execution isn't
  something code can perform on your behalf.
- **Emergency local-account password policy and rotation** — must follow
  your existing privileged-account SOP.

## Suggested next increments, in priority order
1. Wire report export routes (fast — reuses existing queries)
2. Build the guided CSV import screen for initial document/location migration
3. Add QR code generation for location codes (a `qrcode` pip package + a
   route that renders the PNG) and a scan-to-search page
4. Add account lockout + password-policy enforcement for emergency accounts
5. Build the GMP change-control approval gate for `SystemConfig` edits
