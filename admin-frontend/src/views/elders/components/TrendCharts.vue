<template>
  <div class="bg-surface rounded-2xl shadow-sm border border-outline-variant/20 p-6 space-y-6">
    <h3 class="font-headline text-lg font-bold text-on-surface">30 天趋势</h3>

    <!-- Active days bar chart -->
    <div>
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-bold text-on-surface-variant">每日活跃</span>
        <span class="text-xs text-inactive-gray">{{ activeDayCount }}/{{ summary.total_days || 30 }} 天</span>
      </div>
      <div class="flex gap-[2px] h-8 items-end">
        <div
          v-for="(day, i) in dailyActivity"
          :key="i"
          class="flex-1 rounded-t-sm transition-colors"
          :class="day.active ? 'bg-secondary' : 'bg-outline-variant/20'"
          :style="{ height: day.active ? '100%' : '30%' }"
          :title="`${day.date} ${day.active ? '活跃' : '未活跃'}`"
        ></div>
      </div>
    </div>

    <!-- Canteen attendance -->
    <div v-if="dailyCanteen.length">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-bold text-on-surface-variant">食堂出勤</span>
        <span class="text-xs text-inactive-gray">
          {{ canteenPresentCount }}/{{ dailyCanteen.length }} 餐
          ({{ summary.canteen_rate != null ? summary.canteen_rate + '%' : '—' }})
        </span>
      </div>
      <svg :viewBox="`0 0 ${chartW} 60`" class="w-full">
        <polyline
          :points="canteenPoints"
          fill="none"
          stroke="#6B8F71"
          stroke-width="2"
          stroke-linejoin="round"
        />
        <circle
          v-for="(pt, i) in canteenDots"
          :key="i"
          :cx="pt.x"
          :cy="pt.y"
          r="3"
          :fill="pt.present ? '#6B8F71' : '#C44D3E'"
        />
      </svg>
    </div>

    <!-- Risk score trend -->
    <div v-if="riskHistory.length">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-bold text-on-surface-variant">风险分数走势</span>
        <span class="text-xs text-inactive-gray">当前 {{ currentRiskScore }}</span>
      </div>
      <svg :viewBox="`0 0 ${chartW} 60`" class="w-full">
        <!-- Danger zone -->
        <rect x="0" y="0" :width="chartW" height="12" fill="#C44D3E10" />
        <rect x="0" y="12" :width="chartW" height="12" fill="#E67E2210" />

        <polyline
          :points="riskPoints"
          fill="none"
          stroke="#C44D3E"
          stroke-width="2"
          stroke-linejoin="round"
        />
        <circle
          v-for="(pt, i) in riskDots"
          :key="i"
          :cx="pt.x"
          :cy="pt.y"
          r="2.5"
          :fill="riskDotColor(pt.score)"
        />
      </svg>
      <div class="flex justify-between text-[9px] text-inactive-gray mt-1">
        <span>30天前</span>
        <span>今天</span>
      </div>
    </div>

    <!-- Summary stats -->
    <div class="grid grid-cols-3 gap-3 pt-3 border-t border-outline-variant/10">
      <div class="text-center">
        <div class="serif-num text-xl font-bold text-on-surface">{{ summary.active_days || 0 }}</div>
        <div class="text-[10px] text-inactive-gray">活跃天数</div>
      </div>
      <div class="text-center">
        <div class="serif-num text-xl font-bold text-on-surface">{{ summary.total_views || 0 }}</div>
        <div class="text-[10px] text-inactive-gray">查看次数</div>
      </div>
      <div class="text-center">
        <div class="serif-num text-xl font-bold text-on-surface">{{ summary.canteen_rate != null ? summary.canteen_rate + '%' : '—' }}</div>
        <div class="text-[10px] text-inactive-gray">食堂出勤</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  summary: { type: Object, default: () => ({}) },
})

const chartW = 300

const dailyActivity = computed(() => props.summary?.daily_activity || [])
const dailyCanteen = computed(() => props.summary?.daily_canteen || [])
const riskHistory = computed(() => props.summary?.risk_history || [])

const activeDayCount = computed(() => dailyActivity.value.filter(d => d.active).length)
const canteenPresentCount = computed(() => dailyCanteen.value.filter(d => d.present).length)
const currentRiskScore = computed(() => {
  const h = riskHistory.value
  return h.length > 0 ? h[h.length - 1].score : '—'
})

const canteenDots = computed(() => {
  const days = dailyCanteen.value
  if (!days.length) return []
  return days.map((d, i) => ({
    x: (i / Math.max(days.length - 1, 1)) * chartW,
    y: d.present ? 15 : 45,
    present: d.present,
  }))
})

const canteenPoints = computed(() =>
  canteenDots.value.map(p => `${p.x},${p.y}`).join(' ')
)

const riskDots = computed(() => {
  const days = riskHistory.value
  if (!days.length) return []
  return days.map((d, i) => ({
    x: (i / Math.max(days.length - 1, 1)) * chartW,
    y: 55 - (d.score / 100) * 50,
    score: d.score,
  }))
})

const riskPoints = computed(() =>
  riskDots.value.map(p => `${p.x},${p.y}`).join(' ')
)

function riskDotColor(score) {
  if (score <= 30) return '#6B8F71'
  if (score <= 60) return '#D4A24E'
  if (score <= 80) return '#E67E22'
  return '#C44D3E'
}
</script>
