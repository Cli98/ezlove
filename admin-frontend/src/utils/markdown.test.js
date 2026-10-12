import assert from 'node:assert/strict'
import test from 'node:test'
import { renderAgentMarkdown } from './markdown.js'

test('渲染常用 Markdown 并保留老人档案链接', () => {
  const html = renderAgentMarkdown(`## 今日重点

**需要联系**

| 姓名 | 状态 |
| --- | --- |
| 王秀英 | 待确认 |

[[elder:abc-123:王秀英]]`)

  assert.match(html, /<h2>今日重点<\/h2>/)
  assert.match(html, /<strong>需要联系<\/strong>/)
  assert.match(html, /<table>/)
  assert.match(html, /data-elder-id="abc-123"/)
})

test('不执行 AI 返回的原始 HTML', () => {
  assert.match(renderAgentMarkdown('<script>alert(1)</script>'), /&lt;script&gt;/)
})
