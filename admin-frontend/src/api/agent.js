const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
import { ensureFreshToken } from './request'

async function doFetch(messages, token) {
  return fetch(`${API_BASE}/community/agent/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ messages }),
  })
}

export async function* streamAgentChat(messages) {
  let token = await ensureFreshToken()
  let res = await doFetch(messages, token)

  if (res.status === 401 || res.status === 403) {
    const newToken = await ensureFreshToken()
    if (newToken) {
      token = newToken
      res = await doFetch(messages, token)
    }
  }

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6))
        } catch {
          // skip malformed
        }
      }
    }
  }
}
