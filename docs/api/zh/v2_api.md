[English](../en/v2_api.md) | [简体中文](v2_api.md)

---

# V2 API - 高性能查询

**模块**: V2 API (下一代)  
**基础路径**: `/api/v2`  
**版本**: v2.0  
**后端**: SQLite 优化索引  
**性能**: 比 V1 API 快 50-500 倍

---

## 概览

V2 API 使用 SQLite 后端替代文件系统扫描，提供高性能的实验查询。

### V1 vs V2 对比

| 功能 | V1 API | V2 API | 提升 |
|------|--------|--------|------|
| **列出1000个实验** | 5-10 秒 | 50-100 毫秒 | **100倍更快** |
| **复杂过滤** | 不支持 | 支持 | ✓ |
| **分页** | 客户端 | 服务端 | ✓ |
| **搜索** | 不支持 | 全文搜索 | ✓ |
| **排序** | 客户端 | 服务端（索引）| ✓ |

### 何时使用 V2

✅ **使用 V2 API 当**:
- 有 1000+ 个实验
- 需要高级过滤
- 性能是关键
- 需要服务端分页

⚠️ **使用 V1 API 当**:
- 需要向后兼容
- 使用遗留系统
- 偏好基于文件的查询

---

## 端点概览

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/v2/experiments` | 高级过滤列出实验 |
| GET | `/v2/experiments/{exp_id}` | 获取实验详情及指标摘要 |
| GET | `/v2/experiments/{exp_id}/metrics/fast` | 高性能指标检索 |
| POST | `/v2/experiments/batch-delete` | 批量软删除（最多 1000 个）|
| GET | `/v2/analytics/summary` | 聚合分析 |

---

## 列出实验

高级实验列表，支持服务端过滤、分页和排序。

### 请求

```http
GET /api/v2/experiments?{query_params}
```

### 查询参数

#### 过滤参数

| 参数 | 类型 | 描述 | 示例 |
|------|------|------|------|
| `project` | string | 按项目名过滤 | `image_classification` |
| `name` | string | 按实验名过滤 | `resnet_baseline` |
| `status` | string | 按状态过滤（逗号分隔）| `finished,failed` |
| `search` | string | 全文搜索项目/名称/描述 | `resnet` |
| `created_after` | number | Unix 时间戳（包含）| `1704067200` |
| `created_before` | number | Unix 时间戳（包含）| `1704153600` |
| `best_metric_min` | number | 最小最佳指标值 | `0.9` |
| `best_metric_max` | number | 最大最佳指标值 | `1.0` |
| `include_deleted` | boolean | 包含软删除的实验 | `false` |

#### 分页参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `page` | number | 1 | 页码（从 1 开始）|
| `per_page` | number | 50 | 每页结果数（1-1000）|

#### 排序参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `order_by` | string | `created_at` | 排序字段 |
| `order_desc` | boolean | true | 降序（true）或升序（false）|

### 响应

**状态码**: `200 OK`

**响应体**:
```json
{
  "experiments": [...],
  "total": 237,
  "page": 1,
  "per_page": 50,
  "has_next": true,
  "has_prev": false,
  "query_time_ms": 12.34
}
```

---

## 性能基准

测试环境: Windows 10, SSD, 10,000 个实验

| 操作 | V1 API | V2 API | 加速比 |
|------|--------|--------|--------|
| 列出全部 | 5.2 秒 | 52 毫秒 | 100倍 |
| 按项目过滤 | 5.8 秒 | 45 毫秒 | 129倍 |
| 按状态过滤 | 6.1 秒 | 38 毫秒 | 161倍 |
| 按指标排序 | 7.3 秒 | 68 毫秒 | 107倍 |
| 复杂查询 | 8.5 秒 | 85 毫秒 | 100倍 |
| 分页（第2页）| 5.2 秒 | 18 毫秒 | 289倍 |

---

## 最佳实践

### 使用服务端过滤

```python
# ✅ 好: 服务端过滤（快）
response = requests.get('/api/v2/experiments', params={
    'project': 'my_project',
    'status': 'finished'
})

# ❌ 差: 客户端过滤（慢）
all_runs = requests.get('/api/runs').json()
filtered = [r for r in all_runs if r['project'] == 'my_project']
```

---

**最后更新**: 2025-10-14

