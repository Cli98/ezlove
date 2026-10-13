import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getElders, createElder, updateElder, getElderFull, getElderTimeline } from '@/api/community'

export const useEldersStore = defineStore('elders', () => {
  const elders = ref([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(10)
  const totalPages = ref(0)
  const current = ref(null)
  const timeline = ref([])
  const timelineTotal = ref(0)
  const timelineHasMore = ref(false)
  const loading = ref(false)
  const error = ref(null)

  async function load(params) {
    loading.value = true
    error.value = null
    try {
      const data = await getElders(params)
      elders.value = Array.isArray(data) ? data : data.items || []
      total.value = Array.isArray(data) ? data.length : data.total || 0
      page.value = Array.isArray(data) ? 1 : data.page || 1
      pageSize.value = Array.isArray(data) ? data.length : data.page_size || 10
      totalPages.value = Array.isArray(data) ? 1 : data.total_pages || 0
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function loadDetail(id) {
    error.value = null
    current.value = null
    try {
      current.value = await getElderFull(id)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载失败'
    }
  }

  async function loadTimeline(id, params = {}) {
    timeline.value = []
    try {
      const data = await getElderTimeline(id, { days: 30, limit: 20, offset: 0, ...params })
      timeline.value = data.items || []
      timelineTotal.value = data.total || 0
      timelineHasMore.value = data.has_more || false
    } catch (e) {
      console.error('加载时间线失败', e)
    }
  }

  async function loadMoreTimeline(id) {
    try {
      const data = await getElderTimeline(id, {
        days: 30,
        limit: 20,
        offset: timeline.value.length,
      })
      timeline.value.push(...(data.items || []))
      timelineHasMore.value = data.has_more || false
    } catch (e) {
      console.error('加载更多时间线失败', e)
    }
  }

  async function create(data) {
    error.value = null
    try {
      await createElder(data)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '创建失败'
      throw e
    }
  }

  async function update(id, data) {
    error.value = null
    try {
      await updateElder(id, data)
      await load()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '更新失败'
      throw e
    }
  }

  return {
    elders, total, page, pageSize, totalPages, current, timeline, timelineTotal, timelineHasMore,
    loading, error,
    load, loadDetail, loadTimeline, loadMoreTimeline, create, update,
  }
})
