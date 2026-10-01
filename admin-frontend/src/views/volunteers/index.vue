<template>
  <div class="volunteers-page">
    <PageTopbar
      v-model:search="topSearch"
      :worker-name="userStore.worker?.name || '社工'"
      :pending-events="dashboardStore.data?.pending_events || 0"
      @events="router.push('/events')"
      @search="goToElders"
    />

    <header class="volunteers-heading">
      <div class="volunteers-heading__copy"><h1>邻里帮</h1><p>志愿者与积分任务管理</p></div>
      <img src="@/assets/dashboard-composite/hero-community-art-wide.png" alt="" />
      <div class="volunteers-actions">
        <AppButton variant="outline" wide @click="exportRecords"><span class="material-symbols-outlined">ios_share</span>导出记录</AppButton>
        <AppButton wide @click="openCreate"><span class="material-symbols-outlined">add_circle</span>发布任务</AppButton>
      </div>
    </header>

    <AppStatBar :stats="stats" />
    <VolunteerToolbar v-model="activeTab" v-model:search="filters.search" v-model:status="filters.status" v-model:task-type="filters.taskType" />

    <AppPanel class="volunteer-table-panel">
      <header class="volunteer-table-panel__head"><h2>{{ panelTitle }} <span>共 <b>{{ filteredRows.length }}</b> 条</span></h2></header>
      <AppTable :columns="columns" :rows="pagedRows" min-width="1000px" class="volunteer-table" :empty-text="emptyText">
        <template #cell-title="{ row }"><b class="task-title">{{ row.title }}</b></template>
        <template #cell-type="{ row }"><span :class="['type-pill', `type-pill--${row.task_type}`]">{{ row.type_label }}</span></template>
        <template #cell-target="{ row }"><span class="target-text" :title="row.target_label">{{ row.target_label }}</span></template>
        <template #cell-points="{ row }"><b class="points">+{{ row.point_value }}</b></template>
        <template #cell-volunteer="{ row }">{{ row.volunteer_name || '—' }}</template>
        <template #cell-status="{ row }"><span :class="['status-pill', `status-pill--${row.status}`]"><span class="material-symbols-outlined">{{ statusIcon(row.status) }}</span>{{ row.status_label }}</span></template>
        <template #cell-created="{ row }">{{ formatTime(row.created_at) }}</template>
        <template #cell-actions="{ row }"><AppButton variant="link" @click.stop="openTask(row)">{{ row.status === 'completed' ? '审核' : '查看' }}</AppButton></template>

        <template #cell-name="{ row }"><div class="volunteer-name"><span class="material-symbols-outlined">person</span><b>{{ row.elder_name }}</b></div></template>
        <template #cell-total="{ row }"><b class="points">{{ row.total_points }}</b></template>
        <template #cell-available="{ row }">{{ row.available_points }}</template>
        <template #cell-active="{ row }"><span :class="['active-state', { muted: !row.is_active }]"><i></i>{{ row.is_active ? '活跃' : '未活跃' }}</span></template>
        <template #cell-joined="{ row }">{{ formatTime(row.created_at) }}</template>

        <template #cell-rank="{ index }"><b :class="['rank', { medal: index < 3 }]">{{ index + 1 }}</b></template>
        <template #cell-person="{ row }">{{ row.elder_name }}</template>
        <template #cell-tasks="{ row }">完成 {{ row.task_count }} 个任务</template>
        <template #cell-score="{ row }"><b class="points">{{ row.total_points }}</b></template>
      </AppTable>
      <AppPagination :total="filteredRows.length" :page="page" :page-size="pageSize" :total-pages="totalPages" @page="page = $event" @page-size="changePageSize" />
    </AppPanel>

    <VolunteerTaskDialog :open="dialog.open" :mode="dialog.mode" :task="dialog.task" :elders="displayElders" :submitting="submitting" @close="closeDialog" @submit="createTask" @verify="verifyTask" />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useDashboardStore } from '@/stores/dashboard'
