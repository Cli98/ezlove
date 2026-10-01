import elder1 from '@/assets/dashboard-reference/elder-1.png'
import elder2 from '@/assets/dashboard-reference/elder-2.png'

function todayAt(hour, minute) {
  const date = new Date()
  date.setHours(hour, minute, 0, 0)
  return date.toISOString()
}

export const mockElders = [
  { id: 'mock-elder-1', elder_name: '张建国', age: 82, gender: '男', avatar_url: elder1, care_level: 'A', address: '和谐东区1号楼101室', today_active: false, risk_level: 'critical' },
  { id: 'mock-elder-2', elder_name: '李秀兰', age: 79, gender: '女', avatar_url: elder2, care_level: 'B', address: '和谐中区2号楼203室', today_active: true, risk_level: 'normal' },
]

const details = {
  'mock-elder-1': {
    elder: {
      id: 'mock-elder-1', name: '张建国', age: 82, gender: '男', avatar_url: elder1,
      care_level: 'A', address: '1栋 101室', health_notes: '高血压，日常行动基本自理',
      emergency_contact: { name: '张小华（儿子）', phone: '139 8765 4321' },
    },
    today_active: false,
    last_active_at: todayAt(11, 40),
    alerts: [{ id: 'mock-alert-1', alert_type: 'inactive', alert_level: 'critical', message: '连续2天未出现新的日常动态', is_resolved: false, created_at: todayAt(11, 40) }],
    family_relations: [{ relation_id: 'mock-relation-1', family_member_name: '张小华', relation_label: '儿子', status: 'active' }],
    recent_timeline: [
      { id: 'mock-event-1', type: 'event', time: todayAt(16, 20), label: '在楼内活动', description: '社区日常互动记录', severity: 'info', source: '1栋' },
      { id: 'mock-event-2', type: 'canteen_present', time: todayAt(11, 40), label: '食堂到场', description: '午餐到场信号需要结合近期状态核实', severity: 'warning', source: '食堂' },
      { id: 'mock-event-3', type: 'canteen_present', time: todayAt(7, 30), label: '食堂用餐', description: '早餐正常用餐', severity: 'info', source: '食堂' },
      { id: 'mock-event-4', type: 'event', time: todayAt(6, 20), label: '起床', description: '居家设备记录到日常活动', severity: 'info', source: '设备' },
    ],
    activity_summary: { active_days: 20, total_days: 30, total_views: 18, canteen_rate: 40, daily_activity: [], daily_canteen: [], risk_history: [] },
    risk: { score: 78, level: 'critical', calculated_at: todayAt(11, 40), details: {} },
    care_plan: { deadline: '今日 17:00', items: ['电话联系老人或家属，确认近期情况', '如无法联系，安排上门走访'] },
    care_metrics: { canteen: 40, social: 68, health: 20 },
  },
  'mock-elder-2': {
    elder: {
      id: 'mock-elder-2', name: '李秀兰', age: 79, gender: '女', avatar_url: elder2,
      care_level: 'B', address: '2栋 203室', health_notes: '身体状况稳定，按时参加社区活动',
      emergency_contact: { name: '李明（女儿）', phone: '138 5216 9074' },
    },
    today_active: true,
    last_active_at: todayAt(15, 10),
    alerts: [],
    family_relations: [{ relation_id: 'mock-relation-2', family_member_name: '李明', relation_label: '女儿', status: 'active' }],
    recent_timeline: [
      { id: 'mock-event-5', type: 'event', time: todayAt(15, 10), label: '社区活动', description: '参加社区手工活动', severity: 'info', source: '活动室' },
      { id: 'mock-event-6', type: 'canteen_present', time: todayAt(11, 35), label: '食堂到场', description: '午餐正常到场', severity: 'info', source: '食堂' },
      { id: 'mock-event-7', type: 'view', time: todayAt(8, 10), label: '查看牵挂', description: '查看了家人发送的日常内容', severity: 'info', source: '小程序' },
    ],
    activity_summary: { active_days: 26, total_days: 30, total_views: 31, canteen_rate: 86, daily_activity: [], daily_canteen: [], risk_history: [] },
    risk: { score: 12, level: 'normal', calculated_at: todayAt(15, 10), details: {} },
    care_plan: { deadline: '明日 12:00', items: ['保持日常问候，继续关注近期状态'] },
    care_metrics: { canteen: 86, social: 82, health: 12 },
  },
}

export function getMockElderDetail(id) {
  return details[id] || null
}
