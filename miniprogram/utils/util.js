/**
 * 格式化数字，保留指定小数位
 * @param {number} num - 数值
 * @param {number} [digits=2] - 保留小数位数
 * @returns {string} 格式化后的字符串
 */
function formatNumber(num, digits = 2) {
  if (num === null || num === undefined || isNaN(num)) return '--';
  return Number(num).toFixed(digits);
}

/**
 * 格式化金额（亿元/万元自动转换）
 * @param {number} amount - 金额数值
 * @returns {string} 格式化后的金额字符串
 */
function formatAmount(amount) {
  if (amount === null || amount === undefined || isNaN(amount)) return '--';

  const abs = Math.abs(amount);
  const sign = amount < 0 ? '-' : '';

  if (abs >= 100000000) {
    return sign + (abs / 100000000).toFixed(2) + '亿';
  } else if (abs >= 10000) {
    return sign + (abs / 10000).toFixed(2) + '万';
  } else {
    return sign + abs.toFixed(2);
  }
}

/**
 * 根据涨跌幅返回对应的 CSS class
 * @param {number} pct - 涨跌幅百分比（如 5.2 表示涨 5.2%，-3.1 表示跌 3.1%）
 * @returns {string} CSS class 名称
 */
function pctClass(pct) {
  if (pct === null || pct === undefined || isNaN(pct)) return '';
  if (pct > 0) return 'text-green';
  if (pct < 0) return 'text-red';
  return 'text-muted';
}

/**
 * 根据评分返回对应的 CSS class
 * 评分范围 0-100，用于策略推荐等场景
 * @param {number} score - 评分值 (0-100)
 * @returns {string} CSS class 名称
 */
function scoreClass(score) {
  if (score === null || score === undefined || isNaN(score)) return '';
  if (score >= 80) return 'text-green';
  if (score >= 60) return 'text-cyan';
  if (score >= 40) return 'text-yellow';
  if (score >= 20) return 'text-orange';
  return 'text-red';
}

/**
 * 格式化百分比
 * @param {number} pct - 百分比数值
 * @param {number} [digits=2] - 保留小数位数
 * @returns {string} 带正负号和百分号的字符串
 */
function formatPct(pct, digits = 2) {
  if (pct === null || pct === undefined || isNaN(pct)) return '--';
  const sign = pct > 0 ? '+' : '';
  return sign + Number(pct).toFixed(digits) + '%';
}

/**
 * 格式化价格
 * @param {number} price - 价格数值
 * @returns {string} 格式化后的价格字符串
 */
function formatPrice(price) {
  if (price === null || price === undefined || isNaN(price)) return '--';
  return Number(price).toFixed(2);
}

/**
 * 格式化成交量
 * @param {number} volume - 成交量（手）
 * @returns {string} 格式化后的成交量字符串
 */
function formatVolume(volume) {
  if (volume === null || volume === undefined || isNaN(volume)) return '--';
  const abs = Math.abs(volume);
  if (abs >= 10000) {
    return (abs / 10000).toFixed(2) + '万手';
  }
  return abs + '手';
}

/**
 * 防抖函数
 * @param {Function} fn - 需要防抖的函数
 * @param {number} delay - 延迟毫秒数
 * @returns {Function} 防抖后的函数
 */
function debounce(fn, delay = 300) {
  let timer = null;
  return function (...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

/**
 * 节流函数
 * @param {Function} fn - 需要节流的函数
 * @param {number} interval - 间隔毫秒数
 * @returns {Function} 节流后的函数
 */
function throttle(fn, interval = 300) {
  let lastTime = 0;
  return function (...args) {
    const now = Date.now();
    if (now - lastTime >= interval) {
      lastTime = now;
      fn.apply(this, args);
    }
  };
}

/**
 * 日期格式化
 * @param {Date|string|number} date - 日期对象或时间戳
 * @param {string} [fmt='YYYY-MM-DD'] - 格式模板
 * @returns {string} 格式化后的日期字符串
 */
function formatDate(date, fmt = 'YYYY-MM-DD') {
  if (!date) return '';
  const d = new Date(date);
  if (isNaN(d.getTime())) return '';

  const map = {
    'YYYY': d.getFullYear(),
    'MM': String(d.getMonth() + 1).padStart(2, '0'),
    'DD': String(d.getDate()).padStart(2, '0'),
    'HH': String(d.getHours()).padStart(2, '0'),
    'mm': String(d.getMinutes()).padStart(2, '0'),
    'ss': String(d.getSeconds()).padStart(2, '0')
  };

  let result = fmt;
  for (const [key, value] of Object.entries(map)) {
    result = result.replace(key, value);
  }
  return result;
}

module.exports = {
  formatNumber,
  formatAmount,
  pctClass,
  scoreClass,
  formatPct,
  formatPrice,
  formatVolume,
  debounce,
  throttle,
  formatDate
};
