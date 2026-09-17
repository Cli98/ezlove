<template>
  <div
    :class="[
      'p-4 rounded-2xl border cursor-pointer transition-all hover:shadow-md',
      expanded ? 'ring-2 ring-primary/30 bg-primary/5 border-primary/20' : 'bg-surface border-outline-variant/20 hover:border-outline-variant/40',
    ]"
    @click="$emit('toggle', building.name)"
  >
    <div class="flex items-center justify-between mb-2">
      <h5 class="text-sm font-bold text-on-surface">{{ shortName }}</h5>
      <span
        :class="[
          'w-2.5 h-2.5 rounded-full',
          building.status === 'red' ? 'bg-primary animate-pulse' :
          building.status === 'yellow' ? 'bg-accent' : 'bg-secondary',
        ]"
      ></span>
    </div>
    <div class="flex items-end justify-between">
      <div>
        <span class="serif-num text-2xl font-bold text-on-surface">{{ building.elder_count }}</span>
        <span class="text-[10px] text-inactive-gray ml-1">人</span>
      </div>
      <div class="text-right">
        <div class="text-xs font-bold" :class="rateColor">{{ building.active_rate }}%</div>
        <div class="w-16 h-1.5 bg-surface-container rounded-full mt-1 overflow-hidden">
          <div class="h-full rounded-full transition-all duration-500" :style="{ width: building.active_rate + '%', backgroundColor: rateBarColor }"></div>
        </div>
      </div>
    </div>
    <SparkLine
      v-if="trends?.length > 1"
      :data="trends"
      :width="64"
      :height="16"
      :color="rateBarColor"
      :show-dot="false"
      :fill-opacity="0.1"
      :stroke-width="1"
      class="mt-2"
    />
    <div v-if="building.alert_count > 0" class="mt-2 flex items-center gap-1">
      <span class="material-symbols-outlined text-primary text-xs">warning</span>
      <span class="text-[10px] text-primary font-bold">{{ building.alert_count }} 条告警</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SparkLine from './SparkLine.vue'

const props = defineProps({
  building: { type: Object, required: true },
  expanded: { type: Boolean, default: false },
  trends: { type: Array, default: () => [] },
})

defineEmits(['toggle'])

const shortName = computed(() => {
  const n = props.building.name
  const match = n.match(/\d+号楼/)
  return match ? match[0] : n
})

const rateColor = computed(() => {
  const r = props.building.active_rate
  if (r >= 70) return 'text-secondary'
  if (r >= 50) return 'text-accent'
  return 'text-primary'
})

const rateBarColor = computed(() => {
  const r = props.building.active_rate
  if (r >= 70) return '#6B8F71'
  if (r >= 50) return '#D4A24E'
  return '#C44D3E'
})
</script>
