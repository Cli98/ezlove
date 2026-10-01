<template>
  <section class="profile-card focus-gradient-surface">
    <div class="profile-main">
      <label class="avatar-upload" title="上传老人头像">
        <img :src="elder.avatar_url || fallbackAvatar" :alt="elder.name || '老人头像'" />
        <span class="avatar-upload__mask"><i class="material-symbols-outlined">add</i>上传图片</span>
        <input type="file" accept="image/jpeg,image/png,image/gif,image/webp" @change="selectAvatar" />
      </label>
      <div class="profile-copy">
        <div class="profile-name"><h1>{{ elder.name || '未命名老人' }}</h1><span class="level">{{ elder.care_level || 'C' }}级</span><span class="care-tag">{{ careLabel }}</span><button class="edit-profile" @click="$emit('edit')"><span class="material-symbols-outlined">edit</span>编辑</button></div>
        <p class="profile-meta">{{ elder.age ? `${elder.age}岁` : '年龄待补充' }} · {{ elder.gender || '性别待补充' }} · {{ elder.address || '地址待补充' }}</p>
        <p v-if="elder.health_notes" class="health-note" :title="elder.health_notes">健康备注：{{ elder.health_notes }}</p>
      </div>
    </div>
    <div class="profile-status">
      <div :class="['status-line', status.tone]"><span class="material-symbols-outlined">{{ status.icon }}</span><b>{{ status.label }}</b></div>
      <div class="signal-line"><DashboardIcon name="bowl" /><span>{{ lastSignal?.label || '暂无最新信号' }}</span></div>
      <div class="signal-line"><DashboardIcon name="clock" /><span>最后信号　{{ formatDateTime(detail.last_active_at) }}</span></div>
    </div>
    <div class="profile-actions">
      <button class="primary" @click="$emit('contact')"><span class="material-symbols-outlined">phone</span>记录联系 / 走访</button>
      <button @click="$emit('confirm')"><span class="material-symbols-outlined">person</span>人工确认活动</button>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import DashboardIcon from '@/components/DashboardIcon.vue'
import fallbackAvatar from '@/assets/dashboard-reference/elder-1.png'

const emit = defineEmits(['contact', 'confirm', 'edit', 'avatar'])
const props = defineProps({ detail: { type: Object, required: true } })
const elder = computed(() => props.detail.elder || {})
const lastSignal = computed(() => props.detail.recent_timeline?.[0])
const careLabel = computed(() => ({ A: '重点关爱', B: '日常关注', C: '健康互助' }[elder.value.care_level] || '日常关怀'))
const status = computed(() => {
  const risk = props.detail.risk?.level
  if (risk === 'critical') return { tone: 'danger', icon: 'error', label: '当前需要核实' }
  if (risk === 'warning' || risk === 'attention') return { tone: 'warning', icon: 'schedule', label: '当前需要关注' }
  if (props.detail.today_active) return { tone: 'normal', icon: 'check_circle', label: '当前状态正常' }
  return { tone: 'muted', icon: 'schedule', label: '等待今日动态' }
})

function formatDateTime(value) {
  if (!value) return '暂无记录'
  const date = new Date(value)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2,'0')}:${String(date.getMinutes()).padStart(2,'0')}`
}

function selectAvatar(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) return ElMessage.warning('请选择图片文件')
  if (file.size > 5 * 1024 * 1024) return ElMessage.warning('头像不能超过 5MB')
  const reader = new FileReader()
  reader.onload = () => emit('avatar', { file, preview: reader.result })
  reader.readAsDataURL(file)
}
</script>

<style scoped>
.profile-card { display: grid; min-height: 154px; grid-template-columns: minmax(420px,1.45fr) minmax(270px,.9fr) 300px; border: 1px solid #e5ddd5; border-radius: 11px; }
.profile-card::before { display: none; }
.profile-main { display: flex; align-items: center; gap: 20px; padding: 20px 24px; }.avatar-upload { position: relative; display: block; width: 112px; height: 112px; flex: none; overflow: hidden; border-radius: 10px; cursor: pointer; }.avatar-upload img { width: 100%; height: 100%; object-fit: cover; }.avatar-upload input { position: absolute; width: 1px; height: 1px; opacity: 0; }.avatar-upload__mask { position: absolute; inset: 0; display: grid; place-content: center; justify-items: center; gap: 4px; color: #fff; background: rgba(67,68,70,.58); font-size: 12px; opacity: 0; transition: opacity .18s ease; }.avatar-upload__mask i { font-size: 29px; }.avatar-upload:hover .avatar-upload__mask, .avatar-upload:focus-within .avatar-upload__mask { opacity: 1; }.profile-copy { min-width: 0; }.profile-name { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }.profile-name h1 { margin: 0 4px 0 0; color: #172942; font: 900 30px/1.1 'Songti SC','STSong',serif; }.profile-meta { margin: 12px 0 0; color: #44536a; font-size: 17px; }.health-note { max-width: 470px; overflow: hidden; margin: 7px 0 0; color: #7c7b79; font-size: 12px; white-space: nowrap; text-overflow: ellipsis; cursor: help; }.level, .care-tag { display: inline-flex; height: 30px; align-items: center; padding: 0 11px; border-radius: 9px; font-size: 13px; font-weight: 800; }.level { color: #c6533d; background: #fae6de; }.care-tag { color: #c6533d; background: #f8e9e4; }.edit-profile { display: inline-flex; height: 30px; align-items: center; gap: 5px; padding: 0 10px; border: 1px solid #d9cfc6; border-radius: 8px; color: #687183; background: rgba(255,255,255,.62); font-size: 12px; cursor: pointer; }.edit-profile .material-symbols-outlined { font-size: 15px; }
.profile-status { display: grid; align-content: center; gap: 12px; padding: 18px 30px; }.profile-status::before { content: ''; position: absolute; top: 22px; bottom: 22px; left: 0; width: 1px; background: rgba(220,185,160,.56); }.status-line, .signal-line { display: flex; align-items: center; gap: 12px; color: #34425a; font-size: 14px; }.status-line .material-symbols-outlined { font-size: 32px; }.status-line b { font-size: 16px; }.status-line.danger { color: #d75439; }.status-line.warning { color: #cf842b; }.status-line.normal { color: #50856a; }.status-line.muted { color: #78808d; }.signal-line :deep(.dashboard-icon) { color: #34425a; font-size: 25px; }
.profile-actions { display: grid; align-content: center; gap: 9px; padding: 20px 24px; }.profile-actions button { display: flex; width: 100%; height: 45px; align-items: center; justify-content: center; gap: 9px; border: 1px solid #d95a42; border-radius: 7px; color: #cf553d; background: rgba(255,255,255,.72); font-size: 14px; font-weight: 700; cursor: pointer; }.profile-actions button.primary { color: #fff; background: #d85b42; }.profile-actions .material-symbols-outlined { font-size: 20px; }
@media (max-width: 1180px) { .profile-card { grid-template-columns: 1.2fr 1fr; }.profile-actions { grid-column: 1 / -1; grid-template-columns: 1fr 1fr; padding-top: 0; } }
</style>
