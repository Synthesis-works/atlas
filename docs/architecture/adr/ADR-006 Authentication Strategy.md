# ADR 006: Authentication Strategy

## Status
Accepted

## Context
As we build out the Atlas backend (Slice 3), we need to establish the foundations of user identity and authentication. The requirements dictate that we start with local authentication (email/password), implement an ownership and identity model based on Organization Memberships, and ensure that the backend API remains stateless. 

Key decisions must be made regarding:
1. The method of authentication tokenization (Stateful vs. Stateless).
2. The hashing algorithm for passwords.
3. The structure of the identity model encoded in tokens.
4. The immediate vs. future scope (OAuth, Refresh Tokens).

## Decisions

### 1. Stateless Authentication via JWT
We will use **JSON Web Tokens (JWT)** for API authentication.
* **Why JWT?** The Atlas API is designed to be a decoupled backend service consumed by independent frontend clients. Stateless authentication via JWT removes the need for centralized session storage (like Redis), simplifying the initial deployment architecture and scaling seamlessly across horizontally scaled backend instances.
* **Scope in V1:** We will only issue short-lived **Access Tokens**. Refresh tokens introduce stateful tracking and rotation complexity which is deferred to a later iteration (Slice 3C). 
* **No OAuth in V1:** To keep the initial slice lean and focused on domain modeling, we are deferring third-party identity providers (Google, GitHub OAuth). Local username/password registration will be the primary on-ramp.

### 2. Password Hashing with Argon2
We will use **Argon2** via the `pwdlib[argon2]` library for hashing user passwords.
* **Why Argon2?** Argon2 is the winner of the Password Hashing Competition (PHC) and is the current industry standard recommended by OWASP. It provides superior resistance to both GPU-based cracking and side-channel attacks compared to older algorithms like bcrypt or PBKDF2.
* **Why pwdlib?** `pwdlib` is a modern, actively maintained password hashing library recommended by the FastAPI ecosystem, serving as a lightweight successor to `passlib` (which has seen less recent maintenance).

### 3. Membership-Based Identity
Authentication in Atlas is not just about knowing *who* the user is, but *where* they are operating. Because the ownership model places resources under Projects which are owned by Organizations (ADR-005), the user's context is intrinsically tied to their `OrganizationMember` record.
* **Token Claims:** The JWT will contain minimalistic claims:
  * `sub`: The core `User` ID.
  * `membership_id`: The current `OrganizationMember` ID the user is operating under (if applicable).
  * `organization_id`: The organization context.
  * `exp`, `iat`, `jti`: Standard expiration, issuance, and unique token identifiers.
* **Why not shove the whole user object inside the token?** Keeping tokens small reduces HTTP header payload size and ensures that any critical state changes (e.g., getting banned, role demotion) are caught dynamically by the backend, rather than trusting stale data baked into a token.

### 4. Separation of Concerns (AuthService)
Authentication logic (hashing, JWT issuance) will be encapsulated within an `AuthService`.
* **Why?** JWT utilities and cryptographic functions are infrastructure. By injecting an `AuthService` into our FastAPI routers, we decouple the HTTP transport layer from the domain logic of authentication. This makes the system significantly easier to test and maintains the `Router -> Service -> Repository` architectural pattern.

## Consequences
* **Positive:** The system remains entirely stateless and easily scalable. Modern cryptography (Argon2) ensures data security. The `AuthService` abstraction keeps the routing layer clean.
* **Negative:** Without refresh tokens in V1, users will need to log in more frequently if the access token expiration is short. Client applications must handle standard JWT lifecycle management (storing the token, attaching it to the `Authorization` header).
* **Future Work:** We will eventually need to implement token revocation (e.g., a denylist for `jti`), Refresh Tokens, and OAuth integrations.
