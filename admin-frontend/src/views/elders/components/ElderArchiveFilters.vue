<template>
  <section class="archive-filters">
    <label class="archive-filter archive-filter--search">
      <DashboardIcon name="search" />
      <input :value="search" placeholder="搜索姓名、楼栋或门牌号" @input="updateSearch" />
    </label>
    <InlineSelect :model-value="area" :options="areaOptions" class="archive-filter" aria-label="选择片区" @change="update('area', $event)" />
    <InlineSelect :model-value="careLevel" :options="careOptions" class="archive-filter" aria-label="选择关怀分级" @change="update('careLevel', $event)" />
    <label class="follow-toggle">
      <input type="checkbox" :checked="followUp" @change="update('followUp', $event.target.checked)" />
      <i></i><span>仅看待跟进</span>
    </label>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import DashboardIcon from '@/components/DashboardIcon.vue'
import InlineSelect from '@/components/InlineSelect.vue'

const emit = defineEmits(['update:search', 'update:area', 'update:careLevel', 'update:followUp', 'change', 'search'])
const props = defineProps({
  search: { type: String, default: '' },
  area: { type: String, default: '' },
  careLevel: { type: String, default: '' },
  followUp: Boolean,
  areas: { type: Array, default: () => [] },
})
const areaOptions = computed(() => [{ value: '', label: '全部片区' }, ...props.areas.map(item => ({ value: item, label: item }))])
const careOptions = [{ value: '', label: '全部关怀分级' }, { value: 'A', label: 'A级 · 重点关怀' }, { value: 'B', label: 'B级 · 日常关注' }, { value: 'C', label: 'C级 · 健康互助' }]

function update(name, value) {
  emit(`update:${name}`, value)
  emit('change')
}

function updateSearch(event) {
  emit('update:search', event.target.value)
  emit('search')
}

</script>

<style scoped>
.archive-filters { position: relative; display: grid; grid-template-columns: 1.35fr .82fr .82fr auto; gap: 14px; align-items: center; margin-bottom: 14px; padding: 14px 16px; overflow: hidden; isolation: isolate; border-radius: 11px; background: url('@/assets/dashboard-composite/focus-stats-waves.png') right center / auto 100% no-repeat, linear-gradient(102deg, #fbf1e9 0%, #fbf4ed 34%, #faf3ec 63%, #f7efe7 100%); }
.archive-filters::before { content: ''; position: absolute; z-index: 0; top: 0; left: 0; width: 70px; height: 92px; clip-path: path('M0 0 H70 C44 6 16 54 0 82 Z'); background: linear-gradient(135deg, rgba(224,121,68,.16), rgba(232,148,101,.1) 58%, rgba(246,218,200,.035)); pointer-events: none; }.archive-filters > * { position: relative; z-index: 1; }
.archive-filter { width: 100%; height: 44px; padding: 0 14px; color: #545b67; border: 1px solid #ddd5cd; border-radius: 7px; outline: none; background: rgba(255,255,255,.75); font-size: 13px; }
.archive-filter:focus-within { border-color: rgba(196,77,62,.55); }
.archive-filter--search { display: flex; align-items: center; gap: 10px; }
.archive-filter--search :deep(.dashboard-icon) { color: #687485; font-size: 18px; }
.archive-filter--search input { min-width: 0; flex: 1; border: 0; outline: 0; background: transparent; color: #33312f; font-size: 13px; }
.archive-filter--search input::placeholder { color: #8f9298; }
.follow-toggle { display: flex; align-items: center; gap: 10px; padding: 0 7px; color: #505663; font-size: 13px; white-space: nowrap; cursor: pointer; }
.follow-toggle input { position: absolute; opacity: 0; pointer-events: none; }
.follow-toggle i { position: relative; width: 36px; height: 20px; border-radius: 999px; background: #d8d8d8; transition: background .2s; }
.follow-toggle i::after { content: ''; position: absolute; top: 3px; left: 3px; width: 14px; height: 14px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.12); transition: transform .2s; }
.follow-toggle input:checked + i { background: #c75a3d; }.follow-toggle input:checked + i::after { transform: translateX(16px); }
@media (max-width: 1080px) { .archive-filters { grid-template-columns: 1fr 1fr; }.follow-toggle { min-height: 44px; } }
</style>
