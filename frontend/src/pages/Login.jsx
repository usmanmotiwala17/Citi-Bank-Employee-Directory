import { useState } from 'react'
import {
  login,
  getEmployees,
  createEmployee,
  updateEmployee,
  deleteEmployee,
  getDepartments,
  createDepartment,
} from '../services/api'

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'flex-start',
    paddingTop: '4rem',
    paddingBottom: '4rem',
    background: '#f4f5f7',
    fontFamily: 'system-ui, sans-serif',
  },
  card: {
    background: '#fff',
    borderRadius: '10px',
    boxShadow: '0 2px 10px rgba(0, 0, 0, 0.08)',
    padding: '2rem',
    width: '420px',
    maxWidth: '90vw',
  },
  wideCard: {
    background: '#fff',
    borderRadius: '10px',
    boxShadow: '0 2px 10px rgba(0, 0, 0, 0.08)',
    padding: '2rem',
    width: '760px',
    maxWidth: '90vw',
  },
  heading: {
    margin: '0 0 1.5rem',
    fontSize: '1.4rem',
  },
  sectionHeading: {
    margin: '2rem 0 0.75rem',
    fontSize: '1.1rem',
    borderTop: '1px solid #eee',
    paddingTop: '1.5rem',
  },
  field: {
    marginBottom: '1rem',
  },
  label: {
    display: 'block',
    marginBottom: '0.35rem',
    fontSize: '0.85rem',
    color: '#444',
  },
  input: {
    width: '100%',
    padding: '0.5rem 0.65rem',
    boxSizing: 'border-box',
    border: '1px solid #ccc',
    borderRadius: '6px',
    fontSize: '0.95rem',
  },
  smallInput: {
    width: '100%',
    padding: '0.35rem 0.5rem',
    boxSizing: 'border-box',
    border: '1px solid #ccc',
    borderRadius: '6px',
    fontSize: '0.85rem',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '0 1rem',
  },
  button: {
    padding: '0.55rem 1rem',
    border: 'none',
    borderRadius: '6px',
    background: '#2f6fed',
    color: '#fff',
    fontSize: '0.95rem',
    cursor: 'pointer',
    marginTop: '0.25rem',
  },
  secondaryButton: {
    padding: '0.55rem 1rem',
    border: '1px solid #ccc',
    borderRadius: '6px',
    background: '#fff',
    color: '#333',
    fontSize: '0.95rem',
    cursor: 'pointer',
    marginLeft: '0.5rem',
  },
  smallButton: {
    padding: '0.25rem 0.55rem',
    border: 'none',
    borderRadius: '5px',
    background: '#2f6fed',
    color: '#fff',
    fontSize: '0.8rem',
    cursor: 'pointer',
    marginRight: '0.35rem',
  },
  smallDangerButton: {
    padding: '0.25rem 0.55rem',
    border: 'none',
    borderRadius: '5px',
    background: '#c53030',
    color: '#fff',
    fontSize: '0.8rem',
    cursor: 'pointer',
    marginRight: '0.35rem',
  },
  smallSecondaryButton: {
    padding: '0.25rem 0.55rem',
    border: '1px solid #ccc',
    borderRadius: '5px',
    background: '#fff',
    color: '#333',
    fontSize: '0.8rem',
    cursor: 'pointer',
    marginRight: '0.35rem',
  },
  error: {
    background: '#fdecea',
    color: '#b3261e',
    padding: '0.6rem 0.75rem',
    borderRadius: '6px',
    fontSize: '0.85rem',
    marginBottom: '1rem',
  },
  success: {
    background: '#eaf7ec',
    color: '#1e7d32',
    padding: '0.6rem 0.75rem',
    borderRadius: '6px',
    fontSize: '0.85rem',
    marginBottom: '1rem',
  },
  welcome: {
    marginBottom: '1rem',
    fontSize: '1rem',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: '1rem',
    fontSize: '0.85rem',
  },
  th: {
    textAlign: 'left',
    borderBottom: '2px solid #eee',
    padding: '0.4rem',
  },
  td: {
    borderBottom: '1px solid #f0f0f0',
    padding: '0.4rem',
  },
  list: {
    listStyle: 'none',
    padding: 0,
    marginTop: '1rem',
    fontSize: '0.9rem',
  },
  listItem: {
    padding: '0.5rem 0',
    borderBottom: '1px solid #f0f0f0',
  },
}

