import elderFemale1 from '@/assets/avatars/elder-female-1.png'
import elderFemale2 from '@/assets/avatars/elder-female-2.png'
import elderFemale3 from '@/assets/avatars/elder-female-3.png'
import elderMale1 from '@/assets/avatars/elder-male-1.png'
import elderMale2 from '@/assets/avatars/elder-male-2.png'
import elderMale3 from '@/assets/avatars/elder-male-3.png'

const AVATARS = {
  female: [elderFemale1, elderFemale2, elderFemale3],
  male: [elderMale1, elderMale2, elderMale3],
}

const PRESET_AVATARS = {
  'elder-female-1.png': elderFemale1,
  'elder-female-2.png': elderFemale2,
  'elder-female-3.png': elderFemale3,
  'elder-male-1.png': elderMale1,
  'elder-male-2.png': elderMale2,
  'elder-male-3.png': elderMale3,
}

const FEMALE_NAMES = new Set([
  '秀英', '桂兰', '玉珍', '淑芳', '凤英', '秀珍', '翠花', '桂英', '玉兰', '美华',
  '春花', '金凤', '素芬', '丽华', '桂芳', '秀兰', '美珍', '玉芬', '凤兰', '淑华',
  '银花', '慧珍', '宝珠', '月琴', '彩云', '秀梅', '惠芳', '碧云', '巧兰', '瑞芳',
  '翠兰', '雪芬', '荷花', '素英', '慧兰', '明珠', '香莲', '云芳', '巧云', '丽珍',
])

const MALE_NAMES = new Set([
  '建国', '国强', '志明', '永林', '德明', '文华', '正义', '明远', '天福', '长青',
  '金生', '福生', '宝林', '玉山', '大海', '光明', '家宝', '学文', '建华', '国庆',
  '振华', '锦荣', '世安', '永祥', '立功', '恒昌', '良平', '清河', '兴邦', '保国',
  '东升', '耀祖', '承恩', '润生', '树仁', '惠民', '启明', '根生', '庆丰', '定邦',
])

function hash(value) {
  return [...String(value || 'default')].reduce((sum, char) => ((sum * 31) + char.charCodeAt(0)) >>> 0, 0)
}

function identity(person, index) {
  return person?.elder_user_id || person?.elder_id || person?.user_id
    || person?.elder_name || person?.name || person?.id || index
}

function genderOf(person, index) {
  const gender = String(person?.gender ?? person?.sex ?? '').toLowerCase()
  if (['female', 'f', '女', '2'].includes(gender)) return 'female'
  if (['male', 'm', '男', '1'].includes(gender)) return 'male'

  const text = [person?.relation_label, person?.elder_name, person?.name].filter(Boolean).join(' ')
  if (/[女妈母奶姥婆姨姑姐妹媳]/.test(text)) return 'female'
  if (/[男爸父爷公叔伯哥弟婿]/.test(text)) return 'male'

  const givenName = text.replace(/[（(].*$/, '').slice(-2)
  if (FEMALE_NAMES.has(givenName)) return 'female'
  if (MALE_NAMES.has(givenName)) return 'male'
  return hash(identity(person, index)) % 2 ? 'female' : 'male'
}

export function getElderAvatar(person = {}, index = 0) {
  const avatarUrl = person.elder_avatar_url || person.avatar_url
  if (avatarUrl) return PRESET_AVATARS[avatarUrl.split('/').pop()] || avatarUrl
  const pool = AVATARS[genderOf(person, index)]
  return pool[hash(identity(person, index)) % pool.length]
}
