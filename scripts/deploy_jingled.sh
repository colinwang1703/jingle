#!/bin/bash
# 部署 jingled 服务
INSTALL_DIR="/opt/jingle"
SCRIPT_PATH="$INSTALL_DIR/scripts/jingled"
SERVICE_PATH="$INSTALL_DIR/scripts/jingled.service"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}Please run as root${NC}"
  exit 1
fi

echo -e "${GREEN}Deploying jingled...${NC}"

# 检查文件是否存在
if [ ! -f "$SCRIPT_PATH" ] || [ ! -f "$SERVICE_PATH" ]; then
    echo -e "${RED}Error: Cannot find jingled scripts in $INSTALL_DIR/scripts/${NC}"
    echo "Please ensure you are running this after installing jingle to $INSTALL_DIR"
    exit 1
fi

# 确保脚本有执行权限并修复可能的换行符问题
echo "Fixing permissions and line endings..."
chmod +x "$SCRIPT_PATH"
# 如果存在 dos2unix 则使用，否则使用 sed 尝试修复
if command -v dos2unix &> /dev/null; then
    dos2unix "$SCRIPT_PATH"
else
    sed -i 's/\r$//' "$SCRIPT_PATH"
fi

# 复制服务文件
echo "Installing systemd service..."
cp "$SERVICE_PATH" /etc/systemd/system/

# 重新加载并启动
systemctl daemon-reload
systemctl enable jingled
systemctl restart jingled

echo -e "${GREEN}jingled deployed and started.${NC}"
systemctl status jingled --no-pager
