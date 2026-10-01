const at = (daysAgo, hour, minute) => {
  const date = new Date()
  date.setDate(date.getDate() - daysAgo)
  date.setHours(hour, minute, 0, 0)
  return date.toISOString()
}

export const mockVolunteerTasks = [
  { id: 'mock-task-1', title: '陪王阿姨去医院复诊', task_type: 'accompany', target_elder_id: 'mock-elder-1', target_elder_name: '王阿姨', target_address: '5栋102室', point_value: 20, volunteer_name: null, status: 'pending', notes: '陪同就医并协助取药', created_at: at(0, 9, 20) },
  { id: 'mock-task-2', title: '送药上门', task_type: 'errand', target_elder_id: 'mock-elder-2', target_elder_name: '赵叔叔', target_address: '2栋301室', point_value: 10, volunteer_name: '李秀兰', status: 'accepted', notes: '将社区卫生站配好的药送到老人家中', created_at: at(0, 8, 40) },
  { id: 'mock-task-3', title: '午后聊天陪伴', task_type: 'visit', target_elder_id: 'mock-elder-1', target_elder_name: '刘月芳', target_address: '4栋503室', point_value: 15, volunteer_name: '陈志明', status: 'completed', notes: '陪老人聊天并记录近期生活情况', created_at: at(1, 15, 10), completed_at: at(0, 14, 30) },
  { id: 'mock-task-4', title: '社区活动签到', task_type: 'check_in', target_elder_id: null, target_elder_name: '幸福里活动室', target_address: '', point_value: 5, volunteer_name: '王阿姨', status: 'verified', notes: '协助参加活动的老人完成签到', created_at: at(1, 10, 0), verified_at: at(1, 17, 0) },
  { id: 'mock-task-5', title: '帮忙取快递', task_type: 'errand', target_elder_id: 'mock-elder-2', target_elder_name: '孙爷爷', target_address: '1栋203室', point_value: 8, volunteer_name: null, status: 'pending', notes: '到社区快递点取件并送上门', created_at: at(2, 16, 30) },
]

export const mockVolunteers = [
  { id: 'mock-volunteer-1', elder_name: '李秀兰', total_points: 128, available_points: 88, is_active: true, created_at: at(45, 9, 0) },
  { id: 'mock-volunteer-2', elder_name: '陈志明', total_points: 96, available_points: 66, is_active: true, created_at: at(38, 10, 30) },
  { id: 'mock-volunteer-3', elder_name: '王阿姨', total_points: 75, available_points: 55, is_active: true, created_at: at(30, 14, 0) },
]

export const mockLeaderboard = mockVolunteers.map((volunteer, index) => ({
  volunteer_id: volunteer.id,
  elder_name: volunteer.elder_name,
  total_points: volunteer.total_points,
  task_count: 12 - index * 2,
}))
