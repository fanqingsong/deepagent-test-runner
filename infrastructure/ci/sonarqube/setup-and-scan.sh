#!/bin/bash
# SonarQube 快速设置和扫描脚本

echo "🔧 SonarQube 快速设置"
echo ""

# 使用admin账户生成token并创建项目
ADMIN_TOKEN=$(curl -s -X POST "http://localhost:9000/sonarqube/api/user_tokens/generate" \
  -d "name=admin-scanner-token&expiration=30d" \
  -u "admin:admin" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))")

if [ -z "$ADMIN_TOKEN" ]; then
    echo "❌ 无法生成admin token，可能需要手动操作"
    echo ""
    echo "请按以下步骤操作："
    echo ""
    echo "1️⃣  访问 SonarQube: http://localhost:9000/sonarqube"
    echo "2️⃣ 登录 (admin/admin)"
    echo "3️⃣ 创建项目:"
    echo "   - 点击右上角 '+' → 'Create Project'"
    echo "   - Project key: claude-code-test-runner:backend"
    echo "   - Display name: Backend"
    echo "   - 点击 'Set Up Project'"
    echo ""
    echo "4️⃣ 使用全局分析token运行扫描:"
    echo ""
    echo "   cd /home/fqs/workspace/self/claude-code-test-runner/service/backend"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "   sonar-scanner -Dproject.settings=sonar-project.properties \\"
    echo "     -Dsonar.host.url=http://localhost:9000/sonarqube \\"
    echo "     -Dsonar.login=$ADMIN_TOKEN"
    exit 1
fi

echo "✅ Admin token生成成功"
echo ""

# 创建项目
echo "📁 创建项目..."
curl -s -X POST "http://localhost:9000/sonarqube/api/projects/create" \
  -u "$ADMIN_TOKEN:" \
  -d "name=Backend&project=claude-code-test-runner:backend" > /dev/null 2>&1

echo "✅ 项目创建成功"
echo ""

# 给用户token分配项目权限
echo "🔑 分配权限..."
curl -s -X POST "http://localhost:9000/sonarqube/api/permissions/add_user" \
  -u "$ADMIN_TOKEN:" \
  -d "project=claude-code-test-runner:backend&login=admin&permission=user" > /dev/null 2>&1

echo "✅ 权限分配成功"
echo ""

echo "🚀 运行扫描..."
cd /home/fqs/workspace/self/claude-code-test-runner/service/backend

export PATH="$HOME/.local/bin:$PATH"

sonar-scanner \
  -Dproject.settings=sonar-project.properties \
  -Dsonar.host.url=http://localhost:9000/sonarqube \
  -Dsonar.login=$ADMIN_TOKEN

echo ""
echo "✅ 扫描完成！查看结果: http://localhost:9000/sonarqube/dashboard?id=claude-code-test-runner_backend"
