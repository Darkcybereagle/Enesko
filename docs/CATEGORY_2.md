# ENESKO Category 2 — Platform & Product Interfaces

Category 2 preserves the tested Category 1 domain APIs and adds:

1. Alembic migration baseline and PostgreSQL-ready configuration.
2. JWT authentication with Argon2 password hashing.
3. RBAC for the approved ENESKO staff and tenant roles.
4. Mutation audit logging without request-body/password capture.
5. Customer Web on port 3000.
6. Admin Dashboard on port 3001.
7. Tenant Portal on port 3002.
8. Backend tests and frontend production builds as the release gate.

The interfaces consume the existing ENESKO APIs. They do not recreate mall, case, navigation, tenant, activation, cinema or parking business logic.

Development credentials are demo-only. Change JWT_SECRET and DEMO_ADMIN_PASSWORD before any production deployment.
