<template>
  <div v-if="open" class="event-dialog" role="dialog" aria-modal="true" :aria-labelledby="`${mode}-dialog-title`">
    <button type="button" class="event-dialog__mask" aria-label="关闭弹窗" @click="$emit('close')"></button>
    <form class="event-dialog__panel" @submit.prevent="submit">
      <header><h3 :id="`${mode}-dialog-title`">{{ title }}</h3></header>
      <div class="event-dialog__body">
        <template v-if="mode === 'create'">
          <label><b>关怀对象</b><InlineSelect v-model="form.elder_id" :options="elderOptions" /></label>
          <div class="event-dialog__grid">
            <label><b>事件类型</b><InlineSelect v-model="form.event_type" :options="eventTypeOptions" /></label>
            <label><b>关怀程度</b><InlineSelect v-model="form.severity" :options="severityOptions" /></label>
          </div>
          <label><b>事项说明</b><textarea v-model="form.description" rows="4" placeholder="请简要说明需要回应的情况"></textarea></label>
        </template>
        <template v-else-if="mode === 'resolve'">
          <div class="event-dialog__summary">{{ event?.description || '暂无事项说明' }}</div>
          <label><b>处理备注</b><textarea v-model="resolveNote" rows="4" placeholder="例如：已电话联系家属并确认老人平安"></textarea></label>
        </template>
        <template v-else>
          <div class="event-dialog__summary">{{ event?.description || '暂无事项说明' }}</div>
          <dl><dt>处理结果</dt><dd>{{ event?.resolution_note || '已办结，暂无补充备注' }}</dd></dl>
        </template>
      </div>
      <footer>
        <AppButton variant="ghost" @click="$emit('close')">{{ mode === 'view' ? '关闭' : '取消' }}</AppButton>
        <AppButton v-if="mode !== 'view'" type="submit" :disabled="submitting">{{ submitting ? '提交中…' : mode === 'create' ? '确认新增' : '确认办结' }}</AppButton>
      </footer>
    </form>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import AppButton from '@/components/AppButton.vue'
import InlineSelect from '@/components/InlineSelect.vue'

const props = defineProps({ open: Boolean, mode: { type: String, default: 'create' }, event: { type: Object, default: null }, elders: { type: Array, default: () => [] }, submitting: Boolean })
const emit = defineEmits(['close', 'submit'])
const form = reactive({ elder_id: '', event_type: 'other', severity: 'info', description: '' })
const resolveNote = ref('')
const title = computed(() => ({ create: '手动新增关怀事项', resolve: '处理关怀事项', view: '查看办结结果' }[props.mode]))
const elderOptions = computed(() => [{ value: '', label: '请选择老人' }, ...props.elders.map(elder => ({ value: elder.id, label: `${elder.elder_name || elder.name} · ${elder.address || '地址待补充'}` }))])
const eventTypeOptions = [{ value: 'other', label: '日常关怀' }, { value: 'absent', label: '未到场' }, { value: 'visit', label: '上门探访' }, { value: 'emergency', label: '紧急事项' }, { value: 'fall', label: '跌倒情况' }]
const severityOptions = [{ value: 'info', label: '一般' }, { value: 'warning', label: '关注' }, { value: 'urgent', label: '重点' }]

watch(() => props.open, open => {
  if (!open) return
  form.elder_id = props.elders[0]?.id || ''
  form.event_type = 'other'
  form.severity = 'info'
  form.description = ''
  resolveNote.value = ''
})

function submit() {
  if (props.mode === 'create') emit('submit', { ...form })
  else emit('submit', { resolution_note: resolveNote.value.trim() || null })
}
</script>

<style scoped>
.event-dialog { position: fixed; z-index: 200; inset: 0; display: grid; place-items: center; padding: 24px; }
.event-dialog__mask { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; background: rgba(41,37,34,.42); backdrop-filter: blur(3px); cursor: default; }
.event-dialog__panel { position: relative; width: min(560px,100%); overflow: hidden; border: 1px solid #e4d9cf; border-radius: 22px; background: #fffdfb; box-shadow: 0 24px 70px rgba(45,36,29,.24); }
.event-dialog__panel header { padding: 23px 28px 18px; border-bottom: 1px solid #eee5de; }
.event-dialog__panel h3 { margin: 0; color: #292724; font: 700 24px 'Songti SC','STSong',serif; }
.event-dialog__body { display: grid; gap: 18px; padding: 24px 28px; }
.event-dialog__body label { display: grid; gap: 8px; color: #3d3a37; font-size: 13px; }
.event-dialog__body label > b { font-weight: 700; }
.event-dialog__body :deep(.inline-select) { width: 100%; height: 46px; justify-content: space-between; }
.event-dialog__body textarea { width: 100%; padding: 12px 14px; border: 1px solid #ddd3ca; border-radius: 9px; outline: 0; color: #373431; background: #fff; line-height: 1.5; resize: vertical; }
.event-dialog__body textarea:focus { border-color: rgba(196,77,62,.65); }
.event-dialog__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.event-dialog__summary { padding: 14px; border-radius: 9px; color: #5f5c58; background: #f8f2ed; line-height: 1.55; }
.event-dialog dl { margin: 0; }.event-dialog dt { color: #7e7770; font-size: 12px; }.event-dialog dd { margin: 7px 0 0; color: #383532; line-height: 1.55; }
.event-dialog__panel footer { display: flex; justify-content: flex-end; gap: 8px; padding: 15px 22px; border-top: 1px solid #eee5de; }
</style>
