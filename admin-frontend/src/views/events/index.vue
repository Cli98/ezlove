<template>
  <div class="events-page">
    <PageTopbar
      v-model:search="topSearch"
      :worker-name="workerName"
      :pending-events="pendingCount"
      @events="scrollToList"
      @search="goToElders"
    />

    <header class="events-heading">
      <div><h1>关怀事件</h1><p>把需要回应的关怀事项安排清楚</p></div>
      <div class="events-actions">
        <AppButton variant="outline" wide @click="handleExport"><span class="material-symbols-outlined">ios_share</span>导出 Excel</AppButton>
        <AppButton wide @click="openCreate"><span class="material-symbols-outlined">add_circle</span>手动新增</AppButton>
      </div>
    </header>

    <AppStatBar :stats="stats" />
    <EventFilters v-model:status="filters.status" v-model:severity="filters.severity" v-model:source="filters.source" v-model:search="filters.search" />
    <EventTable
      ref="eventTable"
      :rows="pagedRows"
      :loading="eventsStore.loading"
      :total="filteredRows.length"
      :page="page"
      :page-size="pageSize"
      :total-pages="totalPages"
      @process="openProcess"
      @profile="viewProfile"
      @page="page = $event"
      @page-size="changePageSize"
    />

    <EventDialog :open="dialog.open" :mode="dialog.mode" :event="dialog.event" :elders="displayElders" :submitting="submitting" @close="closeDialog" @submit="submitDialog" />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useDashboardStore } from '@/stores/dashboard'
import { useEldersStore } from '@/stores/elders'
import { useEventsStore } from '@/stores/events'
import { useUserStore } from '@/stores/user'
import { downloadExport } from '@/api/export'
import AppButton from '@/components/AppButton.vue'
import AppStatBar from '@/components/AppStatBar.vue'
import PageTopbar from '@/components/PageTopbar.vue'
import EventDialog from './components/EventDialog.vue'
import EventFilters from './components/EventFilters.vue'
import EventTable from './components/EventTable.vue'
import { mockElders } from '@/mocks/elders'
import { mockEvents } from '@/mocks/events'

const router = useRouter()
const eventsStore = useEventsStore()
const eldersStore = useEldersStore()
const dashboardStore = useDashboardStore()
const userStore = useUserStore()
const topSearch = ref('')
const eventTable = ref(null)
const submitting = ref(false)
const page = ref(1)
const pageSize = ref(10)
const filters = reactive({ status: 'all', severity: '', source: '', search: '' })
const dialog = reactive({ open: false, mode: 'create', event: null })

const workerName = computed(() => userStore.worker?.name || '社工')
const displayElders = computed(() => eldersStore.elders.length ? eldersStore.elders : mockElders)
const elderMap = computed(() => new Map(displayElders.value.map(elder => [String(elder.id), elder])))
const sourceRows = computed(() => eventsStore.events.length ? eventsStore.events : mockEvents)
const decoratedRows = computed(() => sourceRows.value.map((row, index) => decorateRow(row, index)))
const filteredRows = computed(() => decoratedRows.value.filter(row => {
  const keyword = filters.search.trim().toLowerCase()
  if (filters.status !== 'all' && row.status_key !== filters.status) return false
  if (filters.severity && row.severity !== filters.severity) return false
  if (filters.source && row.source !== filters.source) return false
  return !keyword || `${row.elder_name}${row.elder_address}${row.description}${row.source_label}`.toLowerCase().includes(keyword)
}))
const totalPages = computed(() => Math.ceil(filteredRows.value.length / pageSize.value))
const pagedRows = computed(() => filteredRows.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))
const pendingCount = computed(() => decoratedRows.value.filter(row => row.status_key === 'pending').length)
const followupCount = computed(() => decoratedRows.value.filter(row => row.status_key === 'followup').length)
const doneCount = computed(() => decoratedRows.value.filter(row => row.status_key === 'done' && isToday(row.resolved_at || row.created_at)).length)
const stats = computed(() => [
  { label: '待处理', value: pendingCount.value, detail: '条事项需要优先回应', icon: 'clipboard', tone: 'terracotta' },
  { label: '跟进中', value: followupCount.value, detail: '条事项正在持续关心', icon: 'clock', tone: 'amber' },
  { label: '今日已办结', value: doneCount.value, detail: '条事项已完成回应', icon: 'check-circle', tone: 'sage' },
])

