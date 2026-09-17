<template>
  <div class="bg-surface rounded-2xl shadow-sm border border-outline-variant/20 p-6">
    <h3 class="font-headline text-lg font-bold text-on-surface mb-4">活动时间线</h3>

    <!-- 活动日历（30天） -->
    <div v-if="activitySummary" class="mb-6">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-bold text-on-surface-variant uppercase tracking-wider">30日活跃度</span>
        <span class="text-xs text-on-surface-variant">
          {{ activitySummary.active_days }}/{{ activitySummary.total_days }} 天活跃
          <template v-if="activitySummary.canteen_rate !== null">
            · 食堂 {{ activitySummary.canteen_rate }}%
          </template>
        </span>
      </div>
      <div class="flex flex-wrap gap-[3px]">
        <div
          v-for="day in activitySummary.daily_activity"
          :key="day.date"
          :title="day.date + (day.active ? ' — 活跃' : ' — 无活动')"
          :class="[
            'w-3 h-3 rounded-sm transition-colors',
            day.active ? 'bg-secondary' : 'bg-outline-variant/30',
          ]"
        ></div>
      </div>
    </div>

    <!-- 过滤标签 -->
    <div class="flex flex-wrap gap-2 mb-4">
      <button
        v-for="tab in filterTabs"
        :key="tab.value"
        :class="[
          'px-3 py-1 rounded-full text-xs font-semibold transition-colors',
          activeFilter === tab.value
            ? 'bg-primary text-white'
            : 'bg-surface-container text-on-surface-variant hover:bg-outline-variant/40',
        ]"
        @click="setFilter(tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 时间线列表 -->
    <div v-if="filteredItems.length > 0" class="space-y-1">
      <div
        v-for="item in filteredItems"
        :key="item.id"
        class="flex items-start gap-3 py-2.5 px-3 rounded-lg hover:bg-surface-container/50 transition-colors"
      >
        <div
          :class="[
            'mt-0.5 w-8 h-8 rounded-lg flex items-center justify-center shrink-0',
            iconBg(item),
          ]"
        >
          <span class="material-symbols-outlined text-base" :class="iconColor(item)">
            {{ iconName(item) }}
          </span>
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold text-on-surface">{{ item.label }}</span>
            <span
              v-if="item.severity && item.severity !== 'info'"
              :class="[
                'px-1.5 py-0.5 rounded text-[10px] font-bold uppercase',
                item.severity === 'urgent' ? 'bg-primary/10 text-primary' :
                item.severity === 'warning' ? 'bg-accent/10 text-accent' :
                'bg-surface-container text-on-surface-variant',
              ]"
            >
              {{ severityLabel(item.severity) }}
            </span>
          </div>
          <p class="text-xs text-on-surface-variant mt-0.5 line-clamp-2">{{ item.description }}</p>
        </div>
        <span class="text-[11px] text-inactive-gray whitespace-nowrap mt-1">{{ formatTime(item.time) }}</span>
      </div>
    </div>
    <div v-else class="flex flex-col items-center justify-center py-8 gap-2 text-inactive-gray">
      <span class="material-symbols-outlined text-3xl">event_busy</span>
      <p class="text-sm">暂无活动记录</p>
    </div>

    <!-- 加载更多 -->
    <button
      v-if="hasMore"
      class="mt-3 w-full py-2 text-xs font-semibold text-primary hover:bg-primary/5 rounded-lg transition-colors"
      @click="$emit('load-more')"
    >
      加载更多
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  activitySummary: { type: Object, default: null },
  hasMore: { type: Boolean, default: false },
})

defineEmits(['load-more'])

const filterTabs = [
  { label: '全部', value: 'all' },
  { label: '查看', value: 'view' },
  { label: '牵挂', value: 'moment' },
  { label: '食堂', value: 'canteen' },
  { label: '告警', value: 'alert' },
  { label: '事件', value: 'event' },
]

const activeFilter = ref('all')

function setFilter(v) {
  activeFilter.value = v
}

const filteredItems = computed(() => {
  if (activeFilter.value === 'all') return props.items
  if (activeFilter.value === 'canteen') {
    return props.items.filter(i => i.type === 'canteen_present' || i.type === 'canteen_absent')
  }
  return props.items.filter(i => i.type === activeFilter.value)
})

const iconMap = {
  view: 'visibility',
  moment: 'favorite',
  canteen_present: 'restaurant',
  canteen_absent: 'no_meals',
  alert: 'warning',
  event: 'event_note',
}

function iconName(item) {
  return iconMap[item.type] || 'info'
}

function iconBg(item) {
  if (item.type === 'alert') return 'bg-primary/10'
  if (item.type === 'canteen_absent') return 'bg-accent/10'
  if (item.type === 'view') return 'bg-secondary/10'
  if (item.type === 'moment') return 'bg-primary-container'
  return 'bg-surface-container'
}

function iconColor(item) {
  if (item.type === 'alert') return 'text-primary'
  if (item.type === 'canteen_absent') return 'text-accent'
  if (item.type === 'view') return 'text-secondary'
  if (item.type === 'moment') return 'text-terracotta'
  return 'text-on-surface-variant'
}

function severityLabel(s) {
  return { urgent: '紧急', warning: '注意', info: '' }[s] || s
}

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  const diffH = (now - d) / 3600000
  if (diffH < 1) return `${Math.round(diffH * 60)}分钟前`
  if (diffH < 24) return `${Math.round(diffH)}小时前`
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>
