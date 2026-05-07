# User APIs and role-specific usage

This document describes how to register and authenticate users for the four roles used in the system:

- `student`
- `lecturer`
- `admin`
- `superadmin` (treated similarly to `admin` but has elevated privileges)

Base API variables
- `{{API_URL}}` — your backend base URL (e.g. `http://localhost:8000/api/v1`)

Register
- Endpoint: `POST {{API_URL}}/auth/register`
- Body (JSON):
  - `first_name` (string)
  - `last_name` (string)
  - `email` (string)
  - `password` (string)
  - `role` (string) — one of `student`, `lecturer`, `admin`, `superadmin`

Examples

- Register a student

```json
POST {{API_URL}}/auth/register
{
  "first_name": "Jane",
  "last_name": "Student",
  "email": "jane.student@example.com",
  "password": "supersecret123",
  "role": "student"
}
```

- Register a lecturer

```json
POST {{API_URL}}/auth/register
{
  "first_name": "Dr",
  "last_name": "Lecturer",
  "email": "dr.lecturer@example.com",
  "password": "supersecret123",
  "role": "lecturer"
}
```

- Register an admin (tenant owner)

```json
POST {{API_URL}}/auth/register
{
  "first_name": "Alice",
  "last_name": "Admin",
  "email": "alice.admin@example.com",
  "password": "supersecret123",
  "role": "admin"
}
```

- Register a superadmin (system-level)

```json
POST {{API_URL}}/auth/register
{
  "first_name": "Root",
  "last_name": "Super",
  "email": "root@example.com",
  "password": "supersecret123",
  "role": "superadmin"
}
```

Login
- Endpoint: `POST {{API_URL}}/auth/login`
- Body:
  - `email`, `password`, optional `tenant_id` if multi-tenant
- Response: `{ user: { ... }, tokens: { access_token, refresh_token } }`

Get current user (me)
- Endpoint: `GET {{API_URL}}/auth/me`
- Header: `Authorization: Bearer <access_token>`

Notes on roles
- `admin` users are expected to create and manage a tenant (institution). After registering an `admin` you typically redirect them to the tenant creation flow.
- `lecturer` can create courses and exams within their tenant and grade submissions.
- `student` can enroll and take exams.
- `superadmin` has elevated global permissions (view/manage all tenants and users).

Authorization examples
- Protecting an admin-only endpoint: server middleware checks `current_user.role` equals `UserRole.ADMIN` or `UserRole.SUPERADMIN`.
- Lecturers or admins: check `current_user.role in (UserRole.LECTURER, UserRole.ADMIN)`.

Postman tips
1. Create an environment with `API_URL` and `access_token` variables.
2. Create requests for each register example above.
3. Use the login request to obtain `access_token` and set it as an environment variable.
4. Use `GET {{API_URL}}/auth/me` to confirm the registered user's role in the `user` object.

If you want, I can also generate a Postman collection JSON file you can import directly — I included one in the repository under `postman/UserRoles.postman_collection.json`.
