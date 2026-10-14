// 最近一次由底部按钮发起的切换（模块级共享）：from 发起页 / path 目标页 / at 发起时间，
// 用于巡检在切换过渡窗口内保持点击即时高亮、并在超时后自动恢复对齐。
let pendingTabSwitch = null;

// 巡检间隔：页面切换时"栈顶更新"与"tabBar 实例挂载"的先后顺序不可控，
// 且不同环境下切换耗时差异大，因此不做一次性的时序假设，
// 由常驻低频巡检兜底：当前显示页的实例最迟 400ms 内对齐高亮。
const WATCH_INTERVAL = 400;
// 点击切换的过渡保护时长，超时自动清除（切换异常时巡检自愈）
const PENDING_TTL = 8000;

Component({
  data: {
    selected: 0,
    color: "#9A8E82",
    selectedColor: "#C44D3E",
    list: [
      {
        pagePath: "/pages/index/index",
        text: "首页",
        iconPath: "/static/tabbar/home.png",
        selectedIconPath: "/static/tabbar/home_active.png",
      },
      {
        pagePath: "/pages/history/index",
        text: "记录",
        iconPath: "/static/tabbar/list.png",
        selectedIconPath: "/static/tabbar/list_active.png",
      },
      {
        pagePath: "/pages/alerts/index",
        text: "提醒",
        iconPath: "/static/tabbar/bell.png",
        selectedIconPath: "/static/tabbar/bell_active.png",
      },
      {
        pagePath: "/pages/profile/index",
        text: "我的",
        iconPath: "/static/tabbar/person.png",
        selectedIconPath: "/static/tabbar/person_active.png",
      },
    ],
  },

  lifetimes: {
    attached() {
      this.startWatch();
    },
    detached() {
      this.stopWatch();
    },
  },

  methods: {
    startWatch() {
      this.stopWatch();
      this._watchTimer = setInterval(() => this.syncIfActive(), WATCH_INTERVAL);
      this.syncIfActive();
    },

    stopWatch() {
      if (this._watchTimer) {
        clearInterval(this._watchTimer);
        this._watchTimer = 0;
      }
    },

    // 仅当本实例是"当前显示页的 tabBar"时，把高亮对齐到栈顶页面；
    // 缓存实例（非当前页）静默跳过，避免误写高亮
    syncIfActive() {
      this.__watchTick = (this.__watchTick || 0) + 1;
      const pages = getCurrentPages();
      const currentPage = pages[pages.length - 1];
      if (!currentPage) return;
      if (typeof currentPage.getTabBar !== "function") return;
      if (currentPage.getTabBar() !== this) return;
      this.__activeTick = (this.__activeTick || 0) + 1;

      const currentPath = `/${currentPage.route}`;
      if (pendingTabSwitch) {
        if (Date.now() - pendingTabSwitch.at > PENDING_TTL) {
          pendingTabSwitch = null;
        } else if (pendingTabSwitch.path === currentPath) {
          pendingTabSwitch = null;
        } else if (pendingTabSwitch.from === currentPath) {
          // 发起页仍在显示：保持点击时的高亮，等待切换完成
          return;
        }
      }

      const selected = this.data.list.findIndex(
        (item) => item.pagePath === currentPath,
      );
      if (selected === -1) return;
      if (selected !== this.data.selected) {
        this.setData({ selected });
      }
    },

    switchTab(event) {
      const { index, path } = event.currentTarget.dataset;
      const pages = getCurrentPages();
      const currentPage = pages[pages.length - 1];
      const currentPath = currentPage ? `/${currentPage.route}` : "";

      // 已在目标页且高亮一致才忽略重复点击；高亮与实际位置不一致时允许点击纠偏
      if (index === this.data.selected && currentPath === path) return;

      pendingTabSwitch = { index, path, from: currentPath, at: Date.now() };
      this.setData({ selected: index });
      if (currentPath !== path) {
        wx.switchTab({ url: path });
      }
    },
  },
});
