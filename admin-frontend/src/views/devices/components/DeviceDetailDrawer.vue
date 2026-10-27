<template>
  <Teleport to="body">
    <Transition name="drawer-fade">
      <div v-if="sn" class="device-drawer-mask" @click="$emit('close')"></div>
    </Transition>
    <Transition name="drawer-slide">
      <aside v-if="sn" class="device-drawer" aria-label="设备详情">
        <header class="device-drawer__head">
          <div>
            <h2>{{ detail?.label || '设备详情' }}</h2>
            <p>{{ detail ? `${detail.type_label} · ${detail.sn_masked}` : '正在读取…' }}</p>
          </div>
          <button class="device-drawer__close" @click="$emit('close')">
            <span class="material-symbols-outlined">close</span>
          </button>
        </header>

        <div class="device-drawer__body">
          <div v-if="loading" class="drawer-state">
            <span class="material-symbols-outlined spinning">progress_activity</span>
            <p>正在读取设备状态…</p>
          </div>
          <div v-else-if="error" class="drawer-state">
            <span class="material-symbols-outlined">error</span>
            <p>{{ error }}</p>
          </div>
          <template v-else-if="detail">
            <div v-if="!detail.platform.available" class="drawer-warn">
              平台数据暂不可用（{{ reasonLabel }}），以下仅显示本地绑定信息
            </div>

            <section class="drawer-card">
              <h3>实时状态</h3>
              <div class="kv-grid">
                <div class="kv"><small>在线状态</small><b :class="['kv-status', statusTone]">{{ detail.platform.available ? detail.platform.status_label : '—' }}</b></div>
                <div class="kv"><small>信号强度</small><b>{{ attrs.signal != null ? `${attrs.signal} / 5` : '—' }}</b></div>
                <div class="kv"><small>电池状态</small><b :class="{ 'kv-low': attrs.battery === 0 }">{{ batteryText }}</b></div>
                <div class="kv"><small>电压</small><b>{{ attrs.voltage != null ? `${attrs.voltage} mV` : '—' }}</b></div>
                <div class="kv"><small>心跳周期</small><b>{{ attrs.heartbeat_hours != null ? `${attrs.heartbeat_hours} 小时` : '—' }}</b></div>
                <div v-if="attrs.ambient_temperature != null" class="kv"><small>环境温度</small><b>{{ attrs.ambient_temperature }} ℃</b></div>
                <div v-if="attrs.manned_unmanned != null" class="kv"><small>人体感应</small><b>{{ attrs.manned_unmanned === 1 ? '有人' : '无人' }}</b></div>
                <div v-if="attrs.tamper_status != null" class="kv"><small>防拆状态</small><b :class="{ 'kv-low': attrs.tamper_status === 1 }">{{ attrs.tamper_status === 1 ? '已拆卸' : '已安装' }}</b></div>
                <div class="kv"><small>最后上报</small><b>{{ formatTime(detail.platform.last_online_time) }}</b></div>
                <div class="kv"><small>属性更新</small><b>{{ formatTime(detail.platform.attributes_updated_at) }}</b></div>
              </div>
            </section>

            <section class="drawer-card">
              <h3>设备信息</h3>
              <div class="kv-grid">
                <div class="kv"><small>设备名称</small><b>{{ detail.platform.device_name || detail.label }}</b></div>
                <div class="kv"><small>型号</small><b>{{ detail.platform.model || '—' }}</b></div>
                <div class="kv"><small>SN（脱敏）</small><b>{{ detail.sn_masked }}</b></div>
                <div class="kv"><small>ICCID（脱敏）</small><b>{{ attrs.iccid || '—' }}</b></div>
                <div v-if="attrs.hardware" class="kv"><small>硬件版本</small><b>{{ attrs.hardware }}</b></div>
              </div>
            </section>

            <section class="drawer-card">
              <h3>关联老人</h3>
              <div v-if="detail.elder.linked" class="elder-row">
                <div class="elder-row__name">
                  <span class="material-symbols-outlined">person</span>
                  <b>{{ detail.elder.name }}</b>
                </div>
                <span v-if="detail.risk" class="risk-badge" :class="`level-${detail.risk.level}`">
                  {{ riskLevelLabel(detail.risk.level) }} · {{ detail.risk.score ?? '—' }} 分
                </span>
              </div>
              <p v-else class="drawer-hint">该设备尚未关联到已建档老人。绑定方法：在设备绑定配置中填写老人档案 ID（可在老人档案详情页地址栏复制）。</p>
            </section>

            <section class="drawer-card">
              <h3>最近记录</h3>
              <div v-if="detail.records && detail.records.length" class="alert-list">
                <div v-for="record in detail.records" :key="record.id" class="alert-item">
                  <span :class="['alert-dot', record.kind === 'device' ? 'info' : (record.is_resolved ? 'resolved' : record.level)]"></span>
                  <div>
                    <p>{{ record.message }}</p>
                    <small>{{ formatTime(record.created_at) }} · {{ record.kind === 'device' ? '设备事件' : (record.is_resolved ? '已处理' : '待处理') }}</small>
                  </div>
                </div>
              </div>
              <p v-else class="drawer-hint">暂无记录</p>
            </section>
          </template>
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { getDeviceDetail } from '@/api/devices'

const props = defineProps({ sn: { type: String, default: null } })
const emit = defineEmits(['close'])

const loading = ref(false)
const error = ref('')
const detail = ref(null)

