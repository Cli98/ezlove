<template>
  <div class="app-table-wrap">
    <table class="app-table" :class="{ 'app-table--compact': compact }" :style="{ minWidth }">
      <thead><tr><th v-for="column in columns" :key="column.key" :style="{ width: column.width }">{{ column.label }}</th></tr></thead>
      <tbody>
        <tr v-for="(row,index) in rows" :key="rowKeyOf(row,index)" :class="{ 'app-table__row--clickable': clickable }" :tabindex="clickable ? 0 : undefined" @click="$emit('row-click', row)" @keyup.enter="$emit('row-click', row)">
          <td v-for="column in columns" :key="column.key"><slot :name="`cell-${column.key}`" :row="row" :index="index">{{ row[column.key] ?? '—' }}</slot></td>
        </tr>
      </tbody>
    </table>
    <div v-if="loading" class="app-table__state">{{ loadingText }}</div>
    <div v-else-if="!rows.length" class="app-table__state">{{ emptyText }}</div>
  </div>
</template>

<script setup>
const props = defineProps({
  columns: { type: Array, default: () => [] },
  rows: { type: Array, default: () => [] },
  rowKey: { type: [String, Function], default: 'id' },
  minWidth: { type: String, default: '0' },
  loading: Boolean,
  loadingText: { type: String, default: '加载中…' },
  emptyText: { type: String, default: '暂无数据' },
  compact: Boolean,
  clickable: Boolean,
})
defineEmits(['row-click'])
function rowKeyOf(row, index) { return typeof props.rowKey === 'function' ? props.rowKey(row, index) : row[props.rowKey] ?? index }
</script>

<style scoped>
.app-table-wrap { min-height: 0; overflow: auto; scrollbar-width: thin; }.app-table { width: 100%; border-collapse: collapse; table-layout: fixed; }.app-table th { padding: 12px 10px; color: #68707d; background: linear-gradient(90deg,#f8f2ed,#fbf6f0); font-size: 13px; font-weight: 800; text-align: left; }.app-table th:first-child { border-radius: 7px 0 0 7px; }.app-table th:last-child { border-radius: 0 7px 7px 0; }.app-table td { height: 70px; padding: 8px 10px; border-bottom: 1px solid #eee9e4; color: #383735; font-size: 13px; vertical-align: middle; }.app-table tbody tr:last-child td { border-bottom: 0; }.app-table__row--clickable { cursor: pointer; }.app-table--compact th { height: 36px; padding: 0 10px; font-size: 11px; font-weight: 500; }.app-table--compact td { height: 37px; padding: 0 10px; color: #4f5e75; font-size: 11px; }.app-table__state { display: grid; min-height: 120px; place-items: center; color: #91867c; font-size: 13px; }
</style>
