const TEMPLATE_IDS = {
  unread: '',
  alert: '',
}

export function requestSubscribe(keys = ['unread', 'alert']) {
  const tmplIds = keys
    .map((k) => TEMPLATE_IDS[k])
    .filter(Boolean)

  if (!tmplIds.length) return Promise.resolve()

  return new Promise((resolve) => {
    uni.requestSubscribeMessage({
      tmplIds,
      success: resolve,
      fail: resolve,
    })
  })
}
