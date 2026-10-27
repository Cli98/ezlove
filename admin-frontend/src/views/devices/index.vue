<template>
  <div class="devices-page">
    <PageTopbar
      v-model:search="topSearch"
      :worker-name="userStore.worker?.name || '社工'"
      :pending-events="dashboardStore.data?.pending_events || 0"
      @events="router.push('/events')"
      @search="goToElders"
    />

    <header class="devices-heading">
      <div class="devices-heading__copy">
        <h1>设备监控</h1>
        <p>智能硬件实时状态与关联老人安全信息</p>
      </div>
      <div class="devices-actions">
        <AppButton variant="outline" wide :disabled="store.loading" @click="store.load()">
          <span class="material-symbols-outlined">refresh</span>刷新状态
        </AppButton>
      </div>
    </header>

    <AppStatBar :stats="stats" />

    <AppPanel class="devices-table-panel">
      <header class="devices-table-panel__head">
        <h2>设备列表 <span>共 <b>{{ store.devices.length }}</b> 台</span></h2>
        <span v-if="store.summary && !store.summary.platform_available" class="platform-warn">
          平台数据暂不可用，当前显示本地绑定信息
        </span>
      </header>
      <AppTable
        class="devices-table"
        :columns="columns"
        :rows="store.devices"
        row-key="sn"
        min-width="980px"
        clickable
        :loading="store.loading"
        empty-text="当前社区暂无接入设备"
        @row-click="openDetail"
      >
        <template #cell-device="{ row }">
          <div class="device-cell">
            <span class="device-cell__icon material-symbols-outlined">{{ deviceIcon(row.device_type) }}</span>
            <div>
              <b>{{ row.label }}</b>
              <small>{{ row.type_label }} · {{ row.sn_masked }}</small>
            </div>
          </div>
        </template>
        <template #cell-elder="{ row }">
          <span v-if="row.elder.linked" class="elder-link">{{ row.elder.name }}</span>
          <span v-else class="elder-unlinked">{{ row.elder.name || '未绑定' }}<small>未建档</small></span>
        </template>
        <template #cell-status="{ row }">
          <span :class="['state-dot', statusTone(row.platform)]"><i></i>{{ row.platform.available ? row.platform.status_label : '—' }}</span>
        </template>
        <template #cell-signal="{ row }">
          <template v-if="row.platform.attributes && row.platform.attributes.signal != null">
            <span :class="['signal-value', signalTone(row.platform.attributes.signal)]">{{ row.platform.attributes.signal }}/5</span>
            <small class="cell-sub">CSQ {{ row.platform.attributes.csq ?? '—' }}</small>
          </template>
          <span v-else>—</span>
        </template>
        <template #cell-battery="{ row }">
          <template v-if="row.platform.attributes && row.platform.attributes.battery != null">
            <span :class="['battery-value', row.platform.attributes.battery === 0 ? 'low' : 'ok']">
              {{ row.platform.attributes.battery === 0 ? '电量低' : '正常' }}
            </span>
            <small class="cell-sub">{{ row.platform.attributes.voltage != null ? row.platform.attributes.voltage + ' mV' : '' }}</small>
          </template>
          <span v-else>—</span>
        </template>
        <template #cell-lastOnline="{ row }">
          <span :title="row.platform.last_online_time || ''">{{ formatAgo(row.platform.last_online_time) }}</span>
        </template>
        <template #cell-alert="{ row }">
          <template v-if="row.last_record">
            <span :class="['alert-tag', recordTone(row.last_record)]">{{ recordLabel(row.last_record) }}</span>
            <small class="cell-sub">{{ formatAgo(row.last_record.created_at) }}</small>
          </template>
          <span v-else>—</span>
        </template>
      </AppTable>
    </AppPanel>

    <DeviceDetailDrawer :sn="activeSn" @close="activeSn = null" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'
import { useDevicesStore } from '@/stores/devices'
import { useUserStore } from '@/stores/user'
import AppButton from '@/components/AppButton.vue'
import AppPanel from '@/components/AppPanel.vue'
import AppStatBar from '@/components/AppStatBar.vue'
import AppTable from '@/components/AppTable.vue'
import PageTopbar from '@/components/PageTopbar.vue'
import DeviceDetailDrawer from './components/DeviceDetailDrawer.vue'

const route = useRoute()
const router = useRouter()
const store = useDevicesStore()
const userStore = useUserStore()
const dashboardStore = useDashboardStore()
const topSearch = ref('')
const activeSn = ref(null)

const columns = [
  { key: 'device', label: '设备', width: '22%' },
  { key: 'elder', label: '关联老人', width: '13%' },
  { key: 'status', label: '在线状态', width: '12%' },
  { key: 'signal', label: '信号', width: '11%' },
  { key: 'battery', label: '电量', width: '13%' },
  { key: 'lastOnline', label: '最后上报', width: '14%' },
  { key: 'alert', label: '最近记录', width: '15%' },
]

const stats = computed(() => {
  const s = store.summary
  if (!s) return []
  return [
    { label: '在线设备', value: s.online, detail: `共 ${s.total} 台接入`, icon: 'check-circle', tone: 'sage' },
    { label: '离线 / 未激活', value: s.offline, detail: s.platform_available ? '需检查供电与网络' : '平台数据暂不可用', icon: 'search', tone: 'amber' },
    { label: '电量偏低', value: s.low_battery, detail: s.unlinked ? `另有 ${s.unlinked} 台未绑定老人` : '电池供电设备关注项', icon: 'bell', tone: 'terracotta' },
  ]
})

