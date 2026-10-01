<template>
  <AppPanel class="event-table-panel">
    <header class="event-table-panel__head"><h2>关怀事项列表 <span>共 {{ total }} 条</span></h2></header>
    <AppTable :columns="columns" :rows="rows" :loading="loading" min-width="1040px" class="event-table" loading-text="正在整理关怀事项…" empty-text="暂无符合条件的关怀事项">
      <template #cell-elder="{ row }">
        <div class="elder-cell"><img :src="row.avatar_url" :alt="row.elder_name" /><div><b>{{ row.elder_name }}</b><small>{{ row.elder_address }}</small></div></div>
      </template>
      <template #cell-description="{ row }"><span class="truncate-cell" :title="row.description">{{ row.description || '—' }}</span></template>
      <template #cell-source="{ row }"><div class="stack"><b>{{ row.source_label }}</b><small>{{ row.created_label }}</small></div></template>
      <template #cell-deadline="{ row }"><span :class="{ urgent: row.status_key === 'pending' }">{{ row.deadline_label }}</span></template>
      <template #cell-status="{ row }"><span :class="['status-pill', `status-pill--${row.status_key}`]"><i></i>{{ row.status_label }}</span></template>
      <template #cell-assignee="{ row }">{{ row.assignee || '待分配' }}</template>
      <template #cell-actions="{ row }">
        <div class="event-actions">
          <AppButton :variant="row.status_key === 'done' ? 'outline' : 'primary'" size="xs" @click.stop="$emit('process', row)">{{ row.status_key === 'done' ? '查看' : '处理' }}</AppButton>
          <AppButton variant="link" @click.stop="$emit('profile', row.elder_id)">查看档案</AppButton>
        </div>
      </template>
    </AppTable>
    <AppPagination :total="total" :page="page" :page-size="pageSize" :total-pages="totalPages" @page="$emit('page', $event)" @page-size="$emit('page-size', $event)" />
  </AppPanel>
</template>

<script setup>
import AppButton from '@/components/AppButton.vue'
import AppPagination from '@/components/AppPagination.vue'
import AppPanel from '@/components/AppPanel.vue'
import AppTable from '@/components/AppTable.vue'

defineEmits(['process', 'profile', 'page', 'page-size'])
defineProps({ rows: { type: Array, default: () => [] }, loading: Boolean, total: { type: Number, default: 0 }, page: { type: Number, default: 1 }, pageSize: { type: Number, default: 10 }, totalPages: { type: Number, default: 0 } })

const columns = [
  { key: 'elder', label: '关怀对象', width: '15%' },
  { key: 'description', label: '事项说明', width: '23%' },
  { key: 'source', label: '依据来源', width: '14%' },
  { key: 'deadline', label: '需要完成', width: '11%' },
  { key: 'status', label: '当前进展', width: '12%' },
  { key: 'assignee', label: '负责人', width: '9%' },
  { key: 'actions', label: '操作', width: '16%' },
]
</script>

<style scoped>
.event-table-panel { display: flex; min-height: 0; flex-direction: column; overflow: hidden; }
.event-table-panel__head { display: flex; min-height: 58px; align-items: center; padding: 9px 18px 5px; }
.event-table-panel__head h2 { margin: 0; color: #292724; font: 700 20px 'Songti SC','STSong',serif; }
.event-table-panel__head span { margin-left: 10px; color: #6c7481; font: 12px sans-serif; }
.event-table { min-height: 0; flex: 1; margin: 0 14px; }
.event-table :deep(.app-table td) { height: 62px; }
.elder-cell { display: flex; align-items: center; gap: 10px; min-width: 0; }
.elder-cell img { width: 43px; height: 43px; flex: none; object-fit: cover; border-radius: 7px; }
.elder-cell div, .stack { min-width: 0; }
.elder-cell b, .stack b { display: block; overflow: hidden; color: #343230; font-size: 12.5px; white-space: nowrap; text-overflow: ellipsis; }
.elder-cell small, .stack small { display: block; margin-top: 4px; color: #7f8895; font-size: 10.5px; white-space: nowrap; }
.truncate-cell { display: -webkit-box; overflow: hidden; line-height: 1.45; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.urgent { color: #c6533d; font-weight: 700; }
.status-pill { display: inline-flex; height: 29px; align-items: center; gap: 7px; padding: 0 11px; border-radius: 7px; font-size: 11.5px; font-weight: 700; white-space: nowrap; }
.status-pill i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.status-pill--pending { color: #c6533d; background: #f9e7df; }
.status-pill--followup { color: #cf852d; background: #fbefdc; }
.status-pill--done { color: #56826a; background: #e6f0e9; }
.event-actions { display: flex; align-items: center; gap: 18px; }
.event-actions :deep(.app-button--xs) { min-width: 62px; }
@media (max-width: 1050px) { .event-table-panel { min-height: 540px; } }
</style>
