const { get } = require('../../utils/request');
const { formatPrice, formatNumber } = require('../../utils/util');

Page({
  data: {
    loading: true,
    boards: [],
    tradingTime: {},
    fees: {},
    rules: {},
    limitPriceExamples: []
  },

  onLoad() {
    this.loadRules();
  },

  onPullDownRefresh() {
    this.loadRules().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 加载交易规则数据
   */
  loadRules() {
    this.setData({ loading: true });

    return get('/api/rules')
      .then(data => {
        // 映射板块涨跌停限制
        const boards = (data.boards || []).map(item => ({
          ...item,
          limitText: formatNumber(item.limit_pct, 1) + '%'
        }));

        // 映射交易时间
        const tradingTime = data.trading_time || {};

        // 映射交易费用
        const fees = data.fees || {};

        // 映射交易规则
        const rules = data.rules || {};

        // 映射涨跌停价格示例
        const limitPriceExamples = (data.limit_price_examples || []).map(item => ({
          ...item,
          upPriceText: formatPrice(item.up_price),
          downPriceText: formatPrice(item.down_price),
          pctText: formatNumber(item.limit_pct, 1) + '%'
        }));

        this.setData({
          loading: false,
          boards,
          tradingTime,
          fees,
          rules,
          limitPriceExamples
        });
      })
      .catch(() => {
        this.setData({ loading: false });
      });
  }
});
