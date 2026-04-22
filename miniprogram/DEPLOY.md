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

### 1.2 本地项目准备

确保你的 Flask 后端项目结构如下：

```
stock_trading_agent/
├── backend/
│   ├── app.py          # Flask 主应用
│   ├── requirements.txt
│   └── ...
├── miniprogram/
│   ├── app.js
│   ├── app.json
│   ├── pages/
│   ├── images/
│   └── ...
└── ...
```

---

## 2. 部署 Flask 后端到 PythonAnywhere

### 2.1 上传代码到 PythonAnywhere

**方式一：通过 Git 克隆（推荐）**

在 PythonAnywhere 的 Bash Console 中执行：

```bash
# 先在 GitHub 上创建仓库并推送代码
# 然后在 PythonAnywhere 上克隆
cd ~
git clone https://github.com/你的用户名/stock_trading_agent.git
```

**方式二：手动上传**

1. 将后端文件打包为 zip
2. 在 PythonAnywhere 页面点击「Files」标签
3. 上传 zip 文件并解压

### 2.2 创建虚拟环境并安装依赖

在 PythonAnywhere 的 Bash Console 中执行：

```bash
# 创建虚拟环境
cd ~/stock_trading_agent/backend
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

> **注意**：PythonAnywhere 免费版预装的包有限，如果安装超时，可以分批安装核心依赖：
> ```bash
> pip install flask flask-cors requests
> ```

### 2.3 创建 WSGI 文件

在 PythonAnywhere 的「Files」页面，找到你的工作目录，创建 `wsgi.py` 文件：

```python
# ~/stock_trading_agent/backend/wsgi.py
import sys
import os

# 添加项目路径
project_home = '/home/你的用户名/stock_trading_agent/backend'
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
   /home/你的用户名/stock_trading_agent/backend/wsgi.py
   ```
5. 在「Virtualenv」中填入：
   ```
   /home/你的用户名/stock_trading_agent/backend/venv
   ```
6. 点击「Save」保存

### 2.5 验证部署

保存配置后，PythonAnywhere 会自动重载应用。访问：

```
https://你的用户名.pythonanywhere.com
```

如果页面正常显示 API 响应，说明部署成功。

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
# 设置智谱 AI (GLM) API 密钥
echo 'export GLM_API_KEY="你的智谱AI密钥"' >> ~/.bashrc

# 设置 Kimi (Moonshot) API 密钥（可选）
echo 'export KIMI_API_KEY="你的Kimi密钥"' >> ~/.bashrc

# 使配置生效
source ~/.bashrc
```

### 4.2 在 PythonAnywhere Web 应用中配置环境变量

由于 Web 应用不会自动加载 `.bashrc`，需要在 WSGI 文件或应用代码中手动加载：

**方式一：在 wsgi.py 中加载（推荐）**

```python
# 在 wsgi.py 文件顶部添加
import os
from dotenv import load_dotenv

# 加载 .env 文件
env_path = os.path.join(project_home, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
```

**方式二：通过 PythonAnywhere 的 Virtualenv 配置**

1. 在「Web」标签页找到「Virtualenv」部分
2. 点击虚拟环境路径旁的「Enter virtualenv」链接
3. 在打开的 Bash 中设置环境变量：
   ```bash
   echo 'export GLM_API_KEY="你的智谱AI密钥"' > venv/bin/activate.d/env_vars.sh
   echo 'export KIMI_API_KEY="你的Kimi密钥"' >> venv/bin/activate.d/env_vars.sh
   mkdir -p venv/bin/activate.d
   ```

**方式三：使用 .env 文件**

1. 在 `backend/` 目录下创建 `.env` 文件：
   ```
   GLM_API_KEY=你的智谱AI密钥
   KIMI_API_KEY=你的Kimi密钥
   ```
2. 在 `requirements.txt` 中添加 `python-dotenv`
3. 在应用入口加载环境变量：
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

> **安全提示**：不要将 `.env` 文件提交到 Git 仓库。确保 `.gitignore` 中包含 `.env`。

### 4.3 获取 API 密钥

| 服务商 | 注册地址 | 用途 |
|--------|---------|------|
| 智谱 AI (GLM) | [https://open.bigmodel.cn](https://open.bigmodel.cn) | 主力对话模型 |
| Kimi (Moonshot) | [https://platform.moonshot.cn](https://platform.moonshot.cn) | 备用对话模型 |

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

1. 检查 WSGI 文件路径是否正确
2. 检查虚拟环境路径是否正确
3. 查看 Error Log（在「Web」页面底部）：
   ```
   /home/你的用户名/logs/user.your_username.pythonanywhere.com.error.log
   ```
4. 确保 Flask 应用对象命名为 `application`

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
cd ~/stock_trading_agent/backend
source venv/bin/activate
pip install -r requirements.txt
```

然后在「Web」页面点击「Reload」。

---

## 附录：快速部署命令汇总

```bash
# 1. 克隆代码
cd ~
git clone https://github.com/你的用户名/stock_trading_agent.git

# 2. 创建虚拟环境并安装依赖
cd ~/stock_trading_agent/backend
python3 -m venv venv
source venv/bin/activate
pip install flask flask-cors requests python-dotenv

# 3. 配置环境变量
echo 'export GLM_API_KEY="你的密钥"' >> ~/.bashrc
source ~/.bashrc

# 4. 创建 .env 文件
cat > ~/stock_trading_agent/backend/.env << 'EOF'
GLM_API_KEY=你的智谱AI密钥
KIMI_API_KEY=你的Kimi密钥
EOF

# 5. 在 PythonAnywhere Web 页面配置 WSGI 路径后点击 Reload
```
