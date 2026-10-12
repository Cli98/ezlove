<template>
  <AppPanel class="volunteer-toolbar">
    <nav class="volunteer-tabs" aria-label="邻里帮功能">
      <button v-for="tab in tabs" :key="tab.value" type="button" :class="{ active: modelValue === tab.value }" @click="$emit('update:modelValue', tab.value)">{{ tab.label }}</button>
    </nav>
    <label class="volunteer-search">
      <DashboardIcon name="search" />
      <input :value="search" :placeholder="searchPlaceholder" @input="$emit('update:search', $event.target.value)" />
    </label>
    <template v-if="modelValue === 'tasks'">
      <InlineSelect :model-value="status" :options="statusOptions" class="volunteer-toolbar__select" @change="$emit('update:status', $event)" />
      <InlineSelect :model-value="taskType" :options="typeOptions" class="volunteer-toolbar__select" @change="$emit('update:taskType', $event)" />
    </template>
  </AppPanel>
</template>

<script setup>
import { computed } from 'vue'
import AppPanel from '@/components/AppPanel.vue'
import DashboardIcon from '@/components/DashboardIcon.vue'
import InlineSelect from '@/components/InlineSelect.vue'

const props = defineProps({ modelValue: String, search: String, status: String, taskType: String })
defineEmits(['update:modelValue', 'update:search', 'update:status', 'update:taskType'])

const tabs = [{ value: 'tasks', label: '任务管理' }, { value: 'volunteers', label: '志愿者名单' }, { value: 'leaderboard', label: '积分排行' }]
const statusOptions = [{ value: '', label: '全部状态' }, { value: 'pending', label: '待接取' }, { value: 'accepted', label: '进行中' }, { value: 'completed', label: '待审核' }, { value: 'verified', label: '已完成' }]
const typeOptions = [{ value: '', label: '全部类型' }, { value: 'visit', label: '探访' }, { value: 'accompany', label: '陪伴' }, { value: 'check_in', label: '签到' }, { value: 'errand', label: '代办' }]
const searchPlaceholder = computed(() => props.modelValue === 'tasks' ? '搜索任务、志愿者或服务对象…' : props.modelValue === 'volunteers' ? '搜索志愿者姓名…' : '搜索排行姓名…')
</script>

<style scoped>
.volunteer-toolbar { display: grid; min-height: 66px; align-items: center; grid-template-columns: minmax(390px,1fr) minmax(250px,330px) 160px 150px; gap: 14px; margin-bottom: 14px; padding: 10px 16px; }
.volunteer-tabs { display: flex; min-width: 0; align-self: stretch; align-items: center; }
.volunteer-tabs button { position: relative; min-width: 112px; height: 100%; padding: 0 18px; border: 0; color: #596271; background: transparent; font: 700 14px 'Songti SC','STSong',serif; cursor: pointer; }
.volunteer-tabs button.active { color: #28313e; font-size: 17px; }
.volunteer-tabs button.active::after { content: ''; position: absolute; right: 18px; bottom: -10px; left: 18px; height: 3px; border-radius: 3px; background: #c6533d; }
.volunteer-search { display: flex; height: 42px; align-items: center; gap: 9px; padding: 0 13px; border: 1px solid #ddd5cd; border-radius: 8px; color: #667080; background: rgba(255,255,255,.78); }
.volunteer-search :deep(.dashboard-icon) { font-size: 17px; }
.volunteer-search input { min-width: 0; flex: 1; border: 0; outline: 0; color: #343536; background: transparent; font-size: 12px; }
.volunteer-search input::placeholder { color: #99969a; }
.volunteer-toolbar__select { width: 100%; height: 42px; justify-content: space-between; background: rgba(255,255,255,.76); }
@media (max-width: 1180px) { .volunteer-toolbar { grid-template-columns: 1fr 150px 140px; }.volunteer-search { grid-column: 1 / -1; grid-row: 2; }.volunteer-tabs button { min-width: 96px; } }
@media (max-width: 820px) { .volunteer-toolbar { grid-template-columns: 1fr; }.volunteer-tabs { min-height: 44px; overflow-x: auto; }.volunteer-search { grid-column: auto; grid-row: auto; } }
</style>
