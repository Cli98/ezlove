<template>
  <aside class="care-card">
    <section class="care-section">
      <h2>下一步关怀</h2>
      <div class="care-meta"><span><i class="material-symbols-outlined">person</i>责任人　<b>{{ workerName }}</b></span><span><i class="material-symbols-outlined">schedule</i>处理时限　<b>{{ plan.deadline }}</b></span></div>
      <div v-for="(item,index) in plan.items" :key="item" class="care-task"><i>{{ index + 1 }}</i><span>{{ item }}</span><button @click="$emit('complete', index)">去完成</button></div>
    </section>
    <section class="care-section evidence">
      <h2>关注依据</h2>
      <div v-for="metric in metrics" :key="metric.label" class="metric"><span>{{ metric.label }}</span><div><i :class="metric.tone" :style="{ width: `${metric.value}%` }"></i></div><b>{{ metric.value }}%</b></div>
    </section>
    <section class="care-section contact">
      <header><h2>联系人信息</h2><button @click="$emit('edit')"><span class="material-symbols-outlined">edit</span>编辑</button></header>
      <div class="contact-row"><span class="material-symbols-outlined">person</span><small>紧急联系人</small><b>{{ contact.name || '待补充' }}</b><a v-if="contact.phone" :href="`tel:${contact.phone}`"><span class="material-symbols-outlined">phone</span>{{ contact.phone }}</a></div>
    </section>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

defineEmits(['complete','edit'])
const props = defineProps({ detail: { type:Object, required:true }, workerName: { type:String, default:'社工' } })
const plan = computed(() => props.detail.care_plan || {
  deadline: ['critical','warning'].includes(props.detail.risk?.level) ? '今日 17:00' : '明日 12:00',
  items: props.detail.alerts?.some(item => !item.is_resolved)
    ? ['电话联系老人或家属，确认近期情况','如无法联系，安排上门走访']
    : ['保持日常问候，继续关注近期状态'],
})
const metrics = computed(() => {
  const source = props.detail.care_metrics || {}
  const summary = props.detail.activity_summary || {}
  const activeRate = summary.total_days ? Math.round((summary.active_days || 0) / summary.total_days * 100) : 0
  return [
    { label:'食堂到勤', value:Math.round(source.canteen ?? summary.canteen_rate ?? 0), tone:'amber' },
    { label:'社交互动', value:Math.round(source.social ?? activeRate), tone:'sage' },
    { label:'健康风险', value:Math.round(source.health ?? props.detail.risk?.score ?? 0), tone:'amber' },
  ]
})
const contact = computed(() => props.detail.elder?.emergency_contact || {})
</script>

<style scoped>
.care-card { min-height: 0; overflow-y: auto; border: 1px solid #e5ddd5; border-radius: 11px; background: rgba(255,255,255,.8); scrollbar-width: thin; }.care-section { padding: 17px 20px; border-top: 1px solid #eee8e2; }.care-section:first-child { border-top: 5px solid #f5c6ad; }.care-section h2 { margin: 0 0 15px; color: #172942; font: 700 20px 'Songti SC','STSong',serif; }.care-meta { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 15px; color: #5c687b; font-size: 12px; }.care-meta span { display: flex; align-items: center; }.care-meta i { margin-right: 6px; color: #d7593f; font-size: 21px; }.care-meta b { color: #26354c; }.care-meta span:last-child b { color: #d7593f; font-size: 14px; }.care-task { display: grid; grid-template-columns: 24px 1fr 64px; min-height: 44px; align-items: center; gap: 8px; margin-top: 8px; padding: 6px 8px; border: 1px solid #eee8e2; border-radius: 7px; color: #5d687a; font-size: 12px; }.care-task > i { display: grid; width: 21px; height: 21px; place-items: center; border-radius: 50%; color: #d05a40; background: #faebe4; font-style: normal; font-weight: 800; }.care-task button { height: 30px; border: 1px solid #d85a42; border-radius: 5px; color: #d2543d; background: #fff; font-size: 12px; font-weight: 700; cursor: pointer; }
.metric { display: grid; grid-template-columns: 70px 1fr 38px; align-items: center; gap: 10px; margin: 12px 0; color: #59667b; font-size: 12px; }.metric > div { height: 12px; overflow: hidden; border-radius: 999px; background: #e8e8e8; }.metric i { display: block; height: 100%; border-radius: inherit; }.metric i.amber { background: linear-gradient(90deg,#d98f32,#e0a54d); }.metric i.sage { background: linear-gradient(90deg,#5d8b77,#77a18d); }.metric b { color: #536178; font-size: 13px; text-align: right; }
.contact header { display: flex; align-items: center; justify-content: space-between; }.contact header h2 { margin-bottom: 0; }.contact header button { display: flex; align-items: center; gap: 5px; border: 0; color: #59667a; background: transparent; font-size: 13px; cursor: pointer; }.contact header button span { font-size: 17px; }.contact-row { display: grid; grid-template-columns: 24px auto 1fr auto; align-items: center; gap: 10px; margin-top: 18px; color: #506078; font-size: 14px; }.contact-row > .material-symbols-outlined { color: #d85a42; font-size: 24px; }.contact-row small { font-size: 13px; }.contact-row b { color: #2f3c52; font-size: 14px; }.contact-row a { display: flex; align-items: center; gap: 8px; color: #59667a; font-size: 14px; }.contact-row a span { color: #d85a42; font-size: 21px; }
</style>
