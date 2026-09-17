import { api } from './request'

export const getVolunteers = () => api.get('/volunteer/admin/volunteers')
export const getTasks = (params) => api.get('/volunteer/admin/tasks', params)
export const createTask = (data) => api.post('/volunteer/admin/tasks', data)
export const verifyTask = (id) => api.put(`/volunteer/admin/tasks/${id}/verify`)
export const getLeaderboard = () => api.get('/volunteer/admin/leaderboard')
