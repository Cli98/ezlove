/**
 * Format an ISO date string into a human-readable form.
 * @param {string} isoStr - ISO 8601 date string
 * @returns {string} formatted date like "2024-03-15 14:30"
 */
export function formatDateTime(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/**
 * Format an ISO date string into a relative or short date for display.
 * @param {string} isoStr - ISO 8601 date string
 * @returns {string} relative time like "刚刚", "5分钟前", "2小时前", or "03-15"
 */
export function formatRelativeTime(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return "";
  const now = Date.now();
  const diff = now - d.getTime();
  if (diff < 60000) return "刚刚";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  if (diff < 86400000 * 30) return `${Math.floor(diff / 86400000)}天前`;
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
