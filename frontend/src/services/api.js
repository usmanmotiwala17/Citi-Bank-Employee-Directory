import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
})

export async function login(email, password) {
  const response = await api.post('/auth/login', { email, password })
  return response.data
}

export async function getEmployees(token) {
  const response = await api.get('/employees', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data
}

export async function createEmployee(token, data) {
  const response = await api.post('/employees', data, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data
}

export async function updateEmployee(token, id, data) {
  const response = await api.put(`/employees/${id}`, data, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data
}

export async function deleteEmployee(token, id) {
  const response = await api.delete(`/employees/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data
}

export async function getDepartments(token) {
  const response = await api.get('/departments', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data
}

export async function createDepartment(token, data) {
  const response = await api.post('/departments', data, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return response.data
}

export default api
