<template>
  <AppPanel class="archive-panel">
    <header class="archive-panel__head">
      <h2>辖区老人档案 <span>共 <b>{{ total }}</b> 位老人</span></h2>
    </header>
    <AppTable
      :columns="columns"
      :rows="rows"
      :loading="loading"
      min-width="1180px"
      loading-text="正在整理老人档案…"
      empty-text="暂无符合条件的老人档案"
      class="archive-table-view"
    >
      <template #cell-elder="{ row }"><div class="elder-cell"><img v-if="getElderAvatar(row)" :src="getElderAvatar(row)" :alt="row.elder_name || '老人头像'" /><span v-else class="avatar-fallback" aria-hidden="true">{{ initialOf(row) }}</span><b>{{ row.elder_name || '未命名老人' }}</b></div></template>
      <template #cell-level="{ row }"><span :class="`level level--${row.care_level || 'C'}`">{{ row.care_level || 'C' }} 级</span></template>
      <template #cell-address="{ row }"><b class="address" :title="row.address || '未分配地址'">{{ row.address || '未分配地址' }}</b></template>
      <template #cell-status="{ row }"><span :class="['today-status', { 'today-status--active': row.today_active }]"><i></i>{{ row.today_active ? '今日有动态' : '暂无新动态' }}</span></template>
      <template #cell-risk="{ row }"><span :class="['risk', `risk--${riskInfo(row).tone}`]">{{ riskInfo(row).text }}</span></template>
      <template #cell-profile="{ row }"><p class="profile-info" :title="profileInfo(row)">{{ profileInfo(row) }}</p></template>
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
  { key: 'level', label: '分级', width: '9%' },
  { key: 'address', label: '楼栋 / 门牌', width: '20%' },
  { key: 'status', label: '今日状态', width: '14%' },
  { key: 'risk', label: '风险', width: '12%' },
  { key: 'profile', label: '年龄 / 性别 / 居住', width: '20%' },
  { key: 'action', label: '操作', width: '10%' },
]

function riskInfo(row) {
  const hasScore = row.risk_score !== null && row.risk_score !== undefined && Number.isFinite(Number(row.risk_score))
  const score = hasScore ? ` · ${Math.round(Number(row.risk_score))}` : ''
  if (row.risk_level === 'critical') return { tone: 'danger', text: `高风险${score}` }
  if (['warning', 'attention'].includes(row.risk_level)) return { tone: 'warning', text: `关注${score}` }
  if (['normal', 'low'].includes(row.risk_level)) return { tone: 'normal', text: `正常${score}` }
  return { tone: 'muted', text: '待评估' }
}

function profileInfo(row) {
  const age = row.elder_age ? `${row.elder_age}岁` : '年龄待补充'
  return `${age} · ${row.elder_gender || '性别待补充'} | ${row.living_status || '居住情况待补充'}`
}

function initialOf(row) { return (row.elder_name || '长').trim().slice(0, 1) }
</script>

<style scoped>
.archive-panel { display: flex; min-height: 0; flex-direction: column; overflow: hidden; }
.archive-panel__head { display: flex; min-height: 62px; align-items: center; padding: 10px 18px 6px; }
.archive-panel__head h2 { margin: 0; color: #272624; font: 700 20px 'Songti SC','STSong',serif; }.archive-panel__head span { margin-left: 8px; color: #5f6670; font: 13px sans-serif; }.archive-panel__head span b { color: #c75a3d; }
.archive-table-view { min-height: 0; flex: 1; margin: 0 14px; }
.elder-cell, .today-status { display: flex; align-items: center; gap: 10px; min-width: 0; }.elder-cell img, .avatar-fallback { width: 45px; height: 48px; flex: none; border-radius: 7px; }.elder-cell img { object-fit: cover; }.avatar-fallback { display: grid; place-items: center; color: #fff; background: #c68a42; font: 700 17px 'Songti SC','STSong',serif; }.elder-cell b, .address { display: block; overflow: hidden; color: #302e2c; font-size: 13px; white-space: nowrap; text-overflow: ellipsis; }
.level { display: inline-flex; min-width: 46px; height: 31px; align-items: center; justify-content: center; border-radius: 7px; font-size: 13px; font-weight: 800; }.level--A { color: #c6533d; background: #fae9e1; }.level--B { color: #c17b25; background: #fbefdd; }.level--C { color: #56826a; background: #e6f0e9; }
.today-status i { width: 9px; height: 9px; flex: none; border-radius: 50%; background: #b7b5af; box-shadow: 0 0 0 4px #f1efeb; }.today-status--active i { background: #6b9878; box-shadow: 0 0 0 4px #e4eee7; }
.risk { display: inline-flex; border-radius: 999px; padding: 5px 10px; font-size: 12px; font-weight: 700; }.risk--danger { color: #c6533d; background: #fae9e1; }.risk--warning { color: #b87923; background: #fbefdd; }.risk--normal { color: #56826a; background: #e6f0e9; }.risk--muted { color: #767b82; background: #efefed; }
.profile-info { overflow: hidden; margin: 0; color: #6f716f; font-size: 12px; white-space: nowrap; text-overflow: ellipsis; }
</style>
