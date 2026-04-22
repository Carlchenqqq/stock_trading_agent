const app = getApp();

function request(url, method = 'GET', data = null) {
  return new Promise((resolve, reject) => {
    wx.showNavigationBarLoading();
    wx.request({
      url: app.globalData.baseUrl + url,
      method,
      data,
      header: { 'content-type': 'application/json' },
      success(res) {
        if (res.statusCode === 200 && res.data && res.data.success) {
          resolve(res.data.data);
        } else {
          const msg = (res.data && res.data.error) || '请求失败';
          wx.showToast({ title: msg, icon: 'none' });
          reject(new Error(msg));
        }
      },
      fail(err) {
        wx.showToast({ title: '网络连接失败', icon: 'none' });
        reject(err);
      },
      complete() {
        wx.hideNavigationBarLoading();
      }
    });
  });
}

/**
 * GET 请求快捷方法
 * @param {string} url - 请求路径
 * @returns {Promise}
 */
function get(url) {
  return request(url, 'GET');
}

/**
 * POST 请求快捷方法
 * @param {string} url - 请求路径
 * @param {Object} data - 请求体数据
 * @returns {Promise}
 */
function post(url, data) {
  return request(url, 'POST', data);
}

module.exports = { request, get, post };
