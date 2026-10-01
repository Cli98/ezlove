<template>
  <AppPanel class="event-filters">
    <nav class="event-tabs" aria-label="关怀事件状态">
      <button v-for="tab in tabs" :key="tab.value" type="button" :class="{ active: status === tab.value }" @click="$emit('update:status', tab.value)">{{ tab.label }}</button>
    </nav>
    <InlineSelect :model-value="severity" :options="severityOptions" class="event-filters__select" @change="$emit('update:severity', $event)" />
    <InlineSelect :model-value="source" :options="sourceOptions" class="event-filters__select" @change="$emit('update:source', $event)" />
    <label class="event-search">
      <DashboardIcon name="search" />
      <input :value="search" placeholder="搜索老人姓名、事项说明或来源…" @input="$emit('update:search', $event.target.value)" />
    </label>
  </AppPanel>
</template>

<script setup>
import AppPanel from '@/components/AppPanel.vue'
import DashboardIcon from '@/components/DashboardIcon.vue'
import InlineSelect from '@/components/InlineSelect.vue'

defineEmits(['update:status', 'update:severity', 'update:source', 'update:search'])
defineProps({ status: String, severity: String, source: String, search: String })

const tabs = [{ value: 'all', label: '全部' }, { value: 'pending', label: '待处理' }, { value: 'followup', label: '跟进中' }, { value: 'done', label: '已办结' }]
const severityOptions = [{ value: '', label: '关怀程度  全部' }, { value: 'urgent', label: '关怀程度  重点' }, { value: 'warning', label: '关怀程度  关注' }, { value: 'info', label: '关怀程度  一般' }]
const sourceOptions = [{ value: '', label: '全部来源' }, { value: 'canteen', label: '食堂记录' }, { value: 'alert', label: '家属提醒' }, { value: 'manual', label: '手动记录' }]
</script>

<style scoped>
.event-filters { display: grid; min-height: 66px; align-items: center; grid-template-columns: minmax(350px,1fr) 180px 150px minmax(250px,330px); gap: 14px; margin-bottom: 14px; padding: 10px 16px; }
.event-tabs { display: flex; min-width: 0; align-self: stretch; align-items: center; }
.event-tabs button { position: relative; min-width: 82px; height: 100%; padding: 0 18px; border: 0; border-right: 1px solid #e5dfd8; color: #596271; background: transparent; font-size: 13px; cursor: pointer; }
.event-tabs button.active { color: #c6533d; font-weight: 800; }
.event-tabs button.active::after { content: ''; position: absolute; right: 15px; bottom: -10px; left: 15px; height: 3px; border-radius: 3px; background: #c6533d; }
.event-filters__select { width: 100%; height: 42px; justify-content: space-between; background: rgba(255,255,255,.76); }
.event-search { display: flex; height: 42px; align-items: center; gap: 9px; padding: 0 13px; border: 1px solid #ddd5cd; border-radius: 8px; color: #667080; background: rgba(255,255,255,.78); }
.event-search :deep(.dashboard-icon) { font-size: 17px; }
.event-search input { min-width: 0; flex: 1; border: 0; outline: 0; color: #343536; background: transparent; font-size: 12px; }
.event-search input::placeholder { color: #99969a; }
@media (max-width: 1180px) { .event-filters { grid-template-columns: 1fr 160px 140px; }.event-search { grid-column: 1 / -1; }.event-tabs button { min-width: 72px; padding-inline: 11px; } }
@media (max-width: 820px) { .event-filters { grid-template-columns: 1fr; }.event-tabs { min-height: 44px; overflow-x: auto; }.event-search { grid-column: auto; } }
</style>
