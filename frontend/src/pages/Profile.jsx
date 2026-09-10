import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box, Typography, Paper, Chip, TextField, Button, Alert, Dialog,
  DialogTitle, DialogContent, DialogActions, Stack, Grid, MenuItem,
  Select, InputLabel, FormControl, Switch, FormControlLabel,
} from '@mui/material'
import PhoneIcon from '@mui/icons-material/Phone'
import EmailIcon from '@mui/icons-material/Email'
import EmployeeAvatar from '../components/EmployeeAvatar'
import AvailabilityIndicator from '../components/AvailabilityIndicator'
import { roleLabel } from '../utils/roleLabel'
import { useAuth } from '../context/AuthContext'
import { getEmployee, getDepartments, updateEmployee, createChangeRequest } from '../services/api'
import { CITI_BLUE, CITI_BLUE_DARK } from '../theme'

function parseSkills(text) {
  return text.split(',').map((s) => s.trim()).filter(Boolean)
}

function Profile() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { token, employee: authEmployee, updateSelf } = useAuth()

  const targetId = id ? Number(id) : authEmployee.id
  const isSelf = targetId === authEmployee.id

  const [employee, setEmployee] = useState(null)
  const [departments, setDepartments] = useState([])
  const [loadError, setLoadError] = useState(null)

  const [editDraft, setEditDraft] = useState(null)
  const [savingEdit, setSavingEdit] = useState(false)
  const [editError, setEditError] = useState(null)
  const [editSaved, setEditSaved] = useState(false)

  const [otherEditDraft, setOtherEditDraft] = useState(null)
  const [savingOther, setSavingOther] = useState(false)
  const [otherEditError, setOtherEditError] = useState(null)
  const [otherEditSaved, setOtherEditSaved] = useState(false)

  const [notesDraft, setNotesDraft] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)
  const [notesError, setNotesError] = useState(null)
  const [notesSaved, setNotesSaved] = useState(false)

  const [phoneDialogOpen, setPhoneDialogOpen] = useState(false)
  const [newPhone, setNewPhone] = useState('')
  const [phoneRequestError, setPhoneRequestError] = useState(null)
  const [phoneRequestSent, setPhoneRequestSent] = useState(false)

  useEffect(() => {
    setLoadError(null)
    setEditSaved(false)
    setOtherEditSaved(false)
    setNotesSaved(false);
    (async () => {
      try {
        const [freshEmployee, depts] = await Promise.all([
          getEmployee(token, targetId),
          getDepartments(token),
        ])
        setEmployee(freshEmployee)
        setDepartments(depts)
        setEditDraft({
          skills: (freshEmployee.skills || []).join(', '),
          availability_status: freshEmployee.availability_status || 'available',
          phone: freshEmployee.phone || '',
          job_title: freshEmployee.job_title || '',
          location: freshEmployee.location || '',
          bio: freshEmployee.bio || '',
        })
        setOtherEditDraft({
          first_name: freshEmployee.first_name || '',
          last_name: freshEmployee.last_name || '',
          email: freshEmployee.email || '',
          phone: freshEmployee.phone || '',
          job_title: freshEmployee.job_title || '',
          location: freshEmployee.location || '',
          skills: (freshEmployee.skills || []).join(', '),
          is_active: freshEmployee.is_active,
        })
        setNotesDraft(freshEmployee.manager_notes || '')
      } catch (err) {
        setLoadError(err.response?.data?.error || 'Failed to load this profile')
      }
    })()
  }, [token, targetId])

  if (loadError) {
    return <Alert severity="error" sx={{ maxWidth: 640 }}>{loadError}</Alert>
  }
  if (!employee || !editDraft) {
    return null
  }

  const isAdmin = employee.role === 'ADMIN'
  const isManager = employee.role === 'MANAGER'
  const departmentName = departments.find((d) => d.id === employee.department_id)?.name
  const canSeeManagerNotes = !isSelf && 'manager_notes' in employee

  // Editing someone else's profile: an ADMIN can edit anyone; a MANAGER can
  // edit only phone/email/status, and only for their own direct reports.
  // employee.manager (from the backend's _enrich_with_org_structure) is the
  // target's actual manager, so comparing its id to our own id tells us
  // whether we're that manager - this mirrors the backend's
  // _is_direct_manager check exactly, it's just re-derived client-side for
  // the UI. The backend is still the real enforcement point either way.
  const canEditAsAdmin = !isSelf && authEmployee.role === 'ADMIN'
  const canEditAsDirectManager = !isSelf && authEmployee.role === 'MANAGER' && employee.manager?.id === authEmployee.id
  const canEditOther = canEditAsAdmin || canEditAsDirectManager

  const goToProfile = (personId) => navigate(`/employees/${personId}`)

  const handleSaveEdit = async () => {
    setEditError(null)
    setEditSaved(false)
    setSavingEdit(true)
    try {
      const body = {
        skills: parseSkills(editDraft.skills),
        availability_status: editDraft.availability_status,
      }
      if (isAdmin) {
        body.phone = editDraft.phone
        body.job_title = editDraft.job_title
        body.location = editDraft.location
        body.bio = editDraft.bio
      } else if (isManager) {
        // Managers can edit their own phone directly - no change-request
        // needed, unlike a plain Employee. Only for their own record; see
        // canEditAsDirectManager for the (narrower) rule on editing someone
        // else's phone.
        body.phone = editDraft.phone
      }
      const updated = await updateEmployee(token, employee.id, body)
      setEmployee(updated)
      updateSelf(updated)
      setEditSaved(true)
    } catch (err) {
      setEditError(err.response?.data?.error || 'Failed to save profile')
    } finally {
      setSavingEdit(false)
    }
  }

  const handleSaveOtherEdit = async () => {
    setOtherEditError(null)
    setOtherEditSaved(false)
    setSavingOther(true)
    try {
      const body = canEditAsAdmin
        ? {
            first_name: otherEditDraft.first_name,
            last_name: otherEditDraft.last_name,
            email: otherEditDraft.email,
            phone: otherEditDraft.phone,
            job_title: otherEditDraft.job_title,
            location: otherEditDraft.location,
            skills: parseSkills(otherEditDraft.skills),
            is_active: otherEditDraft.is_active,
          }
        : {
            // Direct manager, not admin: only phone/email/status.
            phone: otherEditDraft.phone,
            email: otherEditDraft.email,
            is_active: otherEditDraft.is_active,
          }
      const updated = await updateEmployee(token, employee.id, body)
      setEmployee(updated)
      setOtherEditSaved(true)
    } catch (err) {
      setOtherEditError(err.response?.data?.error || 'Failed to update employee')
    } finally {
      setSavingOther(false)
    }
  }

  const handleSaveNotes = async () => {
    setNotesError(null)
    setNotesSaved(false)
    setSavingNotes(true)
    try {
      const updated = await updateEmployee(token, employee.id, { manager_notes: notesDraft })
      setEmployee(updated)
      setNotesSaved(true)
    } catch (err) {
      setNotesError(err.response?.data?.error || 'Failed to save notes')
    } finally {
      setSavingNotes(false)
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

  const cardSize = { xs: 12, sm: 6, md: 4 }

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 800, mb: 3 }}>
        {isSelf ? 'My Profile' : `${employee.first_name} ${employee.last_name}`}
      </Typography>

      {phoneRequestSent && <Alert severity="success" sx={{ mb: 2 }}>Phone number change request submitted for review.</Alert>}

      <Grid container spacing={3}>
        {/* Identity banner - full width, purely introductory */}
        <Grid size={{ xs: 12 }}>
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Stack direction="row" spacing={2} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
              <EmployeeAvatar employee={employee} size={72} />
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>{employee.first_name} {employee.last_name}</Typography>
                <Typography variant="body2" sx={{ color: 'text.secondary', mb: 0.5 }}>
                  {roleLabel(employee.role)}{departmentName ? ` · ${departmentName}` : ''}
                </Typography>
                <AvailabilityIndicator status={employee.availability_status} />
              </Box>
            </Stack>
          </Paper>
        </Grid>

        {/* Overview */}
        <Grid size={cardSize}>
          <Paper variant="outlined" sx={{ p: 3, height: '100%' }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>Overview</Typography>
            <Stack spacing={1.5}>
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
              {employee.bio && <Field label="Bio" value={employee.bio} />}
            </Stack>
          </Paper>
        </Grid>

        {/* Contact Information - visually distinct from the rest of the bio/job info */}
        <Grid size={cardSize}>
          <Paper variant="outlined" sx={{ p: 3, height: '100%', bgcolor: '#eef6fb', borderColor: CITI_BLUE }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>Contact Information</Typography>
            <Stack spacing={2}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
                <PhoneIcon sx={{ color: CITI_BLUE }} />
                {employee.phone ? (
                  <Typography
                    component="a"
                    href={`tel:${employee.phone}`}
                    variant="h6"
                    sx={{ fontWeight: 600, color: 'inherit', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}
                  >
                    {employee.phone}
                  </Typography>
                ) : (
                  <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.secondary' }}>Not provided</Typography>
                )}
                {isSelf && !isAdmin && !isManager && (
                  <Button size="small" onClick={() => setPhoneDialogOpen(true)}>Request Change</Button>
                )}
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <EmailIcon sx={{ color: CITI_BLUE }} />
                <Typography
                  component="a"
                  href={`mailto:${employee.email}`}
                  variant="h6"
                  sx={{ fontWeight: 600, color: 'inherit', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}
                >
                  {employee.email}
                </Typography>
              </Box>
            </Stack>
          </Paper>
        </Grid>

        {employee.manager && (
          <Grid size={cardSize}>
            <Paper variant="outlined" sx={{ p: 3, height: '100%' }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>Reports To</Typography>
              <ProfileLink onClick={() => goToProfile(employee.manager.id)}>
                {employee.manager.first_name} {employee.manager.last_name}
              </ProfileLink>
              {employee.manager.job_title && (
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>{employee.manager.job_title}</Typography>
              )}
            </Paper>
          </Grid>
        )}

        {employee.direct_reports && (
          <Grid size={cardSize}>
            <Paper variant="outlined" sx={{ p: 3, height: '100%' }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
                Direct Reports ({employee.direct_reports.length})
              </Typography>
              {employee.direct_reports.length === 0 ? (
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>No direct reports.</Typography>
              ) : (
                <Stack spacing={1}>
                  {employee.direct_reports.map((report) => (
                    <Box key={report.id}>
                      <ProfileLink onClick={() => goToProfile(report.id)}>
                        {report.first_name} {report.last_name}
                      </ProfileLink>
                      {report.job_title && (
                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>{report.job_title}</Typography>
                      )}
                    </Box>
                  ))}
                </Stack>
              )}
            </Paper>
          </Grid>
        )}

        {canSeeManagerNotes && (
          <Grid size={cardSize}>
            <Paper variant="outlined" sx={{ p: 3, height: '100%' }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Manager Notes</Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1.5 }}>
                Visible only to you and the Admin.
              </Typography>
              {notesError && <Alert severity="error" sx={{ mb: 2 }}>{notesError}</Alert>}
              {notesSaved && <Alert severity="success" sx={{ mb: 2 }}>Notes updated.</Alert>}
              <TextField
                fullWidth
                multiline
                minRows={3}
                placeholder="Performance observations, growth areas, things to follow up on..."
                value={notesDraft}
                onChange={(e) => setNotesDraft(e.target.value)}
                sx={{ mb: 2 }}
              />
              <Button variant="contained" disabled={savingNotes} onClick={handleSaveNotes} sx={{ bgcolor: CITI_BLUE, '&:hover': { bgcolor: CITI_BLUE_DARK } }}>
                {savingNotes ? 'Saving...' : 'Save Notes'}
              </Button>
            </Paper>
          </Grid>
        )}

        {canEditOther && (
          <Grid size={{ xs: 12 }}>
            <Paper variant="outlined" sx={{ p: 3 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>Edit Employee</Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1.5 }}>
                {canEditAsAdmin
                  ? 'As an Admin, you can edit any field on this profile.'
                  : 'As their direct manager, you can edit phone, email, and status.'}
              </Typography>
              {otherEditError && <Alert severity="error" sx={{ mb: 2 }}>{otherEditError}</Alert>}
              {otherEditSaved && <Alert severity="success" sx={{ mb: 2 }}>Employee updated.</Alert>}
              <Grid container spacing={2}>
                {canEditAsAdmin && (
                  <>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField fullWidth label="First Name" value={otherEditDraft.first_name} onChange={(e) => setOtherEditDraft({ ...otherEditDraft, first_name: e.target.value })} />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField fullWidth label="Last Name" value={otherEditDraft.last_name} onChange={(e) => setOtherEditDraft({ ...otherEditDraft, last_name: e.target.value })} />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField fullWidth label="Job Title" value={otherEditDraft.job_title} onChange={(e) => setOtherEditDraft({ ...otherEditDraft, job_title: e.target.value })} />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField fullWidth label="Location" value={otherEditDraft.location} onChange={(e) => setOtherEditDraft({ ...otherEditDraft, location: e.target.value })} />
                    </Grid>
                    <Grid size={{ xs: 12 }}>
                      <TextField fullWidth label="Skills (comma-separated)" value={otherEditDraft.skills} onChange={(e) => setOtherEditDraft({ ...otherEditDraft, skills: e.target.value })} />
                    </Grid>
                  </>
                )}
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField fullWidth label="Phone" value={otherEditDraft.phone} onChange={(e) => setOtherEditDraft({ ...otherEditDraft, phone: e.target.value })} />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField fullWidth label="Email" type="email" value={otherEditDraft.email} onChange={(e) => setOtherEditDraft({ ...otherEditDraft, email: e.target.value })} />
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <FormControlLabel
                    control={<Switch checked={otherEditDraft.is_active} onChange={(e) => setOtherEditDraft({ ...otherEditDraft, is_active: e.target.checked })} />}
                    label="Active"
                  />
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <Button variant="contained" disabled={savingOther} onClick={handleSaveOtherEdit} sx={{ bgcolor: CITI_BLUE, '&:hover': { bgcolor: CITI_BLUE_DARK } }}>
                    {savingOther ? 'Saving...' : 'Save'}
                  </Button>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        )}

        {isSelf && (
          <Grid size={{ xs: 12 }}>
            <Paper variant="outlined" sx={{ p: 3 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>Edit Profile Details</Typography>
              {editError && <Alert severity="error" sx={{ mb: 2 }}>{editError}</Alert>}
              {editSaved && <Alert severity="success" sx={{ mb: 2 }}>Profile updated.</Alert>}
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <TextField
                    fullWidth
                    label="Skills (comma-separated)"
                    value={editDraft.skills}
                    onChange={(e) => setEditDraft({ ...editDraft, skills: e.target.value })}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <FormControl fullWidth>
                    <InputLabel id="availability-edit-label">Availability</InputLabel>
                    <Select
                      labelId="availability-edit-label"
                      label="Availability"
                      value={editDraft.availability_status}
                      onChange={(e) => setEditDraft({ ...editDraft, availability_status: e.target.value })}
                    >
                      <MenuItem value="available">Available</MenuItem>
                      <MenuItem value="unavailable">Unavailable</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                {isAdmin && (
                  <>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField fullWidth label="Phone" value={editDraft.phone} onChange={(e) => setEditDraft({ ...editDraft, phone: e.target.value })} />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField fullWidth label="Job Title" value={editDraft.job_title} onChange={(e) => setEditDraft({ ...editDraft, job_title: e.target.value })} />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField fullWidth label="Location" value={editDraft.location} onChange={(e) => setEditDraft({ ...editDraft, location: e.target.value })} />
                    </Grid>
                    <Grid size={{ xs: 12 }}>
                      <TextField fullWidth label="Bio" multiline minRows={2} value={editDraft.bio} onChange={(e) => setEditDraft({ ...editDraft, bio: e.target.value })} />
                    </Grid>
                  </>
                )}
                {isManager && (
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <TextField fullWidth label="Phone" value={editDraft.phone} onChange={(e) => setEditDraft({ ...editDraft, phone: e.target.value })} />
                  </Grid>
                )}
                <Grid size={{ xs: 12 }}>
                  <Button variant="contained" disabled={savingEdit} onClick={handleSaveEdit} sx={{ bgcolor: CITI_BLUE, '&:hover': { bgcolor: CITI_BLUE_DARK } }}>
                    {savingEdit ? 'Saving...' : 'Save'}
                  </Button>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        )}
      </Grid>

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

function ProfileLink({ onClick, children }) {
  return (
    <Typography
      component="span"
      onClick={onClick}
      sx={{
        color: CITI_BLUE,
        fontWeight: 700,
        cursor: 'pointer',
        '&:hover': { textDecoration: 'underline' },
      }}
    >
      {children}
    </Typography>
  )
}

export default Profile
