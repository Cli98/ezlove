<template>
  <div class="bg-surface rounded-2xl border border-outline-variant/20 p-5">
    <div class="flex items-center justify-between mb-4">
      <h5 class="font-headline text-base font-bold text-on-surface">
        {{ building }}
        <span class="text-xs font-normal text-inactive-gray ml-2">{{ elders.length }} 人</span>
      </h5>
      <button
        class="text-xs text-inactive-gray hover:text-on-surface transition-colors"
        @click="$emit('close')"
      >
        <span class="material-symbols-outlined text-sm">close</span>
      </button>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-8 gap-2 text-inactive-gray">
      <div class="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      <span class="text-xs">加载中...</span>
    </div>

    <div v-else class="flex flex-wrap gap-3">
      <div
        v-for="e in elders"
        :key="e.elder_id"
        :class="[
          'w-12 h-12 text-white flex items-center justify-center rounded-xl font-headline text-lg shadow-sm hover:scale-110 transition-transform cursor-pointer',
          tileColor(e),
        ]"
        :title="tileTitle(e)"
        @click="$router.push(`/elders/${e.id}`)"
      >
        {{ e.name?.charAt(0) || '?' }}
      </div>
    </div>

    <!-- Legend -->
    <div class="flex items-center gap-4 mt-4 pt-3 border-t border-outline-variant/10 text-[10px] font-medium text-inactive-gray">
      <div class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-secondary"></span> 正常</div>
      <div class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-accent"></span> 关注</div>
      <div class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-warning"></span> 预警</div>
      <div class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-primary"></span> 高危</div>
      <div class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-inactive-gray"></span> 离线</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  building: { type: String, required: true },
  elders: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

defineEmits(['close'])

function tileColor(e) {
  if (e.risk_level === 'critical') return 'bg-primary ring-4 ring-primary/20 animate-pulse'
  if (e.risk_level === 'warning') return 'bg-warning'
  if (e.risk_level === 'attention') return 'bg-accent'
  if (e.today_active) return 'bg-secondary'
  return 'bg-inactive-gray opacity-80'
}

function tileTitle(e) {
  const risk = { normal: '正常', attention: '关注', warning: '预警', critical: '高危' }[e.risk_level] || '未评估'
  let s = `${e.name} — ${risk}`
  if (e.risk_score != null) s += ` (${e.risk_score}分)`
  if (e.has_family === false) s += ' · 无家属'
  if (!e.today_active) s += ' · 今日未活跃'
  return s
}
</script>