watch(() => props.sn, async (sn) => {
  if (!sn) {
    detail.value = null
    return
  }
  loading.value = true
  error.value = ''
  detail.value = null
  try {
    detail.value = await getDeviceDetail(sn)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '设备详情读取失败'
  } finally {
    loading.value = false
  }
}, { immediate: true })

const attrs = computed(() => detail.value?.platform?.attributes || {})

const batteryText = computed(() => {
  if (attrs.value.battery == null) return '—'
  return attrs.value.battery === 0 ? '电量低' : '正常'
})

const statusTone = computed(() => {
  const platform = detail.value?.platform
  if (!platform?.available) return 'unknown'
  return platform.platform_status === 1 ? 'online' : 'offline'
})

const reasonLabel = computed(() => ({
  credentials_missing: '未配置平台凭证',
  auth_failed: '平台鉴权失败',
  device_not_found: '平台未找到该设备',
  network_error: '网络连接失败',
}[detail.value?.platform?.reason] || '原因未知'))

function riskLevelLabel(level) {
  return { normal: '平稳', attention: '需关注', warning: '较高', critical: '高风险' }[level] || '待评估'
}

function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function handleEscape(event) {
  if (event.key === 'Escape' && props.sn) emit('close')
}

window.addEventListener('keydown', handleEscape)
onBeforeUnmount(() => window.removeEventListener('keydown', handleEscape))
</script>

<style scoped>
.device-drawer-mask { position: fixed; z-index: 2100; inset: 0; background: rgba(31, 26, 22, .34); }
.device-drawer { position: fixed; z-index: 2101; top: 0; right: 0; bottom: 0; display: flex; width: min(460px, 94vw); flex-direction: column; background: #fdfaf6; box-shadow: -14px 0 40px rgba(46, 34, 26, .16); }
.device-drawer__head { display: flex; align-items: flex-start; justify-content: space-between; padding: 20px 22px 14px; border-bottom: 1px solid #eee4da; }
.device-drawer__head h2 { margin: 0; color: #172942; font: 700 21px 'Songti SC','STSong',serif; }
.device-drawer__head p { margin: 6px 0 0; color: #7a8190; font-size: 12px; }
.device-drawer__close { display: grid; width: 34px; height: 34px; place-items: center; border: 1px solid #e5ddd5; border-radius: 8px; color: #677387; background: #fff; cursor: pointer; }
.device-drawer__close span { font-size: 19px; }
.device-drawer__body { flex: 1; min-height: 0; overflow-y: auto; padding: 16px 22px 26px; scrollbar-width: thin; }
.drawer-state { display: grid; min-height: 220px; place-items: center; align-content: center; gap: 8px; color: #91867c; font-size: 13px; }
.drawer-state > span { font-size: 34px; }.drawer-state p { margin: 0; }
.spinning { animation: spin 1s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }
.drawer-warn { margin-bottom: 12px; padding: 10px 13px; border: 1px solid #f0dfb8; border-radius: 8px; color: #a9751f; background: #fdf5e3; font-size: 12px; }
.drawer-card { margin-top: 12px; padding: 15px 16px; border: 1px solid #e5ddd5; border-radius: 11px; background: #fff; }
.drawer-card:first-of-type { margin-top: 0; }
.drawer-card h3 { margin: 0 0 12px; color: #172942; font: 700 15px 'Songti SC','STSong',serif; }
.kv-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 14px; }
.kv small { display: block; color: #8d8a86; font-size: 11px; }
.kv b { display: block; margin-top: 3px; color: #2e3d54; font-size: 13px; font-weight: 700; }
.kv-status.online { color: #56826a; }.kv-status.offline { color: #c75a3d; }.kv-status.unknown { color: #9a9188; }
.kv-low { color: #c75a3d !important; }
.elder-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.elder-row__name { display: flex; align-items: center; gap: 8px; color: #2e3d54; font-size: 14px; }
.elder-row__name span { display: grid; width: 30px; height: 30px; place-items: center; border-radius: 50%; color: #c75a3d; background: #fae7df; font-size: 17px; }
.risk-badge { display: inline-flex; height: 26px; align-items: center; padding: 0 10px; border-radius: 7px; font-size: 11.5px; font-weight: 700; }
.risk-badge.level-normal { color: #56826a; background: #e6f0e9; }.risk-badge.level-attention { color: #d1842b; background: #fbedd9; }.risk-badge.level-warning { color: #c75a3d; background: #fae7df; }.risk-badge.level-critical { color: #a5321f; background: #f8ddd5; }
.drawer-hint { margin: 0; color: #8d8a86; font-size: 12.5px; line-height: 1.6; }
.alert-list { display: grid; gap: 10px; }
.alert-item { display: flex; gap: 10px; }
.alert-dot { width: 8px; height: 8px; flex: none; margin-top: 5px; border-radius: 50%; background: #b8ac9e; }
.alert-dot.urgent { background: #c75a3d; }.alert-dot.warning { background: #d68f30; }.alert-dot.info { background: #7f95b5; }.alert-dot.resolved { background: #c4bcb2; }
.alert-item p { margin: 0; color: #3c465a; font-size: 12.5px; line-height: 1.55; }
.alert-item small { display: block; margin-top: 3px; color: #9a9188; font-size: 11px; }
.drawer-fade-enter-active, .drawer-fade-leave-active { transition: opacity .2s ease; }
.drawer-fade-enter-from, .drawer-fade-leave-to { opacity: 0; }
.drawer-slide-enter-active, .drawer-slide-leave-active { transition: transform .26s cubic-bezier(.16, 1, .3, 1); }
.drawer-slide-enter-from, .drawer-slide-leave-to { transform: translateX(100%); }
</style>