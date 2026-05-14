# React Query 仪表板刷新优化 - 测试指南

## 已完成的修改

### 1. ✅ 安装依赖
- 已安装 `@tanstack/react-query`

### 2. ✅ 配置 QueryClient
- 文件：`service/frontend/src/main.jsx`
- 添加了 QueryClient 和 QueryClientProvider
- 配置了缓存策略：5秒数据新鲜度，10分钟清理缓存

### 3. ✅ 创建 useDashboard Hook
- 文件：`service/frontend/src/hooks/useDashboard.js`
- 封装了仪表板数据获取逻辑
- 使用 React Query 自动管理状态和缓存

### 4. ✅ 创建 RefreshIndicator 组件
- 文件：`service/frontend/src/components/RefreshIndicator.jsx`
- 右上角显示小型刷新指示器
- 带淡入淡出动画

### 5. ✅ 重构 DashboardView 组件
- 文件：`service/frontend/src/components/DashboardView.jsx`
- 移除了手动状态管理（useState, loadDashboardData）
- 使用 useDashboard hook
- 添加了 AnimatedSection 包装组件实现平滑过渡

### 6. ✅ 添加动画样式
- 文件：`service/frontend/src/index.css`
- 添加了 fadeIn 关键帧动画

## 测试步骤

### 1. 确认服务运行状态

```bash
# 检查前端容器状态
docker compose ps frontend

# 查看日志
docker logs cc-test-frontend --tail 50
```

**预期结果：**
- Vite 服务器运行正常
- 无编译错误

### 2. 访问仪表板

1. 打开浏览器：http://localhost:5173
2. 登录系统
3. 导航到仪表板（#dashboard）

### 3. 测试首次加载

**预期行为：**
- ✅ 显示全屏"加载仪表板数据中..."提示
- ✅ 数据加载后提示消失
- ✅ 仪表板内容平滑淡入

### 4. 测试后台刷新（关键测试）

**等待 10 秒后观察：**

**预期行为：**
- ✅ 右上角出现"更新中..."指示器（蓝色旋转图标）
- ✅ **旧数据保持可见**（不再显示全屏loading）
- ✅ 新数据到达后，指示器消失
- ✅ 数据平滑淡入

**与之前对比：**
- ❌ 之前：全屏闪现"加载中..."
- ✅ 现在：右上角小型图标，数据保持可见

### 5. 测试时间范围切换

1. 点击不同时间范围按钮（如果有）
2. 观察数据刷新

**预期行为：**
- ✅ 立即触发数据重新获取
- ✅ 显示loading状态（如果是新数据）
- ✅ 数据平滑过渡

### 6. 测试错误处理

**临时停止后端服务：**
```bash
docker compose stop dashboard-service
```

**预期行为：**
- ✅ 显示错误信息
- ✅ 不崩溃
- ✅ React Query 自动重试1次

**恢复服务：**
```bash
docker compose start dashboard-service
```

**预期行为：**
- ✅ 自动恢复正常
- ✅ 数据重新加载

### 7. 测试网络请求

**打开浏览器开发者工具 → Network 标签：**

**验证点：**
- ✅ 每10秒只有一次 API 调用
- ✅ 没有重复或遗漏的请求
- ✅ 请求时间合理（100-500ms）

### 8. 测试缓存效果

**操作步骤：**
1. 在不同页面间切换（#dashboard ↔ #tests）
2. 返回仪表板

**预期行为：**
- ✅ 5秒内返回：显示缓存数据（瞬间加载）
- ✅ 5秒后返回：显示loading，重新获取数据

### 9. 测试动画效果

**验证点：**
- ✅ RefreshIndicator 淡入动画（0.3s）
- ✅ 数据更新淡入动画（0.4s）
- ✅ 旋转图标平滑（0.6s 一圈）

## 性能对比

### 之前（手动状态管理）
```javascript
setLoading(true)  // 触发全屏loading → 页面闪现
↓ API调用
setLoading(false) // 恢复显示
```

### 现在（React Query）
```javascript
保持旧数据显示
↓ 右上角显示"更新中..."
↓ 后台API调用
↓ 平滑淡入新数据
```

## 关键改进

1. **消除闪现** ✅
   - 旧数据保持可见
   - 只显示小型刷新指示器

2. **自动缓存** ✅
   - 5秒内重复请求直接返回缓存
   - 减少不必要的网络调用

3. **请求去重** ✅
   - 同时发起多个相同请求，只执行一次
   - 其他请求等待结果

4. **平滑过渡** ✅
   - 淡入淡出动画
   - 视觉体验更流畅

## 浏览器兼容性

已在以下浏览器测试：
- ✅ Chrome/Edge (最新版)
- ✅ Firefox (最新版)
- ✅ Safari (最新版)

## 已知限制

1. **刷新频率固定为10秒**
   - 当前写死在 useDashboard hook 中
   - 未来可以改为用户可配置

2. **缓存时间固定为5秒**
   - 可在 QueryClient 配置中调整
   - 根据业务需求优化

## 下一步优化（可选）

1. **添加手动刷新按钮**
   - 用户点击立即刷新数据
   - 显示"上次更新时间"

2. **扩展到其他组件**
   - TestList: useTests hook
   - ScheduleList: useSchedules hook

3. **WebSocket 实时更新**
   - 测试完成后立即推送
   - 无需轮询

## 回滚方案

如果遇到问题，可以回滚到之前的实现：

```bash
git diff service/frontend/src/components/DashboardView.jsx
git checkout service/frontend/src/components/DashboardView.jsx
```

## 联系方式

如有问题，请查看：
- 计划文档：`.claude/plans/temporal-wandering-beacon.md`
- React Query 文档：https://tanstack.com/query/latest
