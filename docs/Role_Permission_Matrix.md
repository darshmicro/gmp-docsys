# Role / Permission Matrix

Configured in `app/seed.py` (`ROLE_PERMS`) and stored in the
`Roles` / `Permissions` / `RolePermissions` tables — editable at runtime
by a Sysadmin via the Administration module, never hard-coded in route logic.

| Permission Code | Description | System Admin | Doc Cell Admin | Doc Cell User | Viewer |
|---|---|:---:|:---:|:---:|:---:|
| DOC_VIEW | View documents | ✅ | ✅ | ✅ | ✅ |
| DOC_CREATE | Register documents | ✅ | ✅ | ❌ | ❌ |
| DOC_EDIT | Edit document master data | ✅ | ✅ | ❌ | ❌ |
| DOC_ISSUE | Issue documents | ✅ | ✅ | ✅ | ❌ |
| DOC_RETURN | Return documents | ✅ | ✅ | ✅ | ❌ |
| DOC_TRANSFER | Transfer document location | ✅ | ✅ | ❌ | ❌ |
| DOC_STATUS_CHANGE | Change document status | ✅ | ✅ | ❌ | ❌ |
| MASTER_VIEW | View master data | ✅ | ✅ | ✅ | ✅ |
| MASTER_EDIT | Edit storage hierarchy / types / depts | ✅ | ✅ | ❌ | ❌ |
| SEARCH | Search documents | ✅ | ✅ | ✅ | ✅ |
| REPORTS_VIEW | View / export reports | ✅ | ✅ | ✅ | ❌ |
| AUDIT_VIEW | View audit trail | ✅ | ❌ | ❌ | ❌ |
| USER_MANAGE | Manage users and roles | ✅ | ❌ | ❌ | ❌ |
| CONFIG_MANAGE | Manage system configuration | ✅ | ❌ | ❌ | ❌ |

**Notes**
- Audit-trail visibility is deliberately restricted to System Administrator
  only in this default matrix — adjust per your organization's SOP if QA
  leadership also needs direct access; it's a one-row change in
  `RolePermissions`, no code change required.
- No role can edit or delete an `AuditTrail` row — that capability does not
  exist in the application at any permission level (see FRS Section 6).
- AD security groups can be mapped 1:1 to these roles via the
  `ADGroupRoleMapping` table once AD integration is switched on
  (`AUTH_MODE=AD`), so role assignment can be driven centrally from AD
  group membership instead of per-user in this app.
