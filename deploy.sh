#!/bin/bash
# ============================================
# 股票交易Agent 一键部署脚本
# 适用于：腾讯云CVM / Ubuntu系统
# ============================================

set -e

echo "=========================================="
echo "  股票交易Agent 一键部署"
echo "=========================================="

# 1. 更新系统
echo ""
echo "[1/6] 更新系统..."
apt update -y && apt upgrade -y

# 2. 安装依赖
echo ""
echo "[2/6] 安装Python3和Nginx..."
apt install -y python3 python3-pip python3-venv nginx git

# 3. 克隆代码
echo ""
echo "[3/6] 克隆代码..."
cd /opt
if [ -d "/opt/stock_trading_agent" ]; then
    cd /opt/stock_trading_agent && git pull origin main
else
    git clone https://github.com/Carlchenqqq/stock_trading_agent.git
fi

# 4. 创建虚拟环境并安装依赖
echo ""
echo "[4/6] 安装Python依赖..."
cd /opt/stock_trading_agent
python3 -m venv venv
source venv/bin/activate
pip install flask gunicorn requests akshare python-dotenv

# 5. 配置Nginx
echo ""
echo "[5/6] 配置Nginx..."
cat > /etc/nginx/sites-available/stock_trading_agent << 'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 120s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/stock_trading_agent /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx

# 6. 配置Systemd服务（开机自启）
echo ""
echo "[6/6] 配置开机自启..."
cat > /etc/systemd/system/stock_agent.service << 'SERVICE'
[Unit]
Description=Stock Trading Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/stock_trading_agent
Environment="PATH=/opt/stock_trading_agent/venv/bin"
ExecStart=/opt/stock_trading_agent/venv/bin/gunicorn app:app --workers 2 --timeout 120 --bind 0.0.0.0:5000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl start stock_agent
systemctl enable stock_agent

echo ""
echo "=========================================="
echo "  部署完成！"
echo "  访问地址: http://118.195.241.154"
echo "=========================================="
echo ""
echo "常用命令："
echo "  查看日志: journalctl -u stock_agent -f"
echo "  重启服务: systemctl restart stock_agent"
echo "  更新代码: cd /opt/stock_trading_agent && git pull && systemctl restart stock_agent"
