import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getElders, createElder, updateElder, getElderFull, getElderTimeline } from '@/api/community'

export const useEldersStore = defineStore('elders', () => {
  const elders = ref([])
  const current = ref(null)
  const timeline = ref([])
  const timelineTotal = ref(0)
  const timelineHasMore = ref(false)
  const loading = ref(false)
  const error = ref(null)
  const total = ref(0)
  const page = ref(1)
  const totalPages = ref(1)
  const pageSize = ref(20)
  let lastParams = {}

  // 参数语义：传 params（筛选/搜索变化）时回到第 1 页；不传时用上次条件刷新（配合 goToPage 翻页）
  async function load(params) {
    loading.value = true
    error.value = null
    try {
      if (params) {
        lastParams = { ...params }
        page.value = 1
      }
      const data = await getElders({ page: page.value, page_size: pageSize.value, ...lastParams })
      elders.value = data.items || []
      total.value = data.total || 0
      totalPages.value = data.total_pages || 1
      page.value = data.page || page.value
      return true
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载失败'
      return false
    } finally {
      loading.value = false
    }
  }

  function goToPage(target) {
    const p = Math.min(Math.max(1, target), totalPages.value)
    if (p === page.value) return
    const prev = page.value
    page.value = p
    load().then((ok) => { if (!ok) page.value = prev })
  }

  async function loadDetail(id) {
    error.value = null
    try {
      current.value = await getElderFull(id)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载失败'
    }
  }

  async function loadTimeline(id, params = {}) {
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
      await load()
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
    elders, current, timeline, timelineTotal, timelineHasMore,
    loading, error,
    total, page, totalPages, pageSize,
    load, loadDetail, loadTimeline, loadMoreTimeline, create, update, goToPage,
  }
})
