export function getNavigationBarMetrics() {
  const windowInfo = uni.getWindowInfo?.() || {};
  const menuButton = uni.getMenuButtonBoundingClientRect?.();
  const statusBarHeight = windowInfo.statusBarHeight || 20;
  const top = menuButton?.top || statusBarHeight + 6;
  const height = menuButton?.height || 32;
  const gap = Math.max(top - statusBarHeight, 4);
  const totalHeight = top + height + gap;
  const rightInset = menuButton?.left && windowInfo.windowWidth
    ? windowInfo.windowWidth - menuButton.left + 8
    : 16;

  return {
    top,
    height,
    gap,
    totalHeight,
    rightInset,
    barStyle: {
      paddingTop: `${top}px`,
      height: `${height}px`,
      paddingBottom: `${gap}px`,
    },
    titleStyle: {
      top: `${top + height / 2}px`,
    },
  };
}
