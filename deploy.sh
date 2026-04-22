#!/bin/bash
# ============================================
# 股票交易Agent 一键部署脚本
# 适用于：腾讯云CVM / TencentOS / CentOS
# ============================================

set -e

echo "=========================================="
echo "  股票交易Agent 一键部署"
echo "=========================================="

# 1. 更新系统
echo ""
echo "[1/6] 更新系统..."
yum update -y

# 2. 安装依赖
echo ""
echo "[2/6] 安装Python3和Nginx..."
yum install -y python3 python3-pip python3-devel nginx git

# 3. 创建虚拟环境并安装依赖
echo ""
echo "[3/6] 安装Python依赖..."
cd /root/stock_trading_agent
python3 -m venv venv
source venv/bin/activate
pip install flask gunicorn requests akshare python-dotenv

# 4. 配置Nginx
echo ""
echo "[4/6] 配置Nginx..."
cat > /etc/nginx/conf.d/stock_agent.conf << 'NGINX'
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

nginx -t
systemctl restart nginx
systemctl enable nginx

# 5. 配置Systemd服务
echo ""
echo "[5/6] 配置开机自启..."
cat > /etc/systemd/system/stock_agent.service << 'SERVICE'
[Unit]
Description=Stock Trading Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/stock_trading_agent
Environment="PATH=/root/stock_trading_agent/venv/bin"
ExecStart=/root/stock_trading_agent/venv/bin/gunicorn app:app --workers 2 --timeout 120 --bind 0.0.0.0:5000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl start stock_agent
systemctl enable stock_agent

# 6. 放行防火墙
echo ""
echo "[6/6] 放行防火墙..."
firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true

echo ""
echo "=========================================="
echo "  部署完成！"
echo "  访问地址: http://118.195.241.154"
echo "=========================================="
echo ""
echo "常用命令："
echo "  查看日志: journalctl -u stock_agent -f"
echo "  重启服务: systemctl restart stock_agent"
echo "  更新代码: cd ~/stock_trading_agent && git pull && systemctl restart stock_agent"
