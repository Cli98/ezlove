<template>
  <div class="rules-page">
    <header class="rules-head">
      <div>
        <h1>告警规则</h1>
        <p>三条设备规则默认三个等级同一口径，可按需分别微调；保存后最长一个检查周期内生效。</p>
      </div>
      <button class="rules-reload" :disabled="loading" @click="load">
        <span class="material-symbols-outlined">refresh</span>重新读取
      </button>
    </header>

    <div v-if="loading" class="rules-state">
      <span class="material-symbols-outlined spinning">progress_activity</span>正在读取规则配置…
    </div>
    <div v-else-if="error" class="rules-state error">{{ error }}</div>

    <template v-else>
      <section class="rules-card">
        <h2>阈值与开关</h2>
        <table class="rules-table">
          <thead>
            <tr>
              <th>规则</th>
              <th v-for="level in LEVELS" :key="level">{{ level }} 类</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="meta in RULE_META" :key="meta.type">
              <td class="rules-name">
                <b>{{ meta.name }}</b>
                <small>{{ meta.scope }}</small>
              </td>
              <td v-for="level in LEVELS" :key="level" class="rules-cell">
                <template v-if="find(meta.type, level)">
                  <el-input-number
                    :model-value="find(meta.type, level).threshold_hours"
                    :min="1"
                    :max="168"
                    size="small"
                    controls-position="right"
                    @change="value => saveThreshold(meta.type, level, value)"
                  />
                  <el-switch
                    :model-value="find(meta.type, level).enabled"
                    size="small"
                    @change="value => saveEnabled(meta.type, level, value)"
                  />
                </template>
                <span v-else class="rules-missing">未配置</span>
              </td>
              <td class="rules-desc">{{ meta.desc }}</td>
            </tr>
          </tbody>
        </table>
        <p class="rules-note">
          数值单位：小时。关闭开关后该等级不再产生此类提醒。
          设备离线超过 1 小时会自动暂停该设备的活跃提醒并提示核实设备，避免把设备故障当成老人没活动。
        </p>
      </section>

      <section class="rules-card">
        <h2>检查窗口与重复间隔</h2>
        <p class="rules-tip">设备关怀规则的生效时段与提醒间隔，对三个护理等级统一生效。</p>
        <div class="advanced-grid">
          <div v-for="item in advanced" :key="item.type" class="advanced-row">
            <b>{{ item.name }}</b>
            <label v-if="item.window">
              <span>生效时段</span>
              <el-input-number
                :model-value="item.config.check_hours?.[0] ?? 0"
                :min="0" :max="23" size="small" :controls="false"
                @change="value => saveConfig(item, { check_hours: [value, item.config.check_hours?.[1] ?? 22] })"
              />
              <span>至</span>
              <el-input-number
                :model-value="item.config.check_hours?.[1] ?? 22"
                :min="1" :max="24" size="small" :controls="false"
                @change="value => saveConfig(item, { check_hours: [item.config.check_hours?.[0] ?? 7, value] })"
              />
            </label>
            <label v-if="item.hour">
              <span>每日检查时点</span>
              <el-input-number
                :model-value="item.config.check_hour ?? 8"
                :min="0" :max="23" size="small" :controls="false"
                @change="value => saveConfig(item, { check_hour: value })"
              />
            </label>
            <label>
              <span>重复间隔</span>
              <el-input-number
                :model-value="item.config.dedupe_hours ?? item.dedupeDefault"
                :min="1" :max="168" size="small" :controls="false"
                @change="value => saveConfig(item, { dedupe_hours: value })"
              />
              <span>小时</span>
            </label>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAlertRules, seedAlertRules, updateAlertRule } from '@/api/community'

const LEVELS = ['A', 'B', 'C']

const RULE_META = [
  {
    type: 'stillness', name: '红外短时静止', scope: '绑定红外设备',
    desc: '超过阈值没有活动迹象即提醒（可能跌倒），夜间睡眠时段不判',
  },
  {
    type: 'no_activity_trace', name: '长时间无生活轨迹', scope: '绑定红外设备',
    desc: '超过阈值没有任何活动迹象即提醒，全天生效',
  },
  {
    type: 'no_outing', name: '门磁长时间未触发', scope: '绑定门磁',
    desc: '每日检查时点看过去 24 小时有无开/关门；装好满一个周期仍无记录则先提醒核实设备',
  },
  {
    type: 'unread_timeout', name: '牵挂未读提醒', scope: '子女发送的牵挂',
    desc: '牵挂内容超过阈值未被老人查看时提醒子女',
  },
  {
    type: 'canteen_absence', name: '食堂用餐提醒', scope: '有食堂数据的社区',
    desc: '超过阈值没有食堂就餐记录时提醒',
  },
  {
    type: 'no_signal', name: '日常动态提醒', scope: '全部老人',
    desc: '超过阈值没有任何活动信号时提醒',
  },
]

