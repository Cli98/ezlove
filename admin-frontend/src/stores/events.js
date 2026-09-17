import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getEvents, createEvent, resolveEvent } from '@/api/events'

export const useEventsStore = defineStore('events', () => {
  const events = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function load(params) {
    loading.value = true
    error.value = null
    try {
      events.value = await getEvents(params)
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

  return { events, loading, error, load, create, resolve }
})
