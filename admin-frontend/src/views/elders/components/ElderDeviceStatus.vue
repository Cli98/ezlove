<template>
  <section class="elder-device-card">
    <header class="device-head">
      <h2>智能设备</h2>
      <button class="device-more" @click="router.push('/devices')">
        全部设备<span class="material-symbols-outlined">chevron_right</span>
      </button>
    </header>

    <div v-if="loading" class="device-state">正在读取设备状态…</div>
    <div v-else-if="failed" class="device-state">设备状态读取失败</div>
    <div v-else-if="!visibleDevices.length" class="device-state">该老人暂未安装智能设备</div>

    <div v-else class="device-list">
      <button
        v-for="device in visibleDevices"
        :key="device.sn"
        class="device-row"
        @click="openDevice(device)"
      >
        <span class="device-row__icon material-symbols-outlined">
          {{ deviceIcon(device.device_type) }}
        </span>
        <span class="device-row__main">
          <b>{{ device.label }}</b>
          <small>{{ device.type_label }}</small>
        </span>
        <span :class="['device-row__state', stateTone(device)]"><i></i>{{ stateText(device) }}</span>
        <span class="material-symbols-outlined device-row__arrow">chevron_right</span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getDevices } from '@/api/devices'

const props = defineProps({ elderId: { type: String, required: true } })
const router = useRouter()

const loading = ref(false)
const failed = ref(false)
const allDevices = ref([])

// 后端 elder.id 即 CommunityElder.id，与详情页路由参数同源，可直接匹配
const visibleDevices = computed(() => allDevices.value.filter(
  device => device.elder?.linked && String(device.elder.id) === String(props.elderId)
))

function deviceIcon(type) {
  return { 2: 'sensor_door', 6: 'crisis_alert', 12: 'visibility' }[type] || 'visibility'
}

function stateTone(device) {
  if (!device.platform?.available) return 'unknown'
  if (device.platform.platform_status !== 1) return 'offline'
  return device.platform.attributes?.battery === 0 ? 'warn' : 'online'
}

function stateText(device) {
  if (!device.platform?.available) return '待同步'
  if (device.platform.platform_status === 1) {
    return device.platform.attributes?.battery === 0 ? '在线 · 电量低' : '在线'
  }
  return device.platform.status_label || '离线'
}

function openDevice(device) {
  router.push({ path: '/devices', query: { sn: device.sn } })
}

async function load() {
  loading.value = true
  failed.value = false
  try {
    const res = await getDevices()
    allDevices.value = res?.devices || []
  } catch {
    failed.value = true
    allDevices.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.elderId, load)
onMounted(load)
</script>

<style scoped>
.elder-device-card { padding: 14px 16px 12px; border: 1px solid #e5ddd5; border-radius: 11px; background: rgba(255,255,255,.8); }
.device-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.device-head h2 { margin: 0; color: #172942; font: 700 17px 'Songti SC','STSong',serif; }
.device-more { display: flex; align-items: center; gap: 2px; padding: 0; border: 0; color: #8d8a86; background: transparent; font-size: 11.5px; cursor: pointer; }
.device-more:hover { color: #c75a3d; }
.device-more .material-symbols-outlined { font-size: 15px; }
.device-state { margin-top: 10px; padding: 12px 4px; color: #91867c; font-size: 12px; text-align: center; }
.device-list { display: grid; gap: 8px; margin-top: 11px; }
.device-row { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto 18px; align-items: center; gap: 10px; padding: 9px 10px; border: 1px solid #eee8e2; border-radius: 9px; background: #fff; text-align: left; cursor: pointer; transition: border-color .15s, box-shadow .15s; }
.device-row:hover { border-color: #e0c9b8; box-shadow: 0 4px 12px rgba(120, 80, 50, .07); }
.device-row__icon { display: grid; width: 32px; height: 32px; place-items: center; border-radius: 50%; color: #c75a3d; background: #fae7df; font-size: 18px; }
.device-row__main { min-width: 0; }
.device-row__main b { display: block; overflow: hidden; color: #273143; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.device-row__main small { display: block; margin-top: 2px; color: #9a9188; font-size: 10.5px; }
.device-row__state { display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; font-weight: 700; white-space: nowrap; }
.device-row__state i { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.device-row__state.online { color: #56826a; }
.device-row__state.warn { color: #d1842b; }
.device-row__state.offline { color: #c75a3d; }
.device-row__state.unknown { color: #9a9188; }
.device-row__arrow { color: #c4bcb2; font-size: 17px; }
</style>