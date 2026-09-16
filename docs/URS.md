# User Requirements Specification (URS)
## GMP Document Storage & Tracking System

**Document Owner:** Document Cell / Quality Assurance
**Status:** Draft for organizational review — not yet approved/validated

---

## 1. Purpose
Define what the Document Cell needs the system to do so that any GMP document's
physical location, custody, and history can be found in seconds.

## 2. Scope
Intranet-only web application covering: document registration, physical
storage-location management, search, issue/return/transfer of physical
copies, audit trail, dashboards, and reporting. Out of scope: electronic
document content management (this system tracks *physical* documents/copies,
not e-signatures or e-content workflows — that would be a separate
CSV-scope eDMS).

## 3. User Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| UR-01 | User must log in with their corporate AD credentials; system must not store AD passwords | Must |
| UR-02 | User can search a document by number/title/location/status and see its exact physical location within seconds | Must |
| UR-03 | System shows full hierarchy: Room → Rack → Sub-Rack → Shelf → Position | Must |
| UR-04 | System generates a unique, human-readable location code automatically | Must |
| UR-05 | Authorized users can issue a document copy, recording who/why/when/expected return | Must |
| UR-06 | Authorized users can return a document copy; location and status are restored | Must |
| UR-07 | Authorized users can transfer a copy's storage location without losing history | Must |
| UR-08 | Every create/modify/issue/return/transfer/status-change is captured in an audit trail (who, what, when, old→new, reason) | Must |
| UR-09 | Audit trail entries can never be edited or deleted through the application | Must |
| UR-10 | Roles restrict what each user type can do (Sysadmin / Doc Cell Admin / Doc Cell User / Viewer) | Must |
| UR-11 | Dashboard shows document counts by status, storage utilization, and overdue issued documents | Should |
| UR-12 | Reports can be exported to Excel/PDF/CSV | Should |
| UR-13 | System supports QR/barcode scanning of a location or document in the future | Could |
| UR-14 | Excel/CSV import for initial data migration, with duplicate/validation checks | Should |
| UR-15 | All server-side authorization is enforced independent of the UI | Must |

## 4. Assumptions Made (Step 2 gap-fill)
- "Document" in this system refers to the **physical, controlled paper
  copy** and its metadata — not an electronic content repository.
- One organization/site per deployment; multi-site federation is out of
  scope unless raised separately.
- AD group→role mapping will be configured by IT during rollout; no
  self-service role requests are in scope for v1.
- Barcode/QR **generation and scanning UI** is architected for (unique
  location codes exist) but the physical label-printing workflow and
  scanner integration are a Phase 2 item, since they depend on your
  chosen hardware.
- Email notifications for overdue documents require your SMTP relay
  details — the notification *table* and status field exist now; wiring
  actual email delivery is a configuration task at deployment.

## 5. Out of Scope for This Delivery (flagged per Section 44)
- Full IQ/OQ/PQ execution — this is an organizational validation
  activity performed against your SOPs, not something software can
  self-certify.
- Disaster recovery drills / backup job scheduling — infrastructure
  team responsibility; a backup **strategy document** is provided.
- Legal/regulatory sign-off that this system satisfies 21 CFR Part 11
  or Annex 11 for your specific process — that determination requires
  your QA unit's risk assessment against your intended use.
