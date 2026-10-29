<template>
  <button ref="entryRef" type="button" class="wechat-entry" :class="{ 'is-bound': bound }" @click="openPicker">
    <span v-if="loading" class="material-symbols-outlined is-spin">progress_activity</span>
    <span v-else-if="failed" class="material-symbols-outlined">error</span>
    <span v-else-if="bound" class="entry-avatar">
      <img v-if="data.bound_avatar" :src="data.bound_avatar" alt="" />
      <WechatLogo v-else class="entry-logo" />
    </span>
    <WechatLogo v-else class="entry-logo" />
    <span class="entry-label">{{ entryLabel }}</span>
  </button>

  <Teleport to="body">
    <Transition name="wx-fade">
      <div v-if="pickerOpen" class="wx-mask" @click.self="closePicker">
        <section
          ref="panelRef"
          class="wx-panel"
          role="dialog"
          aria-modal="true"
          :aria-label="bound ? '微信绑定状态' : '选择老人的微信账号'"
          tabindex="-1"
          @keydown.esc="closePicker"
        >
          <header class="wx-head">
            <div class="wx-head__copy">
              <h3>{{ bound ? '微信绑定' : '选择老人的微信账号' }}</h3>
              <p v-if="bound">该微信查看过的牵挂会自动记到本档案</p>
              <p v-else>让老人用他的微信打开一次小程序，最近看过的排在最前</p>
            </div>
            <button type="button" class="wx-close" aria-label="关闭" @click="closePicker">
              <span class="material-symbols-outlined">close</span>
            </button>
          </header>

          <template v-if="bound">
            <div class="wx-bound">
              <span class="wx-avatar wx-avatar--lg" :style="avatarStyle(data.bound_avatar, data.elder_name)">
                <img v-if="data.bound_avatar" :src="data.bound_avatar" alt="" />
                <WechatLogo v-else-if="!data.elder_name" class="wx-logo" />
                <span v-else>{{ initialOf(data.elder_name) }}</span>
              </span>
              <div class="wx-bound__copy">
                <b>{{ displayBoundName }}</b>
                <span :title="data.bound_phone_masked ? '' : '让老人在小程序「我的 → 社区档案」点一次授权'">{{ data.bound_phone_masked || '未授权手机号' }}</span>
              </div>
              <span class="wx-badge wx-badge--on">已绑定</span>
            </div>
            <p class="wx-bound__tip">需要换人时，让老人在小程序「我的 → 编辑资料」里重新绑定，当前账号会解除。</p>
            <footer class="wx-foot">
              <button type="button" class="wx-ghost" @click="load">刷新状态</button>
              <button type="button" class="wx-primary" @click="closePicker">知道了</button>
            </footer>
          </template>

          <template v-else>
            <p class="wx-note">
              <span class="material-symbols-outlined">visibility</span>
              <span>微信不会主动把头像和手机号给社区后台。让老人在小程序「我的 → 社区档案」点一次「授权手机号」并选允许，这里就会显示号码；未授权时请按「最近看过」的牵挂内容核对身份。</span>
            </p>

            <div class="wx-listhead">
              <span>可绑定账号 <b>{{ candidates.length }}</b></span>
              <button type="button" class="wx-refresh" :disabled="loading" @click="load">
                <span class="material-symbols-outlined" :class="{ 'is-spin': loading }">refresh</span>
                {{ loading ? '刷新中' : '刷新' }}
              </button>
            </div>

            <div v-if="loading && !candidates.length" class="wx-state">
              <span class="material-symbols-outlined is-spin">progress_activity</span>
              <p>正在读取微信账号…</p>
            </div>
            <div v-else-if="failed" class="wx-state">
              <span class="material-symbols-outlined">error</span>
              <p>读取失败，请检查网络后重试</p>
              <button type="button" class="wx-ghost" @click="load">重新读取</button>
            </div>
            <div v-else-if="!candidates.length" class="wx-state">
              <span class="material-symbols-outlined">person_off</span>
              <p>还没有可绑定的微信账号</p>
              <small>让老人用微信打开一次子女分享的牵挂卡片，再回来刷新</small>
            </div>
            <ul v-else class="wx-list">
              <li v-for="item in candidates" :key="item.id" :class="['wx-item', { 'is-recent': isRecent(item) }]">
                <span class="wx-avatar" :class="{ 'is-anon': !item.avatar_url }" :style="avatarStyle(item.avatar_url, item.id)">
                  <img v-if="item.avatar_url" :src="item.avatar_url" alt="" />
                  <WechatLogo v-else-if="!initialFor(item)" class="wx-logo" />
                  <span v-else>{{ initialFor(item) }}</span>
                </span>
                <div class="wx-item__body">
                  <div class="wx-item__title">
                    <b>{{ displayName(item) }}</b>
                    <span v-if="openidTail(item)" class="wx-tail">#{{ openidTail(item) }}</span>
                    <em v-if="isRecent(item)" class="wx-badge">刚刚</em>
                  </div>
                  <div class="wx-item__meta">
                    <span v-if="item.phone_masked" class="wx-chip">{{ item.phone_masked }}</span>
                    <span v-else class="wx-chip is-muted" title="让老人在小程序「我的 → 社区档案」点一次授权">未授权手机号</span>
                    <span class="wx-seen">{{ seenText(item) }}</span>
                  </div>
                  <p v-if="item.last_view_text" class="wx-watch">最近看过「<em>{{ item.last_view_text }}</em>」</p>
                </div>
                <button
                  type="button"
                  class="wx-primary wx-primary--sm"
                  :disabled="Boolean(binding)"
                  @click="bind(item)"
                >
                  {{ binding === item.id ? '绑定中' : '绑定' }}
                </button>
              </li>
            </ul>

            <footer class="wx-foot">
              <span class="wx-foot__hint">绑定后老人查看牵挂的记录会同步到本档案</span>
              <button type="button" class="wx-ghost" @click="closePicker">关闭</button>
            </footer>
          </template>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, h, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { bindElderWechat, getElderWechatBinding } from '@/api/community'

