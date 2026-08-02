# ADR-005: Ownership Model

**Status:** Proposed

## Context
As Atlas evolves, it needs a robust way to manage resources, permissions, and collaboration. Initially, users might be mapped directly to organizations or projects. However, a rigid mapping prevents users from participating in multiple organizations (e.g., a personal workspace and a corporate workspace). Additionally, attaching users directly to projects creates complex permission matrices when determining who can access what.

## Decision
We will adopt a hierarchical, role-based ownership model:

1. **Organization as the Root**: Organizations are the top-level entity. They act as the billing and isolation boundary. Includes `slug` and `display_name` for future URL routing.
2. **OrganizationMember for Linking**: Users are never attached directly to an Organization or a Project. Instead, an `OrganizationMember` join entity links a `User` to an `Organization`. This allows a single user to belong to multiple organizations. It includes a `MembershipStatus` (`ACTIVE`, `PENDING`, `SUSPENDED`, `LEFT`).
3. **Roles at the Org Level**: The `OrganizationMember` entity carries a `role` enum (`OWNER`, `ADMIN`, `MEMBER`, `VIEWER`). Permissions cascade downwards.
4. **Projects as Resource Containers**: Organizations own Projects. Projects have a `slug` and must have unique names within an Organization. Projects, in turn, own all domain resources (Datasets, Benchmarks, Executions, Evaluations, Reports). Projects perform *no* authorization checks; they only expose ownership.
5. **Invitations**: Organizations can issue `Invitations` (with `email`, `role`, `status`, `expires_at`, `accepted_at`, `revoked_at`, and `invited_by`) to onboard new users.
6. **Active Organization**: Authentication and session state will eventually carry an `active_membership_id` or `current_org_id` so endpoints implicitly know the user's current context.
7. **Audit Trails**: Ownership metadata (e.g. `created_by`) references `OrganizationMember` rather than `User` to enforce context.

### Schema Blueprint
```text
User
  └─ OrganizationMember (role, status)
       └─ Organization (slug, display_name)
            ├─ Invitation (invited_by, timestamps)
            └─ Project (slug, unique(name, org_id))
                 ├─ Dataset
                 ├─ Benchmark
                 ├─ Execution
                 ├─ Evaluation
                 └─ Report
```

## Consequences
- **Positive:** Clean, cascading permissions. If a user is a Viewer in an Organization, they are a Viewer for all Projects and Datasets within that Organization.
- **Positive:** Multi-tenant ready. Users can seamlessly switch between different organizational contexts without creating multiple accounts.
- **Positive:** Safe migration path. We will stage the migration: 1) introduce `OrganizationMember`, 2) migrate data, 3) remove `User.org_id` in a later slice.
- **Positive:** API route structure becomes highly predictable (e.g., `GET /projects/{id}/datasets`).
- **Negative:** Requires joining through `OrganizationMember` to verify permissions, adding a slight query overhead compared to direct `user_id` foreign keys on every table.

## Alternatives Considered
- **Direct User-to-Project linking:** Rejected because it makes organizational billing and admin oversight nearly impossible to manage cleanly at scale.
- **Granular per-resource permissions (ACLs):** Rejected as premature optimization. Org-level roles are sufficient for v1.0 and easier to reason about.
