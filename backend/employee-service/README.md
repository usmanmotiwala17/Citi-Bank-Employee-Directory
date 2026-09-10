# Employee Directory Service

Lambda-backed CRUD API for employees and departments, with JWT auth and
role-based permissions. See [function.py](function.py) for routes,
[postgres_service.py](postgres_service.py) for the DB layer, and
[auth_service.py](auth_service.py) for auth.

## Roles

Three roles, replacing the old `admin`/`manager`/`employee` model with a
Citi-style, department-scoped hierarchy:

| Role       | Access |
|------------|--------|
| `CEO`      | Full access to every employee and department; the only role that can create, update, or delete anyone. |
| `MANAGER`  | Can view and manage (edit job title / active status, deactivate) employees within their own department only. Scoped to one department. |
| `EMPLOYEE` | Can view and edit (phone/bio) their own profile only. Scoped to one department. |

The JWT issued at login carries both `role` and `department_id` (`null` for
CEOs, since they aren't scoped to one department), and both are re-checked
against the database on every request - so changing someone's role or
department invalidates their existing token immediately.

## Seeding sample data

[seed_data.py](seed_data.py) creates 3 departments (Banking & Finance,
Technology & Operations, HR), one manager per department, and 13 employees -
17 people total (1 CEO, 3 MANAGER, 13 EMPLOYEE). Each employee's
`manager_id` is set to their department's manager, so the reporting line is
actually wired up rather than left blank:

```sh
python3 seed_data.py
```

| Name | Email | Role | Department | Job Title | Reports To |
|------|-------|------|------------|-----------|------------|
| Robert Chen | robert.chen@acme.com | CEO | — | Chief Executive Officer | — |
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

Passwords are shared per role tier for easy demo logins: `ceopass123` /
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
