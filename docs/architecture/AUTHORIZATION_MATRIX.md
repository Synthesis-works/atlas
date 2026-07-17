# Authorization & Permissions Matrix

This document defines the Role-Based Access Control (RBAC) model for Atlas.
It serves as the single source of truth for which roles can perform which actions within an Organization.

## Roles

- **OWNER**: The creator of the organization, or someone explicitly granted full administrative privileges, including destructive actions like deleting the organization.
- **ADMIN**: Can manage projects, settings, and invite users, but cannot delete the organization or transfer ownership.
- **MEMBER**: Can create projects, read datasets, and contribute to evaluations. Cannot manage organization settings or members.
- **VIEWER**: Read-only access to the organization's projects and datasets. Cannot create or modify resources.

## Matrix

| Resource / Endpoint | Action | VIEWER | MEMBER | ADMIN | OWNER |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Organization** | Read Org Details (`GET /organizations/{id}`) | ✅ | ✅ | ✅ | ✅ |
| | Update Org Settings (`PUT /organizations/{id}`) | ❌ | ❌ | ✅ | ✅ |
| | Delete Org (`DELETE /organizations/{id}`) | ❌ | ❌ | ❌ | ✅ |
| **Members & Invites** | List Members (`GET /organizations/{id}/members`) | ✅ | ✅ | ✅ | ✅ |
| | Invite Member (`POST /organizations/{id}/invitations`) | ❌ | ❌ | ✅ | ✅ |
| | Remove Member | ❌ | ❌ | ✅ | ✅ |
| **Projects** | List Projects (`GET /organizations/{id}/projects`) | ✅ | ✅ | ✅ | ✅ |
| | Read Project (`GET /projects/{id}`) | ✅ | ✅ | ✅ | ✅ |
| | Create Project (`POST /organizations/{id}/projects`) | ❌ | ✅ | ✅ | ✅ |
| | Update Project | ❌ | ✅ | ✅ | ✅ |
| | Delete Project | ❌ | ❌ | ✅ | ✅ |

*(Future resources like Datasets, Benchmarks, and Runs will follow a similar pattern, generally mapping Read to Viewer+, Create/Update to Member+, and Delete to Admin+).*

## Implementation Details

- Authentication is verified first via `require_authenticated`.
- Organization boundaries are verified via `require_org_member` dependency which asserts the user's `OrganizationMember` record is `ACTIVE`.
- Endpoints requiring specific roles use `require_role([allowed_roles])` to enforce the matrix above.
- Project-level endpoints (e.g. `/projects/{id}`) use a `ProjectAuthorizationService` to look up the parent `org_id` before verifying membership.
