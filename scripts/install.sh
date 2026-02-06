#!/bin/bash

# 配置变量
INSTALL_DIR="/opt/jingle"
VENV_DIR="$INSTALL_DIR/env"
USER_RUN="root" # 建议使用 root 运行以确保音频设备访问权限，或者使用 audio 组用户

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Jingle 部署脚本 ===${NC}"

# 1. 检查是否为 root 运行
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}请使用 sudo 运行此脚本${NC}"
  exit 1
fi

# 2. 检查安装目录
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}错误: 目录 $INSTALL_DIR 不存在。请确保你在这个目录下运行脚本或已正确克隆项目。${NC}"
    # 尝试自动修正：如果当前目录就是代码目录，则提示用户移动或创建链接，这里假设用户已经放好了
    echo "当前目录: $(pwd)"
    read -p "是否将当前目录内容复制到 $INSTALL_DIR ? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mkdir -p "$INSTALL_DIR"
        cp -r ./* "$INSTALL_DIR/"
        echo "已复制文件到 $INSTALL_DIR"
    else
        exit 1
    fi
fi

cd "$INSTALL_DIR"

# 3. 设置 Python 虚拟环境
echo -e "${GREEN}检查 Python 虚拟环境...${NC}"
if [ ! -d "$VENV_DIR" ]; then
    echo "创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo -e "${RED}创建虚拟环境失败，请确保已安装 python3-venv${NC}"
        echo "尝试安装: apt-get install python3-venv"
        apt-get update && apt-get install -y python3-venv
        python3 -m venv "$VENV_DIR"
    fi
else
    echo "虚拟环境已存在"
fi

# 4. 安装依赖
echo -e "${GREEN}安装依赖...${NC}"
"$VENV_DIR/bin/pip" install --upgrade pip
if [ -f "requirements.txt" ]; then
    "$VENV_DIR/bin/pip" install -r requirements.txt
else
    echo "requirements.txt 不存在，尝试直接安装核心依赖..."
    "$VENV_DIR/bin/pip" install flask pygame
fi

# 5. 创建 Systemd 服务文件
echo -e "${GREEN}配置系统服务...${NC}"

# 主程序服务
cat > /etc/systemd/system/jingle-main.service << EOF
[Unit]
Description=Jingle Bell Main Service
After=network.target sound.target

[Service]
Type=simple
User=$USER_RUN
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python3 $INSTALL_DIR/app/main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Web配置服务
cat > /etc/systemd/system/jingle-web.service << EOF
[Unit]
Description=Jingle Bell Web Config Service
After=network.target

[Service]
Type=simple
User=$USER_RUN
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python3 $INSTALL_DIR/app/web.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 6. 启动服务
echo -e "${GREEN}启动服务...${NC}"
systemctl daemon-reload

systemctl enable jingle-main.service
systemctl enable jingle-web.service

systemctl restart jingle-main.service
systemctl restart jingle-web.service

echo -e "${GREEN}=== 部署完成 ===${NC}"
echo "查看主程序状态: systemctl status jingle-main"
echo "查看Web服务状态: systemctl status jingle-web"
echo "查看日志: journalctl -u jingle-main -f"
echo "Web配置地址: http://<IP>:5000"
