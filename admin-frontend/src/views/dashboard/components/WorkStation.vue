<template>
  <div class="bg-surface rounded-3xl shadow-sm border border-outline-variant/20 p-6">
    <h3 class="font-headline text-lg font-bold text-on-surface mb-4">工作台</h3>

    <!-- Tabs -->
    <div class="flex gap-2 mb-4">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="[
          'px-3 py-1.5 rounded-lg text-xs font-bold transition-colors',
          activeTab === tab.key
            ? 'bg-primary text-white'
            : 'bg-surface-container text-on-surface-variant hover:bg-outline-variant/20',
        ]"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
        <span
          v-if="tab.count > 0"
          :class="[
            'ml-1 px-1.5 py-0.5 rounded-full text-[10px]',
            activeTab === tab.key ? 'bg-white/20' : 'bg-primary/10 text-primary',
          ]"
        >{{ tab.count }}</span>
      </button>
    </div>

    <!-- Pending confirmations -->
    <div v-if="activeTab === 'confirm'" class="space-y-2 max-h-80 overflow-y-auto">
      <div v-if="!confirmations.length" class="text-center py-8 text-inactive-gray text-sm">
        A/B 级老人今日均已活跃
      </div>
      <div
        v-for="elder in confirmations"
        :key="elder.id"
        class="flex items-center justify-between p-3 rounded-xl bg-surface-container/50 hover:bg-surface-container transition-colors"
      >
        <div
          class="flex items-center gap-3 min-w-0 cursor-pointer"
          @click="$router.push(`/elders/${elder.id}`)"
        >
          <div
            :class="[
              'w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold shrink-0',
              elder.care_level === 'A' ? 'bg-primary' : 'bg-accent',
            ]"
          >{{ elder.name?.charAt(0) }}</div>
          <div class="min-w-0">
            <p class="text-sm font-bold text-on-surface truncate hover:text-primary transition-colors">{{ elder.name }}</p>
            <p class="text-[10px] text-inactive-gray truncate">{{ elder.care_level }}级 · {{ elder.address }}</p>
          </div>
        </div>
        <button
          class="shrink-0 px-3 py-1.5 rounded-lg text-xs font-bold text-secondary bg-secondary/10 hover:bg-secondary/20 transition-colors"
          @click="$emit('confirm', elder.id)"
        >确认活跃</button>
      </div>
    </div>

    <!-- Pending alerts -->
    <div v-if="activeTab === 'alerts'" class="space-y-2 max-h-80 overflow-y-auto">
      <div v-if="!alerts.length" class="text-center py-8 text-inactive-gray text-sm">
        暂无待处理告警
      </div>
      <div
        v-for="alert in alerts"
        :key="alert.id"
        class="flex items-center gap-3 p-3 rounded-xl hover:bg-surface-container/50 transition-colors cursor-pointer"
        @click="alert.elder_id && $router.push(`/elders/${alert.elder_id}`)"
      >
        <span
          :class="[
            'material-symbols-outlined text-lg',
            alert.alert_level === 'critical' ? 'text-primary' : alert.alert_level === 'warning' ? 'text-warning' : 'text-accent',
          ]"
        >{{ alert.alert_level === 'critical' ? 'emergency' : 'warning' }}</span>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold text-on-surface truncate">{{ alert.elder_name }}</p>
          <p class="text-xs text-on-surface-variant truncate">{{ alert.message }}</p>
        </div>
        <span class="text-[10px] text-inactive-gray shrink-0">{{ formatTime(alert.created_at) }}</span>
      </div>
    </div>

    <!-- Timed out -->
    <div v-if="activeTab === 'timeout'" class="space-y-2 max-h-80 overflow-y-auto">
      <div v-if="!timedOut.length" class="text-center py-8 text-inactive-gray text-sm">
        无超时告警
      </div>
      <div
        v-for="alert in timedOut"
        :key="alert.id"
        class="flex items-center gap-3 p-3 rounded-xl bg-primary/5 border border-primary/10 cursor-pointer hover:bg-primary/10 transition-colors"
        @click="alert.elder_id && $router.push(`/elders/${alert.elder_id}`)"
      >
        <span class="material-symbols-outlined text-primary text-lg animate-pulse">crisis_alert</span>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-bold text-primary truncate">{{ alert.elder_name }}</p>
          <p class="text-xs text-on-surface-variant truncate">{{ alert.message }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  workstation: { type: Object, default: () => ({}) },
  activeArea: { type: String, default: '' },
})

defineEmits(['confirm'])

const activeTab = ref('confirm')

const confirmations = computed(() => {
  const all = props.workstation?.pending_confirmations || []
  if (!props.activeArea) return all
  return all.filter(e => e.address?.includes(props.activeArea))
})
const alerts = computed(() => props.workstation?.pending_alerts || [])
const timedOut = computed(() => props.workstation?.timed_out || [])

const tabs = computed(() => [
  { key: 'confirm', label: '待确认', count: confirmations.value.length },
  { key: 'alerts', label: '待处理', count: alerts.value.length },
  { key: 'timeout', label: '已超时', count: timedOut.value.length },
])

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>
