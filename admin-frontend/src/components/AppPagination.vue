<template>
  <footer class="app-pagination">
    <span>共 {{ total }} 条</span>
    <button type="button" aria-label="上一页" :disabled="page <= 1" @click="$emit('page', page - 1)">‹</button>
    <button
      v-for="item in pageItems"
      :key="item"
      type="button"
      :class="{ active: item === page }"
      @click="$emit('page', item)"
    >{{ item }}</button>
    <button type="button" aria-label="下一页" :disabled="page >= totalPages" @click="$emit('page', page + 1)">›</button>
    <InlineSelect
      :model-value="pageSize"
      :options="pageSizeOptions"
      class="app-pagination__size"
      aria-label="每页显示条数"
      @change="$emit('page-size', $event)"
    />
  </footer>
</template>

<script setup>
import { computed } from 'vue'
import InlineSelect from '@/components/InlineSelect.vue'

defineEmits(['page', 'page-size'])
const props = defineProps({
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 10 },
  totalPages: { type: Number, default: 0 },
  pageSizeOptions: {
    type: Array,
    default: () => [{ value: 10, label: '10 条/页' }, { value: 20, label: '20 条/页' }, { value: 50, label: '50 条/页' }],
  },
})

const pageItems = computed(() => {
  const start = Math.max(1, Math.min(props.page - 2, props.totalPages - 4))
  return Array.from({ length: Math.min(5, props.totalPages) }, (_, index) => start + index)
})
</script>

<style scoped>
.app-pagination { display: flex; min-height: 54px; flex: none; align-items: center; justify-content: flex-end; gap: 6px; padding: 8px 14px; border-top: 1px solid #eee8e2; color: #737984; font-size: 12px; }
.app-pagination > span { margin-right: 8px; }
.app-pagination button { display: grid; width: 31px; height: 31px; padding: 0; place-items: center; border: 1px solid #ddd8d2; border-radius: 5px; color: #626975; background: #fff; font: 16px/1 sans-serif; cursor: pointer; }
.app-pagination button.active { color: #fff; border-color: #c75a3d; background: #c75a3d; }
.app-pagination button:disabled { opacity: .4; cursor: default; }
.app-pagination__size { height: 32px; margin-left: 8px; padding: 0 10px; border-radius: 5px; font-size: 12px; }
</style>
