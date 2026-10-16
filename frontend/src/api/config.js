// API 地址配置。
// 模拟器（DevTools）跑在电脑上 → localhost 就是电脑本身。
// 真机调试时代码跑在手机上 → localhost 指向手机自身，必须用电脑局域网 IP。
// 运行时通过 uni.getSystemInfoSync().platform 区分：'devtools' = 模拟器，其余 = 真机。

// 模拟器后端切换（两种方式，任选其一）：
//   1) 免编译：开发者工具「调试器 → Storage」面板新增 use_prod_backend = true，
//      刷新模拟器即连线上；删除该项即回本地；
//   2) 编译期：将下面 USE_PROD_IN_DEVTOOLS 改为 true 后重新编译小程序。
// 线上注意事项：
//   - 生产环境，dev-login 调试按钮不可用（返回 403 仅开发环境），请用微信一键登录；
//   - 线上数据与本地库完全隔离，测试操作会写入线上库。
const USE_PROD_IN_DEVTOOLS = false;

// 真机后端切换（编译期）：
//   false = 电脑局域网 IP（真机需与电脑同一 WiFi，且 IP 需与电脑实际网络地址一致）
//   true  = 线上后端（手机任意网络均可，公网可达；预览时须在弹窗勾选“启动调试”以跳过域名校验）
const USE_PROD_ON_DEVICE = false;

// 生产构建（npm run build:mp-weixin，体验版/正式版产物）自动连接线上 HTTPS 后端；
// 开发构建（npm run dev:mp-weixin）下真机仍走上面的 device 开关，便于局域网联调。
const IS_PROD_BUILD = import.meta.env.PROD;

// 各环境后端地址（api 为完整前缀，media 为静态资源前缀；两者路径结构略有差异）
const ENDPOINTS = {
  // 本地后端：容器端口 8001 → 内部 8000
  local: {
    api: "http://localhost:8001/api/v1",
    media: "http://localhost:8001",
  },
  // 线上后端：经服务器 nginx 反代（HTTPS 已备案域名；外部 /ezlove-api/ 映射为后端 /api/）
  prod: {
    api: "https://yiguanian.ysgy.org.cn/ezlove-api/v1",
    media: "https://yiguanian.ysgy.org.cn/ezlove-api",
  },
  // 真机：需与电脑同一局域网
  device: {
    api: "http://192.168.1.3:8001/api/v1",
    media: "http://192.168.1.3:8001",
  },
};

function pickEndpoint() {
  if (IS_PROD_BUILD) return ENDPOINTS.prod;
  try {
    // 运行时开关优先生效（Storage 面板设置后可免编译切换线上/本地）
    const saved = uni.getStorageSync("use_prod_backend");
    if (saved === true || saved === "true") return ENDPOINTS.prod;

    const info = uni.getSystemInfoSync();
    if (info.platform === "devtools") {
      return USE_PROD_IN_DEVTOOLS ? ENDPOINTS.prod : ENDPOINTS.local;
    }
    return USE_PROD_ON_DEVICE ? ENDPOINTS.prod : ENDPOINTS.device;
  } catch (_) {
    return ENDPOINTS.local;
  }
}

const ENDPOINT = pickEndpoint();

export const MEDIA_BASE_URL = ENDPOINT.media;

export const BASE_URL = ENDPOINT.api;

const OSS_ASSET_BASE_URL = "https://ezlove-assets.ysgy.org.cn/uploads/assets/main-a0f1788";

export function getFullUrl(url) {
  if (!url) return "";
  if (url.startsWith("/static/avatars/") || url.startsWith("/static/tabbar/")) {
    return `${OSS_ASSET_BASE_URL}${url.replace("/static", "")}`;
  }
  if (url.startsWith("http")) return url;
  return `${MEDIA_BASE_URL}${url}`;
}
