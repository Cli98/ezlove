import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDevices, getDeviceDetail } from '@/api/devices'

export const useDevicesStore = defineStore('devices', () => {
  const devices = ref([])
  const summary = ref(null)
  const detail = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      const data = await getDevices()
      devices.value = data.devices || []
      summary.value = data.summary || null
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function loadDetail(sn) {
    detail.value = null
    error.value = null
    try {
      detail.value = await getDeviceDetail(sn)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载失败'
      throw e
    }
  }

  return { devices, summary, detail, loading, error, load, loadDetail }
})