#!/bin/bash
# SonarQube Scanner 安装脚本（用户版本，无需sudo）

echo "🔍 安装 SonarQube Scanner 到用户目录..."

# 检测操作系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "❌ 不支持的操作系统: $OSTYPE"
    exit 1
fi

# 安装目录（用户主目录）
INSTALL_DIR="$HOME/.sonar-scanner"
BIN_DIR="$HOME/.local/bin"

echo "📥 下载 SonarQube Scanner..."

# 创建临时目录
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

# 下载 SonarQube Scanner
SONAR_VERSION="4.8.0.2856"
if [ "$OS" == "linux" ]; then
    SONAR_ZIP="sonar-scanner-cli-${SONAR_VERSION}-linux.zip"
else
    SONAR_ZIP="sonar-scanner-cli-${SONAR_VERSION}-macosx.zip"
fi

echo "正在下载 ${SONAR_ZIP}..."
curl -sSL -o sonar-scanner.zip \
    "https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/${SONAR_ZIP}"

if [ $? -ne 0 ]; then
    echo "❌ 下载失败"
    exit 1
fi

echo "📦 解压..."
unzip -q sonar-scanner.zip

echo "🚀 安装到 $INSTALL_DIR..."
SONAR_DIR=$(ls -d sonar-scanner-*)

# 创建目录
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# 移动文件
mv "$SONAR_DIR"/* "$INSTALL_DIR/"

# 创建符号链接
ln -sf "$INSTALL_DIR/bin/sonar-scanner" "$BIN_DIR/sonar-scanner"

# 清理
cd /
rm -rf "$TMP_DIR"

echo "✅ SonarQube Scanner 安装完成！"
echo ""
echo "安装位置: $INSTALL_DIR"
echo "可执行文件: $BIN_DIR/sonar-scanner"
echo ""

# 添加到PATH（如果需要）
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "⚠️  请将以下内容添加到 ~/.bashrc 或 ~/.zshrc:"
    echo ""
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "然后运行: source ~/.bashrc  (或 source ~/.zshrc)"
    echo ""
fi

# 验证安装
if [ -x "$INSTALL_DIR/bin/sonar-scanner" ]; then
    echo "✅ 验证安装:"
    "$INSTALL_DIR/bin/sonar-scanner" --version
    echo ""
    echo "🎉 现在可以运行扫描了！"
else
    echo "❌ 安装验证失败"
    exit 1
fi
