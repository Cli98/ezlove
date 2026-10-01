const pad = value => String(value).padStart(2, '0')
const today = new Date()
const dateText = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`
const at = (daysAgo, hour, minute) => {
  const date = new Date()
  date.setDate(date.getDate() - daysAgo)
  date.setHours(hour, minute, 0, 0)
  return date.toISOString()
}

export const mockCanteenMenu = {
  id: 'mock-menu',
  menu_date: dateText,
  meal_type: 'lunch',
  status: 'draft',
  dishes: {
    items: [
      { name: '红烧鱼', description: '鲜香入味，肉质鲜嫩', category: '荤菜' },
      { name: '青椒肉丝', description: '爽口下饭，营养丰富', category: '荤菜' },
      { name: '清炒时蔬', description: '清淡爽口，时令新鲜', category: '素菜' },
      { name: '番茄蛋汤', description: '酸甜开胃，营养丰富', category: '荤菜' },
    ],
    staple: '米饭',
    soup: '',
    summary: '家常营养搭配，清淡易入口',
  },
}

export const mockCanteenParsed = {
  date: dateText,
  meal_type: 'lunch',
  attendees: [
    { elder_id: 'mock-elder-2', elder_name: '李秀兰', care_level: 'A', present: false, notes: '今日未到食堂' },
    { elder_id: 'mock-elder-3', elder_name: '刘月芳', care_level: 'B', present: false, notes: '今日未到食堂' },
    { elder_id: 'mock-elder-4', elder_name: '王阿姨', care_level: 'B', present: false, notes: '今日未到食堂' },
    { elder_id: 'mock-elder-1', elder_name: '张建国', present: true, notes: '' },
    { elder_id: 'mock-elder-5', elder_name: '陈志明', present: true, notes: '' },
    { elder_id: 'mock-elder-6', elder_name: '赵文华', present: true, notes: '' },
  ],
  parse_notes: '根据文本描述匹配辖区老人名单',
}

export const mockCanteenRecords = [
  { id: 'mock-record-1', raw_text: '今天中午食堂，张大爷来了，李奶奶没来，王大爷来了但没怎么吃', source_format: 'text', parse_status: 'success', parsed_data: mockCanteenParsed, created_at: at(0, 11, 40) },
  { id: 'mock-record-2', raw_text: '食堂出勤记录_20240914.xlsx', source_format: 'excel', parse_status: 'success', parsed_data: mockCanteenParsed, created_at: at(1, 11, 32) },
  { id: 'mock-record-3', raw_text: '今天午餐，李奶奶没来，王大爷正常到场', source_format: 'text', parse_status: 'pending', parsed_data: null, created_at: at(2, 11, 5) },
]
