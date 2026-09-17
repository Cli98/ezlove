import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDashboard, getBuildingElders, confirmElderActive } from '@/api/community'

export const useDashboardStore = defineStore('dashboard', () => {
  const data = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const presentationMode = ref(false)

  const activeArea = ref(null)
  const expandedBuilding = ref(null)
  const buildingElders = ref([])
  const buildingLoading = ref(false)

  async function load() {
    loading.value = true
    error.value = null
    try {
      data.value = await getDashboard()
      if (!activeArea.value && data.value?.areas?.length) {
        activeArea.value = data.value.areas[0].name
      }
    } catch (e) {
      error.value = e.response?.data?.detail || e.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function loadBuildingElders(building) {
    if (expandedBuilding.value === building) {
      expandedBuilding.value = null
      buildingElders.value = []
      return
    }
    expandedBuilding.value = building
    buildingLoading.value = true
    try {
      buildingElders.value = await getBuildingElders(building)
    } catch (e) {
      buildingElders.value = []
    } finally {
      buildingLoading.value = false
    }
  }

  async function confirmActive(elderId) {
    await confirmElderActive(elderId)
    if (data.value?.workstation?.pending_confirmations) {
      data.value.workstation.pending_confirmations =
        data.value.workstation.pending_confirmations.filter(e => e.id !== elderId)
    }
    if (expandedBuilding.value) {
      const elder = buildingElders.value.find(e => e.id === elderId)
      if (elder) elder.today_active = true
    }
  }

  return {
    data, loading, error, load,
    activeArea, expandedBuilding, buildingElders, buildingLoading,
    loadBuildingElders, confirmActive,
    presentationMode,
  }
})
