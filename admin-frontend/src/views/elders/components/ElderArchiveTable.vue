<template>
  <AppPanel class="archive-panel">
    <header class="archive-panel__head">
      <h2>辖区老人档案 <span>共 <b>{{ total }}</b> 位老人</span></h2>
    </header>
    <AppTable
      :columns="columns"
      :rows="rows"
      :loading="loading"
      min-width="1280px"
      loading-text="正在整理老人档案…"
      empty-text="暂无符合条件的老人档案"
      class="archive-table-view"
    >
      <template #cell-elder="{ row }"><div class="elder-cell"><img v-if="getElderAvatar(row)" :src="getElderAvatar(row)" :alt="row.elder_name || '老人头像'" /><span v-else class="avatar-fallback" aria-hidden="true">{{ initialOf(row) }}</span><div><b>{{ row.elder_name || '未命名老人' }}</b><small>{{ demographics(row) }}</small></div></div></template>
      <template #cell-level="{ row }"><span :class="`level level--${row.care_level || 'C'}`">{{ row.care_level || 'C' }} 级</span></template>
      <template #cell-address="{ row }"><div class="stack"><b>{{ row.address || '未分配地址' }}</b><small>{{ areaName(row.address) }}</small></div></template>
      <template #cell-status="{ row }"><div :class="['today-status', { 'today-status--active': row.today_active }]"><i></i><div><b>{{ row.today_active ? '今日有动态' : '暂无新动态' }}</b><small>{{ row.today_active ? '状态已更新' : '等待更新' }}</small></div></div></template>
      <template #cell-risk="{ row }"><div :class="['risk', `risk--${riskInfo(row).tone}`]"><b>{{ riskInfo(row).label }}</b><small>{{ riskInfo(row).score }}</small></div></template>
      <template #cell-note="{ row }"><p class="health-note" :title="row.health_notes || '暂无健康备注'">{{ row.health_notes || '暂无健康备注' }}</p></template>
      <template #cell-contact="{ row }"><div class="stack"><b>{{ row.emergency_contact_name || '联系人待补充' }}</b><small>{{ row.emergency_contact_phone || '联系电话待补充' }}</small></div></template>
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
import { getElderAvatar } from '@/utils/avatar'

defineEmits(['view', 'page', 'page-size'])
const props = defineProps({ rows: { type: Array, default: () => [] }, loading: Boolean, total: { type: Number, default: 0 }, page: { type: Number, default: 1 }, pageSize: { type: Number, default: 10 }, totalPages: { type: Number, default: 0 } })
const columns = [
  { key: 'elder', label: '姓名', width: '15%' },
  { key: 'level', label: '分级', width: '8%' },
  { key: 'address', label: '楼栋 / 门牌', width: '17%' },
  { key: 'status', label: '今日状态', width: '12%' },
  { key: 'risk', label: '风险', width: '11%' },
  { key: 'note', label: '健康备注', width: '17%' },
  { key: 'contact', label: '紧急联系人', width: '13%' },
  { key: 'action', label: '操作', width: '7%' },
]

function riskInfo(row) {
  const hasScore = row.risk_score !== null && row.risk_score !== undefined && Number.isFinite(Number(row.risk_score))
  const score = hasScore ? `${Math.round(Number(row.risk_score))} 分` : '尚未计算'
  if (row.risk_level === 'critical') return { tone: 'danger', label: '高风险', score }
  if (['warning', 'attention'].includes(row.risk_level)) return { tone: 'warning', label: '需关注', score }
  if (['normal', 'low'].includes(row.risk_level)) return { tone: 'normal', label: '正常', score }
  return { tone: 'muted', label: '待评估', score: '尚未计算' }
}

function areaName(address) {
  if (!address) return '辖区待分配'
  const match = address.match(/^([^0-9]+)(?=\d)/)
  return match?.[1] ? `${match[1]}片区` : '社区辖区'
}

function demographics(row) { return row.elder_phone || '手机号待补充' }
function initialOf(row) { return (row.elder_name || '长').trim().slice(0, 1) }
</script>

<style scoped>
.archive-panel { display: flex; min-height: 0; flex-direction: column; overflow: hidden; }
.archive-panel__head { display: flex; min-height: 62px; align-items: center; padding: 10px 18px 6px; }
.archive-panel__head h2 { margin: 0; color: #272624; font: 700 20px 'Songti SC','STSong',serif; }.archive-panel__head span { margin-left: 8px; color: #5f6670; font: 13px sans-serif; }.archive-panel__head span b { color: #c75a3d; }
.archive-table-view { min-height: 0; flex: 1; margin: 0 14px; }
.elder-cell, .today-status { display: flex; align-items: center; gap: 10px; min-width: 0; }.elder-cell img, .avatar-fallback { width: 45px; height: 48px; flex: none; border-radius: 7px; }.elder-cell img { object-fit: cover; }.avatar-fallback { display: grid; place-items: center; color: #fff; background: #c68a42; font: 700 17px 'Songti SC','STSong',serif; }.elder-cell div, .stack, .today-status div { min-width: 0; }.elder-cell b, .stack b, .today-status b { display: block; overflow: hidden; color: #302e2c; font-size: 13px; white-space: nowrap; text-overflow: ellipsis; }.elder-cell small, .stack small, .today-status small { display: block; margin-top: 4px; color: #89909a; font-size: 11px; white-space: nowrap; }
.level { display: inline-flex; min-width: 46px; height: 31px; align-items: center; justify-content: center; border-radius: 7px; font-size: 13px; font-weight: 800; }.level--A { color: #c6533d; background: #fae9e1; }.level--B { color: #c17b25; background: #fbefdd; }.level--C { color: #56826a; background: #e6f0e9; }
.today-status i { width: 9px; height: 9px; flex: none; border-radius: 50%; background: #b7b5af; box-shadow: 0 0 0 4px #f1efeb; }.today-status--active i { background: #6b9878; box-shadow: 0 0 0 4px #e4eee7; }
.risk { display: inline-flex; min-width: 62px; flex-direction: column; align-items: flex-start; gap: 3px; }.risk b { border-radius: 999px; padding: 4px 9px; font-size: 12px; }.risk small { padding-left: 9px; color: #8a8f96; font-size: 11px; }.risk--danger b { color: #c6533d; background: #fae9e1; }.risk--warning b { color: #b87923; background: #fbefdd; }.risk--normal b { color: #56826a; background: #e6f0e9; }.risk--muted b { color: #767b82; background: #efefed; }
.health-note { display: -webkit-box; overflow: hidden; margin: 0; color: #6f716f; font-size: 12px; line-height: 1.5; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
</style>