import { useEldersStore } from '@/stores/elders'
import { useUserStore } from '@/stores/user'
import { useVolunteerStore } from '@/stores/volunteer'
import AppButton from '@/components/AppButton.vue'
import AppPagination from '@/components/AppPagination.vue'
import AppPanel from '@/components/AppPanel.vue'
import AppStatBar from '@/components/AppStatBar.vue'
import AppTable from '@/components/AppTable.vue'
import PageTopbar from '@/components/PageTopbar.vue'
import VolunteerTaskDialog from './components/VolunteerTaskDialog.vue'
import VolunteerToolbar from './components/VolunteerToolbar.vue'
import { mockElders } from '@/mocks/elders'
import { mockLeaderboard, mockVolunteers, mockVolunteerTasks } from '@/mocks/volunteers'

const router = useRouter()
const store = useVolunteerStore()
const userStore = useUserStore()
const eldersStore = useEldersStore()
const dashboardStore = useDashboardStore()
const topSearch = ref('')
const activeTab = ref('tasks')
const page = ref(1)
const pageSize = ref(10)
const submitting = ref(false)
const localMockTasks = ref(mockVolunteerTasks.map(task => ({ ...task })))
const filters = reactive({ search: '', status: '', taskType: '' })
const dialog = reactive({ open: false, mode: 'create', task: null })

const displayElders = computed(() => eldersStore.elders.length ? eldersStore.elders : mockElders)
const elderMap = computed(() => new Map(displayElders.value.map(elder => [String(elder.id), elder])))
const allTasks = computed(() => (store.tasks.length ? store.tasks : localMockTasks.value).map(decorateTask))
const allVolunteers = computed(() => store.volunteers.length ? store.volunteers : mockVolunteers)
const allLeaderboard = computed(() => store.leaderboard.length ? store.leaderboard : mockLeaderboard)
const sourceRows = computed(() => activeTab.value === 'tasks' ? allTasks.value : activeTab.value === 'volunteers' ? allVolunteers.value : allLeaderboard.value)
const filteredRows = computed(() => sourceRows.value.filter(row => {
  const keyword = filters.search.trim().toLowerCase()
  if (activeTab.value === 'tasks') {
    if (filters.status && row.status !== filters.status) return false
    if (filters.taskType && row.task_type !== filters.taskType) return false
    return !keyword || `${row.title}${row.target_label}${row.volunteer_name || ''}${row.notes || ''}`.toLowerCase().includes(keyword)
  }
  return !keyword || `${row.elder_name || ''}`.toLowerCase().includes(keyword)
}))
const totalPages = computed(() => Math.ceil(filteredRows.value.length / pageSize.value))
const pagedRows = computed(() => filteredRows.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))
const stats = computed(() => [
  { label: '位活跃志愿者', value: allVolunteers.value.filter(item => item.is_active).length, detail: '当前可参与社区互助', icon: 'people', tone: 'sage' },
  { label: '项待接取任务', value: allTasks.value.filter(item => item.status === 'pending').length, detail: '等待志愿者响应', icon: 'clipboard', tone: 'amber' },
  { label: '项待审核任务', value: allTasks.value.filter(item => item.status === 'completed').length, detail: '完成后等待积分发放', icon: 'shield-check', tone: 'terracotta' },
])
const panelTitle = computed(() => ({ tasks: '互助任务列表', volunteers: '志愿者名单', leaderboard: '积分排行' }[activeTab.value]))
const emptyText = computed(() => ({ tasks: '暂无符合条件的互助任务', volunteers: '暂无志愿者', leaderboard: '暂无排行数据' }[activeTab.value]))
const columns = computed(() => activeTab.value === 'tasks' ? [
  { key: 'title', label: '任务名称', width: '19%' }, { key: 'type', label: '类型', width: '10%' }, { key: 'target', label: '服务对象', width: '18%' },
  { key: 'points', label: '积分', width: '8%' }, { key: 'volunteer', label: '志愿者', width: '11%' }, { key: 'status', label: '状态', width: '14%' },
  { key: 'created', label: '发布时间', width: '13%' }, { key: 'actions', label: '操作', width: '7%' },
] : activeTab.value === 'volunteers' ? [
  { key: 'name', label: '姓名', width: '28%' }, { key: 'total', label: '累计积分', width: '18%' }, { key: 'available', label: '可用积分', width: '18%' },
  { key: 'active', label: '状态', width: '18%' }, { key: 'joined', label: '注册时间', width: '18%' },
] : [
  { key: 'rank', label: '排名', width: '14%' }, { key: 'person', label: '志愿者', width: '30%' }, { key: 'tasks', label: '完成情况', width: '30%' }, { key: 'score', label: '累计积分', width: '26%' },
])

