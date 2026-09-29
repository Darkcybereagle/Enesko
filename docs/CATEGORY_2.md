# ENESKO Category 2 — Platform & Product Interfaces

**Status:** COMPLETE & FROZEN  
**Release gate:** passed on the local development workflow before Category 3 work.

Category 2 preserves the tested Category 1 domain APIs and adds:

1. Alembic migration baseline and incremental schema changes.
2. JWT authentication with Argon2 password hashing.
3. RBAC for the approved ENESKO staff and tenant roles.
4. Mutation audit logging without request-body/password capture.
5. Customer Web on port 3000.
6. Admin Operations Dashboard on port 3001.
7. Tenant Operations Portal on port 3002.
8. Cross-app backend verification for customer, staff and tenant workflows.
9. Tenant request lifecycle monitoring from receipt through closure.
10. Backend tests and frontend production builds as the release gate.

The interfaces consume the same ENESKO APIs. They do not recreate mall, case, navigation, tenant, activation, cinema or parking business logic.

## Tenant request lifecycle

Tenant operational requests use the unified Case engine and the final Category 2 lifecycle:

```text
OPEN          -> tenant label: Received
IN_PROGRESS   -> tenant label: In progress
RESOLVED      -> tenant label: Resolved
CLOSED        -> tenant label: Closed
```

ENESKO OPS controls the status transition. The Tenant Portal reads the same record and CaseEvent history, refreshes the workspace automatically every eight seconds while open, and displays the current state, lifecycle rail, activity timestamps and lifecycle metrics.

This is near-live application monitoring. Category 3 may later replace polling with push/realtime delivery where justified, without changing the shared case lifecycle.

## Local identity model

Local development uses:

- Staff: `admin@enesko.local` / `EneskoLocal2026!`
- Tenant: `tenant@enesko.local` / `TenantLocal2026!`

The tenant account is attached to an `ENESKO Reference Tenant` workspace only in development. Automated tests use an isolated `Test Tenant`. Neither is presented as authorized ICM tenant data. Production tenant accounts must be provisioned from authorized mall onboarding.

## Category 2 release gate

Category 2 was frozen after the following release gate:

- all backend tests pass;
- all three Next.js workspaces build;
- Customer Web reaches the FastAPI backend;
- Tenant Portal requests enter the unified Case engine;
- ENESKO OPS observes tenant-request counts and queues;
- an OPS status update appears back in the Tenant Portal as Received -> In progress -> Resolved -> Closed;
- tenant accounts remain tenant-scoped;
- staff actions remain protected by RBAC and are recorded in the audit trail where applicable.

Category 2 now receives only bug/security fixes. New product capabilities belong to Category 3 or a later approved roadmap category.
