<template>
  <div class="contributors-page">
    <PageTopbar
      v-model:search="search"
      placeholder="搜索姓名或微信号…"
      :worker-name="userStore.worker?.name || '社工'"
      :pending-events="dashboardStore.data?.pending_events || 0"
      @events="router.push('/events')"
    />

    <header class="contributors-heading">
      <div class="contributors-heading__copy">
        <h1>公益贡献</h1>
        <p>易挂念 · 公益志愿同学贡献页 —— 感谢每一位让牵挂更温暖的同行者</p>
      </div>
    </header>

    <AppPanel class="contributors-panel">
      <header class="contributors-panel__head">
        <h2>志愿同学名单 <span>共 <b>{{ filteredRows.length }}</b> 位</span></h2>
      </header>
      <AppTable
        :columns="columns"
        :rows="filteredRows"
        min-width="720px"
        class="contributors-table"
        :loading="loading"
        empty-text="暂无名单，等待补充"
      >
        <template #cell-wechat="{ row }">
          <span class="wechat-cell">
            <b>{{ row.wechat_id }}</b>
            <button class="copy-btn" type="button" @click="copyWechat(row.wechat_id)">复制</button>
          </span>
        </template>
      </AppTable>
    </AppPanel>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useDashboardStore } from '@/stores/dashboard'
import { useUserStore } from '@/stores/user'
import { getContributors } from '@/api/contributor'
import AppPanel from '@/components/AppPanel.vue'
import AppTable from '@/components/AppTable.vue'
import PageTopbar from '@/components/PageTopbar.vue'

const router = useRouter()
const userStore = useUserStore()
const dashboardStore = useDashboardStore()
const rows = ref([])
const loading = ref(true)
const search = ref('')

const columns = [
  { key: 'name', label: '姓名', width: '20%' },
  { key: 'wechat', label: '微信号', width: '32%' },
  { key: 'note', label: '寄语', width: '48%' },
]

const filteredRows = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) return rows.value
  return rows.value.filter(row => `${row.name || ''}${row.wechat_id || ''}${row.note || ''}`.toLowerCase().includes(keyword))
})

onMounted(async () => {
  if (!dashboardStore.data) dashboardStore.load()
  try {
    const data = await getContributors()
    rows.value = Array.isArray(data) ? data : []
  } catch {
    // 请求层已统一提示
  } finally {
    loading.value = false
  }
})

async function copyWechat(value) {
  try {
    await navigator.clipboard.writeText(value)
    ElMessage.success('微信号已复制')
  } catch {
    ElMessage.warning('复制失败，请手动选中复制')
  }
}
</script>

<style scoped>
.contributors-page { display: grid; height: 100%; min-height: 0; grid-template-rows: auto auto minmax(0,1fr); }
.contributors-heading { position: relative; display: flex; min-height: 96px; align-items: center; padding: 4px 4px 8px 8px; }
.contributors-heading__copy { position: relative; z-index: 2; }
.contributors-heading h1 { margin: 0; color: #1f2b36; font: 900 31px/1.1 'Songti SC','STSong','Noto Serif SC',serif; letter-spacing: .04em; }
.contributors-heading p { margin: 8px 0 0; color: #617087; font-size: 13px; }
.contributors-panel { display: flex; min-height: 0; flex-direction: column; overflow: hidden; }
.contributors-panel__head { display: flex; min-height: 58px; align-items: center; padding: 9px 18px 5px; }
.contributors-panel__head h2 { margin: 0; color: #203044; font: 700 20px 'Songti SC','STSong',serif; }
.contributors-panel__head span { margin-left: 10px; color: #6c7481; font: 12px sans-serif; }
.contributors-panel__head b { color: #c6533d; }
.contributors-table { min-height: 0; flex: 1; margin: 0 14px; }
.contributors-table :deep(.app-table td) { height: 58px; color: #46546a; }
.wechat-cell { display: inline-flex; align-items: center; gap: 10px; }
.wechat-cell b { color: #2a3546; font-size: 13.5px; letter-spacing: .01em; }
.copy-btn { height: 26px; padding: 0 12px; border: 1px solid rgba(198, 83, 61, .45); border-radius: 999px; color: #c6533d; background: #fff; font-size: 11.5px; cursor: pointer; transition: background .15s, color .15s; }
.copy-btn:hover { color: #fff; background: #c6533d; }
@media (max-width: 1050px) { .contributors-page { height: auto; min-height: 100%; } .contributors-panel { min-height: 480px; } }
</style>
