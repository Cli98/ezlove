const BASE_URL = import.meta.env.VITE_API_BASE_URL
import { ElMessage } from 'element-plus'

export function downloadExport(path, params = {}) {
  const token = localStorage.getItem('community_access_token')
  const url = new URL(`${window.location.origin}${BASE_URL}${path}`)
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
