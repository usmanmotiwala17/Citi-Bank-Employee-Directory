import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { login as apiLogin, getChangeRequests } from '../services/api'

const AuthContext = createContext(null)

function readStoredEmployee() {
  try {
    const raw = localStorage.getItem('employee')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [employee, setEmployee] = useState(readStoredEmployee)
  const [pendingCount, setPendingCount] = useState(0)

  const refreshPendingCount = useCallback(async () => {
    if (!token || !employee || employee.role === 'EMPLOYEE') {
      setPendingCount(0)
      return
    }
    try {
      const requests = await getChangeRequests(token)
      setPendingCount(requests.length)
    } catch {
      // Sidebar badge just won't update this cycle.
    }
  }, [token, employee])

  useEffect(() => {
    refreshPendingCount()
  }, [refreshPendingCount])

  const login = async (email, password) => {
    const data = await apiLogin(email, password)
    setToken(data.access_token)
    setEmployee(data.employee)
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('employee', JSON.stringify(data.employee))
    return data
  }

  const logout = () => {
    setToken(null)
    setEmployee(null)
    setPendingCount(0)
    localStorage.removeItem('token')
    localStorage.removeItem('employee')
  }

  const updateSelf = (updatedEmployee) => {
    setEmployee(updatedEmployee)
    localStorage.setItem('employee', JSON.stringify(updatedEmployee))
  }

  return (
    <AuthContext.Provider
      value={{ token, employee, login, logout, updateSelf, pendingCount, refreshPendingCount }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
