<template>
  <div class="canteen-page">
    <PageTopbar
      v-model:search="searchKeyword"
      :worker-name="userStore.worker?.name || '社工'"
      :pending-events="dashboardStore.data?.pending_events || 0"
      @events="router.push('/events')"
      @search="goToElders"
    />

    <header class="canteen-heading">
      <div><h1>食堂记录</h1><p>录入就餐数据，辅助识别需关注情况</p></div>
      <img class="canteen-heading__art" src="@/assets/canteen/canteen-rice-art.png" alt="" />
      <div class="canteen-actions">
        <AppButton variant="outline" wide @click="handleExport"><span class="material-symbols-outlined">ios_share</span>导出出勤</AppButton>
        <AppButton wide :disabled="store.generating" @click="handleGenerateMenu"><span class="material-symbols-outlined">description</span>{{ store.generating ? '生成中…' : '生成今日菜单' }}</AppButton>
      </div>
    </header>

    <div class="canteen-grid">
      <CanteenEntryCard
        v-model:raw-text="rawText"
        :file-name="fileBytes?.name || ''"
        :submitting="store.submitting"
        @file="fileBytes = $event"
        @submit="handleSubmit"
      />
      <CanteenMenuCard
        v-model:meal-type="menuMealType"
        :menu="displayMenu"
        :date-label="selectedDateLabel"
        :busy="store.generating || menuActionBusy"
        @shift="shiftMenuDate"
        @publish="handlePublish"
        @delete="handleDeleteMenu"
      />
      <CanteenParsedResult :result="lastParsed || mockCanteenParsed" />
      <CanteenHistoryCard :records="displayRecords" :loading="store.loading && !displayRecords.length" @refresh="store.load()" @select="selectRecord" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useCanteenStore } from '@/stores/canteen'
import { useDashboardStore } from '@/stores/dashboard'
import { useUserStore } from '@/stores/user'
import { downloadExport } from '@/api/export'
import PageTopbar from '@/components/PageTopbar.vue'
import AppButton from '@/components/AppButton.vue'
import CanteenEntryCard from './components/CanteenEntryCard.vue'
import CanteenMenuCard from './components/CanteenMenuCard.vue'
import CanteenParsedResult from './components/CanteenParsedResult.vue'
import CanteenHistoryCard from './components/CanteenHistoryCard.vue'
import { mockCanteenMenu, mockCanteenParsed, mockCanteenRecords } from '@/mocks/canteen'

const router = useRouter()
const store = useCanteenStore()
const dashboardStore = useDashboardStore()
const userStore = useUserStore()
const localDate = date => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
const today = localDate(new Date())
const searchKeyword = ref('')
const rawText = ref('今天中午食堂，张大爷来了，李奶奶没来，王大爷来了但没怎么吃')
const fileBytes = ref(null)
const lastParsed = ref(mockCanteenParsed)
const menuMealType = ref('lunch')
const selectedDate = ref(today)
const mockMenuVisible = ref(true)
const menuActionBusy = ref(false)

const selectedDateLabel = computed(() => {
  const date = new Date(`${selectedDate.value}T00:00:00`)
  return `${date.getMonth() + 1}月${date.getDate()}日`
})
const displayMenu = computed(() => {
  const menu = store.menus.find(item => item.menu_date === selectedDate.value && item.meal_type === menuMealType.value)
  if (menu) return menu
  return !store.menus.length && mockMenuVisible.value && selectedDate.value === today && menuMealType.value === 'lunch' ? mockCanteenMenu : null
})
const displayRecords = computed(() => store.records.length ? store.records : mockCanteenRecords)

onMounted(() => {
  store.load()
  store.loadMenus()
  if (!dashboardStore.data) dashboardStore.load()
})

function goToElders() { router.push({ path: '/elders', query: searchKeyword.value ? { search: searchKeyword.value } : {} }) }
function handleExport() { downloadExport('/community/export/canteen') }
function shiftMenuDate(offset) {
  const date = new Date(`${selectedDate.value}T00:00:00`)
  date.setDate(date.getDate() + offset)
  selectedDate.value = localDate(date)
}
async function handleGenerateMenu() {
  selectedDate.value = today
  try { await store.generate(menuMealType.value, today) } catch { /* 请求层已提示 */ }
}
async function handlePublish() {
  menuActionBusy.value = true
  try {
    const menu = displayMenu.value?.id === 'mock-menu' ? await store.generate(menuMealType.value, selectedDate.value) : displayMenu.value
    if (!menu) return ElMessage.warning('请先生成菜单')
    if (menu.status !== 'published') await store.publish(menu.id)
    ElMessage.success('菜单已发布')
  } catch { /* 请求层已提示 */ } finally { menuActionBusy.value = false }
}
async function handleDeleteMenu() {
  if (!displayMenu.value) return
  try { await ElMessageBox.confirm('确定删除这份菜单？', '删除确认', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }) } catch { return }
  if (displayMenu.value.id === 'mock-menu') { mockMenuVisible.value = false; return }
  try { await store.remove(displayMenu.value.id); ElMessage.success('菜单已删除') } catch { /* 请求层已提示 */ }
}
function selectRecord(record) { if (record.parsed_data) lastParsed.value = record.parsed_data }
async function handleSubmit() {
  if (!rawText.value.trim() && !fileBytes.value) return ElMessage.warning('请输入就餐描述或上传 Excel 文件')
  const formData = new FormData()
  if (rawText.value.trim()) formData.append('raw_text', rawText.value.trim())
  if (fileBytes.value) formData.append('file', fileBytes.value)
  try {
    const result = await store.submit(formData)
    if (result?.parse_status === 'success' && result.parsed_data) lastParsed.value = result.parsed_data
    rawText.value = ''
    fileBytes.value = null
  } catch { /* 请求层已提示 */ }
}
</script>

<style scoped>
.canteen-page { display: grid; height: 100%; min-height: 0; grid-template-rows: auto auto minmax(0,1fr); }.canteen-heading { position: relative; display: flex; min-height: 112px; align-items: center; justify-content: space-between; padding: 5px 4px 8px 8px; }.canteen-heading h1 { margin: 0; color: #17242f; font: 900 31px/1.1 'Songti SC','STSong','Noto Serif SC',serif; letter-spacing: .04em; }.canteen-heading p { margin: 8px 0 0; color: #617087; font-size: 13px; }.canteen-heading__art { position: absolute; top: 12px; left: 49%; width: 210px; height: 78px; object-fit: contain; opacity: .62; filter: saturate(.72); transform: translateX(-50%); pointer-events: none; }.canteen-actions { display: flex; gap: 12px; }.canteen-actions :deep(.app-button) { min-width: 144px; }.canteen-grid { display: grid; min-height: 0; overflow: hidden; grid-template-columns: 1fr 1fr; grid-template-rows: minmax(350px,1.55fr) minmax(210px,1fr); gap: 13px; }
@media (max-width: 1050px) { .canteen-page { height: auto; min-height: 100%; }.canteen-heading__art { display: none; }.canteen-grid { overflow: visible; grid-template-columns: 1fr; grid-template-rows: none; }.canteen-grid > * { min-height: 280px; } }
</style>
