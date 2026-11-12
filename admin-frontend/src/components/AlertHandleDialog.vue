<template>
  <Teleport to="body">
    <Transition name="handle-fade">
      <div v-if="open && alert" class="handle-mask" @click.self="close">
        <div class="handle-dialog" role="dialog" aria-label="处理提醒">
          <header class="handle-head">
            <span class="handle-head__icon">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.2 3.4 19.6h17.2L12 3.2Z"/><path d="M12 9.6v4.4"/><path d="M12 17.1h.01"/></svg>
            </span>
            <div class="handle-head__text">
              <h2>处理提醒</h2>
              <p>确认这条提醒是误报还是真实有效</p>
            </div>
            <button class="handle-close" aria-label="关闭" @click="close">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6.5 6.5 11 11M17.5 6.5l-11 11"/></svg>
            </button>
          </header>

          <div class="handle-body">
            <div :class="['handle-alert', `is-${levelTone}`]">
              <div class="handle-alert__top">
                <span class="handle-alert__tag">{{ levelLabel }}</span>
                <time>{{ formatTime(alert.created_at) }}</time>
              </div>
              <p>{{ alert.message }}</p>
            </div>

            <p class="handle-question">这条提醒属于</p>
            <div class="handle-options">
              <button
                :class="['handle-option', { active: conclusion === 'false_alarm' }]"
                @click="conclusion = 'false_alarm'"
              >
                <span class="handle-option__icon">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.4"/><path d="m9.2 9.2 5.6 5.6M14.8 9.2l-5.6 5.6"/></svg>
                </span>
                <span class="handle-option__text">
                  <b>误报</b>
                  <small>设备误触、重复报警，无需跟进</small>
                </span>
                <span class="handle-option__check">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.6 4.6L19 7"/></svg>
                </span>
              </button>
              <button
                :class="['handle-option', 'is-valid', { active: conclusion === 'valid' }]"
                @click="conclusion = 'valid'"
              >
                <span class="handle-option__icon">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.4 5.4 6v5c0 4.4 2.6 7.8 6.6 9.6 4-1.8 6.6-5.2 6.6-9.6V6L12 3.4Z"/><path d="m9.2 12 2 2 3.6-3.8"/></svg>
                </span>
                <span class="handle-option__text">
                  <b>真实有效</b>
                  <small>确有情况，已确认或已安排跟进</small>
                </span>
                <span class="handle-option__check">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.6 4.6L19 7"/></svg>
                </span>
              </button>
            </div>

            <label class="handle-note-label" for="handle-note">
              处理说明<span>选填</span>
            </label>
            <textarea
              id="handle-note"
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
              {{ submitLabel }}
            </AppButton>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
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

const levelTone = computed(() => ({
  urgent: 'urgent', critical: 'urgent', warning: 'warning', info: 'info',
}[props.alert?.alert_level] || 'warning'))

const levelLabel = computed(() => ({
  urgent: '紧急', critical: '紧急', warning: '需关注', info: '提示',
}[props.alert?.alert_level] || '提醒'))

