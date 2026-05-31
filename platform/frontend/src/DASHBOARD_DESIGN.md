# Dashboard 仪表板设计方案

## 1. 组件架构

```
App.jsx
├── Navigation (新增) - 导航切换
├── DashboardView (新增) - 仪表板主视图
│   ├── StatsCards (新增) - 统计卡片
│   ├── ChartsSection (新增) - 图表区域
│   │   ├── TrendChart (新增) - 趋势图
│   │   ├── PassRateChart (新增) - 通过率饼图
│   │   └── DurationChart (新增) - 时长柱状图
│   └── RecentTests (新增) - 最近测试列表
└── TestManagementView (现有) - 测试管理
    ├── TestList (现有)
    └── TestForm (现有)
```

## 2. 数据流设计

### API 端点
- `GET /api/dashboard` - 仪表板统计数据
- `GET /api/test-runs` - 测试运行历史
- `GET /api/v1/test-definitions/` - 测试定义

### 状态管理
```jsx
// Dashboard 状态
{
  stats: {
    totalRuns: number,
    passRate: number,
    avgDuration: number,
    totalTests: number
  },
  trends: [
    { date: '2024-01-01', passed: 10, failed: 2, duration: 45 }
  ],
  recentRuns: [
    { id, test_name, status, duration, timestamp }
  ],
  timeRange: '7d' | '30d' | '90d'
}
```

## 3. UI 布局设计

### 仪表板视图布局
```
+------------------------------------------+
|  导航栏: [Dashboard] [Test Management]   |
+------------------------------------------+
|  统计卡片区域                             |
|  [总运行数] [通过率] [平均时长] [测试数]  |
+------------------------------------------+
|  时间范围选择器: [7天] [30天] [90天]      |
+------------------------------------------+
|  图表区域                                 |
|  +----------------+  +----------------+  |
|  |  趋势折线图     |  |  通过率饼图    |  |
|  +----------------+  +----------------+  |
|  +----------------+                     |
|  |  时长柱状图     |                     |
|  +----------------+                     |
+------------------------------------------+
|  最近测试运行列表                         |
|  [测试名称] [状态] [时长] [时间]          |
+------------------------------------------+
```

## 4. 组件功能规格

### StatsCards
- 4个统计卡片：总运行数、通过率、平均时长、测试总数
- 颜色编码：绿色(成功)、红色(失败)、蓝色(信息)
- 响应式布局：移动端单列，桌面端4列

### TrendChart
- 折线图显示测试执行趋势
- X轴：日期，Y轴：测试数量
- 两条线：通过数量、失败数量
- 支持时间范围切换

### PassRateChart
- 饼图显示通过/失败比例
- 百分比标签
- 颜色：绿色(通过)、红色(失败)

### DurationChart
- 柱状图显示平均执行时长
- X轴：日期，Y轴：时长(秒)
- 颜色渐变

### RecentTests
- 表格显示最近测试运行
- 列：测试名称、状态、时长、时间戳
- 状态徽章：成功(绿色)、失败(红色)、运行中(蓝色)

## 5. 技术实现

### 依赖库
```json
{
  "chart.js": "^4.4.0",
  "react-chartjs-2": "^5.2.0"
}
```

### 样式方案
- 使用内联样式保持一致性
- 响应式设计：媒体查询
- 颜色主题：Material Design 配色

### API 扩展
```javascript
// api.js 新增函数
export const getDashboardData = async (days = 30) => { }
export const getTestRuns = async (limit = 20) => { }
export const getTestStats = async () => { }
```

## 6. 实现优先级

1. ✅ 基础架构和导航
2. ✅ 统计卡片组件
3. ✅ API 扩展和数据获取
4. ✅ 趋势图表组件
5. ✅ 通过率和时长图表
6. ✅ 最近测试列表
7. ✅ 响应式优化

## 7. 数据模拟

由于当前系统没有测试数据，需要：
- 提供模拟数据用于开发
- 在实际有数据时切换到真实 API
- 空状态处理和提示
