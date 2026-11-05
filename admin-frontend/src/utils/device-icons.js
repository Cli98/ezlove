// 设备类型 → 图标名称。
// 2 门磁 / 6 报警主机（仅语音报警器用喇叭，一键报警按钮保留警示三角）/ 12 红外。
// 'voice' 由 DeviceTypeIcon 用内联 SVG 渲染，其余走 Material Symbols 字体。
const TYPE_ICONS = { 2: 'sensor_door', 12: 'visibility' }

export function deviceIcon(type, label = '') {
  const t = Number(type)
  if (t === 6) return String(label).includes('语音') ? 'voice' : 'crisis_alert'
  return TYPE_ICONS[t] || 'visibility'
}