const submitLabel = computed(() => {
  if (submitting.value) return '提交中…'
  if (conclusion.value === 'false_alarm') return '确认为误报'
  if (conclusion.value === 'valid') return '确认为真实有效'
  return '确认处理'
})

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
    ElMessage.success(conclusion.value === 'valid' ? '已确认为真实有效' : '已标记为误报')
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
.handle-mask { position: fixed; z-index: 2200; inset: 0; display: grid; place-items: center; padding: 24px; background: rgba(31, 26, 22, .46); }
.handle-dialog { display: flex; box-sizing: border-box; width: min(480px, 100%); max-height: 88vh; flex-direction: column; overflow: hidden; border-radius: 16px; background: #fdfaf6; box-shadow: 0 24px 64px rgba(46, 34, 26, .26); }

.handle-head { display: flex; align-items: center; gap: 12px; padding: 20px 22px 16px; border-bottom: 1px solid #f0e6dc; }
.handle-head__icon { display: grid; width: 38px; height: 38px; flex: none; place-items: center; border-radius: 11px; color: #c6533d; background: #fbeae2; }
.handle-head__icon svg { width: 21px; height: 21px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.handle-head__text { flex: 1; min-width: 0; }
.handle-head h2 { margin: 0; color: #172942; font: 700 19px 'Songti SC','STSong',serif; letter-spacing: .5px; }
.handle-head p { margin: 4px 0 0; color: #8a8078; font-size: 12px; }
.handle-close { display: grid; width: 30px; height: 30px; flex: none; place-items: center; border: 0; border-radius: 8px; color: #9a9188; background: transparent; cursor: pointer; transition: background .18s, color .18s; }
.handle-close:hover { color: #6b655f; background: #f1e9e1; }
.handle-close svg { width: 17px; height: 17px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; }

.handle-body { flex: 1; min-height: 0; overflow-x: hidden; overflow-y: auto; padding: 16px 22px 2px; scrollbar-width: thin; }

.handle-alert { position: relative; padding: 12px 14px 13px 17px; border: 1px solid #f0e2d7; border-radius: 11px; background: #fff; }
.handle-alert::before { content: ''; position: absolute; top: 13px; bottom: 13px; left: 0; width: 3px; border-radius: 0 3px 3px 0; background: #d68f30; }
.handle-alert.is-urgent::before { background: #c6533d; }
.handle-alert.is-info::before { background: #7f95b5; }
.handle-alert__top { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 7px; }
.handle-alert__tag { padding: 2px 8px; border-radius: 5px; color: #b3701c; background: #fdf1dd; font-size: 11px; font-weight: 700; }
.is-urgent .handle-alert__tag { color: #c6533d; background: #fbe9e3; }
.is-info .handle-alert__tag { color: #63799c; background: #edf1f7; }
.handle-alert__top time { color: #a49b92; font-size: 11px; }
.handle-alert p { margin: 0; color: #3c465a; font-size: 13.5px; line-height: 1.65; }

.handle-question { margin: 18px 0 10px; color: #5c687b; font-size: 12.5px; font-weight: 700; letter-spacing: .3px; }

.handle-options { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.handle-option { position: relative; display: flex; box-sizing: border-box; min-width: 0; align-items: flex-start; gap: 10px; padding: 13px 14px; border: 1.5px solid #ece3db; border-radius: 11px; background: #fff; text-align: left; cursor: pointer; transition: border-color .18s, background .18s, box-shadow .18s; }
.handle-option:hover { border-color: #dcc8bb; }
.handle-option__icon { display: grid; width: 30px; height: 30px; flex: none; place-items: center; border-radius: 9px; color: #8d8a86; background: #f5efe9; transition: color .18s, background .18s; }
.handle-option__icon svg { width: 17px; height: 17px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.handle-option__text { min-width: 0; }
.handle-option__text b { display: block; color: #2e3d54; font-size: 13.5px; }
.handle-option__text small { display: block; margin-top: 3px; color: #948b83; font-size: 11px; line-height: 1.5; }
.handle-option__check { position: absolute; top: 9px; right: 9px; display: grid; width: 16px; height: 16px; place-items: center; border-radius: 50%; color: #fff; background: #c6533d; opacity: 0; transform: scale(.6); transition: opacity .16s, transform .16s; }
.handle-option__check svg { width: 10px; height: 10px; fill: none; stroke: currentColor; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
.handle-option.active { border-color: #c6533d; background: #fdf1ec; box-shadow: 0 2px 10px rgba(198, 83, 61, .1); }
.handle-option.active .handle-option__icon { color: #c6533d; background: #f8ded4; }
.handle-option.active .handle-option__check { opacity: 1; transform: scale(1); }
.handle-option.is-valid.active { border-color: #56826a; background: #eef5f0; box-shadow: 0 2px 10px rgba(86, 130, 106, .1); }
.handle-option.is-valid.active .handle-option__icon { color: #45705a; background: #dcebe2; }
.handle-option.is-valid.active .handle-option__check { background: #56826a; }

.handle-note-label { display: flex; align-items: baseline; gap: 6px; margin: 18px 0 8px; color: #5c687b; font-size: 12.5px; font-weight: 700; }
.handle-note-label span { color: #a49b92; font-size: 11px; font-weight: 500; }
.handle-note { display: block; box-sizing: border-box; width: 100%; padding: 11px 13px; border: 1.5px solid #ece3db; border-radius: 10px; color: #2e3d54; background: #fff; font-family: inherit; font-size: 13px; line-height: 1.65; resize: none; transition: border-color .18s, box-shadow .18s; }
.handle-note::placeholder { color: #b3aaa2; }
.handle-note:focus { border-color: #cf624d; outline: none; box-shadow: 0 0 0 3px rgba(198, 83, 61, .09); }
.handle-error { margin: 10px 0 0; color: #c6533d; font-size: 12px; }

.handle-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 22px 20px; }

.handle-fade-enter-active, .handle-fade-leave-active { transition: opacity .18s ease; }
.handle-fade-enter-from, .handle-fade-leave-to { opacity: 0; }
.handle-fade-enter-active .handle-dialog, .handle-fade-leave-active .handle-dialog { transition: transform .2s cubic-bezier(.16, 1, .3, 1); }
.handle-fade-enter-from .handle-dialog, .handle-fade-leave-to .handle-dialog { transform: translateY(10px) scale(.985); }
</style>