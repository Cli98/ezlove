// 自定义 tabBar 高亮同步：在 tab 页 onShow 中调用，将高亮对齐到当前页面。
// onShow 触发时 getCurrentPages() 栈顶即当前页，但 tabBar 组件实例可能尚未挂载，
// 因此短间隔重试兜底（每拍都按当时栈顶重新计算，幂等安全）。
// 数组顺序必须与 custom-tab-bar/index.js 的 list 一致。
const TAB_PATHS = [
  "/pages/index/index",
  "/pages/history/index",
  "/pages/alerts/index",
  "/pages/profile/index",
];

const RETRY_INTERVAL = 100;
const MAX_RETRIES = 5;

function applySync() {
  const pages = getCurrentPages();
  const currentPage = pages[pages.length - 1];
  if (!currentPage) return;
  const selected = TAB_PATHS.indexOf(`/${currentPage.route}`);
  if (selected === -1) return;
  const tabBar =
    typeof currentPage.getTabBar === "function"
      ? currentPage.getTabBar()
      : null;
  if (tabBar) {
    tabBar.setData({ selected });
    tabBar.__syncCount = (tabBar.__syncCount || 0) + 1;
  }
}

export function syncTabBar() {
  applySync();
  let tries = 0;
  const timer = setInterval(() => {
    tries += 1;
    applySync();
    if (tries >= MAX_RETRIES) {
      clearInterval(timer);
    }
  }, RETRY_INTERVAL);
}
