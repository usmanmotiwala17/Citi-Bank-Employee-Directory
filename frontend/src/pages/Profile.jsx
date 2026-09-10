import { useEffect, useState } from 'react'
import {
  Box, Typography, Paper, Chip, TextField, Button, Alert, Dialog,
  DialogTitle, DialogContent, DialogActions, Stack,
} from '@mui/material'
import EmployeeAvatar from '../components/EmployeeAvatar'
import { useAuth } from '../context/AuthContext'
import { getEmployee, getDepartments, updateEmployee, createChangeRequest } from '../services/api'
import { CITI_BLUE, CITI_BLUE_DARK } from '../theme'

function Profile() {
  const { token, employee: authEmployee, updateSelf } = useAuth()

  const [employee, setEmployee] = useState(authEmployee)
  const [departments, setDepartments] = useState([])
  const [loadError, setLoadError] = useState(null)

  const [skillsDraft, setSkillsDraft] = useState((authEmployee.skills || []).join(', '))
  const [savingSkills, setSavingSkills] = useState(false)
  const [skillsError, setSkillsError] = useState(null)
  const [skillsSaved, setSkillsSaved] = useState(false)

  const isCEO = employee.role === 'CEO'
  const [ceoForm, setCeoForm] = useState({
    phone: employee.phone || '', bio: employee.bio || '', job_title: employee.job_title || '',
    location: employee.location || '',
  })
  const [savingCeo, setSavingCeo] = useState(false)
  const [ceoError, setCeoError] = useState(null)
  const [ceoSaved, setCeoSaved] = useState(false)

  const [phoneDialogOpen, setPhoneDialogOpen] = useState(false)
  const [newPhone, setNewPhone] = useState('')
  const [phoneRequestError, setPhoneRequestError] = useState(null)
  const [phoneRequestSent, setPhoneRequestSent] = useState(false)

  useEffect(() => {
    (async () => {
      try {
        const [freshEmployee, depts] = await Promise.all([
          getEmployee(token, authEmployee.id),
          getDepartments(token),
        ])
        setEmployee(freshEmployee)
        setDepartments(depts)
        setSkillsDraft((freshEmployee.skills || []).join(', '))
        setCeoForm({
          phone: freshEmployee.phone || '', bio: freshEmployee.bio || '',
          job_title: freshEmployee.job_title || '', location: freshEmployee.location || '',
        })
      } catch (err) {
        setLoadError(err.response?.data?.error || 'Failed to load your profile')
      }
    })()
  }, [token, authEmployee.id])

  const departmentName = departments.find((d) => d.id === employee.department_id)?.name

  const handleSaveSkills = async () => {
    setSkillsError(null)
    setSkillsSaved(false)
    setSavingSkills(true)
    try {
      const skills = skillsDraft.split(',').map((s) => s.trim()).filter(Boolean)
      const updated = await updateEmployee(token, employee.id, { skills })
      setEmployee(updated)
      updateSelf(updated)
      setSkillsSaved(true)
    } catch (err) {
      setSkillsError(err.response?.data?.error || 'Failed to save skills')
    } finally {
      setSavingSkills(false)
    }
  }

  const handleSaveCeoFields = async () => {
    setCeoError(null)
    setCeoSaved(false)
    setSavingCeo(true)
    try {
      const updated = await updateEmployee(token, employee.id, ceoForm)
      setEmployee(updated)
      updateSelf(updated)
      setCeoSaved(true)
    } catch (err) {
      setCeoError(err.response?.data?.error || 'Failed to save profile')
    } finally {
      setSavingCeo(false)
    }
  }

  const handleSubmitPhoneRequest = async (e) => {
    e.preventDefault()
    setPhoneRequestError(null)
    try {
      await createChangeRequest(token, { field: 'phone', value: newPhone })
      setPhoneDialogOpen(false)
      setNewPhone('')
      setPhoneRequestSent(true)
    } catch (err) {
      setPhoneRequestError(err.response?.data?.error || 'Failed to submit request')
    }
  }

  return (
    <Box sx={{ maxWidth: 640 }}>
      <Typography variant="h5" sx={{ fontWeight: 800, mb: 3 }}>My Profile</Typography>

      {loadError && <Alert severity="error" sx={{ mb: 2 }}>{loadError}</Alert>}

      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={2} sx={{ alignItems: 'center', mb: 2 }}>
          <EmployeeAvatar employee={employee} size={72} />
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>{employee.first_name} {employee.last_name}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>{employee.role}{departmentName ? ` · ${departmentName}` : ''}</Typography>
          </Box>
        </Stack>

        <Stack spacing={1.5}>
          <Field label="Email" value={employee.email} />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Field label="Phone" value={employee.phone || '—'} />
            {!isCEO && (
              <Button size="small" onClick={() => setPhoneDialogOpen(true)}>Request Change</Button>
            )}
          </Box>
          <Field label="Job Title" value={employee.job_title || '—'} />
          <Field label="Location" value={employee.location || '—'} />
          <Box>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>Skills</Typography>
            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
              {(employee.skills || []).length === 0
                ? <Typography variant="body2" sx={{ color: 'text.secondary' }}>No skills listed.</Typography>
                : employee.skills.map((s) => <Chip key={s} size="small" label={s} />)}
            </Box>
          </Box>
        </Stack>
      </Paper>

      {phoneRequestSent && <Alert severity="success" sx={{ mb: 2 }}>Phone number change request submitted for review.</Alert>}

      {/* Skills - editable by everyone on their own profile */}
      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>Edit Skills</Typography>
        {skillsError && <Alert severity="error" sx={{ mb: 2 }}>{skillsError}</Alert>}
        {skillsSaved && <Alert severity="success" sx={{ mb: 2 }}>Skills updated.</Alert>}
        <TextField
          fullWidth
          label="Skills (comma-separated)"
          value={skillsDraft}
          onChange={(e) => setSkillsDraft(e.target.value)}
          sx={{ mb: 2 }}
        />
        <Button variant="contained" disabled={savingSkills} onClick={handleSaveSkills} sx={{ bgcolor: CITI_BLUE, '&:hover': { bgcolor: CITI_BLUE_DARK } }}>
          {savingSkills ? 'Saving...' : 'Save'}
        </Button>
      </Paper>

      {/* CEO-only: broader self-edit permissions per backend rules */}
      {isCEO && (
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>Edit Profile Details</Typography>
          {ceoError && <Alert severity="error" sx={{ mb: 2 }}>{ceoError}</Alert>}
          {ceoSaved && <Alert severity="success" sx={{ mb: 2 }}>Profile updated.</Alert>}
          <Stack spacing={2}>
            <TextField label="Phone" value={ceoForm.phone} onChange={(e) => setCeoForm({ ...ceoForm, phone: e.target.value })} />
            <TextField label="Job Title" value={ceoForm.job_title} onChange={(e) => setCeoForm({ ...ceoForm, job_title: e.target.value })} />
            <TextField label="Location" value={ceoForm.location} onChange={(e) => setCeoForm({ ...ceoForm, location: e.target.value })} />
            <TextField label="Bio" multiline minRows={2} value={ceoForm.bio} onChange={(e) => setCeoForm({ ...ceoForm, bio: e.target.value })} />
            <Button variant="contained" disabled={savingCeo} onClick={handleSaveCeoFields} sx={{ bgcolor: CITI_BLUE, alignSelf: 'flex-start', '&:hover': { bgcolor: CITI_BLUE_DARK } }}>
              {savingCeo ? 'Saving...' : 'Save'}
            </Button>
          </Stack>
        </Paper>
      )}

      <Dialog open={phoneDialogOpen} onClose={() => setPhoneDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Request Phone Number Change</DialogTitle>
        <Box component="form" onSubmit={handleSubmitPhoneRequest}>
          <DialogContent>
            {phoneRequestError && <Alert severity="error" sx={{ mb: 2 }}>{phoneRequestError}</Alert>}
            <TextField
              fullWidth
              label="New Phone Number"
              required
              value={newPhone}
              onChange={(e) => setNewPhone(e.target.value)}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setPhoneDialogOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained" sx={{ bgcolor: CITI_BLUE }}>Submit</Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Box>
  )
}

function Field({ label, value }) {
  return (
    <Box>
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>{label}</Typography>
      <Typography variant="body1">{value}</Typography>
    </Box>
  )
}

export default Profile
