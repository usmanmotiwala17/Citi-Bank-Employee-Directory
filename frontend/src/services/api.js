import axios from 'axios'

// In production, VITE_API_URL is the CloudFront domain and VITE_API_ENDPOINTS
// maps each backend service to its path prefix behind that domain (e.g.
// "/api/employee-service") - see bin/generate-env.sh. Locally, neither is
// set, so this falls back to local_server.py's unprefixed localhost:8000.
const API_ENDPOINTS = (() => {
  try {
    return JSON.parse(import.meta.env.VITE_API_ENDPOINTS || '{}')
  } catch {
    return {}
  }
})()

const api = axios.create({
  baseURL: (import.meta.env.VITE_API_URL || 'http://localhost:8000') + (API_ENDPOINTS['employee-service'] || ''),
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
