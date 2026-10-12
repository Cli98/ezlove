<template>
  <div v-if="open" class="task-dialog" role="dialog" aria-modal="true" :aria-labelledby="`${mode}-task-title`">
    <button type="button" class="task-dialog__mask" aria-label="关闭弹窗" @click="$emit('close')"></button>
    <form class="task-dialog__panel" @submit.prevent="submit">
      <header><h3 :id="`${mode}-task-title`">{{ mode === 'create' ? '发布互助任务' : '任务详情' }}</h3></header>
      <div class="task-dialog__body">
        <template v-if="mode === 'create'">
          <label><b>任务标题</b><input v-model.trim="form.title" placeholder="例如：陪王阿姨去医院复诊" /></label>
          <div class="task-dialog__grid">
            <label><b>任务类型</b><InlineSelect v-model="form.task_type" :options="typeOptions" /></label>
            <label><b>积分奖励</b><input v-model.number="form.point_value" type="number" min="1" max="999" /></label>
          </div>
          <label><b>服务对象</b><InlineSelect v-model="form.target_elder_id" :options="elderOptions" /></label>
          <label><b>任务说明</b><textarea v-model.trim="form.notes" rows="4" placeholder="补充时间、地点或注意事项"></textarea></label>
        </template>
        <template v-else>
          <div class="task-dialog__summary"><strong>{{ task?.title }}</strong><p>{{ task?.notes || '暂无补充说明' }}</p></div>
          <dl>
            <div><dt>服务对象</dt><dd>{{ task?.target_label || '社区公共服务' }}</dd></div>
            <div><dt>任务类型</dt><dd>{{ task?.type_label }}</dd></div>
            <div><dt>积分奖励</dt><dd>+{{ task?.point_value }}</dd></div>
            <div><dt>当前状态</dt><dd>{{ task?.status_label }}</dd></div>
            <div><dt>志愿者</dt><dd>{{ task?.volunteer_name || '等待接取' }}</dd></div>
          </dl>
        </template>
      </div>
      <footer>
        <AppButton variant="ghost" @click="$emit('close')">关闭</AppButton>
        <AppButton v-if="mode === 'create'" type="submit" :disabled="submitting">{{ submitting ? '发布中…' : '确认发布' }}</AppButton>
        <AppButton v-else-if="task?.status === 'completed'" :disabled="submitting" @click="$emit('verify', task)">{{ submitting ? '审核中…' : '审核通过' }}</AppButton>
      </footer>
    </form>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import AppButton from '@/components/AppButton.vue'
import InlineSelect from '@/components/InlineSelect.vue'

const props = defineProps({ open: Boolean, mode: { type: String, default: 'create' }, task: { type: Object, default: null }, elders: { type: Array, default: () => [] }, submitting: Boolean })
const emit = defineEmits(['close', 'submit', 'verify'])
const form = reactive({ title: '', task_type: 'visit', target_elder_id: '', point_value: 10, notes: '' })
const typeOptions = [{ value: 'visit', label: '探访' }, { value: 'accompany', label: '陪伴' }, { value: 'check_in', label: '签到' }, { value: 'errand', label: '代办' }]
const elderOptions = computed(() => [{ value: '', label: '社区公共服务（不指定老人）' }, ...props.elders.map(elder => ({ value: elder.id, label: `${elder.elder_name || elder.name} · ${elder.address || '地址待补充'}` }))])

watch(() => props.open, open => {
  if (!open || props.mode !== 'create') return
  Object.assign(form, { title: '', task_type: 'visit', target_elder_id: '', point_value: 10, notes: '' })
})

function submit() {
  emit('submit', { ...form, target_elder_id: form.target_elder_id || null, notes: form.notes || null })
}
</script>

<style scoped>
.task-dialog { position: fixed; z-index: 200; inset: 0; display: grid; place-items: center; padding: 24px; }
.task-dialog__mask { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; background: rgba(41,37,34,.42); backdrop-filter: blur(3px); cursor: default; }
.task-dialog__panel { position: relative; width: min(570px,100%); overflow: hidden; border: 1px solid #e4d9cf; border-radius: 22px; background: #fffdfb; box-shadow: 0 24px 70px rgba(45,36,29,.24); }
.task-dialog__panel header { padding: 23px 28px 18px; border-bottom: 1px solid #eee5de; }
.task-dialog__panel h3 { margin: 0; color: #292724; font: 700 24px 'Songti SC','STSong',serif; }
.task-dialog__body { display: grid; gap: 18px; padding: 24px 28px; }
.task-dialog__body label { display: grid; gap: 8px; color: #3d3a37; font-size: 13px; }
.task-dialog__body label > b { font-weight: 700; }
.task-dialog__body input, .task-dialog__body textarea { width: 100%; padding: 12px 14px; border: 1px solid #ddd3ca; border-radius: 9px; outline: 0; color: #373431; background: #fff; line-height: 1.5; }
.task-dialog__body input { height: 46px; }.task-dialog__body textarea { resize: vertical; }
.task-dialog__body input:focus, .task-dialog__body textarea:focus { border-color: rgba(196,77,62,.65); }
.task-dialog__body :deep(.inline-select) { width: 100%; height: 46px; justify-content: space-between; }
.task-dialog__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.task-dialog__summary { padding: 15px; border-radius: 9px; background: #f8f2ed; }.task-dialog__summary strong { color: #30302e; }.task-dialog__summary p { margin: 8px 0 0; color: #6c6863; line-height: 1.55; }
.task-dialog dl { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin: 0; }.task-dialog dl div { padding-bottom: 10px; border-bottom: 1px solid #eee7e1; }.task-dialog dt { color: #8b847d; font-size: 11px; }.task-dialog dd { margin: 5px 0 0; color: #383532; font-size: 13px; }
.task-dialog__panel footer { display: flex; justify-content: flex-end; gap: 8px; padding: 15px 22px; border-top: 1px solid #eee5de; }
</style>
