const TEMPLATE_IDS = {
  // 互助服务进度通知（家属·牵挂未读）：服务名称 thing2 / 温馨提示 thing4
  unread: 'p_MxQhikiBKFwk9B4rDl0t5j-DAfWpiiPxlY1P60dk0',
  // 报告生成通知（网格员·新告警）：报告主题 thing1 / 风险等级 thing2 / 温馨提示 thing4
  alert: 'zexOpSD1IIUC7tutlM_LmI-f_zYJnVycELwYlFYAcLQ',
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
