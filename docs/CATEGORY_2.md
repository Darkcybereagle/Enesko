# ENESKO Category 2 — Platform & Product Interfaces

Category 2 preserves the tested Category 1 domain APIs and adds:

1. Alembic migration baseline and incremental schema changes.
2. JWT authentication with Argon2 password hashing.
3. RBAC for the approved ENESKO staff and tenant roles.
4. Mutation audit logging without request-body/password capture.
5. Customer Web on port 3000.
6. Admin Operations Dashboard on port 3001.
7. Tenant Operations Portal on port 3002.
8. Cross-app backend verification for customer, staff and tenant workflows.
9. Backend tests and frontend production builds as the release gate.

The interfaces consume the same ENESKO APIs. They do not recreate mall, case, navigation, tenant, activation, cinema or parking business logic.

## Local identity model

Local development uses:

- Staff: `admin@enesko.local` / `EneskoLocal2026!`
- Tenant: `tenant@enesko.local` / `TenantLocal2026!`

The tenant account is attached to an `ENESKO Reference Tenant` workspace only in development. Automated tests use an isolated `Test Tenant`. Neither is presented as authorized ICM tenant data. Production tenant accounts must be provisioned from authorized mall onboarding.

## Category 2 release gate

Before Category 2 is frozen:

- all backend tests must pass;
- all three Next.js workspaces must build;
- Customer Web must reach the FastAPI backend;
- Tenant Portal requests must enter the unified Case engine;
- ENESKO OPS must be able to observe tenant-request counts and queues;
- tenant accounts must remain tenant-scoped;
- staff actions must continue to be protected by RBAC and recorded in the audit trail where applicable.
