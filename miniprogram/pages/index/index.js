const { get } = require('../../utils/request');
const { formatNumber, formatPct, pctClass } = require('../../utils/util');

Page({
  data: {
    // 市场数据
    marketLoading: true,
    shIndex: { value: '--', change: '--', changePct: '--' },
    limitUp: '--',
    limitDown: '--',
    advanceDeclineRatio: '--',

    // AI 分析
    aiLoading: true,
    aiAnalysis: '',

    // 涨跌颜色 class
    shIndexClass: '',
    limitUpClass: 'text-green',
    limitDownClass: 'text-red'
  },

  _loaded: false,

  onLoad() {
    this.loadMarketData();
    this.loadAIMarketAnalysis();
    this._loaded = true;
  },

  onShow() {
    // 非首次显示时才刷新（从其他页面返回时）
    if (this._loaded) {
      this.loadMarketData();
      this.loadAIMarketAnalysis();
    }
  },

  onPullDownRefresh() {
    Promise.all([
      this.loadMarketData(),
      this.loadAIMarketAnalysis()
    ]).finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 加载市场概览数据
   */
  loadMarketData() {
    this.setData({ marketLoading: true });

    get('/api/market')
      .then(data => {
        const shIndex = data.shIndex || {};
        const changePct = shIndex.changePct || 0;

        this.setData({
          marketLoading: false,
          shIndex: {
            value: formatNumber(shIndex.value),
            change: formatPct(shIndex.change),
            changePct: formatPct(changePct)
          },
          limitUp: data.limitUp != null ? data.limitUp : '--',
          limitDown: data.limitDown != null ? data.limitDown : '--',
          advanceDeclineRatio: data.advanceDeclineRatio || '--',
          shIndexClass: pctClass(changePct)
        });
      })
      .catch(() => {
        this.setData({ marketLoading: false });
      });
  },

  /**
   * 加载 AI 市场分析
   */
  loadAIMarketAnalysis() {
    this.setData({ aiLoading: true });

    get('/api/ai/market')
      .then(data => {
        this.setData({
          aiLoading: false,
          aiAnalysis: data.analysis || data.content || '暂无分析数据'
        });
      })
      .catch(() => {
        this.setData({
          aiLoading: false,
          aiAnalysis: 'AI 分析加载失败，请稍后重试'
        });
      });
  },

  /**
   * 跳转到 AI 分析页面
   */
  goToAI() {
    wx.navigateTo({ url: '/pages/ai/ai' });
  },

  /**
   * 跳转到策略分析页面
   */
  goToStrategy() {
    wx.navigateTo({ url: '/pages/strategy/strategy' });
  },

  /**
   * 跳转到股票推荐页面
   */
  goToRecommend() {
    wx.navigateTo({ url: '/pages/recommend/recommend' });
  },

  /**
   * 跳转到交易规则页面
   */
  goToRules() {
    wx.navigateTo({ url: '/pages/rules/rules' });
  }
});
