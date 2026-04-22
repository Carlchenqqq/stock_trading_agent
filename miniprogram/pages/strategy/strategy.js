const { get } = require('../../utils/request');
const { formatPrice, formatPct, formatNumber, pctClass, scoreClass } = require('../../utils/util');

Page({
  data: {
    loading: true,
    refreshing: false,
    isEmpty: false,

    // 策略列表
    strategyList: [],

    // 当前展开的策略索引
    expandedIndex: -1
  },

  _loaded: false,

  onLoad() {
    this.loadStrategy();
    this._loaded = true;
  },

  onShow() {
    if (this._loaded) {
      this.loadStrategy();
    }
  },

  onPullDownRefresh() {
    this.setData({ refreshing: true });
    this.loadStrategy().finally(() => {
      wx.stopPullDownRefresh();
      this.setData({ refreshing: false });
    });
  },

  /**
   * 加载策略分析数据
   */
  loadStrategy() {
    this.setData({ loading: true });

    return get('/api/strategy')
      .then(data => {
        // 将策略对象转为数组
        const strategyMap = data.strategies || data;

        const strategyNames = {
          '动量策略': { icon: '🚀', desc: '捕捉价格动量趋势' },
          '均值回归': { icon: '📊', desc: '识别超买超卖回归机会' },
          '趋势跟踪': { icon: '📈', desc: '跟踪中长期趋势方向' },
          '波动率突破': { icon: '⚡', desc: '突破波动率区间交易' }
        };

        const strategyList = Object.keys(strategyMap).map((name, idx) => {
          const rawSignals = strategyMap[name] || [];
          const meta = strategyNames[name] || { icon: '📋', desc: '' };

          const signals = rawSignals.map(item => ({
            ...item,
            priceText: formatPrice(item.price),
            changePctText: formatPct(item.changePct),
            changePctClass: pctClass(item.changePct),
            scoreText: formatNumber(item.score, 1),
            scoreClass: scoreClass(item.score),
            actionText: item.action || item.signal || '--',
            actionClass: this._actionClass(item.action || item.signal || '')
          }));

          return {
            id: idx,
            name,
            icon: meta.icon,
            desc: meta.desc,
            signals,
            signalCount: signals.length,
            expanded: false
          };
        });

        this.setData({
          loading: false,
          isEmpty: strategyList.length === 0,
          strategyList
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
   * 操作信号标签样式
   */
  _actionClass(action) {
    if (!action) return 'tag-blue';
    const a = action.toLowerCase();
    if (a.includes('买入') || a.includes('buy') || a.includes('做多')) return 'tag-green';
    if (a.includes('卖出') || a.includes('sell') || a.includes('做空')) return 'tag-red';
    if (a.includes('持有') || a.includes('hold')) return 'tag-cyan';
    if (a.includes('观望') || a.includes('watch')) return 'tag-yellow';
    if (a.includes('止损') || a.includes('stop')) return 'tag-orange';
    return 'tag-blue';
  },

  /**
   * 展开/收起策略卡片
   */
  onToggleStrategy(e) {
    const idx = e.currentTarget.dataset.index;
    const key = 'strategyList[' + idx + '].expanded';
    const current = this.data.strategyList[idx].expanded;
    this.setData({ [key]: !current });
  },

  /**
   * AI 策略分析
   */
  goToAIStrategy() {
    wx.navigateTo({ url: '/pages/ai/ai?type=strategy' });
  },

  /**
   * 点击股票行
   */
  onStockTap(e) {
    const code = e.currentTarget.dataset.code;
    if (!code) return;
    wx.navigateTo({
      url: '/pages/ai/ai?code=' + encodeURIComponent(code)
    });
  }
});
