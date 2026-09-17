import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getCommunities, switchCommunity as switchApi } from '@/api/auth'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  const worker = ref(JSON.parse(localStorage.getItem('community_worker') || 'null'))
  const token = ref(localStorage.getItem('community_access_token') || '')
  const communities = ref([])
  const currentCommunityId = ref(localStorage.getItem('community_current_id') || '')

  const isLoggedIn = computed(() => !!token.value)

  const currentCommunityName = computed(() => {
    const found = communities.value.find(c => c.community_id === currentCommunityId.value)
    return found?.community_name || ''
  })

  async function login(phone, password) {
    const data = await loginApi(phone, password)
    token.value = data.access_token
    worker.value = data.worker
    currentCommunityId.value = data.worker.community_id
    localStorage.setItem('community_access_token', data.access_token)
    localStorage.setItem('community_current_id', data.worker.community_id)
    if (data.refresh_token) {
      localStorage.setItem('community_refresh_token', data.refresh_token)
    }
    localStorage.setItem('community_worker', JSON.stringify(data.worker))
    router.push('/')
  }

  async function loadCommunities() {
    try {
      communities.value = await getCommunities()
      if (!currentCommunityId.value && worker.value?.community_id) {
        currentCommunityId.value = worker.value.community_id
      }
    } catch (e) {
      communities.value = []
    }
  }

  async function switchCommunity(communityId) {
    const data = await switchApi(communityId)
    token.value = data.access_token
    currentCommunityId.value = data.community_id
    localStorage.setItem('community_access_token', data.access_token)
    localStorage.setItem('community_current_id', data.community_id)
    if (data.refresh_token) {
      localStorage.setItem('community_refresh_token', data.refresh_token)
    }
  }

  function logout() {
    token.value = ''
    worker.value = null
    communities.value = []
    currentCommunityId.value = ''
    localStorage.removeItem('community_access_token')
    localStorage.removeItem('community_refresh_token')
    localStorage.removeItem('community_worker')
    localStorage.removeItem('community_current_id')
    router.push('/login')
  }

  return {
    worker, token, communities, currentCommunityId, currentCommunityName,
    isLoggedIn, login, logout, loadCommunities, switchCommunity,
  }
})
