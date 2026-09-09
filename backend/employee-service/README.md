# Employee Directory Service

Lambda-backed CRUD API for employees and departments, with JWT auth and
role-based permissions. See [function.py](function.py) for routes,
[postgres_service.py](postgres_service.py) for the DB layer, and
[auth_service.py](auth_service.py) for auth.

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
server needed):

```sh
python3 test_manual.py
```
