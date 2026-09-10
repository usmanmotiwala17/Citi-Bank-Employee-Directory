import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Box, Typography, Grid, Card, CardContent, Chip, Select, MenuItem,
  InputLabel, FormControl, OutlinedInput, Button, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, Alert, IconButton, Switch,
  FormControlLabel, Divider,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import EmployeeAvatar from '../components/EmployeeAvatar'
import { useAuth } from '../context/AuthContext'
import {
  getEmployees, getDepartments, createEmployee, createDepartment, updateEmployee,
} from '../services/api'
import { CITI_BLUE, CITI_BLUE_DARK } from '../theme'

const EMPTY_CREATE_FORM = {
  first_name: '', last_name: '', email: '', password: '',
  role: 'EMPLOYEE', department_id: '', manager_id: '', skills: '', location: '',
}

function parseSkills(text) {
  return text.split(',').map((s) => s.trim()).filter(Boolean)
}

function canManage(viewer, target) {
  if (viewer.role === 'CEO') return true
  return viewer.role === 'MANAGER' && target.department_id === viewer.department_id
}

function Directory() {
  const { token, employee: viewer } = useAuth()

  const [employees, setEmployees] = useState([])
  const [departments, setDepartments] = useState([])
  const [loadError, setLoadError] = useState(null)

  const [skillFilter, setSkillFilter] = useState('')
  const [deptFilter, setDeptFilter] = useState('')
  const [locationFilter, setLocationFilter] = useState('')

  const [addEmployeeOpen, setAddEmployeeOpen] = useState(false)
  const [createForm, setCreateForm] = useState(EMPTY_CREATE_FORM)
  const [createError, setCreateError] = useState(null)

  const [addDeptOpen, setAddDeptOpen] = useState(false)
  const [deptForm, setDeptForm] = useState({ name: '', description: '' })
  const [deptError, setDeptError] = useState(null)

  const [editTarget, setEditTarget] = useState(null)
  const [editDraft, setEditDraft] = useState({ job_title: '', is_active: true })
  const [editError, setEditError] = useState(null)

  const loadAll = useCallback(async () => {
    setLoadError(null)
    try {
      const [emps, depts] = await Promise.all([getEmployees(token), getDepartments(token)])
      setEmployees(emps)
      setDepartments(depts)
    } catch (err) {
      setLoadError(err.response?.data?.error || 'Failed to load the directory')
    }
  }, [token])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const departmentName = (id) => departments.find((d) => d.id === id)?.name || '—'

  const allSkills = useMemo(() => {
    const set = new Set()
    employees.forEach((e) => (e.skills || []).forEach((s) => set.add(s)))
    return [...set].sort()
  }, [employees])

  const allLocations = useMemo(() => {
    const set = new Set()
    employees.forEach((e) => e.location && set.add(e.location))
    return [...set].sort()
  }, [employees])

  const filtered = employees.filter((e) => {
    if (deptFilter && String(e.department_id) !== deptFilter) return false
    if (locationFilter && e.location !== locationFilter) return false
    if (skillFilter && !(e.skills || []).includes(skillFilter)) return false
    return true
  })

  const ceos = filtered.filter((e) => e.role === 'CEO')
  const managers = filtered.filter((e) => e.role === 'MANAGER')
  const staff = filtered.filter((e) => e.role === 'EMPLOYEE')

  const openEdit = (emp) => {
    setEditError(null)
    setEditTarget(emp)
    setEditDraft({ job_title: emp.job_title || '', is_active: emp.is_active })
  }

  const handleSaveEdit = async () => {
    setEditError(null)
    try {
      await updateEmployee(token, editTarget.id, {
        job_title: editDraft.job_title,
        is_active: editDraft.is_active,
      })
      setEditTarget(null)
      await loadAll()
    } catch (err) {
      setEditError(err.response?.data?.error || 'Failed to update employee')
    }
  }

  const handleCreateEmployee = async (e) => {
    e.preventDefault()
    setCreateError(null)
    try {
      await createEmployee(token, {
        first_name: createForm.first_name,
        last_name: createForm.last_name,
        email: createForm.email,
        password: createForm.password,
        role: createForm.role,
        department_id: createForm.department_id ? Number(createForm.department_id) : null,
        manager_id: createForm.manager_id ? Number(createForm.manager_id) : null,
        skills: parseSkills(createForm.skills),
        location: createForm.location || null,
      })
      setAddEmployeeOpen(false)
      setCreateForm(EMPTY_CREATE_FORM)
      await loadAll()
    } catch (err) {
      setCreateError(err.response?.data?.error || 'Failed to create employee')
    }
  }

  const handleCreateDepartment = async (e) => {
    e.preventDefault()
    setDeptError(null)
    try {
      await createDepartment(token, deptForm)
      setAddDeptOpen(false)
      setDeptForm({ name: '', description: '' })
      await loadAll()
    } catch (err) {
      setDeptError(err.response?.data?.error || 'Failed to create department')
    }
  }

  const managerOptions = employees.filter(
    (e) => e.role === 'MANAGER' && (!createForm.department_id || String(e.department_id) === createForm.department_id),
  )

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 800 }}>Employee Directory</Typography>
        {viewer.role === 'CEO' && (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant="outlined" onClick={() => setAddDeptOpen(true)} sx={{ borderColor: CITI_BLUE, color: CITI_BLUE }}>
              + Add Department
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setAddEmployeeOpen(true)}
              sx={{ bgcolor: CITI_BLUE, '&:hover': { bgcolor: CITI_BLUE_DARK } }}
            >
              Add Employee
            </Button>
          </Box>
        )}
      </Box>

      {loadError && <Alert severity="error" sx={{ mb: 2 }}>{loadError}</Alert>}

      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel id="skill-filter-label">Skill</InputLabel>
          <Select labelId="skill-filter-label" value={skillFilter} label="Skill" input={<OutlinedInput label="Skill" />} onChange={(e) => setSkillFilter(e.target.value)}>
            <MenuItem value="">All Skills</MenuItem>
            {allSkills.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel id="dept-filter-label">Department</InputLabel>
          <Select labelId="dept-filter-label" value={deptFilter} label="Department" input={<OutlinedInput label="Department" />} onChange={(e) => setDeptFilter(e.target.value)}>
            <MenuItem value="">All Departments</MenuItem>
            {departments.map((d) => <MenuItem key={d.id} value={String(d.id)}>{d.name}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel id="location-filter-label">Location</InputLabel>
          <Select labelId="location-filter-label" value={locationFilter} label="Location" input={<OutlinedInput label="Location" />} onChange={(e) => setLocationFilter(e.target.value)}>
            <MenuItem value="">All Locations</MenuItem>
            {allLocations.map((l) => <MenuItem key={l} value={l}>{l}</MenuItem>)}
          </Select>
        </FormControl>
      </Box>

      <DirectorySection title="CEO" people={ceos} departmentName={departmentName} viewer={viewer} onEdit={openEdit} />
      <DirectorySection title="Managers" people={managers} departmentName={departmentName} viewer={viewer} onEdit={openEdit} />
      <DirectorySection title="Employees" people={staff} departmentName={departmentName} viewer={viewer} onEdit={openEdit} />

      {/* Add Employee dialog (CEO only) */}
      <Dialog open={addEmployeeOpen} onClose={() => setAddEmployeeOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Employee</DialogTitle>
        <Box component="form" onSubmit={handleCreateEmployee}>
          <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {createError && <Alert severity="error">{createError}</Alert>}
            <TextField label="First Name" required value={createForm.first_name} onChange={(e) => setCreateForm({ ...createForm, first_name: e.target.value })} />
            <TextField label="Last Name" required value={createForm.last_name} onChange={(e) => setCreateForm({ ...createForm, last_name: e.target.value })} />
            <TextField label="Email" type="email" required value={createForm.email} onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })} />
            <TextField label="Password" type="password" required value={createForm.password} onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })} />
            <FormControl fullWidth>
              <InputLabel id="create-role-label">Role</InputLabel>
              <Select labelId="create-role-label" label="Role" value={createForm.role} onChange={(e) => setCreateForm({ ...createForm, role: e.target.value, department_id: e.target.value === 'CEO' ? '' : createForm.department_id })}>
                <MenuItem value="EMPLOYEE">EMPLOYEE</MenuItem>
                <MenuItem value="MANAGER">MANAGER</MenuItem>
                <MenuItem value="CEO">CEO</MenuItem>
              </Select>
            </FormControl>
            {createForm.role !== 'CEO' && (
              <FormControl fullWidth>
                <InputLabel id="create-department-label">Department</InputLabel>
                <Select labelId="create-department-label" label="Department" value={createForm.department_id} onChange={(e) => setCreateForm({ ...createForm, department_id: e.target.value, manager_id: '' })}>
                  {departments.map((d) => <MenuItem key={d.id} value={String(d.id)}>{d.name}</MenuItem>)}
                </Select>
              </FormControl>
            )}
            {createForm.role === 'EMPLOYEE' && (
              <FormControl fullWidth>
                <InputLabel id="create-manager-label">Manager (optional)</InputLabel>
                <Select labelId="create-manager-label" label="Manager (optional)" value={createForm.manager_id} onChange={(e) => setCreateForm({ ...createForm, manager_id: e.target.value })}>
                  <MenuItem value="">None</MenuItem>
                  {managerOptions.map((m) => <MenuItem key={m.id} value={String(m.id)}>{m.first_name} {m.last_name}</MenuItem>)}
                </Select>
              </FormControl>
            )}
            <TextField label="Skills (comma-separated)" value={createForm.skills} onChange={(e) => setCreateForm({ ...createForm, skills: e.target.value })} />
            <TextField label="Location" value={createForm.location} onChange={(e) => setCreateForm({ ...createForm, location: e.target.value })} />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAddEmployeeOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained" sx={{ bgcolor: CITI_BLUE }}>Create</Button>
          </DialogActions>
        </Box>
      </Dialog>

      {/* Add Department dialog (CEO only) */}
      <Dialog open={addDeptOpen} onClose={() => setAddDeptOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Department</DialogTitle>
        <Box component="form" onSubmit={handleCreateDepartment}>
          <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {deptError && <Alert severity="error">{deptError}</Alert>}
            <TextField label="Name" required value={deptForm.name} onChange={(e) => setDeptForm({ ...deptForm, name: e.target.value })} />
            <TextField label="Description" value={deptForm.description} onChange={(e) => setDeptForm({ ...deptForm, description: e.target.value })} />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAddDeptOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained" sx={{ bgcolor: CITI_BLUE }}>Create</Button>
          </DialogActions>
        </Box>
      </Dialog>

      {/* Manage employee dialog (job title / active status) */}
      <Dialog open={!!editTarget} onClose={() => setEditTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Manage {editTarget?.first_name} {editTarget?.last_name}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {editError && <Alert severity="error">{editError}</Alert>}
          <TextField
            label="Job Title"
            value={editDraft.job_title}
            onChange={(e) => setEditDraft({ ...editDraft, job_title: e.target.value })}
          />
          <FormControlLabel
            control={<Switch checked={editDraft.is_active} onChange={(e) => setEditDraft({ ...editDraft, is_active: e.target.checked })} />}
            label="Active"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditTarget(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveEdit} sx={{ bgcolor: CITI_BLUE }}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

function DirectorySection({ title, people, departmentName, viewer, onEdit }) {
  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 1.5 }}>{title}</Typography>
      <Divider sx={{ mb: 2 }} />
      {people.length === 0 ? (
        <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>No matching employees.</Typography>
      ) : (
        <Grid container spacing={2}>
          {people.map((emp) => (
            <Grid key={emp.id} size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
              <Card variant="outlined" sx={{ height: '100%' }}>
                <CardContent sx={{ textAlign: 'center', position: 'relative' }}>
                  {canManage(viewer, emp) && (
                    <IconButton size="small" onClick={() => onEdit(emp)} sx={{ position: 'absolute', top: 6, right: 6 }}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                  )}
                  <Box sx={{ display: 'flex', justifyContent: 'center', mb: 1.5 }}>
                    <EmployeeAvatar employee={emp} size={64} />
                  </Box>
                  <Typography sx={{ fontWeight: 700 }}>{emp.first_name} {emp.last_name}</Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>{emp.job_title || emp.role}</Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary', mb: 1 }}>{departmentName(emp.department_id)}</Typography>
                  {!emp.is_active && <Chip size="small" label="Inactive" sx={{ mt: 0.5 }} />}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  )
}

export default Directory
