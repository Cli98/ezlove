export function getElderAvatar(person = {}) {
  const avatar = person?.elder_avatar_url || person?.avatar_url
  return typeof avatar === 'string' ? avatar : ''
}