function deviceIcon(type) {
  return { 2: 'sensor_door', 6: 'crisis_alert', 12: 'visibility' }[type] || 'visibility'
}

function statusTone(platform) {
  if (!platform.available) return 'unknown'
  if (platform.platform_status === 1) return 'online'
  return 'offline'
}

function signalTone(value) {
  if (value >= 4) return 'strong'
  if (value >= 3) return 'mid'
  return 'weak'
}

function alertTypeLabel(type) {
  return { sos: '紧急报警', device_battery: '电量低', unread: '未读提醒', timeout: '超时未响应' }[type] || type
}

function recordLabel(record) {
  if (record.kind === 'device') {
    return { door_open: '门磁打开', door_close: '门磁关闭' }[record.event_type] || '设备记录'
  }
  return alertTypeLabel(record.alert_type)
}

function recordTone(record) {
  if (record.kind === 'device') return 'info'
  return alertTagTone(record)
}

function alertTagTone(alert) {
  if (alert.is_resolved) return 'resolved'
  return { urgent: 'urgent', warning: 'warning' }[alert.alert_level] || 'info'
}

function formatAgo(value) {
  if (!value) return '—'
  const diff = Date.now() - new Date(value).getTime()
  const minutes = Math.round(diff / 60000)
  if (minutes < 2) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.round(hours / 24)
  if (days < 30) return `${days} 天前`
  const date = new Date(value)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function openDetail(row) {
  activeSn.value = row.sn
}

function goToElders() {
  router.push({ path: '/elders', query: topSearch.value ? { search: topSearch.value } : {} })
}

onMounted(() => {
  store.load()
  if (route.query.sn) activeSn.value = String(route.query.sn)
})
</script>

<style scoped>
.devices-page { display: grid; height: 100%; min-height: 0; grid-template-rows: auto auto auto minmax(0,1fr); }
.devices-heading { display: flex; min-height: 92px; align-items: center; justify-content: space-between; padding: 4px 4px 8px 8px; }
.devices-heading h1 { margin: 0; color: #1f2b36; font: 900 31px/1.1 'Songti SC','STSong','Noto Serif SC',serif; letter-spacing: .04em; }
.devices-heading p { margin: 8px 0 0; color: #617087; font-size: 13px; }
.devices-actions { display: flex; gap: 12px; }.devices-actions :deep(.app-button) { min-width: 132px; }
.devices-table-panel { display: flex; min-height: 0; flex-direction: column; overflow: hidden; }
.devices-table-panel__head { display: flex; min-height: 58px; align-items: center; gap: 14px; padding: 9px 18px 5px; }
.devices-table-panel__head h2 { margin: 0; color: #203044; font: 700 20px 'Songti SC','STSong',serif; }
.devices-table-panel__head span { margin-left: 10px; color: #6c7481; font: 12px sans-serif; }
.devices-table-panel__head b { color: #c6533d; }
.platform-warn { display: inline-flex; height: 26px; align-items: center; padding: 0 10px; border-radius: 6px; color: #b07a20 !important; background: #fdf3e0; font-size: 11.5px !important; }
.devices-table { min-height: 0; flex: 1; margin: 0 14px; }
.devices-table :deep(.app-table td) { height: 66px; color: #46546a; }
.device-cell { display: flex; align-items: center; gap: 10px; }
.device-cell__icon { display: grid; width: 34px; height: 34px; flex: none; place-items: center; border-radius: 50%; color: #c75a3d; background: #fae7df; font-size: 19px; }
.device-cell b { display: block; color: #273143; font-size: 13.5px; }
.device-cell small { display: block; margin-top: 3px; color: #8d8a86; font-size: 11px; }
.elder-link { color: #273143; font-weight: 700; }
.elder-unlinked { color: #9a9188; font-size: 12.5px; }.elder-unlinked small { display: block; margin-top: 2px; color: #b8ac9e; font-size: 10.5px; }
.state-dot { display: inline-flex; align-items: center; gap: 7px; font-size: 12.5px; font-weight: 700; }
.state-dot i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.state-dot.online { color: #56826a; }.state-dot.offline { color: #c75a3d; }.state-dot.unknown { color: #9a9188; }
.signal-value { font-size: 13px; font-weight: 800; }.signal-value.strong { color: #56826a; }.signal-value.mid { color: #d68f30; }.signal-value.weak { color: #c75a3d; }
.battery-value { font-size: 13px; font-weight: 800; }.battery-value.ok { color: #56826a; }.battery-value.low { color: #c75a3d; }
.cell-sub { display: block; margin-top: 2px; color: #9a9188; font-size: 10.5px; }
.alert-tag { display: inline-flex; height: 24px; align-items: center; padding: 0 9px; border-radius: 6px; font-size: 11.5px; font-weight: 700; }
.alert-tag.urgent { color: #c75a3d; background: #fae7df; }.alert-tag.warning { color: #d1842b; background: #fbedd9; }.alert-tag.info { color: #617087; background: #eef0f3; }.alert-tag.resolved { color: #8d8a86; background: #f2eee9; }
@media (max-width: 1050px) { .devices-page { height: auto; min-height: 100%; }.devices-table-panel { min-height: 540px; } }
</style>