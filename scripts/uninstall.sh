#!/bin/bash

# 配置变量
INSTALL_DIR="/opt/jingle"
SERVICE_MAIN="jingle-main.service"
SERVICE_WEB="jingle-web.service"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${RED}=== Jingle 卸载脚本 ===${NC}"

# 1. 检查是否为 root 运行
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}请使用 sudo 运行此脚本${NC}"
  exit 1
fi

# 2. 停止并禁用服务
echo -e "${GREEN}正在停止服务...${NC}"
if systemctl is-active --quiet $SERVICE_MAIN; then
    systemctl stop $SERVICE_MAIN
    echo "停止 $SERVICE_MAIN"
fi
if systemctl is-active --quiet $SERVICE_WEB; then
    systemctl stop $SERVICE_WEB
    echo "停止 $SERVICE_WEB"
fi

echo -e "${GREEN}正在禁用服务...${NC}"
systemctl disable $SERVICE_MAIN 2>/dev/null
systemctl disable $SERVICE_WEB 2>/dev/null

# 3. 删除服务文件
echo -e "${GREEN}删除系统服务文件...${NC}"
rm -f "/etc/systemd/system/$SERVICE_MAIN"
rm -f "/etc/systemd/system/$SERVICE_WEB"

systemctl daemon-reload
echo "Systemd 配置已重载"

# 4. 删除程序文件（可选）
echo -e "${YELLOW}是否删除安装目录 $INSTALL_DIR 及其所有内容（包括配置文件和日志）?${NC}"
read -p "请输入 (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        echo -e "${GREEN}已彻底删除 $INSTALL_DIR${NC}"
    else
        echo "目录 $INSTALL_DIR 不存在"
    fi
else
    echo "保留安装目录 $INSTALL_DIR"
fi

echo -e "${GREEN}=== 卸载完成 ===${NC}"