watch([activeTab, filters], () => { page.value = 1 }, { deep: true })
watch(totalPages, value => { if (value && page.value > value) page.value = value })
onMounted(() => {
  store.loadTasks(); store.loadVolunteers(); store.loadLeaderboard()
  eldersStore.load({ page: 1, page_size: 100 })
  if (!dashboardStore.data) dashboardStore.load()
  document.addEventListener('keydown', handleEscape)
})
onUnmounted(() => document.removeEventListener('keydown', handleEscape))

function decorateTask(task) {
  const elder = elderMap.value.get(String(task.target_elder_id)) || {}
  const name = task.target_elder_name || elder.elder_name || elder.name || '社区公共服务'
  const address = task.target_address || elder.address || ''
  return { ...task, type_label: typeLabel(task.task_type), status_label: statusLabel(task.status), target_label: address ? `${name} · ${address}` : name }
}
function typeLabel(value) { return { visit: '探访', accompany: '陪伴', check_in: '签到', errand: '代办' }[value] || value }
function statusLabel(value) { return { pending: '待接取', accepted: '进行中', completed: '待审核', verified: '已完成' }[value] || value }
function statusIcon(value) { return { pending: 'error', accepted: 'play_circle', completed: 'schedule', verified: 'check_circle' }[value] || 'circle' }
function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
function changePageSize(value) { pageSize.value = value; page.value = 1 }
function goToElders() { router.push({ path: '/elders', query: topSearch.value ? { search: topSearch.value } : {} }) }
function openCreate() { Object.assign(dialog, { open: true, mode: 'create', task: null }) }
function openTask(task) { Object.assign(dialog, { open: true, mode: 'view', task }) }
function closeDialog() { dialog.open = false }
function handleEscape(event) { if (event.key === 'Escape') closeDialog() }

async function createTask(payload) {
  if (!payload.title) return ElMessage.warning('请填写任务标题')
  submitting.value = true
  try { await store.create(payload); closeDialog(); ElMessage.success('任务已发布') } catch { /* 请求层已统一提示 */ } finally { submitting.value = false }
}
async function verifyTask(task) {
  try { await ElMessageBox.confirm(`审核通过后将发放 ${task.point_value} 积分`, `确认通过「${task.title}」？`, { confirmButtonText: '确认通过', cancelButtonText: '取消', type: 'success' }) } catch { return }
  submitting.value = true
  try {
    if (String(task.id).startsWith('mock-')) localMockTasks.value = localMockTasks.value.map(item => item.id === task.id ? { ...item, status: 'verified', verified_at: new Date().toISOString() } : item)
    else await store.verify(task.id)
    closeDialog(); ElMessage.success('审核通过，积分已发放')
  } catch { /* 请求层已统一提示 */ } finally { submitting.value = false }
}
function exportRecords() {
  const rows = activeTab.value === 'tasks' ? [['任务名称','类型','服务对象','积分','志愿者','状态','发布时间'], ...filteredRows.value.map(row => [row.title,row.type_label,row.target_label,row.point_value,row.volunteer_name || '',row.status_label,formatTime(row.created_at)])]
    : activeTab.value === 'volunteers' ? [['姓名','累计积分','可用积分','状态','注册时间'], ...filteredRows.value.map(row => [row.elder_name,row.total_points,row.available_points,row.is_active ? '活跃' : '未活跃',formatTime(row.created_at)])]
      : [['排名','志愿者','完成任务','累计积分'], ...filteredRows.value.map((row,index) => [index + 1,row.elder_name,row.task_count,row.total_points])]
  const csv = `\ufeff${rows.map(row => row.map(value => `"${String(value ?? '').replaceAll('"','""')}"`).join(',')).join('\n')}`
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a'); link.href = url; link.download = `${panelTitle.value}.csv`; link.click(); URL.revokeObjectURL(url)
}
</script>

