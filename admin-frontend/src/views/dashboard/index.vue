<template>
  <div class="dashboard-page">
    <DashboardHero
      v-model:search="searchKeyword"
      :worker-name="userStore.worker?.name || '社工'"
      :pending-events="store.data?.pending_events || 0"
      @events="router.push('/events')"
      @search="goToElders"
    />

    <AppStatBar :stats="focusStats" />

    <div class="dashboard-grid">
      <PriorityCareList
        :items="priorityItems"
        :loading="store.loading && !store.data"
        @all="router.push('/events')"
        @view="viewElder"
      />
      <div class="dashboard-side">
        <AreaCareOverview :areas="areaOverview" @all="router.push('/elders')" />
        <GoodNewsCard :items="goodNews" @all="router.push('/elders')" />
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'
import { useUserStore } from '@/stores/user'
import DashboardHero from './components/DashboardHero.vue'
import AppStatBar from '@/components/AppStatBar.vue'
import PriorityCareList from './components/PriorityCareList.vue'
import AreaCareOverview from './components/AreaCareOverview.vue'
import GoodNewsCard from './components/GoodNewsCard.vue'
import elder1 from '@/assets/dashboard-reference/elder-1.png'
import elder2 from '@/assets/dashboard-reference/elder-2.png'
import elder3 from '@/assets/dashboard-reference/elder-3.png'
import elder4 from '@/assets/dashboard-reference/elder-4.png'

const router = useRouter()
const store = useDashboardStore()
const userStore = useUserStore()
const searchKeyword = ref('')
let refreshTimer
const elderAvatars = [elder1, elder2, elder3, elder4]

onMounted(() => {
  store.load()
  refreshTimer = window.setInterval(() => store.load(), 30000)
})
onUnmounted(() => window.clearInterval(refreshTimer))

const workstation = computed(() => store.data?.workstation || {})
const confirmations = computed(() => workstation.value.pending_confirmations || [])
const pendingAlerts = computed(() => workstation.value.pending_alerts || [])
const timedOut = computed(() => workstation.value.timed_out || [])

const focusStats = computed(() => [
  { label: '位待核实', value: confirmations.value.length, detail: '有异常信号，需确认情况', icon: 'clipboard', tone: 'terracotta' },
  { label: '位待跟进', value: pendingAlerts.value.length, detail: '已接收，稍后续关注', icon: 'people', tone: 'amber' },
  { label: '项临近响应时间', value: timedOut.value.length, detail: timedOut.value.length ? '请及时处理，避免超时' : '当前没有超时事项', icon: 'clock', tone: 'sage' },
])

const priorityItems = computed(() => {
  const confirmationItems = confirmations.value.map((elder, index) => ({
    id: elder.id,
    elderId: elder.id,
    avatar: elderAvatars[index % elderAvatars.length],
    name: elder.name,
    address: elder.address,
    careLevel: elder.care_level,
    message: '今天还未看到日常动态，建议电话问候一下。',
    time: index === 0 ? '今日待确认' : '今天',
    source: '日常关怀提醒',
    sourceDetail: '等待确认',
    icon: index % 2 ? 'heart' : 'bowl',
    tone: 'terracotta',
  }))
  const alertItems = pendingAlerts.value.map((alert, index) => ({
    id: alert.id,
    avatar: elderAvatars[(confirmationItems.length + index) % elderAvatars.length],
    name: alert.elder_name,
    address: '社区居民',
    careLevel: alert.alert_level === 'critical' ? 'A' : 'B',
    message: alert.message || '有一条需要关注的社区动态。',
    time: formatTime(alert.created_at),
    source: alert.trigger_rule || '关怀事件',
    sourceDetail: alert.alert_level === 'critical' ? '请优先处理' : '等待跟进',
    icon: alert.alert_type === 'canteen' ? 'bowl' : 'heart',
    tone: alert.alert_level === 'critical' ? 'terracotta' : 'amber',
  }))
  return [...confirmationItems, ...alertItems]
})

const areaOverview = computed(() => (store.data?.areas || []).map(area => {
  const buildings = area.buildings || []
  const count = buildings.reduce((sum, building) => sum + building.elder_count, 0)
  const active = buildings.reduce((sum, building) => sum + building.active_count, 0)
  return { name: area.name, count, rate: count ? Math.round(active / count * 100) : 0 }
}))

const goodNews = computed(() => {
  const active = store.data?.today_active_count || 0
  const rate = store.data?.today_active_rate || 0
  return [
    { icon: 'heart', tone: 'heart', text: `今天已有 ${active} 位老人留下温暖日常`, time: '今天' },
    { icon: 'bowl', tone: 'food', text: `今日社区活跃率达到 ${rate}%`, time: '更新中' },
    { icon: 'walk', tone: 'walk', text: '每一次日常互动，都让牵挂更安心', time: '社区' },
  ]
})

function formatTime(value) {
  if (!value) return '刚刚'
  const date = new Date(value)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function viewElder(id) {
  router.push(id ? `/elders/${id}` : '/elders')
}

function goToElders() {
  router.push({ path: '/elders', query: searchKeyword.value ? { search: searchKeyword.value } : {} })
}
</script>

<style scoped>
.dashboard-page { display: grid; height: 100%; grid-template-rows: auto auto minmax(0, 1fr); }.dashboard-grid { display: grid; min-height: 0; overflow: hidden; grid-template-columns: minmax(0, 1fr) 388px; gap: 14px; align-items: stretch; }.dashboard-side { display: grid; height: 100%; min-height: 0; overflow: hidden; grid-template-rows: minmax(0, 3fr) minmax(0, 2fr); gap: 13px; }
@media (max-width: 1180px) { .dashboard-grid { grid-template-columns: minmax(0, 1fr) 330px; } } @media (max-width: 1050px) { .dashboard-page { height: auto; min-height: 100%; }.dashboard-grid { overflow: visible; grid-template-columns: 1fr; }.dashboard-side { height: auto; overflow: visible; grid-template-rows: auto; } }
</style>
