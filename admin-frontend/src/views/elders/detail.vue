<template>
  <div class="elder-detail-page">
    <PageTopbar
      v-model:search="search"
      :worker-name="workerName"
      :pending-events="dashboardStore.data?.pending_events || 0"
      @search="searchElders"
      @events="router.push('/events')"
    />

    <nav class="breadcrumb" aria-label="面包屑">
      <button @click="router.push('/elders')"><DashboardIcon name="home" />老人档案</button>
      <span>›</span>
      <b>{{ detail?.elder?.name || '档案详情' }}</b>
    </nav>

    <template v-if="detail">
      <ElderProfileSummary
        :detail="detail"
        @contact="showPending('联系与走访记录')"
        @confirm="confirmActivity"
        @edit="editOpen = true"
        @avatar="uploadAvatar"
      />

      <div class="detail-grid">
        <ElderDailyActivity
          :elder-id="elderId"
          :initial-items="timelineItems"
          :mock="isMock"
          @all="showPending('全部活动记录')"
        />
        <ElderCareSidebar
          :detail="detail"
          :worker-name="workerName"
          @complete="showPending('关怀任务')"
          @edit="showPending('联系人编辑')"
        />
      </div>
    </template>

    <div v-else-if="loading" class="page-state">
      <span class="material-symbols-outlined spinning">progress_activity</span>
      <p>正在整理老人档案…</p>
    </div>

    <div v-else class="page-state">
      <span class="material-symbols-outlined">person_off</span>
      <p>老人档案不存在或暂时无法读取</p>
      <button @click="router.push('/elders')">返回档案列表</button>
    </div>

    <ElderCreateDialog
      :open="editOpen"
      :submitting="submitting"
      :initial="detail?.elder || {}"
      mode="edit"
      @close="editOpen = false"
      @submit="saveElder"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useDashboardStore } from '@/stores/dashboard'
import { useEldersStore } from '@/stores/elders'
import { useUserStore } from '@/stores/user'
import { getMockElderDetail } from '@/mocks/elders'
import { uploadElderAvatar } from '@/api/community'
import DashboardIcon from '@/components/DashboardIcon.vue'
import PageTopbar from '@/components/PageTopbar.vue'
import ElderCareSidebar from './components/ElderCareSidebar.vue'
import ElderCreateDialog from './components/ElderCreateDialog.vue'
import ElderDailyActivity from './components/ElderDailyActivity.vue'
import ElderProfileSummary from './components/ElderProfileSummary.vue'

const route = useRoute()
const router = useRouter()
const dashboardStore = useDashboardStore()
const eldersStore = useEldersStore()
const userStore = useUserStore()
const search = ref('')
const loading = ref(false)
const editOpen = ref(false)
const submitting = ref(false)
const elderId = computed(() => String(route.params.id || ''))
const mockDetail = computed(() => getMockElderDetail(elderId.value))
const isMock = computed(() => Boolean(mockDetail.value))
const detail = computed(() => mockDetail.value || eldersStore.current)
const timelineItems = computed(() => isMock.value
  ? mockDetail.value.recent_timeline
  : eldersStore.timeline.length ? eldersStore.timeline : detail.value?.recent_timeline || [])
const workerName = computed(() => userStore.worker?.name || '社工')

onMounted(async () => {
  if (!dashboardStore.data) dashboardStore.load()
  if (isMock.value) return
  loading.value = true
  await Promise.all([
    eldersStore.loadDetail(elderId.value),
    eldersStore.loadTimeline(elderId.value),
  ])
  loading.value = false
})

function searchElders() {
  router.push({ path: '/elders', query: search.value.trim() ? { search: search.value.trim() } : {} })
}

async function confirmActivity() {
  if (detail.value?.today_active) {
    ElMessage.info('今日活动已确认')
    return
  }
  if (isMock.value) {
    mockDetail.value.today_active = true
    ElMessage.success('已确认今日活动（演示数据）')
    return
  }
  try {
    await dashboardStore.confirmActive(elderId.value)
    if (eldersStore.current) eldersStore.current.today_active = true
    ElMessage.success('已确认今日活动')
  } catch {
    // 请求层已展示错误信息
  }
}

function showPending(name) {
  ElMessage.info(`${name}的数据写入接口暂未提供，当前已完成界面流程`)
}

async function saveElder(payload) {
  submitting.value = true
  try {
    if (isMock.value) {
      const { emergency_contact_name, emergency_contact_phone, ...elderData } = payload
      Object.assign(mockDetail.value.elder, elderData, {
        emergency_contact: { name: emergency_contact_name, phone: emergency_contact_phone },
      })
      ElMessage.success('演示档案已更新')
    } else {
      await eldersStore.update(elderId.value, payload)
      await eldersStore.loadDetail(elderId.value)
      ElMessage.success('老人信息已更新')
    }
    editOpen.value = false
  } catch {
    // 请求层已展示错误信息
  } finally {
    submitting.value = false
  }
}

async function uploadAvatar({ file, preview }) {
  const previous = detail.value.elder.avatar_url
  detail.value.elder.avatar_url = preview
  if (isMock.value) {
    ElMessage.success('演示头像已在本地更新')
    return
  }
  const data = new FormData()
  data.append('file', file)
  try {
    const result = await uploadElderAvatar(elderId.value, data)
    detail.value.elder.avatar_url = result.url
    ElMessage.success('头像已更新')
  } catch {
    detail.value.elder.avatar_url = previous
  }
}
</script>

<style scoped>
.elder-detail-page {
  display: grid;
  height: 100%;
  min-height: 0;
  grid-template-rows: auto 34px auto minmax(0, 1fr);
  gap: 10px;
}
.breadcrumb { display: flex; align-items: center; gap: 12px; min-width: 0; color: #7a8190; font-size: 12px; }
.breadcrumb button { display: flex; align-items: center; gap: 8px; padding: 0; border: 0; color: #677387; background: transparent; font-size: 12px; cursor: pointer; }
.breadcrumb button :deep(.dashboard-icon) { font-size: 15px; }.breadcrumb b { color: #2e3d54; font-size: 13px; }
.detail-grid { display: grid; min-height: 0; grid-template-columns: minmax(0, 1.72fr) minmax(340px, .98fr); gap: 12px; }
.page-state { display: grid; min-height: 360px; place-items: center; align-content: center; gap: 8px; color: #91867c; border: 1px solid #e5ddd5; border-radius: 11px; background: rgba(255,255,255,.72); }
.page-state > span { color: #c85b43; font-size: 40px; }.page-state p { margin: 0; font-size: 14px; }.page-state button { height: 36px; padding: 0 20px; border: 1px solid #d85a42; border-radius: 7px; color: #d2543d; background: #fff; cursor: pointer; }
.spinning { animation: spin 1s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 1050px) {
  .elder-detail-page { height: auto; min-height: 100%; grid-template-rows: auto 34px auto auto; }
  .detail-grid { grid-template-columns: 1fr; }
}
</style>
