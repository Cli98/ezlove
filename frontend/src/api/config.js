// API 地址配置。
// 模拟器（DevTools）跑在电脑上 → localhost 就是电脑本身。
// 真机调试时代码跑在手机上 → localhost 指向手机自身，必须用电脑局域网 IP。
// 运行时通过 uni.getSystemInfoSync().platform 区分：'devtools' = 模拟器，其余 = 真机。

function resolveApiBase() {
  try {
    const info = uni.getSystemInfoSync();
    return info.platform === "devtools"
      ? "http://localhost:8001"
      : "http://192.168.1.3:8001";
  } catch (_) {
    return "http://localhost:8001";
  }
}

const DEV_API_BASE = resolveApiBase();

export const MEDIA_BASE_URL = DEV_API_BASE;

export const BASE_URL = `${DEV_API_BASE}/api/v1`;

export function getFullUrl(url) {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  return `${MEDIA_BASE_URL}${url}`;
}
