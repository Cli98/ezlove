import test from 'node:test'
import assert from 'node:assert/strict'
import { shouldRefreshAuth } from './auth-refresh.js'

test('只有携带访问令牌的 401 才触发刷新', () => {
  assert.equal(shouldRefreshAuth({ response: { status: 401 }, config: { headers: {} } }), false)
  assert.equal(shouldRefreshAuth({ response: { status: 401 }, config: { headers: { Authorization: 'Bearer expired' } } }), true)
  assert.equal(shouldRefreshAuth({ response: { status: 401 }, config: { _retry: true, headers: { Authorization: 'Bearer expired' } } }), false)
})
