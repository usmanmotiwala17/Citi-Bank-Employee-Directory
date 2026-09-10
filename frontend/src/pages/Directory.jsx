import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Typography, Grid, Card, CardContent, Chip, Select, MenuItem,
  InputLabel, FormControl, OutlinedInput, Button, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, Alert, Divider, InputAdornment, Paper,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import SearchIcon from '@mui/icons-material/Search'
import EmployeeAvatar from '../components/EmployeeAvatar'
import AvailabilityIndicator from '../components/AvailabilityIndicator'
import { roleLabel } from '../utils/roleLabel'
import { useAuth } from '../context/AuthContext'
import {
  getEmployees, getDepartments, createEmployee, createDepartment,
} from '../services/api'
import { CITI_BLUE, CITI_BLUE_DARK } from '../theme'

const EMPTY_CREATE_FORM = {
  first_name: '', last_name: '', email: '', password: '',
  role: 'EMPLOYEE', department_id: '', manager_id: '', skills: '', location: '',
}

function parseSkills(text) {
  return text.split(',').map((s) => s.trim()).filter(Boolean)
}

function Directory() {
  const { token, employee: viewer } = useAuth()
  const navigate = useNavigate()

  const [employees, setEmployees] = useState([])
  const [departments, setDepartments] = useState([])
  const [loadError, setLoadError] = useState(null)

  const [searchQuery, setSearchQuery] = useState('')
  const [skillFilter, setSkillFilter] = useState('')
  const [deptFilter, setDeptFilter] = useState('')
  const [locationFilter, setLocationFilter] = useState('')
  const [availabilityFilter, setAvailabilityFilter] = useState('')

  const [addEmployeeOpen, setAddEmployeeOpen] = useState(false)
  const [createForm, setCreateForm] = useState(EMPTY_CREATE_FORM)
  const [createError, setCreateError] = useState(null)

  const [addDeptOpen, setAddDeptOpen] = useState(false)
  const [deptForm, setDeptForm] = useState({ name: '', description: '' })
  const [deptError, setDeptError] = useState(null)

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
    if (searchQuery && !`${e.first_name} ${e.last_name}`.toLowerCase().includes(searchQuery.trim().toLowerCase())) return false
    if (deptFilter && String(e.department_id) !== deptFilter) return false
    if (locationFilter && e.location !== locationFilter) return false
    if (skillFilter && !(e.skills || []).includes(skillFilter)) return false
    if (availabilityFilter && e.availability_status !== availabilityFilter) return false
    return true
  })

  const admins = filtered.filter((e) => e.role === 'ADMIN')
  const managers = filtered.filter((e) => e.role === 'MANAGER')
  const staff = filtered.filter((e) => e.role === 'EMPLOYEE')

  // Company-wide totals - unaffected by search/filters, so this stays a
  // stable "at a glance" summary while the cards below get filtered down.
  const departmentCount = departments.length
  const adminCount = employees.filter((e) => e.role === 'ADMIN').length
  const managerCount = employees.filter((e) => e.role === 'MANAGER').length
  const employeeCount = employees.filter((e) => e.role === 'EMPLOYEE').length

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
      <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 1.5, mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 800 }}>Employee Directory</Typography>
        {viewer.role === 'ADMIN' && (
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
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
        <StatTile label="Departments" value={departmentCount} />
        <StatTile label="Admins" value={adminCount} />
        <StatTile label="Managers" value={managerCount} />
        <StatTile label="Employees" value={employeeCount} />
      </Box>

      <TextField
        size="small"
        fullWidth
        placeholder="Search by name..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        sx={{ mb: 2, maxWidth: 420 }}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" sx={{ color: 'text.secondary' }} />
              </InputAdornment>
            ),
          },
        }}
      />

      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <FormControl size="small" sx={{ width: { xs: '100%', sm: 180 } }}>
          <InputLabel id="skill-filter-label">Skill</InputLabel>
          <Select labelId="skill-filter-label" value={skillFilter} label="Skill" input={<OutlinedInput label="Skill" />} onChange={(e) => setSkillFilter(e.target.value)}>
            <MenuItem value="">All Skills</MenuItem>
            {allSkills.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ width: { xs: '100%', sm: 180 } }}>
          <InputLabel id="dept-filter-label">Department</InputLabel>
          <Select labelId="dept-filter-label" value={deptFilter} label="Department" input={<OutlinedInput label="Department" />} onChange={(e) => setDeptFilter(e.target.value)}>
            <MenuItem value="">All Departments</MenuItem>
            {departments.map((d) => <MenuItem key={d.id} value={String(d.id)}>{d.name}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ width: { xs: '100%', sm: 180 } }}>
          <InputLabel id="location-filter-label">Location</InputLabel>
          <Select labelId="location-filter-label" value={locationFilter} label="Location" input={<OutlinedInput label="Location" />} onChange={(e) => setLocationFilter(e.target.value)}>
            <MenuItem value="">All Locations</MenuItem>
            {allLocations.map((l) => <MenuItem key={l} value={l}>{l}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ width: { xs: '100%', sm: 180 } }}>
          <InputLabel id="availability-filter-label">Availability</InputLabel>
          <Select labelId="availability-filter-label" value={availabilityFilter} label="Availability" input={<OutlinedInput label="Availability" />} onChange={(e) => setAvailabilityFilter(e.target.value)}>
            <MenuItem value="">All</MenuItem>
            <MenuItem value="available">Available</MenuItem>
            <MenuItem value="unavailable">Unavailable</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <DirectorySection title="Admin" people={admins} departmentName={departmentName} onOpenProfile={(id) => navigate(`/employees/${id}`)} />
      <DirectorySection title="Managers" people={managers} departmentName={departmentName} onOpenProfile={(id) => navigate(`/employees/${id}`)} />
      <DirectorySection title="Employees" people={staff} departmentName={departmentName} onOpenProfile={(id) => navigate(`/employees/${id}`)} />

      {/* Add Employee dialog (Admin only) */}
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
              <Select labelId="create-role-label" label="Role" value={createForm.role} onChange={(e) => setCreateForm({ ...createForm, role: e.target.value, department_id: e.target.value === 'ADMIN' ? '' : createForm.department_id })}>
                <MenuItem value="EMPLOYEE">EMPLOYEE</MenuItem>
                <MenuItem value="MANAGER">MANAGER</MenuItem>
                <MenuItem value="ADMIN">Admin</MenuItem>
              </Select>
            </FormControl>
            {createForm.role !== 'ADMIN' && (
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

      {/* Add Department dialog (Admin only) */}
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

    </Box>
  )
}

function StatTile({ label, value }) {
  return (
    <Paper variant="outlined" sx={{ px: 2.5, py: 1.5, flex: '1 1 140px', minWidth: 140 }}>
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>{label}</Typography>
      <Typography variant="h5" sx={{ fontWeight: 700, mt: 0.25 }}>{value}</Typography>
    </Paper>
  )
}

function DirectorySection({ title, people, departmentName, onOpenProfile }) {
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
                <CardContent
                  onClick={() => onOpenProfile(emp.id)}
                  sx={{ textAlign: 'center', cursor: 'pointer' }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'center', mb: 1.5 }}>
                    <EmployeeAvatar employee={emp} size={64} />
                  </Box>
                  <Typography sx={{ fontWeight: 700 }}>{emp.first_name} {emp.last_name}</Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>{emp.job_title || roleLabel(emp.role)}</Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary', mb: 1 }}>{departmentName(emp.department_id)}</Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'center', mb: 0.5 }}>
                    <AvailabilityIndicator status={emp.availability_status} />
                  </Box>
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
