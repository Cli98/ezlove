// 设备类型 → 图标名称。
// 2 门磁 / 6 报警主机（语音报警器、一键报警按钮等同属一类）/ 12 红外。
// 'voice' 由 DeviceTypeIcon 用内联 SVG 渲染，其余走 Material Symbols 字体。
const TYPE_ICONS = { 2: 'sensor_door', 6: 'voice', 12: 'visibility' }

export function deviceIcon(type) {
  return TYPE_ICONS[Number(type)] || 'visibility'
}