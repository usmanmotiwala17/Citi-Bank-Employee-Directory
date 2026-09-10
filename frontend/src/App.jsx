import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider, CssBaseline } from '@mui/material'
import Box from '@mui/material/Box'
import { theme } from './theme'
import { AuthProvider, useAuth } from './context/AuthContext'
import Sidebar, { SIDEBAR_WIDTH } from './components/Sidebar'
import Login from './pages/Login'
import Directory from './pages/Directory'
import Requests from './pages/Requests'
import Profile from './pages/Profile'

function Shell() {
  const { token, employee } = useAuth()

  if (!token || !employee) {
    return <Login />
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: '#f4f6f8' }}>
      <Sidebar />
      <Box component="main" sx={{ flexGrow: 1, width: `calc(100% - ${SIDEBAR_WIDTH}px)`, p: 4 }}>
        <Routes>
          <Route path="/" element={<Directory />} />
          <Route path="/requests" element={<Requests />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Box>
    </Box>
  )
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AuthProvider>
          <Shell />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