// 微信双气泡 logo 用内联 SVG：本地图标字体子集里没有 wechat 字形，图标名会退化成英文
const WECHAT_LOGO_PATH =
  'M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 0 0 .167-.054l1.903-1.114a.864.864 0 0 1 .717-.098 10.16 10.16 0 0 0 2.837.403c.276 0 .543-.027.811-.05-.857-2.578.157-4.972 1.932-6.446 1.703-1.415 3.882-1.98 5.853-1.838-.576-3.583-4.196-6.348-8.596-6.348zM5.785 5.991c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178A1.17 1.17 0 0 1 4.623 7.17c0-.651.52-1.18 1.162-1.18zm5.813 0c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178 1.17 1.17 0 0 1-1.162-1.178c0-.651.52-1.18 1.162-1.18zm5.34 2.867c-1.797-.052-3.746.512-5.28 1.786-1.72 1.428-2.687 3.72-1.78 6.22.942 2.453 3.666 4.229 6.884 4.229.826 0 1.622-.12 2.361-.336a.722.722 0 0 1 .598.082l1.584.926a.272.272 0 0 0 .14.047c.134 0 .24-.111.24-.247 0-.06-.023-.12-.038-.177l-.327-1.233a.582.582 0 0 1-.023-.156.49.49 0 0 1 .201-.398C23.024 18.48 24 16.82 24 14.98c0-3.21-2.931-5.837-6.656-6.088V8.89c-.135-.01-.27-.027-.406-.032zm-2.53 3.274c.535 0 .969.44.969.982a.976.976 0 0 1-.969.983.976.976 0 0 1-.969-.983c0-.542.434-.982.97-.982zm4.844 0c.535 0 .969.44.969.982a.976.976 0 0 1-.969.983.976.976 0 0 1-.969-.983c0-.542.434-.982.969-.982z'

const WechatLogo = () =>
  h('svg', { viewBox: '0 0 24 24', 'aria-hidden': 'true', focusable: 'false' }, [
    h('path', { fill: 'currentColor', d: WECHAT_LOGO_PATH }),
  ])

const props = defineProps({ elderId: { type: String, required: true } })

const loading = ref(false)
const failed = ref(false)
const bound = ref(false)
const data = ref({})
const pickerOpen = ref(false)
const binding = ref('')
const entryRef = ref(null)
const panelRef = ref(null)
const candidates = computed(() => data.value.candidates || [])

const pad = (n) => String(n).padStart(2, '0')
const RECENT_MS = 10 * 60 * 1000
const AVATAR_TONES = [
  ['#f6e4d9', '#b25f45'],
  ['#e6efe8', '#4f7a5f'],
  ['#f7ecd6', '#a2762d'],
  ['#e5ecf3', '#4b6b88'],
  ['#f0e6ef', '#85557b'],
]

const displayBoundName = computed(() => {
  const name = (data.value.elder_name || '').trim()
  return !name || name === '微信用户' ? '微信已绑定' : name
})