const ADVANCED_META = [
  { type: 'stillness', name: '红外短时静止', window: true, hour: false, dedupeDefault: 6 },
  { type: 'no_activity_trace', name: '长时间无生活轨迹', window: true, hour: false, dedupeDefault: 12 },
  { type: 'no_outing', name: '门磁长时间未触发', window: false, hour: true, dedupeDefault: 24 },
]

const rules = ref([])
const loading = ref(false)
const error = ref('')

function find(type, level) {
  return rules.value.find(rule => rule.rule_type === type && rule.care_level === level)
}

const advanced = computed(() => ADVANCED_META.map(item => {
  const rows = rules.value.filter(rule => rule.rule_type === item.type)
  return {
    ...item,
    rows,
    config: rows[0]?.config || {},
  }
}).filter(item => item.rows.length))

function replaceRule(updated) {
  const index = rules.value.findIndex(rule => rule.id === updated.id)
  if (index >= 0) rules.value.splice(index, 1, updated)
}

async function persist(rule, payload) {
  try {
    const updated = await updateAlertRule(rule.id, payload)
    replaceRule(updated)
    return true
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
    await load()
    return false
  }
}

async function saveThreshold(type, level, value) {
  const rule = find(type, level)
  if (!rule || !value || value === rule.threshold_hours) return
  if (await persist(rule, { threshold_hours: value })) {
    ElMessage.success(`${typeLabel(type)} · ${level} 类阈值已更新`)
  }
}

async function saveEnabled(type, level, value) {
  const rule = find(type, level)
  if (!rule) return
  if (await persist(rule, { enabled: value })) {
    ElMessage.success(`${typeLabel(type)} · ${level} 类已${value ? '开启' : '关闭'}`)
  }
}

async function saveConfig(item, patch) {
  for (const rule of item.rows) {
    await persist(rule, { config: { ...(rule.config || {}), ...patch } })
  }
}

function typeLabel(type) {
  return RULE_META.find(item => item.type === type)?.name || type
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    rules.value = await getAlertRules()
    // 老社区缺新增规则时按内置默认补齐，页面无需手动初始化
    if (RULE_META.some(meta => !find(meta.type, 'A'))) {
      await seedAlertRules()
      rules.value = await getAlertRules()
    }
  } catch (e) {
    error.value = e.response?.data?.detail || '规则读取失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.rules-page { padding: 22px 26px 40px; }
.rules-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.rules-head h1 { margin: 0; color: #172942; font: 700 22px 'Songti SC','STSong',serif; }
.rules-head p { margin: 6px 0 0; color: #8d847b; font-size: 12.5px; max-width: 720px; line-height: 1.6; }
.rules-reload { display: inline-flex; align-items: center; gap: 4px; padding: 7px 12px; border: 1px solid #e5ddd5; border-radius: 9px; color: #6c6259; background: #fff; font-size: 12px; cursor: pointer; }
.rules-reload:hover:not(:disabled) { border-color: #e0c9b8; color: #c75a3d; }
.rules-reload:disabled { opacity: .6; cursor: default; }
.rules-reload .material-symbols-outlined { font-size: 16px; }
.rules-state { margin-top: 40px; color: #91867c; font-size: 13px; text-align: center; }
.rules-state.error { color: #c75a3d; }
.spinning { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.rules-card { margin-top: 18px; padding: 16px 18px 18px; border: 1px solid #e5ddd5; border-radius: 12px; background: rgba(255,255,255,.86); }
.rules-card h2 { margin: 0 0 12px; color: #172942; font: 700 16px 'Songti SC','STSong',serif; }
.rules-tip { margin: 0 0 12px; color: #8d847b; font-size: 12px; }
.rules-table { width: 100%; border-collapse: collapse; }
.rules-table th { padding: 8px 10px; border-bottom: 1px solid #ece5de; color: #6c6259; font-size: 12px; text-align: left; font-weight: 700; }
.rules-table td { padding: 10px; border-bottom: 1px solid #f2ece6; vertical-align: middle; }
.rules-name b { display: block; color: #273143; font-size: 13.5px; }
.rules-name small { display: block; margin-top: 2px; color: #9a9188; font-size: 11px; }
.rules-cell { white-space: nowrap; }
.rules-cell :deep(.el-input-number) { width: 88px; }
.rules-cell :deep(.el-switch) { margin-left: 10px; vertical-align: middle; }
.rules-missing { color: #b8afa6; font-size: 12px; }
.rules-desc { color: #8d847b; font-size: 12px; line-height: 1.6; }
.rules-note { margin: 12px 0 0; color: #91867c; font-size: 11.5px; }

.advanced-grid { display: grid; gap: 10px; }
.advanced-row { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; padding: 11px 12px; border: 1px solid #eee8e2; border-radius: 10px; background: #fffdfb; }
.advanced-row b { min-width: 150px; color: #273143; font-size: 13px; }
.advanced-row label { display: inline-flex; align-items: center; gap: 6px; color: #6c6259; font-size: 12px; }
.advanced-row :deep(.el-input-number) { width: 62px; }
</style>
