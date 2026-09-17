import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getVolunteers, getTasks, createTask, verifyTask, getLeaderboard } from '@/api/volunteer'

export const useVolunteerStore = defineStore('volunteer', () => {
  const volunteers = ref([])
  const tasks = ref([])
  const leaderboard = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function loadVolunteers() {
    loading.value = true
    error.value = null
    try {
      volunteers.value = await getVolunteers()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function loadTasks(params) {
    loading.value = true
    error.value = null
    try {
      tasks.value = await getTasks(params)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function loadLeaderboard() {
    loading.value = true
    error.value = null
    try {
      leaderboard.value = await getLeaderboard()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function create(data) {
    error.value = null
    try {
      await createTask(data)
      await loadTasks()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '创建失败'
      throw e
    }
  }

  async function verify(id) {
    error.value = null
    try {
      await verifyTask(id)
      await loadTasks()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '审核失败'
      throw e
    }
  }

  return { volunteers, tasks, leaderboard, loading, error, loadVolunteers, loadTasks, loadLeaderboard, create, verify }
})