<style scoped>
.volunteers-page { display: grid; height: 100%; min-height: 0; grid-template-rows: auto auto auto auto minmax(0,1fr); }
.volunteers-heading { position: relative; display: flex; min-height: 120px; align-items: center; justify-content: space-between; overflow: hidden; padding: 4px 4px 8px 8px; }
.volunteers-heading__copy, .volunteers-actions { position: relative; z-index: 2; }.volunteers-heading h1 { margin: 0; color: #1f2b36; font: 900 31px/1.1 'Songti SC','STSong','Noto Serif SC',serif; letter-spacing: .04em; }.volunteers-heading p { margin: 8px 0 0; color: #617087; font-size: 13px; }
.volunteers-heading img { position: absolute; z-index: 1; top: 4px; right: 0; width: min(680px,58%); height: 112px; object-fit: cover; object-position: center bottom; opacity: .74; pointer-events: none; }
.volunteers-actions { display: flex; gap: 12px; }.volunteers-actions :deep(.app-button) { min-width: 142px; }
.volunteer-table-panel { display: flex; min-height: 0; flex-direction: column; overflow: hidden; }.volunteer-table-panel__head { display: flex; min-height: 58px; align-items: center; padding: 9px 18px 5px; }.volunteer-table-panel__head h2 { margin: 0; color: #203044; font: 700 20px 'Songti SC','STSong',serif; }.volunteer-table-panel__head span { margin-left: 10px; color: #6c7481; font: 12px sans-serif; }.volunteer-table-panel__head b { color: #c6533d; }.volunteer-table { min-height: 0; flex: 1; margin: 0 14px; }.volunteer-table :deep(.app-table td) { height: 62px; color: #46546a; }
.task-title { color: #273143; }.target-text { display: block; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }.points { color: #d45a41; font-size: 14px; }
.type-pill, .status-pill { display: inline-flex; align-items: center; border-radius: 7px; font-size: 11.5px; font-weight: 700; white-space: nowrap; }.type-pill { height: 29px; padding: 0 11px; }.type-pill--accompany { color: #c75a3d; background: #fae7df; }.type-pill--visit { color: #d1842b; background: #fbedd9; }.type-pill--check_in, .type-pill--errand { color: #56826a; background: #e6f0e9; }
.status-pill { height: 29px; gap: 6px; padding: 0 10px; }.status-pill .material-symbols-outlined { font-size: 18px; }.status-pill--pending { color: #c75a3d; background: #f9e7df; }.status-pill--accepted, .status-pill--verified { color: #56826a; background: #e6f0e9; }.status-pill--completed { color: #cf852d; background: #fbefdc; }
.volunteer-name { display: flex; align-items: center; gap: 10px; }.volunteer-name .material-symbols-outlined { display: grid; width: 32px; height: 32px; place-items: center; border-radius: 50%; color: #56826a; background: #e6f0e9; }.active-state { display: inline-flex; align-items: center; gap: 7px; color: #56826a; }.active-state i { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }.active-state.muted { color: #8d8a86; }.rank { display: grid; width: 30px; height: 30px; place-items: center; border-radius: 50%; color: #7b818b; background: #f2eee9; }.rank.medal { color: #fff; background: #d4a853; }
@media (max-width: 1050px) { .volunteers-page { height: auto; min-height: 100%; }.volunteers-heading img { display: none; }.volunteer-table-panel { min-height: 540px; } }
</style>
