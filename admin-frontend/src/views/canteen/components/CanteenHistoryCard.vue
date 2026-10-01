<template>
  <AppPanel class="history-card">
    <header><h2>历史记录</h2><AppButton variant="ghost" size="xs" @click="$emit('refresh')"><span class="material-symbols-outlined">refresh</span>刷新</AppButton></header>
    <AppTable :columns="columns" :rows="records" :loading="loading" compact clickable empty-text="暂无就餐记录" class="history-table" @row-click="selectRow">
      <template #cell-time="{ row }"><time>{{ formatTime(row.created_at) }}</time></template>
      <template #cell-source="{ row }"><b :class="row.source_format">{{ row.source_format === 'excel' ? 'Excel' : '文本' }}</b></template>
      <template #cell-status="{ row }"><b :class="row.parse_status">{{ statusLabel(row.parse_status) }}</b></template>
      <template #cell-content="{ row }"><span class="history-content" :title="row.raw_text">{{ row.raw_text || '—' }}</span></template>
    </AppTable>
  </AppPanel>
</template>

<script setup>
import AppButton from '@/components/AppButton.vue'
import AppPanel from '@/components/AppPanel.vue'
import AppTable from '@/components/AppTable.vue'

defineProps({ records: { type: Array, default: () => [] }, loading: Boolean })
const emit = defineEmits(['refresh', 'select'])
const columns = [
  { key: 'time', label: '时间', width: '128px' },
  { key: 'source', label: '来源', width: '80px' },
  { key: 'status', label: '状态', width: '92px' },
  { key: 'content', label: '原始内容' },
]

function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
function statusLabel(status) { return ({ success: '已解析', failed: '失败', pending: '解析中' }[status] || status) }
function selectRow(row) { if (row.parsed_data) emit('select', row) }
</script>

<style scoped>
.history-card { display: flex; flex-direction: column; padding: 15px 18px; overflow: hidden; }.history-card header { display: flex; align-items: center; justify-content: space-between; }.history-card h2 { margin: 0; color: #172942; font: 700 20px 'Songti SC','STSong',serif; }.history-card header .material-symbols-outlined { font-size: 17px; }.history-table { min-height: 0; margin-top: 10px; }.history-table b { display: inline-flex; padding: 4px 10px; border-radius: 999px; color: #bd634f; background: #faeee8; font-size: 10px; font-weight: 500; }.history-table b.excel, .history-table b.success { color: #4e826b; background: #eaf3ee; }.history-table b.pending { color: #aa7527; background: #fbf0dc; }.history-table b.failed { color: #c44d3e; background: #fae9e3; }.history-content { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
