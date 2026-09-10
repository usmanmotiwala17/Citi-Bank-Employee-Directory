import { useCallback, useEffect, useState } from 'react'
import {
  Box, Typography, Alert, Table, TableHead, TableRow, TableCell, TableBody,
  TableContainer, Paper, Button, Chip,
} from '@mui/material'
import { useAuth } from '../context/AuthContext'
import { getChangeRequests, updateChangeRequest } from '../services/api'
import { CITI_BLUE, CITI_BLUE_DARK } from '../theme'

function Requests() {
  const { token, employee, refreshPendingCount } = useAuth()
  const [requests, setRequests] = useState([])
  const [error, setError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const data = await getChangeRequests(token)
      setRequests(data)
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load change requests')
    }
  }, [token])

  useEffect(() => {
    if (employee.role !== 'EMPLOYEE') load()
  }, [employee.role, load])

  if (employee.role === 'EMPLOYEE') {
    return <Alert severity="error">You don't have access to this page.</Alert>
  }

  const handleReview = async (id, status) => {
    setActionError(null)
    setBusyId(id)
    try {
      await updateChangeRequest(token, id, { status })
      setRequests((prev) => prev.filter((r) => r.id !== id))
      await refreshPendingCount()
    } catch (err) {
      setActionError(err.response?.data?.error || 'Failed to update request')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 800, mb: 3 }}>Requests</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {actionError && <Alert severity="error" sx={{ mb: 2 }}>{actionError}</Alert>}

      {requests.length === 0 && !error ? (
        <Typography sx={{ color: 'text.secondary' }}>No pending requests.</Typography>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table sx={{ minWidth: 560 }}>
            <TableHead>
              <TableRow>
                <TableCell>Employee</TableCell>
                <TableCell>Current Phone</TableCell>
                <TableCell>Requested Phone</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {requests.map((req) => (
                <TableRow key={req.id}>
                  <TableCell>{req.employee_name}</TableCell>
                  <TableCell>{req.current_value || '—'}</TableCell>
                  <TableCell>{req.requested_value}</TableCell>
                  <TableCell><Chip size="small" label={req.status} /></TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      variant="contained"
                      disabled={busyId === req.id}
                      onClick={() => handleReview(req.id, 'approved')}
                      sx={{ bgcolor: CITI_BLUE, mr: 1, '&:hover': { bgcolor: CITI_BLUE_DARK } }}
                    >
                      Approve
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      disabled={busyId === req.id}
                      onClick={() => handleReview(req.id, 'rejected')}
                    >
                      Reject
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  )
}

export default Requests