const EMPTY_EMPLOYEE_FORM = {
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  role: 'employee',
  manager_id: '',
  department_id: '',
}

const EMPTY_DEPARTMENT_FORM = { name: '', description: '' }

function Login() {
  const [email, setEmail] = useState('admin@acme.com')
  const [password, setPassword] = useState('yourchosenpassword')
  const [loginError, setLoginError] = useState(null)
  const [loggingIn, setLoggingIn] = useState(false)

  const [token, setToken] = useState(null)
  const [employee, setEmployee] = useState(null)

  const [employees, setEmployees] = useState(null)
  const [employeesError, setEmployeesError] = useState(null)
  const [loadingEmployees, setLoadingEmployees] = useState(false)

  const [createForm, setCreateForm] = useState(EMPTY_EMPLOYEE_FORM)
  const [createError, setCreateError] = useState(null)
  const [createSuccess, setCreateSuccess] = useState(null)
  const [creating, setCreating] = useState(false)

  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState({ job_title: '', is_active: true })
  const [rowError, setRowError] = useState(null)

  const [departments, setDepartments] = useState(null)
  const [departmentsError, setDepartmentsError] = useState(null)
  const [loadingDepartments, setLoadingDepartments] = useState(false)

  const [deptForm, setDeptForm] = useState(EMPTY_DEPARTMENT_FORM)
  const [deptError, setDeptError] = useState(null)
  const [deptSuccess, setDeptSuccess] = useState(null)
  const [creatingDept, setCreatingDept] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoginError(null)
    setLoggingIn(true)
    try {
      const data = await login(email, password)
      setToken(data.access_token)
      setEmployee(data.employee)
    } catch (err) {
      setLoginError(err.response?.data?.error || 'Login failed')
    } finally {
      setLoggingIn(false)
    }
  }

  const handleLoadEmployees = async () => {
    setEmployeesError(null)
    setLoadingEmployees(true)
    try {
      const data = await getEmployees(token)
      setEmployees(data)
    } catch (err) {
      setEmployeesError(err.response?.data?.error || 'Failed to load employees')
    } finally {
      setLoadingEmployees(false)
    }
  }

  const handleLogOut = () => {
    setToken(null)
    setEmployee(null)
    setEmployees(null)
    setEmployeesError(null)
    setLoginError(null)
    setCreateForm(EMPTY_EMPLOYEE_FORM)
    setCreateError(null)
    setCreateSuccess(null)
    setEditingId(null)
    setRowError(null)
    setDepartments(null)
    setDepartmentsError(null)
    setDeptForm(EMPTY_DEPARTMENT_FORM)
    setDeptError(null)
    setDeptSuccess(null)
  }

  const handleCreateEmployee = async (e) => {
    e.preventDefault()
    setCreateError(null)
    setCreateSuccess(null)
    setCreating(true)
    try {
      const payload = {
        first_name: createForm.first_name,
        last_name: createForm.last_name,
        email: createForm.email,
        password: createForm.password,
        role: createForm.role,
        manager_id: createForm.manager_id ? Number(createForm.manager_id) : null,
        department_id: createForm.department_id ? Number(createForm.department_id) : null,
      }
      await createEmployee(token, payload)
      setCreateSuccess('Employee created.')
      setCreateForm(EMPTY_EMPLOYEE_FORM)
      if (employees) await handleLoadEmployees()
    } catch (err) {
      setCreateError(err.response?.data?.error || 'Failed to create employee')
    } finally {
      setCreating(false)
    }
  }

  const startEditing = (row) => {
    setRowError(null)
    setEditingId(row.id)
    setEditDraft({ job_title: row.job_title || '', is_active: row.is_active })
  }

  const cancelEditing = () => {
    setEditingId(null)
  }

  const handleSaveEdit = async (id) => {
    setRowError(null)
    try {
      await updateEmployee(token, id, {
        job_title: editDraft.job_title,
        is_active: editDraft.is_active,
      })
      setEditingId(null)
      await handleLoadEmployees()
    } catch (err) {
      setRowError(err.response?.data?.error || 'Failed to update employee')
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm(`Delete employee #${id}? This deactivates their account.`)) return
    setRowError(null)
    try {
      await deleteEmployee(token, id)
      await handleLoadEmployees()
    } catch (err) {
      setRowError(err.response?.data?.error || 'Failed to delete employee')
    }
  }

  const handleLoadDepartments = async () => {
    setDepartmentsError(null)
    setLoadingDepartments(true)
    try {
      const data = await getDepartments(token)
      setDepartments(data)
    } catch (err) {
      setDepartmentsError(err.response?.data?.error || 'Failed to load departments')
    } finally {
      setLoadingDepartments(false)
    }
  }

  const handleCreateDepartment = async (e) => {
    e.preventDefault()
    setDeptError(null)
    setDeptSuccess(null)
    setCreatingDept(true)
    try {
      await createDepartment(token, deptForm)
      setDeptSuccess('Department created.')
      setDeptForm(EMPTY_DEPARTMENT_FORM)
      if (departments) await handleLoadDepartments()
    } catch (err) {
      setDeptError(err.response?.data?.error || 'Failed to create department')
    } finally {
      setCreatingDept(false)
    }
  }

  if (!token) {
    return (
      <div style={styles.page}>
        <div style={styles.card}>
          <h1 style={styles.heading}>Employee Directory Login</h1>
          {loginError && <div style={styles.error}>{loginError}</div>}
          <form onSubmit={handleSubmit}>
            <div style={styles.field}>
              <label style={styles.label} htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                style={styles.input}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div style={styles.field}>
              <label style={styles.label} htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                style={styles.input}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <button type="submit" style={styles.button} disabled={loggingIn}>
              {loggingIn ? 'Logging in...' : 'Log In'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.page}>
      <div style={styles.wideCard}>
        <h1 style={styles.heading}>Employee Directory</h1>
        <div style={styles.welcome}>
          Logged in as {employee.first_name} {employee.last_name} ({employee.role})
        </div>

        {employeesError && <div style={styles.error}>{employeesError}</div>}
        {rowError && <div style={styles.error}>{rowError}</div>}

        <button style={styles.button} onClick={handleLoadEmployees} disabled={loadingEmployees}>
          {loadingEmployees ? 'Loading...' : 'Load Employee Directory'}
        </button>
        <button style={styles.secondaryButton} onClick={handleLogOut}>
          Log Out
        </button>

        {employees && (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>ID</th>
                <th style={styles.th}>First Name</th>
                <th style={styles.th}>Last Name</th>
                <th style={styles.th}>Email</th>
                <th style={styles.th}>Role</th>
                <th style={styles.th}>Job Title</th>
                <th style={styles.th}>Active</th>
                <th style={styles.th}></th>
              </tr>
            </thead>
            <tbody>
              {employees.map((emp) => (
                <tr key={emp.id}>
                  {editingId === emp.id ? (
                    <>
                      <td style={styles.td}>{emp.id}</td>
                      <td style={styles.td}>{emp.first_name}</td>
                      <td style={styles.td}>{emp.last_name}</td>
                      <td style={styles.td}>{emp.email}</td>
                      <td style={styles.td}>{emp.role}</td>
                      <td style={styles.td}>
                        <input
                          style={styles.smallInput}
                          value={editDraft.job_title}
                          onChange={(e) => setEditDraft({ ...editDraft, job_title: e.target.value })}
                        />
                      </td>
                      <td style={styles.td}>
                        <input
                          type="checkbox"
                          checked={editDraft.is_active}
                          onChange={(e) => setEditDraft({ ...editDraft, is_active: e.target.checked })}
                        />
                      </td>
                      <td style={styles.td}>
                        <button style={styles.smallButton} onClick={() => handleSaveEdit(emp.id)}>
                          Save
                        </button>
                        <button style={styles.smallSecondaryButton} onClick={cancelEditing}>
                          Cancel
                        </button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td style={styles.td}>{emp.id}</td>
                      <td style={styles.td}>{emp.first_name}</td>
                      <td style={styles.td}>{emp.last_name}</td>
                      <td style={styles.td}>{emp.email}</td>
                      <td style={styles.td}>{emp.role}</td>
                      <td style={styles.td}>{emp.job_title}</td>
                      <td style={styles.td}>{emp.is_active ? 'Yes' : 'No'}</td>
                      <td style={styles.td}>
                        <button style={styles.smallButton} onClick={() => startEditing(emp)}>
                          Edit
                        </button>
                        <button style={styles.smallDangerButton} onClick={() => handleDelete(emp.id)}>
                          Delete
                        </button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <h2 style={styles.sectionHeading}>Create Employee</h2>
        {createError && <div style={styles.error}>{createError}</div>}
        {createSuccess && <div style={styles.success}>{createSuccess}</div>}
        <form onSubmit={handleCreateEmployee}>
          <div style={styles.formGrid}>
            <div style={styles.field}>
              <label style={styles.label}>First Name</label>
              <input
                style={styles.input}
                value={createForm.first_name}
                onChange={(e) => setCreateForm({ ...createForm, first_name: e.target.value })}
                required
              />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Last Name</label>
              <input
                style={styles.input}
                value={createForm.last_name}
                onChange={(e) => setCreateForm({ ...createForm, last_name: e.target.value })}
                required
              />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Email</label>
              <input
                type="email"
                style={styles.input}
                value={createForm.email}
                onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                required
              />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Password</label>
              <input
                type="password"
                style={styles.input}
                value={createForm.password}
                onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                required
              />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Role</label>
              <select
                style={styles.input}
                value={createForm.role}
                onChange={(e) => setCreateForm({ ...createForm, role: e.target.value })}
              >
                <option value="employee">employee</option>
                <option value="manager">manager</option>
                <option value="admin">admin</option>
              </select>
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Manager ID (optional)</label>
              <input
                type="number"
                style={styles.input}
                value={createForm.manager_id}
                onChange={(e) => setCreateForm({ ...createForm, manager_id: e.target.value })}
              />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Department ID (optional)</label>
              <input
                type="number"
                style={styles.input}
                value={createForm.department_id}
                onChange={(e) => setCreateForm({ ...createForm, department_id: e.target.value })}
              />
            </div>
          </div>
          <button type="submit" style={styles.button} disabled={creating}>
            {creating ? 'Creating...' : 'Create Employee'}
          </button>
        </form>

        <h2 style={styles.sectionHeading}>Departments</h2>
        {departmentsError && <div style={styles.error}>{departmentsError}</div>}

        <button style={styles.button} onClick={handleLoadDepartments} disabled={loadingDepartments}>
          {loadingDepartments ? 'Loading...' : 'Load Departments'}
        </button>

        {departments && (
          <ul style={styles.list}>
            {departments.map((dept) => (
              <li key={dept.id} style={styles.listItem}>
                <strong>#{dept.id} {dept.name}</strong>
                {dept.description ? ` — ${dept.description}` : ''}
              </li>
            ))}
          </ul>
        )}

        <h2 style={styles.sectionHeading}>Create Department</h2>
        {deptError && <div style={styles.error}>{deptError}</div>}
        {deptSuccess && <div style={styles.success}>{deptSuccess}</div>}
        <form onSubmit={handleCreateDepartment}>
          <div style={styles.field}>
            <label style={styles.label}>Name</label>
            <input
              style={styles.input}
              value={deptForm.name}
              onChange={(e) => setDeptForm({ ...deptForm, name: e.target.value })}
              required
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Description</label>
            <input
              style={styles.input}
              value={deptForm.description}
              onChange={(e) => setDeptForm({ ...deptForm, description: e.target.value })}
            />
          </div>
          <button type="submit" style={styles.button} disabled={creatingDept}>
            {creatingDept ? 'Creating...' : 'Create Department'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default Login