const entryLabel = computed(() => {
  if (failed.value) return '绑定状态读取失败'
  if (!bound.value) return '绑定微信'
  return data.value.bound_phone_masked
    ? `${displayBoundName.value} · ${data.value.bound_phone_masked}`
    : displayBoundName.value
})

function hashOf(text) {
  let hash = 0
  for (let i = 0; i < String(text || '').length; i += 1) {
    hash = (hash * 31 + String(text).charCodeAt(i)) % 9973
  }
  return hash
}

function avatarStyle(url, seed) {
  if (url) return {}
  const [bg, fg] = AVATAR_TONES[hashOf(seed) % AVATAR_TONES.length]
  return { background: bg, color: fg }
}

function initialOf(name) {
  const text = (name || '').trim()
  return text ? text.charAt(0) : '微'
}

function openidTail(item) {
  const masked = (item.openid_masked || '').trim()
  return masked ? masked.slice(-4) : ''
}

function initialFor(item) {
  // 匿名微信返回空串，模板改用微信 logo 占位（openid 尾号首字符当头像会让人无法辨认）
  const name = (item.nickname || '').trim()
  if (!name || name === '微信用户') return ''
  return name.charAt(0)
}

function displayName(item) {
  const name = (item.nickname || '').trim()
  return !name || name === '微信用户' ? '微信用户' : name
}

