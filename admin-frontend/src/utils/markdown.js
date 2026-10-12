import MarkdownIt from 'markdown-it'

const markdown = new MarkdownIt({ html: false, breaks: true, linkify: true })

export function renderAgentMarkdown(text) {
  if (!text) return ''
  return markdown.render(text).replace(
    /\[\[elder:([\w-]+):(.*?)\]\]/g,
    '<a href="#" data-elder-id="$1" class="agent-elder-link">$2</a>'
  )
}
