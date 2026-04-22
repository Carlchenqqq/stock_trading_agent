# 微信小程序部署指南

本文档介绍如何将「智能交易 Agent」微信小程序的后端 Flask 服务部署到 PythonAnywhere（免费版），以及如何配置小程序前端和 AI API 密钥。

---

## 目录

1. [环境准备](#1-环境准备)
2. [部署 Flask 后端到 PythonAnywhere](#2-部署-flask-后端到-pythonanywhere)
3. [配置小程序 baseUrl](#3-配置小程序-baseurl)
4. [配置 AI API 密钥](#4-配置-ai-api-密钥)
5. [常见问题](#5-常见问题)

---

## 1. 环境准备

### 1.1 注册 PythonAnywhere 账号

1. 访问 [https://www.pythonanywhere.com](https://www.pythonanywhere.com)
2. 点击「Sign up」注册免费账号（免费版支持一个 Web 应用）
3. 通过邮箱验证完成注册

### 1.2 本地项目结构

项目结构如下（`app.py` 在根目录下）：

```
stock_trading_agent/
├── app.py                # Flask 主应用（Web仪表盘 + API后端）
├── models.py             # 统一数据模型
├── akshare_adapter.py    # AKShare数据适配器
├── hybrid_agent.py       # 交易Agent核心逻辑
├── trading_rules.py      # A股交易规则引擎
├── stock_recommender.py  # 股票推荐引擎
├── ai_analyzer.py        # AI分析模块
├── trading_strategies.py # 交易策略
├── market_analyzer.py    # 市场分析
├── agent.py              # 交易费用计算
├── data_adapter.py       # 数据适配器基类
├── real_data_agent.py    # 真实数据Agent
├── main.py               # 命令行入口
├── requirements.txt      # Python依赖
├── templates/
│   └── index.html        # Web仪表盘前端页面
├── miniprogram/          # 微信小程序前端
│   ├── app.js
│   ├── app.json
│   ├── app.wxss
│   ├── pages/
│   ├── images/
│   ├── utils/
│   └── DEPLOY.md
└── .gitignore
```

---

## 2. 部署 Flask 后端到 PythonAnywhere

### 2.1 上传代码到 PythonAnywhere

**方式一：通过 Git 克隆（推荐）**

在 PythonAnywhere 的 Bash Console 中执行：

```bash
cd ~
git clone https://github.com/Carlchenqqq/stock_trading_agent.git
```

**方式二：手动上传**

1. 将项目文件打包为 zip
2. 在 PythonAnywhere 页面点击「Files」标签
3. 上传 zip 文件并解压

### 2.2 创建虚拟环境并安装依赖

在 PythonAnywhere 的 Bash Console 中执行：

```bash
# 创建虚拟环境
cd ~/stock_trading_agent
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

> **注意**：PythonAnywhere 免费版预装的包有限，如果安装超时，可以分批安装核心依赖：
> ```bash
> pip install flask requests akshare
> ```

### 2.3 创建 WSGI 文件

在项目根目录下创建 `wsgi.py` 文件：

```python
# ~/stock_trading_agent/wsgi.py
import sys
import os

# 添加项目路径
project_home = '/home/你的用户名/stock_trading_agent'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 激活虚拟环境
activate_this = os.path.join(project_home, 'venv/bin/activate_this.py')
with open(activate_this) as f:
    exec(f.read(), {'__file__': activate_this})

# 导入 Flask 应用
from app import app as application
```

> **重要**：将 `你的用户名` 替换为你的 PythonAnywhere 用户名。Flask 应用对象必须命名为 `application`。

### 2.4 配置 Web 应用

1. 在 PythonAnywhere 页面点击「Web」标签
2. 点击「Add a new web app」
3. 选择「Python 3.10」（或最新可用版本）
4. 在「WSGI configuration file」中填入：
   ```
   /home/你的用户名/stock_trading_agent/wsgi.py
   ```
5. 在「Virtualenv」中填入：
   ```
   /home/你的用户名/stock_trading_agent/venv
   ```
6. 在「Code directory」中填入：
   ```
   /home/你的用户名/stock_trading_agent
   ```
7. 点击「Save」保存

### 2.5 验证部署

保存配置后，PythonAnywhere 会自动重载应用。访问：

```
https://你的用户名.pythonanywhere.com
```

如果页面正常显示 Web 仪表盘，说明部署成功。

### 2.6 后续更新代码

每次修改代码后，在 Bash Console 中执行：

```bash
cd ~/stock_trading_agent
git pull origin main
```

然后在「Web」页面点击「Reload」按钮重载应用。

---

## 3. 配置小程序 baseUrl

### 3.1 修改 app.js

打开 `miniprogram/app.js`，将 `baseUrl` 修改为你的 PythonAnywhere 地址：

```javascript
App({
  globalData: {
    // 将下面的地址替换为你的 PythonAnywhere 地址
    baseUrl: 'https://你的用户名.pythonanywhere.com',
    userInfo: null
  },
  onLaunch() {
    console.log('股票交易Agent小程序启动');
  }
});
```

### 3.2 配置服务器域名

微信小程序要求所有网络请求必须使用 HTTPS，并且域名需要在小程序管理后台配置：

1. 登录 [微信公众平台](https://mp.weixin.qq.com)
2. 进入「开发」->「开发管理」->「开发设置」
3. 在「服务器域名」中，将 `request合法域名` 设置为：
   ```
   https://你的用户名.pythonanywhere.com
   ```

> **注意**：PythonAnywhere 的免费版自带 HTTPS 证书，无需额外配置 SSL。

### 3.3 开发阶段跳过域名校验

在开发阶段，可以在微信开发者工具中勾选：

「详情」->「本地设置」->「不校验合法域名、web-view（业务域名）、TLS版本以及HTTPS证书」

这样可以在本地调试时使用任意地址。

---

## 4. 配置 AI API 密钥

### 4.1 在 PythonAnywhere 上设置环境变量

在 PythonAnywhere 的 Bash Console 中执行：

```bash
# 设置 AI API 密钥（三选一，或都设置）
echo 'export AI_API_KEY="你的API密钥"' >> ~/.bashrc
echo 'export AI_API_BASE="https://open.bigmodel.cn/api/paas/v4"' >> ~/.bashrc
echo 'export AI_MODEL="glm-4-flash"' >> ~/.bashrc

# 使配置生效
source ~/.bashrc
```

### 4.2 在 PythonAnywhere Web 应用中配置环境变量

由于 Web 应用不会自动加载 `.bashrc`，推荐使用 `.env` 文件：

1. 在项目根目录 `stock_trading_agent/` 下创建 `.env` 文件：
   ```
   AI_API_KEY=你的API密钥
   AI_API_BASE=https://open.bigmodel.cn/api/paas/v4
   AI_MODEL=glm-4-flash
   ```
2. 在 `requirements.txt` 中添加 `python-dotenv`
3. 在 `app.py` 入口处加载环境变量：
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

> **安全提示**：不要将 `.env` 文件提交到 Git 仓库。`.gitignore` 中已包含 `.env`。

### 4.3 获取 API 密钥

| 服务商 | 注册地址 | API Base | 模型 |
|--------|---------|----------|------|
| 智谱 AI (GLM) | [https://open.bigmodel.cn](https://open.bigmodel.cn) | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash`（免费） |
| Kimi (Moonshot) | [https://platform.moonshot.cn](https://platform.moonshot.cn) | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| DeepSeek | [https://platform.deepseek.com](https://platform.deepseek.com) | `https://api.deepseek.com/v1` | `deepseek-chat` |

注册后在控制台创建 API Key 即可使用。

---

## 5. 常见问题

### Q1: PythonAnywhere 免费版有什么限制？

- **CPU 时间**：每天 100 秒 CPU 时间（Web 应用）
- **内存**：512MB
- **磁盘空间**：512MB
- **不支持 WebSocket**
- **不支持自定义域名**（免费版）

对于个人开发和小规模使用，免费版足够。

### Q2: 部署后页面报 502 错误？

1. 检查 WSGI 文件路径是否正确（`/home/用户名/stock_trading_agent/wsgi.py`）
2. 检查虚拟环境路径是否正确（`/home/用户名/stock_trading_agent/venv`）
3. 检查 Code directory 是否正确（`/home/用户名/stock_trading_agent`）
4. 查看 Error Log（在「Web」页面底部）：
   ```
   /home/你的用户名/logs/user.your_username.pythonanywhere.com.error.log
   ```
5. 确保 Flask 应用对象命名为 `application`

### Q3: 小程序请求失败？

1. 确认 `baseUrl` 使用 HTTPS（不是 HTTP）
2. 确认已在微信公众平台配置服务器域名
3. 在开发者工具中检查网络请求详情
4. 确认后端 API 路由正确且返回 JSON 格式

### Q4: 如何查看应用日志？

在 PythonAnywhere 的「Web」页面底部：
- **Access Log**：访问日志
- **Error Log**：错误日志

也可以在 Bash Console 中查看：
```bash
tail -f ~/logs/user.你的用户名.pythonanywhere.com.error.log
```

### Q5: 如何更新依赖？

```bash
cd ~/stock_trading_agent
source venv/bin/activate
pip install -r requirements.txt
```

然后在「Web」页面点击「Reload」。

---

## 附录：快速部署命令汇总

```bash
# 1. 克隆代码
cd ~
git clone https://github.com/Carlchenqqq/stock_trading_agent.git

# 2. 创建虚拟环境并安装依赖
cd ~/stock_trading_agent
python3 -m venv venv
source venv/bin/activate
pip install flask requests akshare python-dotenv

# 3. 配置环境变量
echo 'export AI_API_KEY="你的密钥"' >> ~/.bashrc
echo 'export AI_API_BASE="https://open.bigmodel.cn/api/paas/v4"' >> ~/.bashrc
echo 'export AI_MODEL="glm-4-flash"' >> ~/.bashrc
source ~/.bashrc

# 4. 创建 .env 文件（Web应用会读取此文件）
cat > ~/stock_trading_agent/.env << 'EOF'
AI_API_KEY=你的API密钥
AI_API_BASE=https://open.bigmodel.cn/api/paas/v4
AI_MODEL=glm-4-flash
EOF

# 5. 在 PythonAnywhere Web 页面配置：
#    WSGI: /home/你的用户名/stock_trading_agent/wsgi.py
#    Virtualenv: /home/你的用户名/stock_trading_agent/venv
#    Code: /home/你的用户名/stock_trading_agent
#    然后点击 Reload
```
