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
      this.syncSelected();
    },
    ready() {
      this.syncSelected();
    },
  },

  pageLifetimes: {
    show() {
      this.syncSelected();
    },
  },

  methods: {
    syncSelected() {
      const pages = getCurrentPages();
      const currentPage = pages[pages.length - 1];
      if (!currentPage) return;

      const currentPath = `/${currentPage.route}`;
      const selected = this.data.list.findIndex(
        (item) => item.pagePath === currentPath,
      );
      if (selected !== -1 && selected !== this.data.selected) {
        this.setData({ selected });
      }
    },

    switchTab(event) {
      const { index, path } = event.currentTarget.dataset;
      if (index === this.data.selected) return;

      this.setData({ selected: index });
      wx.switchTab({ url: path });
    },
  },
});
