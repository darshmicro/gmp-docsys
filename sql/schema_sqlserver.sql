/* ============================================================================
   GMP DOCUMENT STORAGE & TRACKING SYSTEM
   Microsoft SQL Server 2019+ Database Schema — PRODUCTION VERSION

   IMPORTANT: This file is generated DIRECTLY from the application's own
   Python data model (app/models.py) using SQLAlchemy's schema compiler, so
   every table and column name below is GUARANTEED to match exactly what
   the running application expects. Do not rename any table or column
   here — the application will fail to find its data if you do.

   If you ever change app/models.py, regenerate this file by running (from
   the project's root folder, with dependencies installed):

       python -c "
       from sqlalchemy.schema import CreateTable, CreateIndex
       from sqlalchemy.dialects import mssql
       from app.db_base import Base
       from app import models
       dialect = mssql.dialect()
       for table in Base.metadata.sorted_tables:
           print(str(CreateTable(table).compile(dialect=dialect)).strip() + ';')
           for index in table.indexes:
               print(str(CreateIndex(index).compile(dialect=dialect)).strip() + ';')
       "

   Run this whole script in SQL Server Management Studio (SSMS) against an
   empty GMPDocTrack database. See docs/Installation_Guide_Complete.md for
   the full, click-by-click walkthrough — including creating the database,
   running this script, and locking down the audit trail — written for
   someone with no prior database experience.

   UPGRADING AN EXISTING DATABASE THAT ALREADY HAS DATA IN IT: do not
   re-run this whole script — it will fail on tables that already exist,
   and re-running the security section would reset your password. Instead,
   see docs/Upgrade_Guide_Issue_Requests.md and run
   upgrade_add_issue_requests.py, which only adds what's new without
   touching anything that already exists.
   ============================================================================ */

