<template>
  <AppPanel class="archive-panel">
    <header class="archive-panel__head">
      <h2>辖区老人档案 <span>共 <b>{{ total }}</b> 位老人</span></h2>
    </header>
    <AppTable
      :columns="columns"
      :rows="rows"
      :loading="loading"
      min-width="1050px"
      loading-text="正在整理老人档案…"
      empty-text="暂无符合条件的老人档案"
      class="archive-table-view"
    >
      <template #cell-elder="{ row, index }"><div class="elder-cell"><img :src="row.avatar_url || avatars[index % avatars.length]" :alt="row.elder_name || '老人头像'" /><div><b>{{ row.elder_name || '未命名老人' }}</b><small>{{ demographics(row) }}</small></div></div></template>
      <template #cell-level="{ row }"><span :class="`level level--${row.care_level || 'C'}`">{{ row.care_level || 'C' }} 级</span></template>
      <template #cell-address="{ row }"><div class="stack"><b>{{ row.address || '未分配地址' }}</b><small>{{ areaName(row.address) }}</small></div></template>
      <template #cell-status="{ row }"><div :class="['status', `status--${statusInfo(row).tone}`]"><span class="material-symbols-outlined">{{ statusInfo(row).icon }}</span><div><b>{{ statusInfo(row).label }}</b><small>{{ statusInfo(row).detail }}</small></div></div></template>
      <template #cell-signal="{ row }"><div class="signal"><span class="material-symbols-outlined">{{ row.today_active ? 'directions_walk' : 'notifications_none' }}</span><div><b>{{ row.today_active ? '今日有动态' : '暂无新动态' }}</b><small>{{ row.today_active ? '状态已更新' : '等待更新' }}</small></div></div></template>
      <template #cell-note="{ row }"><span :class="['care-note', careHint(row).tone]">{{ careHint(row).text }}</span></template>
      <template #cell-action="{ row }"><AppButton variant="link" @click="$emit('view', row.id)">查看档案</AppButton></template>
    </AppTable>
    <AppPagination :total="total" :page="page" :page-size="pageSize" :total-pages="totalPages" @page="$emit('page', $event)" @page-size="$emit('page-size', $event)" />
  </AppPanel>
</template>

<script setup>
import AppButton from '@/components/AppButton.vue'
import AppPanel from '@/components/AppPanel.vue'
import AppTable from '@/components/AppTable.vue'
import AppPagination from '@/components/AppPagination.vue'
import elder1 from '@/assets/dashboard-reference/elder-1.png'
import elder2 from '@/assets/dashboard-reference/elder-2.png'
import elder3 from '@/assets/dashboard-reference/elder-3.png'
import elder4 from '@/assets/dashboard-reference/elder-4.png'

defineEmits(['view', 'page', 'page-size'])
const props = defineProps({ rows: { type: Array, default: () => [] }, loading: Boolean, total: { type: Number, default: 0 }, page: { type: Number, default: 1 }, pageSize: { type: Number, default: 10 }, totalPages: { type: Number, default: 0 } })
const avatars = [elder1, elder2, elder3, elder4]
const columns = [
  { key: 'elder', label: '老人信息', width: '16%' },
  { key: 'level', label: '关怀分级', width: '10%' },
  { key: 'address', label: '居住地址', width: '14%' },
  { key: 'status', label: '当前状态', width: '15%' },
  { key: 'signal', label: '最近信号', width: '15%' },
  { key: 'note', label: '关怀提示', width: '20%' },
  { key: 'action', label: '操作', width: '10%' },
]

function statusInfo(row) {
  if (row.risk_level === 'critical') return { tone: 'danger', icon: 'error', label: '待核实', detail: '建议尽快确认' }
  if (['warning', 'attention'].includes(row.risk_level)) return { tone: 'warning', icon: 'schedule', label: '需关注', detail: '近期持续留意' }
  if (row.today_active) return { tone: 'normal', icon: 'check_circle', label: '正常', detail: '今日状态已更新' }
  return { tone: 'muted', icon: 'schedule', label: '待跟进', detail: '今日尚无动态' }
}

function careHint(row) {
  if (row.risk_level === 'critical') return { tone: 'danger', text: '当前状态需要尽快核实' }
  if (row.risk_level === 'warning') return { tone: 'warning', text: '近期状态需要持续关注' }
  if (!row.today_active && row.care_level === 'A') return { tone: 'danger', text: '今日尚无新动态' }
  if (!row.today_active) return { tone: 'warning', text: '建议近期多问候一次' }
  return { tone: '', text: '无异常' }
}

function areaName(address) {
  if (!address) return '辖区待分配'
  const match = address.match(/^([^0-9]+)(?=\d)/)
  return match?.[1] ? `${match[1]}片区` : '社区辖区'
}

function demographics(row) {
  if (row.age && row.gender) return `${row.age}岁 · ${row.gender}`
  return '年龄性别待补充'
}
</script>

<style scoped>
.archive-panel { display: flex; min-height: 0; flex-direction: column; overflow: hidden; }
.archive-panel__head { display: flex; min-height: 62px; align-items: center; padding: 10px 18px 6px; }
.archive-panel__head h2 { margin: 0; color: #272624; font: 700 20px 'Songti SC','STSong',serif; }.archive-panel__head span { margin-left: 8px; color: #5f6670; font: 13px sans-serif; }.archive-panel__head span b { color: #c75a3d; }
.archive-table-view { min-height: 0; flex: 1; margin: 0 14px; }
.elder-cell, .status, .signal { display: flex; align-items: center; gap: 10px; min-width: 0; }.elder-cell img { width: 45px; height: 48px; flex: none; object-fit: cover; border-radius: 7px; }.elder-cell div, .stack, .status div, .signal div { min-width: 0; }.elder-cell b, .stack b, .status b, .signal b { display: block; overflow: hidden; color: #302e2c; font-size: 13px; white-space: nowrap; text-overflow: ellipsis; }.elder-cell small, .stack small, .status small, .signal small { display: block; margin-top: 4px; color: #89909a; font-size: 11px; white-space: nowrap; }
.level { display: inline-flex; min-width: 46px; height: 31px; align-items: center; justify-content: center; border-radius: 7px; font-size: 13px; font-weight: 800; }.level--A { color: #c6533d; background: #fae9e1; }.level--B { color: #c17b25; background: #fbefdd; }.level--C { color: #56826a; background: #e6f0e9; }
.status .material-symbols-outlined, .signal .material-symbols-outlined { font-size: 28px; }.status--danger, .care-note.danger { color: #cb4f3a; }.status--warning, .care-note.warning { color: #cf852d; }.status--normal, .signal .material-symbols-outlined { color: #4d8b69; }.status--muted { color: #7d8490; }.status b, .signal b { color: currentColor; }
.care-note { color: #7b8088; line-height: 1.35; }
</style>
