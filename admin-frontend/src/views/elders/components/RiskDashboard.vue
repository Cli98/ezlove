<template>
  <div class="bg-surface rounded-2xl shadow-sm border border-outline-variant/20 p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="font-headline text-lg font-bold text-on-surface">风险评估</h3>
      <button
        class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold text-primary bg-primary/5 hover:bg-primary/10 transition-colors"
        :disabled="refreshing"
        @click="$emit('refresh')"
      >
        <span class="material-symbols-outlined text-sm" :class="{ 'animate-spin': refreshing }">refresh</span>
        刷新评分
      </button>
    </div>

    <!-- 风险分数圆环 -->
    <div class="flex items-center justify-center mb-6">
      <div class="relative w-32 h-32">
        <svg viewBox="0 0 120 120" class="w-full h-full -rotate-90">
          <circle cx="60" cy="60" r="52" fill="none" stroke-width="8" class="stroke-outline-variant/20" />
          <circle
            cx="60" cy="60" r="52" fill="none" stroke-width="8"
            stroke-linecap="round"
            :stroke="riskColor"
            :stroke-dasharray="`${(score / 100) * 327} 327`"
            class="transition-all duration-700"
          />
        </svg>
        <div class="absolute inset-0 flex flex-col items-center justify-center">
          <span class="text-3xl font-bold" :style="{ color: riskColor }">{{ score }}</span>
          <span class="text-xs text-on-surface-variant">{{ riskLabel }}</span>
        </div>
      </div>
    </div>

    <!-- 5维度条形图 -->
    <div class="space-y-3">
      <div v-for="dim in dimensions" :key="dim.key" class="space-y-1">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-on-surface-variant">{{ dim.label }}</span>
          <span v-if="!dim.skipped" class="text-xs text-on-surface">{{ dim.score }}/100</span>
          <span v-else class="text-[10px] text-inactive-gray italic">已跳过</span>
        </div>
        <div v-if="!dim.skipped" class="h-1.5 bg-outline-variant/20 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-500"
            :style="{ width: dim.score + '%', backgroundColor: barColor(dim.score) }"
          ></div>
        </div>
        <p class="text-[10px] text-inactive-gray">{{ dim.detail }}</p>
      </div>
    </div>

    <!-- AI分析 -->
    <div v-if="showAiSection" class="mt-5 pt-4 border-t border-outline-variant/20">
      <button
        v-if="!aiResult && !aiLoading"
        class="w-full py-2.5 rounded-lg text-sm font-semibold text-primary border border-primary/30 hover:bg-primary/5 transition-colors"
        @click="$emit('request-ai')"
      >
        <span class="material-symbols-outlined text-sm align-middle mr-1">psychology</span>
        AI 趋势分析
      </button>
      <div v-else-if="aiLoading" class="flex items-center justify-center py-4 gap-2 text-inactive-gray">
        <div class="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
        <span class="text-xs">AI 分析中…</span>
      </div>
      <div v-else-if="aiResult" class="space-y-2">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-sm text-primary">psychology</span>
          <span class="text-xs font-bold text-on-surface">AI 分析结果</span>
          <span
            :class="[
              'px-1.5 py-0.5 rounded text-[10px] font-bold',
              aiResult.trend === 'improving' ? 'bg-secondary/10 text-secondary' :
              aiResult.trend === 'deteriorating' ? 'bg-primary/10 text-primary' :
              'bg-surface-container text-on-surface-variant',
            ]"
          >
            {{ trendLabel(aiResult.trend) }}
          </span>
        </div>
        <p class="text-sm text-on-surface leading-relaxed">{{ aiResult.summary }}</p>
        <div v-if="aiResult.concern_points?.length" class="flex flex-wrap gap-1.5">
          <span
            v-for="point in aiResult.concern_points"
            :key="point"
            class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-accent/10 text-accent"
          >
            {{ point }}
          </span>
        </div>
        <p class="text-xs text-on-surface-variant italic">{{ aiResult.suggested_action }}</p>
      </div>
    </div>

    <!-- 最后计算时间 -->
    <p v-if="calculatedAt" class="mt-3 text-[10px] text-inactive-gray text-right">
      最后评估: {{ formatTime(calculatedAt) }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  risk: { type: Object, default: () => ({}) },
  refreshing: { type: Boolean, default: false },
  aiResult: { type: Object, default: null },
  aiLoading: { type: Boolean, default: false },
})

defineEmits(['refresh', 'request-ai'])

const score = computed(() => props.risk?.score ?? 0)
const calculatedAt = computed(() => props.risk?.calculated_at)

const riskColor = computed(() => {
  const s = score.value
  if (s <= 30) return '#6B8F71'
  if (s <= 60) return '#D4A24E'
  if (s <= 80) return '#E67E22'
  return '#C44D3E'
})

const riskLabel = computed(() => {
  const s = score.value
  if (s <= 30) return '正常'
  if (s <= 60) return '关注'
  if (s <= 80) return '预警'
  return '高危'
})

const showAiSection = computed(() => {
  const level = props.risk?.level
  return level === 'warning' || level === 'critical' || level === 'attention'
})

const hasFamily = computed(() => props.risk?.details?.has_family !== false)

const dimensions = computed(() => {
  const d = props.risk?.details || {}
  const noFamily = !hasFamily.value
  return [
    {
      key: 'view',
      label: '牵挂查看',
      score: noFamily ? 0 : (d.view_frequency?.score ?? 0),
      skipped: noFamily,
      detail: noFamily
        ? '无家属绑定（此维度已跳过）'
        : `7天查看率 ${Math.round((d.view_frequency?.view_rate ?? 1) * 100)}% (${d.view_frequency?.viewed ?? 0}/${d.view_frequency?.moments ?? 0})`,
    },
    {
      key: 'canteen',
      label: '食堂出勤',
      score: d.canteen_attendance?.score ?? 0,
      detail: `${d.canteen_attendance?.present ?? 0}/${d.canteen_attendance?.total_meals ?? 0} 餐到场`,
    },
    {
      key: 'active',
      label: '活跃时间',
      score: d.last_active?.score ?? 0,
      detail: `最后活跃 ${d.last_active?.hours_inactive ?? '—'} 小时前`,
    },
    {
      key: 'alerts',
      label: '告警密度',
      score: d.alert_density?.score ?? 0,
      detail: `近30天 ${d.alert_density?.count_30d ?? 0} 次告警`,
    },
    {
      key: 'base',
      label: '基础等级',
      score: d.base_risk?.score ?? 0,
      detail: `护理等级 ${d.base_risk?.care_level ?? '—'}`,
    },
  ]
})

function barColor(s) {
  if (s <= 30) return '#6B8F71'
  if (s <= 60) return '#D4A24E'
  if (s <= 80) return '#E67E22'
  return '#C44D3E'
}

function trendLabel(t) {
  return { improving: '好转', stable: '稳定', deteriorating: '恶化' }[t] || t
}

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>
