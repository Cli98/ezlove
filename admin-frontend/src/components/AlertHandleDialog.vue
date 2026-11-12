<template>
  <Teleport to="body">
    <Transition name="handle-fade">
      <div v-if="open && alert" class="handle-mask" @click.self="close">
        <div class="handle-dialog" role="dialog" aria-label="处理提醒">
          <header class="handle-head">
            <div>
              <h2>处理提醒</h2>
              <p>请确认这条提醒是误报还是真实有效</p>
            </div>
            <button class="handle-close" @click="close">
              <span class="material-symbols-outlined">close</span>
            </button>
          </header>

          <div class="handle-body">
            <div class="handle-alert">
              <p>{{ alert.message }}</p>
              <small>{{ formatTime(alert.created_at) }} · {{ levelLabel }}</small>
            </div>

            <p class="handle-question">这条提醒属于：</p>
            <div class="handle-options">
              <button
                :class="['handle-option', { active: conclusion === 'false_alarm' }]"
                @click="conclusion = 'false_alarm'"
              >
                <span class="material-symbols-outlined">not_interested</span>
                <b>误报</b>
                <small>设备误触、重复报警，无需跟进</small>
              </button>
              <button
                :class="['handle-option', 'handle-option--valid', { active: conclusion === 'valid' }]"
                @click="conclusion = 'valid'"
              >
                <span class="material-symbols-outlined">verified_user</span>
                <b>真实有效</b>
                <small>确有情况，已确认或已安排跟进</small>
              </button>
            </div>

            <label class="handle-note-label">处理说明（选填）</label>
            <textarea
              v-model="note"
              class="handle-note"
              rows="3"
              maxlength="200"
              placeholder="例如：已电话联系老人及家属，确认安全"
            ></textarea>

            <p v-if="error" class="handle-error">{{ error }}</p>
          </div>

          <footer class="handle-foot">
            <AppButton variant="ghost" @click="close">取消</AppButton>
            <AppButton variant="primary" :disabled="!conclusion || submitting" @click="submit">
              {{ submitting ? '提交中…' : '确认处理' }}
            </AppButton>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AppButton from './AppButton.vue'
import { respondAlert } from '@/api/community'

const props = defineProps({
  open: Boolean,
  alert: { type: Object, default: null },
})
const emit = defineEmits(['close', 'done'])

const conclusion = ref(null)
const note = ref('')
const submitting = ref(false)
const error = ref('')

watch(() => props.open, (open) => {
  if (!open) return
  conclusion.value = null
  note.value = ''
  error.value = ''
  submitting.value = false
})

const levelLabel = computed(() => ({
  urgent: '紧急', critical: '紧急', warning: '需关注', info: '提示',
}[props.alert?.alert_level] || '提醒'))

function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function close() {
  if (submitting.value) return
  emit('close')
}

async function submit() {
  if (!props.alert || !conclusion.value || submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    await respondAlert(props.alert.id, {
      conclusion: conclusion.value,
      response_note: note.value.trim() || null,
    })
    emit('done')
    emit('close')
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '处理失败，请重试'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.handle-mask { position: fixed; z-index: 2200; inset: 0; display: grid; place-items: center; padding: 20px; background: rgba(31, 26, 22, .42); }
.handle-dialog { display: flex; width: min(460px, 100%); max-height: 90vh; flex-direction: column; overflow: hidden; border-radius: 14px; background: #fdfaf6; box-shadow: 0 24px 60px rgba(46, 34, 26, .24); }
.handle-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 20px 22px 12px; border-bottom: 1px solid #eee4da; }
.handle-head h2 { margin: 0; color: #172942; font: 700 20px 'Songti SC','STSong',serif; }
.handle-head p { margin: 6px 0 0; color: #7a8190; font-size: 12px; }
.handle-close { display: grid; width: 32px; height: 32px; flex: none; place-items: center; border: 1px solid #e5ddd5; border-radius: 8px; color: #677387; background: #fff; cursor: pointer; }
.handle-close span { font-size: 18px; }
.handle-body { flex: 1; min-height: 0; overflow-y: auto; padding: 14px 22px 4px; }
.handle-alert { padding: 12px 14px; border: 1px solid #f0e2d7; border-radius: 10px; background: #fff; }
.handle-alert p { margin: 0; color: #3c465a; font-size: 13.5px; line-height: 1.6; }
.handle-alert small { display: block; margin-top: 5px; color: #9a9188; font-size: 11.5px; }
.handle-question { margin: 16px 0 9px; color: #5c687b; font-size: 13px; font-weight: 700; }
.handle-options { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.handle-option { display: grid; justify-items: start; gap: 4px; padding: 13px 14px; border: 1.5px solid #e7ddd7; border-radius: 10px; background: #fff; text-align: left; cursor: pointer; transition: border-color .18s, background .18s; }
.handle-option .material-symbols-outlined { color: #8d8a86; font-size: 22px; }
.handle-option b { color: #2e3d54; font-size: 14px; }
.handle-option small { color: #91867c; font-size: 11.5px; line-height: 1.5; }
.handle-option.active { border-color: #c6533d; background: #fdf0ea; }
.handle-option.active .material-symbols-outlined, .handle-option.active b { color: #c6533d; }
.handle-option--valid.active { border-color: #56826a; background: #eef5f0; }
.handle-option--valid.active .material-symbols-outlined, .handle-option--valid.active b { color: #45705a; }
.handle-note-label { display: block; margin: 16px 0 7px; color: #5c687b; font-size: 13px; font-weight: 700; }
.handle-note { width: 100%; box-sizing: border-box; resize: vertical; padding: 10px 12px; border: 1px solid #e5ddd5; border-radius: 9px; color: #2e3d54; background: #fff; font-size: 13px; line-height: 1.6; }
.handle-note:focus { border-color: #cf624d; outline: none; }
.handle-error { margin: 10px 0 0; color: #c6533d; font-size: 12.5px; }
.handle-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 22px 18px; }
.handle-fade-enter-active, .handle-fade-leave-active { transition: opacity .18s ease; }
.handle-fade-enter-from, .handle-fade-leave-to { opacity: 0; }
</style>