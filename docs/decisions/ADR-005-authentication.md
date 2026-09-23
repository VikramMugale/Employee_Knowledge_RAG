# ADR-005: Authentication & ABAC/RBAC Authorization Architecture

## Status
Accepted (supersedes Microsoft Entra / OIDC SSO)

## Context
Employee policy information access depends on employee role, department, employment status, and location. Unauthorized personnel must never retrieve confidential executive or HR documents.

## Decision
Issue and verify locally signed JWTs with **PyJWT (HS256)**. Clients authenticate with email/password against `POST /api/v1/auth/login` and send `Authorization: Bearer <jwt>` on subsequent requests. Microsoft SSO / Entra ID is not used.

## Rationale
- PyJWT verifies signature, expiry, issuer, and audience on every request.
- Two roles only: `EMPLOYEE` (ask + read public policies) and `ADMIN` (seed, evaluate, analytics, unrestricted retrieval).
- Attributes (`department`, `location`, `employment_type`, `access_levels`) stay on the JWT for later document ACLs, but they do not create extra roles.
- **Security Invariant**: ACL filtering occurs at retrieval time before candidates are returned or sent to the LLM.
