const { get } = require('../../utils/request');
const { formatPrice, formatPct, formatNumber, pctClass, scoreClass } = require('../../utils/util');

Page({
  data: {
    loading: true,
    stockCode: '',
    stockName: '',

    // 股票AI分析结果
    stockAnalysis: null,

    // AI仪表盘数据
    aiStatus: {
      provider: '',
      model: '',
      configured: false
    },
    analysisResult: '',
    analysisLoading: false,
    analysisType: ''
  },

  onLoad(options) {
    if (options && options.code) {
      this.setData({ stockCode: decodeURIComponent(options.code) });
      this.loadStockAI();
    } else {
      this.loadAIStatus();
    }
  },

  onPullDownRefresh() {
    const p = this.data.stockCode ? this.loadStockAI() : this.loadAIStatus();
    p.finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 加载股票AI分析
   */
  loadStockAI() {
    if (!this.data.stockCode) return Promise.reject(new Error('缺少股票代码'));

    this.setData({ loading: true });

    return get('/api/ai/stock/' + this.data.stockCode)
      .then(data => {
        const analysis = {
          ...data,
          priceText: formatPrice(data.price),
          changePctText: formatPct(data.change_pct),
          changePctClass: pctClass(data.change_pct),
          scoreText: formatNumber(data.score, 1),
          scoreClass: scoreClass(data.score)
        };

        this.setData({
          loading: false,
          stockName: data.name || '',
          stockAnalysis: analysis
        });
      })
      .catch(() => {
        this.setData({ loading: false });
      });
  },

  /**
   * 加载AI状态
   */
  loadAIStatus() {
    this.setData({ loading: true });

    return get('/api/ai/status')
      .then(data => {
        this.setData({
          loading: false,
          aiStatus: {
            provider: data.provider || '--',
            model: data.model || '--',
            configured: !!data.configured
          }
        });
      })
      .catch(() => {
        this.setData({ loading: false });
      });
  },

  /**
   * 市场分析
   */
  loadAIMarket() {
    this.setData({ analysisLoading: true, analysisType: '市场分析', analysisResult: '' });

    return get('/api/ai/market')
      .then(data => {
        const result = typeof data === 'string' ? data : (data.analysis || data.result || JSON.stringify(data));
        this.setData({ analysisLoading: false, analysisResult: result });
      })
      .catch(() => {
        this.setData({ analysisLoading: false, analysisResult: '分析请求失败，请稍后重试。' });
      });
  },

  /**
   * 策略分析
   */
  loadAIStrategy() {
    this.setData({ analysisLoading: true, analysisType: '策略分析', analysisResult: '' });

    return get('/api/ai/strategy')
      .then(data => {
        const result = typeof data === 'string' ? data : (data.analysis || data.result || JSON.stringify(data));
        this.setData({ analysisLoading: false, analysisResult: result });
      })
      .catch(() => {
        this.setData({ analysisLoading: false, analysisResult: '分析请求失败，请稍后重试。' });
      });
  },

  /**
   * 推荐分析
   */
  loadAIRecommend() {
    this.setData({ analysisLoading: true, analysisType: '推荐分析', analysisResult: '' });

    return get('/api/ai/recommend')
      .then(data => {
        const result = typeof data === 'string' ? data : (data.analysis || data.result || JSON.stringify(data));
        this.setData({ analysisLoading: false, analysisResult: result });
      })
      .catch(() => {
        this.setData({ analysisLoading: false, analysisResult: '分析请求失败，请稍后重试。' });
      });
  }
});
