import { ElMessage } from 'element-plus'
import { API_BASE_URL, ensureFreshToken } from './request'

export async function downloadExport(path, params = {}) {
  const token = await ensureFreshToken()
  const url = new URL(`${API_BASE_URL}${path}`, window.location.origin)
  Object.entries(params).forEach(([k, v]) => {
    if (v != null && v !== '') url.searchParams.set(k, v)
  })

  return fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((res) => {
      if (!res.ok) throw new Error('导出失败')
      const disposition = res.headers.get('content-disposition') || ''
      const match = disposition.match(/filename="?(.+?)"?$/)
      const filename = match ? match[1] : 'export.xlsx'
      return res.blob().then((blob) => ({ blob, filename }))
    })
    .then(({ blob, filename }) => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = filename
      a.click()
      URL.revokeObjectURL(a.href)
    })
    .catch(() => {
      ElMessage.error('导出失败，请稍后再试')
    })
}
