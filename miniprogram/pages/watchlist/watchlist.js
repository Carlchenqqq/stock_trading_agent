const { get } = require('../../utils/request');
const { formatPrice, formatPct, formatVolume, formatAmount, pctClass } = require('../../utils/util');

Page({
  data: {
    loading: true,
    refreshing: false,
    stockList: [],
    isEmpty: false
  },

  _loaded: false,

  onLoad() {
    this.loadWatchlist();
    this._loaded = true;
  },

  onShow() {
    // 非首次显示时才刷新（从其他页面返回时）
    if (this._loaded) {
      this.loadWatchlist();
    }
  },

  onPullDownRefresh() {
    this.setData({ refreshing: true });
    this.loadWatchlist().finally(() => {
      wx.stopPullDownRefresh();
      this.setData({ refreshing: false });
    });
  },

  /**
   * 加载自选股列表
   */
  loadWatchlist() {
    this.setData({ loading: true });

    return get('/api/watchlist')
      .then(data => {
        const list = (data.list || data || []).map(item => ({
          ...item,
          priceText: formatPrice(item.price),
          changePctText: formatPct(item.changePct),
          changePctClass: pctClass(item.changePct),
          volumeText: formatVolume(item.volume),
          amountText: formatAmount(item.amount)
        }));

        this.setData({
          loading: false,
          stockList: list,
          isEmpty: list.length === 0
        });
      })
      .catch(() => {
        this.setData({
          loading: false,
          isEmpty: true
        });
      });
  },

  /**
   * 跳转到 AI 分析页面（带股票代码参数）
   * @param {Object} e - 事件对象
   */
  loadAIStock(e) {
    const code = e.currentTarget.dataset.code;
    if (!code) return;
    wx.navigateTo({
      url: '/pages/ai/ai?code=' + encodeURIComponent(code)
    });
  },

  /**
   * 点击股票行，跳转到详情页
   * @param {Object} e - 事件对象
   */
  onStockTap(e) {
    const code = e.currentTarget.dataset.code;
    if (!code) return;
    wx.navigateTo({
      url: '/pages/ai/ai?code=' + encodeURIComponent(code)
    });
  }
});