watch(filters, () => { page.value = 1 }, { deep: true })
watch(totalPages, value => { if (value && page.value > value) page.value = value })

onMounted(() => {
  eventsStore.load({ page: 1, page_size: 100 })
  eldersStore.load({ page: 1, page_size: 100 })
  if (!dashboardStore.data) dashboardStore.load()
  document.addEventListener('keydown', handleEscape)
})
onUnmounted(() => document.removeEventListener('keydown', handleEscape))

function decorateRow(row, index) {
  const elder = elderMap.value.get(String(row.elder_id)) || {}
  const statusKey = row.status || (row.is_resolved ? 'done' : row.severity === 'urgent' ? 'pending' : 'followup')
  const statusLabel = { pending: '待处理', followup: '跟进中', done: '已办结' }[statusKey]
  return {
    ...row,
    elder_name: row.elder_name || elder.elder_name || elder.name || '老人档案',
    elder_address: row.elder_address || elder.address || '地址待补充',
    avatar_url: row.avatar_url || elder.avatar_url || mockElders[index % mockElders.length].avatar_url,
    source_label: { canteen: '食堂到场', alert: '家属来电', manual: '上门探访' }[row.source] || '社区记录',
    created_label: formatTime(row.created_at),
    deadline_label: row.deadline || (statusKey === 'done' ? '已完成' : row.severity === 'urgent' ? '尽快处理' : '持续跟进'),
    assignee: row.assignee || (row.is_resolved ? workerName.value : '待分配'),
    status_key: statusKey,
    status_label: statusLabel,
  }
}

function formatTime(value) {
  if (!value) return '时间待补充'
  const date = new Date(value)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
function isToday(value) {
  if (!value) return false
  const date = new Date(value)
  const today = new Date()
  return date.getFullYear() === today.getFullYear() && date.getMonth() === today.getMonth() && date.getDate() === today.getDate()
}
function changePageSize(value) { pageSize.value = value; page.value = 1 }
function goToElders() { router.push({ path: '/elders', query: topSearch.value ? { search: topSearch.value } : {} }) }
function scrollToList() { eventTable.value?.$el?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }) }
function handleExport() { downloadExport('/community/export/events') }
function viewProfile(id) { router.push(`/elders/${id}`) }
function openCreate() { Object.assign(dialog, { open: true, mode: 'create', event: null }) }
function openProcess(event) { Object.assign(dialog, { open: true, mode: event.status_key === 'done' ? 'view' : 'resolve', event }) }
function closeDialog() { dialog.open = false }
function handleEscape(event) { if (event.key === 'Escape') closeDialog() }

async function submitDialog(payload) {
  if (dialog.mode === 'create' && (!payload.elder_id || !payload.description.trim())) return ElMessage.warning('请选择老人并填写事项说明')
  submitting.value = true
  try {
    if (dialog.mode === 'create') {
      await eventsStore.create(payload)
      ElMessage.success('关怀事项已新增')
    } else {
      await eventsStore.resolve(dialog.event.id, payload)
      ElMessage.success('关怀事项已办结')
    }
    closeDialog()
  } catch {
    // 请求层已统一提示
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.events-page { display: grid; height: 100%; min-height: 0; grid-template-rows: auto auto auto auto minmax(0,1fr); }
.events-heading { display: flex; min-height: 106px; align-items: end; justify-content: space-between; padding: 7px 4px 12px 8px; }
.events-heading h1 { margin: 0; color: #292724; font: 900 30px/1.12 'Songti SC','STSong','Noto Serif SC',serif; letter-spacing: .02em; }
.events-heading p { margin: 6px 0 0; color: #687488; font-size: 13px; }
.events-actions { display: flex; gap: 12px; }
.events-actions :deep(.app-button) { min-width: 142px; }
@media (max-width: 1050px) { .events-page { height: auto; min-height: 100%; }.events-heading { align-items: center; }.events-actions { flex-wrap: wrap; justify-content: flex-end; } }
</style>
