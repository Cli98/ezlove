// 告警类型代码 → 中文文案（避免界面直接暴露英文枚举）
const ALERT_TYPE_LABELS = {
  sos: '紧急报警',
  device_battery: '电量低',
  unread: '未读提醒',
  timeout: '超时未响应',
  morning_silence: '晨间关怀提醒',
  unread_timeout: '牵挂未读提醒',
  canteen_absence: '食堂用餐提醒',
  no_signal: '日常动态提醒',
  stillness: '活动静止提醒',
  no_activity: '无生活轨迹提醒',        // alerts.alert_type 短名（设备页按此取文案）
  no_activity_trace: '无生活轨迹提醒',  // trigger_rule / rule_type 全名
  no_outing: '长时间未外出提醒',
  device_check: '设备核实提醒',
  device_offline: '设备离线提醒',
}

export function alertTypeLabel(type) {
  return ALERT_TYPE_LABELS[type] || '关怀记录'
}