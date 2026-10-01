import elder1 from '@/assets/dashboard-reference/elder-1.png'
import elder2 from '@/assets/dashboard-reference/elder-2.png'
import elder3 from '@/assets/dashboard-reference/elder-3.png'
import elder4 from '@/assets/dashboard-reference/elder-4.png'

const at = (daysAgo, hour, minute) => {
  const date = new Date()
  date.setDate(date.getDate() - daysAgo)
  date.setHours(hour, minute, 0, 0)
  return date.toISOString()
}

export const mockEvents = [
  { id: 'mock-event-1', elder_id: 'mock-elder-1', elder_name: '张建国', elder_address: '1栋 101室', avatar_url: elder1, event_type: 'absent', source: 'canteen', description: '连续2天未出现新动态，建议联系确认老人近期身体状况', severity: 'urgent', is_resolved: false, status: 'pending', deadline: '今日 17:00', assignee: '李社工', created_at: at(0, 11, 40) },
  { id: 'mock-event-2', elder_id: 'mock-elder-2', elder_name: '刘月芳', elder_address: '3栋 301室', avatar_url: elder2, event_type: 'other', source: 'alert', description: '女儿来电反映老人近两天食欲下降，请上门了解情况', severity: 'warning', is_resolved: false, status: 'followup', deadline: '明日 12:00', assignee: '王社工', created_at: at(0, 15, 20) },
  { id: 'mock-event-3', elder_id: 'mock-elder-3', elder_name: '陈志明', elder_address: '3栋 502室', avatar_url: elder3, event_type: 'visit', source: 'manual', description: '网格走访时发现老人情绪低落，建议后续持续关心', severity: 'warning', is_resolved: false, status: 'followup', deadline: '9月30日', assignee: '李社工', created_at: at(0, 10, 15) },
  { id: 'mock-event-4', elder_id: 'mock-elder-4', elder_name: '王秀英', elder_address: '2栋 201室', avatar_url: elder4, event_type: 'emergency', source: 'alert', description: '连续3天未到食堂就餐，电话未接通，请尽快联系确认', severity: 'urgent', is_resolved: false, status: 'pending', deadline: '今日 18:00', assignee: '张社工', created_at: at(1, 16, 30) },
  { id: 'mock-event-5', elder_id: 'mock-elder-5', elder_name: '赵文华', elder_address: '4栋 401室', avatar_url: elder1, event_type: 'visit', source: 'manual', description: '今日已上门探访，老人状态良好，生活正常', severity: 'info', is_resolved: true, status: 'done', deadline: '已完成', assignee: '王社工', resolution_note: '已上门确认，老人状态良好', resolved_at: at(0, 9, 40), created_at: at(0, 9, 20) },
]
