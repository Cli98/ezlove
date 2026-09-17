import { api } from './request'
import request from './request'

export const submitCanteen = (formData) =>
  request.post('/community/canteen/submit', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
export const getCanteenRecords = () => api.get('/community/canteen/records')
export const getCanteenRecord = (id) => api.get(`/community/canteen/records/${id}`)
export const correctCanteenRecord = (id, data) =>
  api.put(`/community/canteen/records/${id}`, data)

export const generateMenu = (formData) =>
  request.post('/community/canteen/menu/generate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
export const getMenus = () => api.get('/community/canteen/menus')
export const updateMenu = (id, data) => api.put(`/community/canteen/menu/${id}`, data)
export const publishMenu = (id) => api.post(`/community/canteen/menu/${id}/publish`)
export const deleteMenu = (id) => api.delete(`/community/canteen/menu/${id}`)
