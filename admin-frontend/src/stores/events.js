import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getEvents, createEvent, resolveEvent } from '@/api/events'

export const useEventsStore = defineStore('events', () => {
  const events = ref([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const totalPages = ref(0)
  const loading = ref(false)
  const error = ref(null)

  async function load(params) {
    loading.value = true
    error.value = null
    try {
      const data = await getEvents(params)
      events.value = Array.isArray(data) ? data : data.items || []
      total.value = Array.isArray(data) ? data.length : data.total || 0
      page.value = Array.isArray(data) ? 1 : data.page || 1
      pageSize.value = Array.isArray(data) ? data.length : data.page_size || 20
      totalPages.value = Array.isArray(data) ? 1 : data.total_pages || 0
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function create(data) {
    error.value = null
    try {
      await createEvent(data)
      await load()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '创建失败'
      throw e
    }
  }

  async function resolve(id, data) {
    error.value = null
    try {
      await resolveEvent(id, data)
      await load()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '处理失败'
      throw e
    }
  }

  return { events, total, page, pageSize, totalPages, loading, error, load, create, resolve }
})
