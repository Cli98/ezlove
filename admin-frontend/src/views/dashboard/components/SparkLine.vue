<template>
  <svg :width="width" :height="height" class="overflow-visible">
    <defs v-if="fillOpacity > 0">
      <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" :stop-color="color" :stop-opacity="fillOpacity" />
        <stop offset="100%" :stop-color="color" stop-opacity="0" />
      </linearGradient>
    </defs>
    <polygon
      v-if="fillOpacity > 0 && points.length > 1"
      :points="fillPoints"
      :fill="`url(#${gradientId})`"
    />
    <polyline
      v-if="points.length > 1"
      :points="linePoints"
      fill="none"
      :stroke="color"
      :stroke-width="strokeWidth"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <circle
      v-if="showDot && points.length > 0"
      :cx="points[points.length - 1][0]"
      :cy="points[points.length - 1][1]"
      :r="strokeWidth + 0.5"
      :fill="color"
    />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  width: { type: Number, default: 80 },
  height: { type: Number, default: 24 },
  color: { type: String, default: '#6B8F71' },
  showDot: { type: Boolean, default: true },
  fillOpacity: { type: Number, default: 0.15 },
  strokeWidth: { type: Number, default: 1.5 },
})

const gradientId = computed(() => `spark-${Math.random().toString(36).slice(2, 8)}`)

const points = computed(() => {
  if (!props.data || props.data.length < 2) return []
  const pad = 2
  const w = props.width - pad * 2
  const h = props.height - pad * 2
  const min = Math.min(...props.data)
  const max = Math.max(...props.data)
  const range = max - min || 1
  return props.data.map((v, i) => [
    pad + (i / (props.data.length - 1)) * w,
    pad + h - ((v - min) / range) * h,
  ])
})

const linePoints = computed(() => points.value.map(p => p.join(',')).join(' '))

const fillPoints = computed(() => {
  if (points.value.length < 2) return ''
  const first = points.value[0]
  const last = points.value[points.value.length - 1]
  return `${first[0]},${props.height} ${linePoints.value} ${last[0]},${props.height}`
})
</script>
