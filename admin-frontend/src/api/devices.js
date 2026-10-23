import { api } from './request'

export const getDevices = () => api.get('/community/devices')
export const getDeviceDetail = (sn) => api.get(`/community/devices/${sn}`)
export const getElderRiskHistory = (elderId, days = 30) => api.get(`/community/elders/${elderId}/risk/history`, { days })