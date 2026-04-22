const { get } = require('../../utils/request');
const { formatPrice, formatPct, formatNumber, pctClass, scoreClass } = require('../../utils/util');

Page({
  data: {
    loading: true,
    refreshing: false,
    isEmpty: false,

    // 市场情绪
    sentiment: {
      label: '--',
      level: '',
      class: ''
    },

    // 预警信息
    warnings: [],

    // 推荐列表
    recommendList: []
  },

  _loaded: false,

  onLoad() {
    this.loadRecommend();
    this._loaded = true;
  },

  onShow() {
    if (this._loaded) {
      this.loadRecommend();
    }
  },

  onPullDownRefresh() {
    this.setData({ refreshing: true });
    this.loadRecommend().finally(() => {
      wx.stopPullDownRefresh();
      this.setData({ refreshing: false });
    });
  },

  /**
   * 加载推荐数据
   */
  loadRecommend() {
    this.setData({ loading: true });

    return get('/api/recommend')
      .then(data => {
        // 市场情绪
        const sentiment = this._mapSentiment(data.sentiment);

        // 预警信息
        const warnings = (data.warnings || []).map((w, idx) => ({
          id: idx,
          text: w.text || w.message || w,
          level: w.level || 'warning'
        }));

        // 推荐列表
        const recommendList = (data.list || data.stocks || []).map((item, idx) => ({
          ...item,
          rank: idx + 1,
          rankClass: idx === 0 ? 'rank-gold' : idx === 1 ? 'rank-silver' : idx === 2 ? 'rank-bronze' : 'rank-normal',
          priceText: formatPrice(item.price),
          changePctText: formatPct(item.changePct),
          changePctClass: pctClass(item.changePct),
          totalScoreText: formatNumber(item.totalScore, 1),
          totalScoreClass: scoreClass(item.totalScore),
          totalScoreWidth: Math.min(Math.max(item.totalScore || 0, 0), 100),
          trendScoreText: formatNumber(item.trendScore, 1),
          momentumScoreText: formatNumber(item.momentumScore, 1),
          volumeScoreText: formatNumber(item.volumeScore, 1),
          signals: (item.signals || []).map(s => ({
            text: s.text || s,
            class: this._signalClass(s.text || s)
          }))
        }));

        this.setData({
          loading: false,
          isEmpty: recommendList.length === 0,
          sentiment,
          warnings,
          recommendList
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
   * 映射市场情绪
   */
  _mapSentiment(sentiment) {
    if (!sentiment) return { label: '暂无数据', level: '', class: '' };

    const label = sentiment.label || sentiment.text || sentiment;
    const level = sentiment.level || '';

    let cls = 'tag-blue';
    if (level === 'greed' || level === 'bull' || label.includes('贪婪') || label.includes('乐观')) {
      cls = 'tag-green';
    } else if (level === 'fear' || level === 'bear' || label.includes('恐惧') || label.includes('悲观')) {
      cls = 'tag-red';
    } else if (level === 'extreme_greed' || label.includes('极度贪婪')) {
      cls = 'tag-orange';
    } else if (level === 'extreme_fear' || label.includes('极度恐惧')) {
      cls = 'tag-red';
    }

    return { label, level, class: cls };
  },

  /**
   * 信号标签样式
   */
  _signalClass(signal) {
    if (!signal) return 'tag-blue';
    const s = signal.toLowerCase();
    if (s.includes('买入') || s.includes('buy') || s.includes('看多')) return 'tag-green';
    if (s.includes('卖出') || s.includes('sell') || s.includes('看空')) return 'tag-red';
    if (s.includes('关注') || s.includes('watch') || s.includes('观望')) return 'tag-yellow';
    if (s.includes('突破') || s.includes('breakout')) return 'tag-cyan';
    if (s.includes('回调') || s.includes('pullback')) return 'tag-orange';
    return 'tag-blue';
  },

  /**
   * AI 推荐分析
   */
  goToAIRecommend() {
    wx.navigateTo({ url: '/pages/ai/ai?type=recommend' });
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
