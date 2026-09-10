// Display-only relabeling: the backend role value is "ADMIN" (see
// backend/employee-service/postgres_service.py VALID_ROLES) - this only
// changes the casing shown on screen ("Admin" instead of the raw "ADMIN"),
// consistent with how MANAGER/EMPLOYEE are shown as-is. Never compare
// against the return value of this function; always compare the actual
// `role` field instead.
export function roleLabel(role) {
  return role === 'ADMIN' ? 'Admin' : role
}