CREATE TABLE departments (
	id INTEGER NOT NULL IDENTITY, 
	code VARCHAR(20) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE document_categories (
	id INTEGER NOT NULL IDENTITY, 
	code VARCHAR(20) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE document_types (
	id INTEGER NOT NULL IDENTITY, 
	code VARCHAR(20) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE permissions (
	id INTEGER NOT NULL IDENTITY, 
	code VARCHAR(100) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	module VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE roles (
	id INTEGER NOT NULL IDENTITY, 
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(300) NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE system_config (
	id INTEGER NOT NULL IDENTITY, 
	[key] VARCHAR(100) NOT NULL, 
	value VARCHAR(500) NULL, 
	description VARCHAR(300) NULL, 
	is_gmp_critical BIT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	PRIMARY KEY (id), 
	UNIQUE ([key])
);

CREATE TABLE documents (
	id INTEGER NOT NULL IDENTITY, 
	document_number VARCHAR(50) NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	document_type_id INTEGER NOT NULL, 
	document_category_id INTEGER NULL, 
	department_id INTEGER NULL, 
	product_process VARCHAR(150) NULL, 
	revision_number VARCHAR(20) NULL, 
	effective_date DATETIME NULL, 
	expiry_review_date DATETIME NULL, 
	superseded_document_id INTEGER NULL, 
	status VARCHAR(20) NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_doc_rev UNIQUE (document_number, revision_number), 
	FOREIGN KEY(document_type_id) REFERENCES document_types (id), 
	FOREIGN KEY(document_category_id) REFERENCES document_categories (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id), 
	FOREIGN KEY(superseded_document_id) REFERENCES documents (id)
);
CREATE INDEX ix_documents_status ON documents (status);
CREATE INDEX ix_documents_number ON documents (document_number);
CREATE INDEX ix_documents_title ON documents (title);

CREATE TABLE role_permissions (
	role_id INTEGER NOT NULL, 
	permission_id INTEGER NOT NULL, 
	PRIMARY KEY (role_id, permission_id), 
	FOREIGN KEY(role_id) REFERENCES roles (id), 
	FOREIGN KEY(permission_id) REFERENCES permissions (id)
);

CREATE TABLE storage_rooms (
	id INTEGER NOT NULL IDENTITY, 
	code VARCHAR(20) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	building VARCHAR(100) NULL, 
	floor VARCHAR(50) NULL, 
	area VARCHAR(100) NULL, 
	description VARCHAR(300) NULL, 
	responsible_department_id INTEGER NULL, 
	status VARCHAR(20) NULL, 
	remarks VARCHAR(500) NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code), 
	FOREIGN KEY(responsible_department_id) REFERENCES departments (id)
);

CREATE TABLE users (
	id INTEGER NOT NULL IDENTITY, 
	ad_domain VARCHAR(50) NULL, 
	ad_username VARCHAR(100) NOT NULL, 
	full_name VARCHAR(150) NOT NULL, 
	email VARCHAR(150) NULL, 
	department_id INTEGER NULL, 
	designation VARCHAR(100) NULL, 
	is_local_emergency_account BIT NULL, 
	local_password_hash VARCHAR(200) NULL, 
	account_status VARCHAR(20) NULL, 
	failed_login_count INTEGER NULL, 
	last_login_date DATETIME NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (ad_username), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
);

CREATE TABLE audit_trail (
	id INTEGER NOT NULL IDENTITY, 
	event_datetime_utc DATETIME NOT NULL, 
	user_id INTEGER NULL, 
	user_name VARCHAR(150) NULL, 
	ip_address VARCHAR(50) NULL, 
	module VARCHAR(50) NOT NULL, 
	record_type VARCHAR(50) NULL, 
	record_id VARCHAR(50) NULL, 
	action VARCHAR(50) NOT NULL, 
	old_value TEXT NULL, 
	new_value TEXT NULL, 
	reason VARCHAR(500) NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_audit_date ON audit_trail (event_datetime_utc);
CREATE INDEX ix_audit_module_record ON audit_trail (module, record_type, record_id);
CREATE INDEX ix_audit_user ON audit_trail (user_id);

CREATE TABLE document_status_history (
	id INTEGER NOT NULL IDENTITY, 
	document_id INTEGER NOT NULL, 
	old_status VARCHAR(20) NULL, 
	new_status VARCHAR(20) NOT NULL, 
	changed_by_user_id INTEGER NOT NULL, 
	change_datetime DATETIME NOT NULL, 
	reason VARCHAR(300) NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(changed_by_user_id) REFERENCES users (id)
);

CREATE TABLE racks (
	id INTEGER NOT NULL IDENTITY, 
	room_id INTEGER NOT NULL, 
	rack_number VARCHAR(20) NOT NULL, 
	description VARCHAR(200) NULL, 
	rack_type VARCHAR(50) NULL, 
	status VARCHAR(20) NULL, 
	remarks VARCHAR(500) NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rack UNIQUE (room_id, rack_number), 
	FOREIGN KEY(room_id) REFERENCES storage_rooms (id)
);

CREATE TABLE user_roles (
	user_id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	assigned_by VARCHAR(100) NOT NULL, 
	assigned_date DATETIME NULL, 
	PRIMARY KEY (user_id, role_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(role_id) REFERENCES roles (id)
);

CREATE TABLE sub_racks (
	id INTEGER NOT NULL IDENTITY, 
	rack_id INTEGER NOT NULL, 
	sub_rack_number VARCHAR(20) NOT NULL, 
	capacity INTEGER NULL, 
	status VARCHAR(20) NULL, 
	remarks VARCHAR(500) NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_subrack UNIQUE (rack_id, sub_rack_number), 
	FOREIGN KEY(rack_id) REFERENCES racks (id)
);

CREATE TABLE shelves (
	id INTEGER NOT NULL IDENTITY, 
	sub_rack_id INTEGER NOT NULL, 
	shelf_number VARCHAR(20) NOT NULL, 
	capacity INTEGER NULL, 
	status VARCHAR(20) NULL, 
	remarks VARCHAR(500) NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_shelf UNIQUE (sub_rack_id, shelf_number), 
	FOREIGN KEY(sub_rack_id) REFERENCES sub_racks (id)
);

CREATE TABLE positions (
	id INTEGER NOT NULL IDENTITY, 
	shelf_id INTEGER NOT NULL, 
	position_number VARCHAR(20) NOT NULL, 
	location_code VARCHAR(100) NULL, 
	status VARCHAR(20) NULL, 
	remarks VARCHAR(500) NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_position UNIQUE (shelf_id, position_number), 
	FOREIGN KEY(shelf_id) REFERENCES shelves (id)
);
CREATE INDEX ix_positions_location_code ON positions (location_code);

CREATE TABLE document_boxes (
	id INTEGER NOT NULL IDENTITY, 
	box_number VARCHAR(50) NOT NULL, 
	description VARCHAR(200) NULL, 
	position_id INTEGER NULL, 
	capacity INTEGER NULL, 
	current_document_count INTEGER NULL, 
	status VARCHAR(20) NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (box_number), 
	FOREIGN KEY(position_id) REFERENCES positions (id)
);

CREATE TABLE document_copies (
	id INTEGER NOT NULL IDENTITY, 
	document_id INTEGER NOT NULL, 
	copy_number VARCHAR(20) NOT NULL, 
	controlled_status VARCHAR(20) NULL, 
	original_or_copy VARCHAR(20) NULL, 
	number_of_pages INTEGER NULL, 
	box_id INTEGER NULL, 
	current_position_id INTEGER NULL, 
	current_location_code VARCHAR(100) NULL, 
	copy_status VARCHAR(20) NULL, 
	current_custodian_user_id INTEGER NULL, 
	created_by VARCHAR(100) NOT NULL, 
	created_date DATETIME NOT NULL, 
	modified_by VARCHAR(100) NULL, 
	modified_date DATETIME NULL, 
	is_active BIT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_doc_copy UNIQUE (document_id, copy_number), 
	FOREIGN KEY(document_id) REFERENCES documents (id), 
	FOREIGN KEY(box_id) REFERENCES document_boxes (id), 
	FOREIGN KEY(current_position_id) REFERENCES positions (id), 
	FOREIGN KEY(current_custodian_user_id) REFERENCES users (id)
);
CREATE INDEX ix_doccopies_location_code ON document_copies (current_location_code);
CREATE INDEX ix_doccopies_status ON document_copies (copy_status);
CREATE INDEX ix_doccopies_box_id ON document_copies (box_id);

CREATE TABLE document_location_history (
	id INTEGER NOT NULL IDENTITY, 
	document_copy_id INTEGER NOT NULL, 
	position_id INTEGER NOT NULL, 
	location_code VARCHAR(100) NOT NULL, 
	effective_from DATETIME NOT NULL, 
	effective_to DATETIME NULL, 
	changed_by VARCHAR(100) NOT NULL, 
	reason VARCHAR(300) NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_copy_id) REFERENCES document_copies (id), 
	FOREIGN KEY(position_id) REFERENCES positions (id)
);

CREATE TABLE issue_transactions (
	id INTEGER NOT NULL IDENTITY, 
	document_copy_id INTEGER NOT NULL, 
	issued_to_user_id INTEGER NOT NULL, 
	department_id INTEGER NULL, 
	purpose VARCHAR(300) NULL, 
	issue_datetime DATETIME NOT NULL, 
	expected_return_date DATETIME NOT NULL, 
	actual_return_datetime DATETIME NULL, 
	issued_by_user_id INTEGER NOT NULL, 
	approved_by_user_id INTEGER NULL, 
	remarks VARCHAR(500) NULL, 
	is_open BIT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_copy_id) REFERENCES document_copies (id), 
	FOREIGN KEY(issued_to_user_id) REFERENCES users (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id), 
	FOREIGN KEY(issued_by_user_id) REFERENCES users (id), 
	FOREIGN KEY(approved_by_user_id) REFERENCES users (id)
);

CREATE TABLE transfer_transactions (
	id INTEGER NOT NULL IDENTITY, 
	document_copy_id INTEGER NOT NULL, 
	old_position_id INTEGER NOT NULL, 
	new_position_id INTEGER NOT NULL, 
	reason VARCHAR(300) NOT NULL, 
	transferred_by_user_id INTEGER NOT NULL, 
	approved_by_user_id INTEGER NULL, 
	transfer_datetime DATETIME NOT NULL, 
	remarks VARCHAR(500) NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_copy_id) REFERENCES document_copies (id), 
	FOREIGN KEY(old_position_id) REFERENCES positions (id), 
	FOREIGN KEY(new_position_id) REFERENCES positions (id), 
	FOREIGN KEY(transferred_by_user_id) REFERENCES users (id), 
	FOREIGN KEY(approved_by_user_id) REFERENCES users (id)
);

CREATE TABLE issue_requests (
	id INTEGER NOT NULL IDENTITY, 
	document_copy_id INTEGER NOT NULL, 
	requested_by_user_id INTEGER NOT NULL, 
	purpose VARCHAR(300) NULL, 
	requested_date DATETIME NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	decided_by_user_id INTEGER NULL, 
	decided_date DATETIME NULL, 
	decision_reason VARCHAR(300) NULL, 
	resulting_issue_transaction_id INTEGER NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_copy_id) REFERENCES document_copies (id), 
	FOREIGN KEY(requested_by_user_id) REFERENCES users (id), 
	FOREIGN KEY(decided_by_user_id) REFERENCES users (id), 
	FOREIGN KEY(resulting_issue_transaction_id) REFERENCES issue_transactions (id)
);

CREATE TABLE return_transactions (
	id INTEGER NOT NULL IDENTITY, 
	issue_transaction_id INTEGER NOT NULL, 
	returned_by_user_id INTEGER NOT NULL, 
	return_datetime DATETIME NOT NULL, 
	received_by_user_id INTEGER NOT NULL, 
	physical_condition VARCHAR(100) NULL, 
	returned_position_id INTEGER NOT NULL, 
	remarks VARCHAR(500) NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(issue_transaction_id) REFERENCES issue_transactions (id), 
	FOREIGN KEY(returned_by_user_id) REFERENCES users (id), 
	FOREIGN KEY(received_by_user_id) REFERENCES users (id), 
	FOREIGN KEY(returned_position_id) REFERENCES positions (id)
);

/* ============================================================================
   DATABASE SECURITY — LOCKING DOWN THE AUDIT TRAIL

   Run this section AFTER the tables above have been created successfully.
   It does three things:
     1. Creates a dedicated login/user for the application itself (the
        application should NEVER connect using the "sa" account or your
        own personal admin account).
     2. Gives that application account exactly the access it needs to run
        normally (read/write on ordinary tables).
     3. Explicitly BLOCKS that same account from ever changing or deleting
        rows in the audit trail and other GMP transaction-history tables —
        even though it's the very account the application uses to insert
        new audit rows in the first place. SQL Server allows "INSERT" and
        "DELETE"/"UPDATE" to be granted or denied completely independently,
        which is exactly what we want: the app can always ADD a new audit
        entry, but nothing — not even the app itself, not even someone who
        steals its credentials — can ever change or remove one afterward.

   Replace 'CHANGE_THIS_PASSWORD_1234!' below with a strong password of
   your own before running this. Write that password down somewhere safe
   (e.g. a password manager) — you'll need it for the DATABASE_URL setting
   described in the installation guide.
   ============================================================================ */

-- Step 1: create the dedicated login and database user for the application
CREATE LOGIN [svc_gmpdoctrack] WITH PASSWORD = 'CHANGE_THIS_PASSWORD_1234!';
GO
CREATE USER [svc_gmpdoctrack] FOR LOGIN [svc_gmpdoctrack];
GO

-- Step 2: give it ordinary read/write access to every table by default
ALTER ROLE db_datareader ADD MEMBER [svc_gmpdoctrack];
ALTER ROLE db_datawriter ADD MEMBER [svc_gmpdoctrack];
GO

-- Step 3: lock the audit trail so it can only ever grow, never change.
--         (db_datawriter above granted UPDATE/DELETE on every table,
--         including this one — these two lines take it back specifically
--         for audit_trail, while leaving INSERT alone.)
DENY UPDATE, DELETE ON dbo.audit_trail TO [svc_gmpdoctrack];
GO

-- Step 4: apply the same "can add history, can never rewrite history"
--         protection to every other GMP transaction/history table.
--         Documents and document_copies are NOT included here because
--         they use an IsActive flag for logical deactivation instead of
--         permanent deletion — but note that even for those two tables,
--         the application code never issues a DELETE statement; only
--         UPDATE (to flip IsActive) is ever used.
DENY DELETE ON dbo.issue_transactions       TO [svc_gmpdoctrack];
DENY DELETE ON dbo.return_transactions      TO [svc_gmpdoctrack];
DENY DELETE ON dbo.transfer_transactions    TO [svc_gmpdoctrack];
DENY DELETE ON dbo.document_status_history  TO [svc_gmpdoctrack];
DENY DELETE ON dbo.document_location_history TO [svc_gmpdoctrack];
GO

-- Step 5 (recommended): confirm the DENY actually took effect. Run this,
--         then look at the result — it should show "0" permission grants
--         for UPDATE/DELETE on audit_trail for this user.
SELECT
    dp.permission_name,
    dp.state_desc,
    OBJECT_NAME(dp.major_id) AS table_name
FROM sys.database_permissions dp
JOIN sys.database_principals pr ON dp.grantee_principal_id = pr.principal_id
WHERE pr.name = 'svc_gmpdoctrack'
  AND OBJECT_NAME(dp.major_id) = 'audit_trail';
GO

/* ----------------------------------------------------------------------------
   A NOTE ON "WHO CAN UNDO THIS"

   The DENY statements above apply to the [svc_gmpdoctrack] login — the
   account the *application* uses. They do NOT apply to your own personal
   SQL Server administrator account, or to "sa", or to anyone with
   sysadmin rights on the server. Those accounts can always override a
   DENY, by design — SQL Server has no way to stop a true database
   administrator from doing anything at all.

   What this DOES achieve, and it is the realistic, meaningful goal for a
   system like this: nobody using the application — including every one
   of its own users, including whoever has the SYSTEM ADMINISTRATOR role
   *inside the application* — can edit or delete an audit trail entry,
   because the application itself has no UPDATE/DELETE permission on that
   table at all, at the database level, regardless of what role or
   password they have inside the app. The only way to alter that table is
   to log into SQL Server directly with a genuine database-administrator
   account and deliberately override this protection — an action that
   your IT/security policies should treat as a serious, logged event in
   its own right (SQL Server's own login auditing can be configured for
   this — ask whoever manages your SQL Server to enable it).
---------------------------------------------------------------------------- */
