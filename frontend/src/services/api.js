import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
})

function authHeaders(token) {
  return { headers: { Authorization: `Bearer ${token}` } }
}

export async function login(email, password) {
  const response = await api.post('/auth/login', { email, password })
  return response.data
}

export async function getEmployees(token) {
  const response = await api.get('/employees', authHeaders(token))
  return response.data
}

export async function getEmployee(token, id) {
  const response = await api.get(`/employees/${id}`, authHeaders(token))
  return response.data
}

export async function createEmployee(token, data) {
  const response = await api.post('/employees', data, authHeaders(token))
  return response.data
}

export async function updateEmployee(token, id, data) {
  const response = await api.put(`/employees/${id}`, data, authHeaders(token))
  return response.data
}

export async function deleteEmployee(token, id) {
  const response = await api.delete(`/employees/${id}`, authHeaders(token))
  return response.data
}

export async function getDepartments(token) {
  const response = await api.get('/departments', authHeaders(token))
  return response.data
}

export async function createDepartment(token, data) {
  const response = await api.post('/departments', data, authHeaders(token))
  return response.data
}

export async function getChangeRequests(token) {
  const response = await api.get('/change-requests', authHeaders(token))
  return response.data
}

export async function createChangeRequest(token, data) {
  const response = await api.post('/change-requests', data, authHeaders(token))
  return response.data
}

export async function updateChangeRequest(token, id, data) {
  const response = await api.put(`/change-requests/${id}`, data, authHeaders(token))
  return response.data
}

export default api