function formatTime(value) {
  if (!value) return '时间未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间未知'
  return `${date.getMonth() + 1}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function relativeTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const diff = Date.now() - date.getTime()
  if (diff < 60 * 1000) return '刚刚'
  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 24 * 60 * 60 * 1000) return `今天 ${pad(date.getHours())}:${pad(date.getMinutes())}`
  return formatTime(value)
}

function isRecent(item) {
  const time = new Date(item.last_viewed_at || '').getTime()
  return !Number.isNaN(time) && Date.now() - time < RECENT_MS
}

function seenText(item) {
  if (item.last_viewed_at) {
    const count = item.view_count ? ` · 共 ${item.view_count} 次` : ''
    return `最近查看 ${relativeTime(item.last_viewed_at)}${count}`
  }
  return `尚未查看过牵挂 · 首次登录 ${formatTime(item.created_at)}`
}

async function load() {
  loading.value = true
  failed.value = false
  try {
    const res = await getElderWechatBinding(props.elderId)
    data.value = res || {}
    bound.value = Boolean(res?.bound)
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

function openPicker() {
  pickerOpen.value = true
  if (!data.value.candidates || !bound.value) load()
}

function closePicker() {
  pickerOpen.value = false
  nextTick(() => entryRef.value?.focus())
}

async function bind(item) {
  const parts = []
  if (item.phone_masked) parts.push(`手机号 ${item.phone_masked}`)
  parts.push(item.last_viewed_at ? `最近查看 ${relativeTime(item.last_viewed_at)}` : '还没有查看过牵挂')
  try {
    await ElMessageBox.confirm(
      `确认绑定到「${displayName(item)}」，${parts.join('，')}？绑定后老人的查看记录会同步到该档案。`,
      '确认绑定',
      { confirmButtonText: '确认绑定', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  binding.value = item.id
  try {
    await bindElderWechat(props.elderId, item.id)
    ElMessage.success('已绑定微信账号')
    pickerOpen.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '绑定失败')
  } finally {
    binding.value = ''
  }
}

watch(pickerOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
  if (open) nextTick(() => panelRef.value?.focus())
})

watch(() => props.elderId, load)
onMounted(load)
onBeforeUnmount(() => {
  document.body.style.overflow = ''
})
</script>

<style scoped>
.wechat-entry {
  display: flex; width: 100%; height: 45px; align-items: center; justify-content: center; gap: 8px;
  padding: 0 12px; border: 1px solid #d95a42; border-radius: 7px; color: #cf553d;
  background: rgba(255, 255, 255, .72); font-size: 14px; font-weight: 700;
  cursor: pointer; overflow: hidden; white-space: nowrap; appearance: none; outline: none;
  transition: background .16s, border-color .16s, color .16s;
}
.wechat-entry:hover { background: #fdf1ec; border-color: #c94a31; }
.wechat-entry:focus-visible { outline: 2px solid rgba(196, 77, 62, .35); outline-offset: 2px; }
.wechat-entry .material-symbols-outlined { flex: none; font-size: 19px; }
.wechat-entry.is-bound { color: #4f7a5f; border-color: #bcd8c2; background: #f6fbf7; }
.wechat-entry.is-bound:hover { background: #eef7f0; }
.entry-avatar { display: grid; width: 22px; height: 22px; flex: none; overflow: hidden; place-items: center; border-radius: 50%; color: #4f7a5f; background: #e3efe6; }
.entry-avatar img { width: 100%; height: 100%; object-fit: cover; }
.wx-logo { width: 18px; height: 18px; flex: none; color: #07c160; }
.entry-logo { width: 19px; height: 19px; color: #07c160; }
.wechat-entry.is-bound .entry-logo { color: #4f7a5f; }
.entry-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.is-spin { animation: wx-spin 1s linear infinite; }
@keyframes wx-spin { to { transform: rotate(360deg); } }

.wx-mask {
  position: fixed; inset: 0; z-index: 1500; display: grid; place-items: center;
  padding: 28px; background: rgba(35, 29, 25, .5); isolation: isolate;
}
.wx-panel {
  display: flex; flex-direction: column; width: min(560px, 100%); max-height: min(84vh, 720px);
  overflow: hidden; border: 1px solid #ece1d8; border-radius: 18px; background: #fffdfb;
  box-shadow: 0 28px 80px rgba(45, 34, 26, .3); outline: none; isolation: isolate;
}
.wx-head { display: flex; flex: none; align-items: flex-start; gap: 16px; padding: 22px 24px 0; }
.wx-head__copy { min-width: 0; flex: 1; }
.wx-head__copy h3 { margin: 0; color: #22201d; font: 700 19px/1.3 'Songti SC', 'STSong', serif; letter-spacing: .2px; }
.wx-head__copy p { margin: 6px 0 0; color: #8b8178; font-size: 12.5px; line-height: 1.5; }
.wx-close {
  display: grid; width: 32px; height: 32px; flex: none; place-items: center; border: 0;
  border-radius: 50%; color: #8f857b; background: #f5f0ea; cursor: pointer; transition: background .16s, color .16s;
}
.wx-close:hover { color: #b8503a; background: #f7e6df; }
.wx-close .material-symbols-outlined { font-size: 19px; }

.wx-note {
  display: flex; flex: none; align-items: flex-start; gap: 8px; margin: 16px 24px 0; padding: 10px 12px;
  border-radius: 10px; color: #8a6a55; background: #fbf3ec; font-size: 12px; line-height: 1.5;
}
.wx-note .material-symbols-outlined { flex: none; margin-top: 1px; font-size: 16px; color: #b9765a; }

.wx-listhead { display: flex; flex: none; align-items: center; justify-content: space-between; padding: 18px 24px 10px; }
.wx-listhead > span { color: #5d554d; font-size: 13px; font-weight: 700; }
.wx-listhead > span b { color: #c04f36; }
.wx-refresh {
  display: inline-flex; align-items: center; gap: 4px; padding: 4px 8px; border: 0; border-radius: 7px;
  color: #a2735f; background: transparent; font-size: 12px; font-weight: 700; cursor: pointer;
}
.wx-refresh:hover { color: #c04f36; background: #fbf1eb; }
.wx-refresh:disabled { cursor: default; opacity: .6; }
.wx-refresh .material-symbols-outlined { font-size: 15px; }

.wx-list {
  display: grid; flex: 1 1 auto; gap: 8px; min-height: 0; margin: 0;
  padding: 0 24px 6px; overflow-y: auto; overscroll-behavior: contain; list-style: none;
  scrollbar-width: thin; scrollbar-color: #e2d5c9 transparent;
}
.wx-list::-webkit-scrollbar { width: 7px; }
.wx-list::-webkit-scrollbar-thumb { border: 2px solid transparent; border-radius: 999px; background: #e2d5c9; background-clip: content-box; }
.wx-list::-webkit-scrollbar-track { background: transparent; }

.wx-item {
  display: grid; grid-template-columns: 42px minmax(0, 1fr) auto; align-items: center; gap: 12px;
  padding: 11px 12px; border: 1px solid #efe7df; border-radius: 12px; background: #fff;
  transition: border-color .16s, box-shadow .16s, background .16s;
}
.wx-item:hover { border-color: #e2cbb9; box-shadow: 0 6px 18px rgba(120, 82, 52, .08); }
.wx-item.is-recent { border-color: #bcd8c2; background: #f8fcf9; }
.wx-avatar {
  display: grid; width: 42px; height: 42px; overflow: hidden; place-items: center; border-radius: 50%;
  color: #a2762d; background: #f7ecd6; font-size: 16px; font-weight: 700;
}
.wx-avatar img { width: 100%; height: 100%; object-fit: cover; }
.wx-avatar.is-anon { background: #eaf7ee; color: #07c160; }
.wx-avatar .wx-logo { width: 21px; height: 21px; }
.wx-avatar--lg { width: 52px; height: 52px; font-size: 20px; }
.wx-item__body { min-width: 0; }
.wx-item__title { display: flex; align-items: center; gap: 6px; min-width: 0; }
.wx-item__title b { overflow: hidden; color: #2c2a27; font-size: 13.5px; text-overflow: ellipsis; white-space: nowrap; }
.wx-tail { flex: none; color: #a49a90; font-size: 11px; letter-spacing: .3px; }
.wx-item__meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; min-width: 0; color: #96908a; font-size: 11.5px; }
.wx-chip { flex: none; padding: 1px 7px; border-radius: 6px; color: #6d7d72; background: #eef4f0; font-size: 11px; }
.wx-chip.is-muted { color: #a89e95; background: #f4f0ec; }
.wx-watch { margin: 5px 0 0; overflow: hidden; color: #7b7169; font-size: 11.5px; text-overflow: ellipsis; white-space: nowrap; }
.wx-watch em { color: #4c453f; font-style: normal; font-weight: 600; }
.wx-seen { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wx-badge { flex: none; padding: 1px 6px; border-radius: 999px; color: #3d7a52; background: #e3f2e7; font-size: 10.5px; font-style: normal; font-weight: 700; }
.wx-badge--on { padding: 3px 9px; font-size: 11px; }

.wx-primary {
  display: inline-flex; height: 36px; align-items: center; justify-content: center; padding: 0 16px;
  border: 0; border-radius: 9px; color: #fff; background: #c44d3e; font-size: 13px; font-weight: 700;
  white-space: nowrap; cursor: pointer; box-shadow: 0 4px 12px rgba(196, 77, 62, .22);
  transition: background .16s, box-shadow .16s;
}
.wx-primary:hover { background: #ad4032; box-shadow: 0 6px 16px rgba(196, 77, 62, .28); }
.wx-primary:disabled { cursor: default; opacity: .65; box-shadow: none; }
.wx-primary--sm { height: 32px; padding: 0 14px; border-radius: 8px; font-size: 12.5px; }
.wx-ghost {
  display: inline-flex; height: 36px; align-items: center; padding: 0 14px; border: 1px solid #e2d6cb;
  border-radius: 9px; color: #7c7168; background: #fff; font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .16s, color .16s;
}
.wx-ghost:hover { border-color: #d3b7a5; color: #b8503a; }

.wx-state { display: grid; flex: 1 1 auto; align-content: center; justify-items: center; gap: 8px; padding: 34px 24px; text-align: center; }
.wx-state .material-symbols-outlined { font-size: 34px; color: #c9b6a7; }
.wx-state p { margin: 0; color: #6b625a; font-size: 13px; font-weight: 600; }
.wx-state small { max-width: 320px; color: #9c9188; font-size: 11.5px; line-height: 1.6; }

.wx-foot { display: flex; flex: none; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 24px 18px; border-top: 1px solid #f2eae3; background: #fffdfb; }
.wx-foot__hint { min-width: 0; overflow: hidden; color: #a1968c; font-size: 11.5px; text-overflow: ellipsis; white-space: nowrap; }

.wx-bound { display: flex; align-items: center; gap: 14px; margin: 18px 24px 0; padding: 16px; border: 1px solid #d9e8dd; border-radius: 14px; background: #f7fbf8; }
.wx-bound__copy { min-width: 0; flex: 1; }
.wx-bound__copy b { display: block; overflow: hidden; color: #27362c; font-size: 15px; text-overflow: ellipsis; white-space: nowrap; }
.wx-bound__copy span { display: block; margin-top: 4px; color: #7d8b82; font-size: 12px; }
.wx-bound__tip { margin: 14px 24px 0; color: #9a9086; font-size: 12px; line-height: 1.6; }

.wx-fade-enter-active, .wx-fade-leave-active { transition: opacity .18s ease; }
.wx-fade-enter-from, .wx-fade-leave-to { opacity: 0; }
.wx-fade-enter-active .wx-panel { animation: wx-pop .2s ease-out; }
@keyframes wx-pop { from { transform: translateY(10px) scale(.98); } to { transform: translateY(0) scale(1); } }

@media (max-width: 720px) {
  .wx-panel { max-height: calc(100vh - 32px); border-radius: 16px; }
  .wx-foot__hint { display: none; }
  .wx-foot { justify-content: flex-end; }
}
@media (prefers-reduced-motion: reduce) {
  .wx-fade-enter-active, .wx-fade-leave-active, .wx-fade-enter-active .wx-panel { transition: none; animation: none; }
}
</style>