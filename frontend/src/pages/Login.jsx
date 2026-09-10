import { useState } from 'react'
import { Box, Paper, Typography, TextField, Button, Alert } from '@mui/material'
import { useAuth } from '../context/AuthContext'
import { CITI_BLUE, CITI_BLUE_DARK } from '../theme'
import CitiLogo from '../components/CitiLogo'

function Login() {
  const { login } = useAuth()
  const [email, setEmail] = useState('robert.chen@acme.com')
  const [password, setPassword] = useState('ceopass123')
  const [error, setError] = useState(null)
  const [loggingIn, setLoggingIn] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoggingIn(true)
    try {
      await login(email, password)
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed')
    } finally {
      setLoggingIn(false)
    }
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        bgcolor: '#f4f6f8',
      }}
    >
      <Paper elevation={2} sx={{ p: 4, width: 380, maxWidth: '90vw' }}>
        <CitiLogo fontSize="1.8rem" />
        <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3, mt: 0.5 }}>
          Sign in to the Employee Directory
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            fullWidth
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            sx={{ mb: 3 }}
          />
          <Button
            fullWidth
            type="submit"
            variant="contained"
            disabled={loggingIn}
            sx={{ bgcolor: CITI_BLUE, py: 1.1, '&:hover': { bgcolor: CITI_BLUE_DARK } }}
          >
            {loggingIn ? 'Logging in...' : 'Log In'}
          </Button>
        </Box>
      </Paper>
    </Box>
  )
}

export default Login
