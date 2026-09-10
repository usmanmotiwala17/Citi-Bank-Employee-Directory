# Employee Directory Service

Lambda-backed CRUD API for employees and departments, with JWT auth and
role-based permissions. See [function.py](function.py) for routes,
[postgres_service.py](postgres_service.py) for the DB layer, and
[auth_service.py](auth_service.py) for auth.

## Roles

Three roles, replacing the old `admin`/`manager`/`employee` model with a
Citi-style, department-scoped hierarchy. Viewing and managing are scoped
differently: **every** authenticated employee can view **every** other
employee's profile, company-wide, read-only - only *managing* (editing
someone else, deactivating them) is scoped by role:

| Role       | Can manage (edit/deactivate) |
|------------|--------|
| `ADMIN`    | Anyone, and the only role that can create employees/departments. |
| `MANAGER`  | Employees within their own department only. |
| `EMPLOYEE` | No one but themselves (skills/availability only - phone goes through a change request). |

`manager_notes` is the one field that isn't universally viewable: it's
restricted to the ADMIN and the subject's own direct manager, and is never
included in a response served to the employee it's about (see below).

The JWT issued at login carries both `role` and `department_id` (`null` for
Admins, since they aren't scoped to one department), and both are re-checked
against the database on every request - so changing someone's role or
department invalidates their existing token immediately.

There is only ever one active Admin at a time - creating or promoting a
second one is rejected with a 400.

## Other employee fields

- `manager_notes` - free-text notes visible/editable only by the Admin and
  the employee's direct manager. It's omitted entirely from any response
  served to the employee it's about (rather than sent blank), and self-
  service updates can never touch it.
- `availability_status` - `"available"` or `"unavailable"`, defaults to
  `"available"`. Anyone can edit their own, and no one else's.

`GET /employees/{id}` also returns `manager` (brief info on who this
person reports to, if anyone) and, for a `MANAGER`, `direct_reports` (brief
info on everyone reporting to them) - used to render org structure on the
frontend's profile pages.

## Seeding sample data

[seed_data.py](seed_data.py) creates 3 departments (Banking & Finance,
Technology & Operations, HR), one manager per department, and 13 employees -
17 people total (1 ADMIN, 3 MANAGER, 13 EMPLOYEE). Each employee's
`manager_id` is set to their department's manager, so the reporting line is
actually wired up rather than left blank:

```sh
python3 seed_data.py
```

| Name | Email | Role | Department | Job Title | Reports To |
|------|-------|------|------------|-----------|------------|
| Robert Chen | robert.chen@acme.com | ADMIN | — | Chief Executive Officer | — |
| Sarah Johnson | sarah.johnson@acme.com | MANAGER | Banking & Finance | Banking & Finance Manager | — |
| Emily Davis | emily.davis@acme.com | MANAGER | Technology & Operations | Technology & Operations Manager | — |
| Patricia Garcia | patricia.garcia@acme.com | MANAGER | HR | HR Manager | — |
| Michael Brown | michael.brown@acme.com | EMPLOYEE | Banking & Finance | Financial Analyst | Sarah Johnson |
| Carol White | carol.white@acme.com | EMPLOYEE | Banking & Finance | Loan Officer | Sarah Johnson |
| Kevin Lee | kevin.lee@acme.com | EMPLOYEE | Banking & Finance | Financial Analyst | Sarah Johnson |
| Nancy Clark | nancy.clark@acme.com | EMPLOYEE | Banking & Finance | Risk Analyst | Sarah Johnson |
| James Wilson | james.wilson@acme.com | EMPLOYEE | Technology & Operations | Software Engineer | Emily Davis |
| Steven Lewis | steven.lewis@acme.com | EMPLOYEE | Technology & Operations | IT Support Specialist | Emily Davis |
| Angela Walker | angela.walker@acme.com | EMPLOYEE | Technology & Operations | Software Engineer | Emily Davis |
| Brian Hall | brian.hall@acme.com | EMPLOYEE | Technology & Operations | IT Support Specialist | Emily Davis |
| Karen Young | karen.young@acme.com | EMPLOYEE | Technology & Operations | Business Operations Analyst | Emily Davis |
| David Rodriguez | david.rodriguez@acme.com | EMPLOYEE | HR | HR Coordinator | Patricia Garcia |
| Jason King | jason.king@acme.com | EMPLOYEE | HR | Recruiter | Patricia Garcia |
| Michelle Scott | michelle.scott@acme.com | EMPLOYEE | HR | HR Coordinator | Patricia Garcia |
| Daniel Adams | daniel.adams@acme.com | EMPLOYEE | HR | Recruiter | Patricia Garcia |

Passwords are shared per role tier for easy demo logins: `adminpass123` /
`managerpass123` / `employeepass123`.

## Running locally over real HTTP

[local_server.py](local_server.py) wraps `handler()` in a plain
`http.server` so you can hit the API with curl, Postman, or a frontend dev
server (e.g. Vite on `localhost:5173`) instead of calling `handler()`
directly with fake event dicts.

```sh
python3 local_server.py
```

By default it listens on `http://localhost:8000`. Override the port with
`LOCAL_PORT`:

```sh
LOCAL_PORT=8080 python3 local_server.py
```

**This is separate from the actual AWS Lambda deployment path**
(`bin/deploy-backend.sh`), which deploys `function.py` behind API Gateway.
`local_server.py` is purely a local development convenience and is never
used in the deployed environment.

## Manual smoke tests

[test_manual.py](test_manual.py) exercises the API end-to-end against a
real local Postgres database by calling `handler()` directly (no HTTP
server needed). Run the seed script first so the accounts it expects exist:

```sh
python3 seed_data.py
python3 test_manual.py
```
