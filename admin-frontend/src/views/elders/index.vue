<template>
  <div class="elders-page">
    <PageTopbar
      v-model:search="topSearch"
      :worker-name="userStore.worker?.name || '社工'"
      :pending-events="dashboardStore.data?.pending_events || 0"
      @events="router.push('/events')"
      @search="applyTopSearch"
    />

    <header class="archive-heading">
      <div><h1>老人档案</h1><p>查看辖区老人信息与关怀状态</p></div>
      <div class="archive-actions">
        <AppButton variant="outline" wide @click="handleExport"><span class="material-symbols-outlined">ios_share</span>导出 Excel</AppButton>
        <AppButton wide @click="showDialog = true"><span class="material-symbols-outlined">add_circle</span>新增老人</AppButton>
      </div>
    </header>

    <ElderArchiveFilters
      v-model:search="filters.search"
      v-model:care-level="filters.care_level"
      @change="applyFilters"
      @search="debouncedSearch"
    />

    <ElderArchiveTable
      :rows="store.elders"
      :loading="store.loading"
      :total="store.total"
      :page="store.page"
      :page-size="store.pageSize"
      :total-pages="store.totalPages"
      @view="id => router.push(`/elders/${id}`)"
      @page="changePage"
      @page-size="changePageSize"
    />

    <ElderCreateDialog :open="showDialog" :submitting="submitting" @close="showDialog = false" @submit="handleCreate" />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useEldersStore } from '@/stores/elders'
import { useDashboardStore } from '@/stores/dashboard'
import { useUserStore } from '@/stores/user'
import { downloadExport } from '@/api/export'
import PageTopbar from '@/components/PageTopbar.vue'
import AppButton from '@/components/AppButton.vue'
import ElderArchiveFilters from './components/ElderArchiveFilters.vue'
import ElderArchiveTable from './components/ElderArchiveTable.vue'
import ElderCreateDialog from './components/ElderCreateDialog.vue'

const route = useRoute()
const router = useRouter()
const store = useEldersStore()
const dashboardStore = useDashboardStore()
const userStore = useUserStore()
const showDialog = ref(false)
const submitting = ref(false)
const topSearch = ref(route.query.search || '')
const filters = reactive({ search: route.query.search || '', care_level: '', page: 1, page_size: 10 })
let searchTimer

onMounted(() => {
  store.load(filters)
  if (!dashboardStore.data) dashboardStore.load()
  document.addEventListener('keydown', handleEscape)
})
onUnmounted(() => {
  clearTimeout(searchTimer)
  document.removeEventListener('keydown', handleEscape)
})

watch(() => route.query.search, search => {
  if ((search || '') === filters.search) return
  filters.search = search || ''
  topSearch.value = search || ''
  applyFilters()
})

function requestData() { store.load({ ...filters }) }
function applyFilters() { filters.page = 1; requestData() }
function debouncedSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(applyFilters, 300) }
function applyTopSearch() { filters.search = topSearch.value; applyFilters() }
function changePage(page) { filters.page = page; requestData() }
function changePageSize(pageSize) { filters.page = 1; filters.page_size = pageSize; requestData() }
function handleEscape(event) { if (event.key === 'Escape') showDialog.value = false }
function handleExport() { downloadExport('/community/export/elders') }

async function handleCreate(form) {
  submitting.value = true
  try {
    await store.create(form)
    showDialog.value = false
    requestData()
    ElMessage.success('老人档案已创建')
  } catch {
    // 请求层已统一提示
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.elders-page { display: grid; height: 100%; min-height: 0; grid-template-rows: auto auto auto minmax(0,1fr); }
.archive-heading { display: flex; min-height: 108px; align-items: end; justify-content: space-between; padding: 8px 4px 12px 8px; }
.archive-heading h1 { align-self: flex-start; margin: 0; color: #292724; font: 900 30px/1.18 'Songti SC','STSong','Noto Serif SC',serif; letter-spacing: -.01em; transform: scaleX(.94); transform-origin: left center; }.archive-heading p { margin: 7px 0 0; color: #6e737b; font-size: 13px; letter-spacing: .02em; }
.archive-actions { display: flex; gap: 12px; }
@media (max-width: 1050px) { .elders-page { height: auto; min-height: 100%; }.archive-heading { align-items: center; }.archive-actions { flex-wrap: wrap; justify-content: flex-end; } }
</style>
