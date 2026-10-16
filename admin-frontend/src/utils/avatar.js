export function getElderAvatar(person = {}) {
  const avatar = person?.elder_avatar_url || person?.avatar_url
  // 小程序内置头像只存在于小程序包内，后台沿用首字头像兜底。
  return typeof avatar === 'string' && !avatar.startsWith('/static/avatars/') ? avatar : ''
}
