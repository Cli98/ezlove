import { api } from './request'

export const getContributors = () => api.get('/contributors')
