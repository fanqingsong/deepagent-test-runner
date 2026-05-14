#!/bin/bash
# SonarQube Scanner 安装脚本

echo "🔍 检测系统..."

# 检测操作系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "❌ 不支持的操作系统: $OSTYPE"
    exit 1
fi

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

echo "🚀 安装到 /usr/local/bin..."
SONAR_DIR=$(ls -d sonar-scanner-*)

# 移动到 /usr/local
sudo mv "$SONAR_DIR" /usr/local/sonar-scanner
sudo ln -sf /usr/local/sonar-scanner/bin/sonar-scanner /usr/local/bin/sonar-scanner

# 清理
cd /
rm -rf "$TMP_DIR"

echo "✅ SonarQube Scanner 安装完成！"
echo ""
echo "验证安装:"
sonar-scanner --version
echo ""
echo "现在可以运行扫描:"
echo "  cd service/backend"
echo "  sonar-scanner -Dproject.settings=sonar-project.properties \\"
echo "    -Dsonar.host.url=http://localhost:9000/sonarqube \\"
echo "    -Dsonar.login=admin"
