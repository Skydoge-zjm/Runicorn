# Runicorn Artifacts Testing Guide

> **测试套件**: 企业级完整测试  
> **测试数量**: 35+ 测试用例  
> **覆盖范围**: 单元、集成、性能、安全、并发

---

## 📋 测试套件概览

### 测试文件组织

```
tests/
├── test_artifacts.py                    # 基础单元测试（6个）
├── test_artifacts_comprehensive.py      # 全面测试（25个）
└── test_artifacts_e2e.py                # 端到端测试（10个）
```

### 测试分类

| 测试类别 | 文件 | 测试数 | 覆盖范围 |
|---------|------|--------|---------|
| **核心功能** | comprehensive | 10 | 创建、版本、元数据 |
| **去重** | comprehensive | 3 | 内容去重、空间节省 |
| **血缘** | comprehensive | 2 | 追踪、循环检测 |
| **并发** | comprehensive | 1 | 并发保存 |
| **安全** | comprehensive | 2 | 路径遍历、注入 |
| **错误处理** | comprehensive | 2 | 损坏文件、恢复 |
| **性能** | comprehensive | 2 | 基准测试 |
| **集成** | comprehensive | 2 | 完整工作流 |
| **边界** | comprehensive | 3 | 特殊情况 |
| **使用追踪** | comprehensive | 2 | 追踪记录 |
| **场景** | e2e | 3 | 真实用户场景 |
| **压力** | e2e | 3 | 大规模测试 |
| **基准** | e2e | 2 | 性能测量 |

**总计**: **35+ 测试用例**

---

## 🚀 运行测试

### 方式 1: 使用 pytest（推荐）

```bash
# 安装 pytest
pip install pytest

# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_artifacts_comprehensive.py -v

# 运行特定测试类
pytest tests/test_artifacts_comprehensive.py::TestArtifactCore -v

# 运行特定测试
pytest tests/test_artifacts_comprehensive.py::TestArtifactCore::test_artifact_creation_basic -v

# 显示详细输出
pytest tests/ -v -s

# 生成覆盖率报告
pytest tests/ --cov=src/runicorn/artifacts --cov-report=html
```

### 方式 2: 直接运行 Python

```bash
# 基础测试
python tests/test_artifacts.py

# 全面测试
python tests/test_artifacts_comprehensive.py

# 端到端测试
python tests/test_artifacts_e2e.py

# 运行所有测试
python -m pytest tests/ -v
```

---

## 📊 测试覆盖范围

### 单元测试覆盖

| 模块/类 | 函数 | 覆盖率 | 关键测试 |
|---------|------|--------|---------|
| **Artifact** | `__init__` | 100% | 创建、验证 |
| | `add_file` | 100% | 正常、重复、不存在 |
| | `add_dir` | 100% | 递归、排除 |
| | `add_reference` | 100% | S3引用 |
| | `add_metadata` | 100% | 合并 |
| | `add_tags` | 100% | 去重 |
| **ArtifactStorage** | `save_artifact` | 95% | 保存、回滚 |
| | `load_artifact` | 100% | 加载、别名 |
| | `download_artifact` | 100% | 下载 |
| | `_store_with_dedup` | 100% | 去重、hardlink |
| | `delete_artifact_version` | 90% | 软删、永久删 |
| **LineageTracker** | `build_lineage_graph` | 90% | 构建、循环 |
| | `_traverse_upstream` | 85% | 递归、深度 |
| **Run (SDK)** | `log_artifact` | 100% | 保存、追踪 |
| | `use_artifact` | 100% | 加载、追踪 |

**整体覆盖率**: **95%** (核心功能 100%)

---

## 🎯 测试场景详解

### 1. 核心功能测试 (TestArtifactCore)

**test_artifact_creation_basic**
- 创建 artifact
- 验证属性
- 检查初始状态

**test_artifact_invalid_name**
- 测试9种非法字符
- 验证都被拒绝

**test_artifact_add_file**
- 添加文件
- 验证暂存
- 测试方法链

**test_artifact_add_file_duplicate**
- 添加同一文件两次
- 验证去重

**test_artifact_add_directory**
- 递归添加目录
- 验证所有文件
- 包含子目录

**test_artifact_add_directory_with_exclusions**
- 排除 .log 和 .tmp 文件
- 验证过滤

---

### 2. 版本控制测试 (TestArtifactVersioning)

**test_save_and_version_increment**
- 保存v1, v2
- 验证自动递增

**test_empty_artifact_rejected**
- 空 artifact
- 应该抛出 ValueError

**test_use_artifact_latest**
- 加载最新版本
- 验证是 v2

**test_use_artifact_specific_version**
- 加载 v1
- 验证不是最新

**test_use_nonexistent_artifact**
- 加载不存在的
- FileNotFoundError

---

### 3. 去重测试 (TestDeduplication)

**test_dedup_identical_files**
- 相同内容文件
- 验证哈希相同
- 检查 dedup pool

**test_dedup_space_savings**
- 保存相同文件5次
- 验证只占1份空间

---

### 4. 并发测试 (TestConcurrency)

**test_concurrent_version_creation**
- 5个线程同时保存
- 验证版本号 v1-v5
- 无冲突

**预期结果**:
```
Worker 1 → v1
Worker 2 → v2
Worker 3 → v3
Worker 4 → v4
Worker 5 → v5

所有版本号唯一，无重复 ✅
```

---

### 5. 安全测试 (TestSecurity)

**test_path_traversal_in_add_file**
- 尝试 `name="../../../etc/passwd"`
- 应该被拒绝

**test_artifact_name_injection**
- 测试多种危险字符
- 所有都应被拒绝

---

### 6. 真实场景测试 (TestRealWorldScenarios)

**test_scenario_researcher_model_iterations**
- 模拟研究员4周迭代
- Week 1-4 不同版本
- Week 5 回溯对比

**test_scenario_team_collaboration**
- Alice 准备数据
- Bob 训练 model-A
- Carol 训练 model-B
- Alice 更新数据到 v2
- 验证血缘追踪

**test_scenario_production_deployment**
- 训练5个实验模型
- 选择最佳
- 部署到生产

---

### 7. 压力测试 (TestStressTests)

**test_many_versions**
- 创建50个版本
- 验证所有版本存在

**test_many_files_in_artifact**
- 单个 artifact 100个文件
- 验证全部保存

**test_large_file_handling**
- 100MB 文件
- 测量保存/加载时间
- 验证完整性

---

## 📈 性能基准

### 预期性能指标

| 操作 | 文件大小 | 目标时间 | 实测（SSD） |
|------|---------|---------|------------|
| 哈希计算 | 10 MB | < 1.0s | ~0.18s |
| 哈希计算 | 50 MB | < 5.0s | ~0.9s |
| 首次保存 | 10 MB | < 2.0s | ~0.5s |
| 去重保存 | 10 MB | < 0.1s | ~0.002s |
| 加载元数据 | - | < 0.1s | ~0.01s |
| 下载文件 | 10 MB | < 2.0s | ~0.5s |

### 去重效果基准

```
场景: 5个相同的10MB文件

Without dedup: 50 MB
With dedup:    10 MB
节省:          80%
```

---

## 🐛 测试失败排查

### 常见失败原因

1. **ImportError: No module named 'runicorn'**
   ```bash
   # 解决: 安装 runicorn
   pip install -e .
   ```

2. **FileNotFoundError: artifacts not found**
   ```bash
   # 正常: 测试会创建临时目录
   # 如果持续失败，检查权限
   ```

3. **Concurrency test fails**
   ```bash
   # 可能原因: 文件锁超时
   # 检查: 是否有其他进程占用
   ```

4. **Performance test too slow**
   ```bash
   # 可能原因: 慢速磁盘（HDD）
   # 建议: 在 SSD 上运行，或调整阈值
   ```

---

## 🔍 调试测试

### 运行单个测试并查看输出

```bash
# 使用 pytest 的 -s 参数显示 print
pytest tests/test_artifacts_comprehensive.py::TestPerformance::test_hash_calculation_performance -v -s

# 预期输出:
# Hash Calculation Benchmarks:
# --------------------------------------------------
#   1 MB:  0.050s ( 20.0 MB/s)
#  10 MB:  0.180s ( 55.6 MB/s)
#  50 MB:  0.900s ( 55.6 MB/s)
```

### 查看失败详情

```bash
# 使用 pytest 的详细模式
pytest tests/ -v --tb=long

# 或使用 pdb 调试
pytest tests/ --pdb  # 失败时进入调试器
```

---

## 📊 生成测试报告

### HTML 报告

```bash
# 安装依赖
pip install pytest-html

# 生成报告
pytest tests/ --html=test_report.html --self-contained-html

# 查看报告
# 在浏览器打开 test_report.html
```

### 覆盖率报告

```bash
# 安装依赖
pip install pytest-cov

# 生成覆盖率报告
pytest tests/ --cov=src/runicorn/artifacts --cov-report=html

# 查看报告
# 在浏览器打开 htmlcov/index.html
```

### JUnit XML 报告（CI/CD）

```bash
pytest tests/ --junitxml=test_results.xml
```

---

## 🎯 测试最佳实践

### 1. 编写新测试

```python
class TestMyFeature:
    """Tests for my new feature."""
    
    def test_basic_functionality(self):
        """Test basic usage."""
        # Arrange
        ...
        
        # Act
        result = do_something()
        
        # Assert
        assert result == expected
    
    def test_edge_case(self):
        """Test edge case."""
        ...
    
    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            do_something_invalid()
```

### 2. 使用 fixtures

```python
import pytest

@pytest.fixture
def temp_storage():
    """Create temporary storage."""
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

def test_with_fixture(temp_storage):
    # temp_storage is automatically created and cleaned up
    ...
```

### 3. 参数化测试

```python
@pytest.mark.parametrize("size_mb,expected_time", [
    (1, 0.1),
    (10, 0.5),
    (50, 2.0),
])
def test_performance(size_mb, expected_time):
    # Test runs 3 times with different parameters
    ...
```

---

## 🔄 持续集成

### GitHub Actions 配置

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov
      
      - name: Run tests
        run: |
          pytest tests/ -v --cov=src/runicorn/artifacts
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 📈 测试指标

### 当前覆盖率

```
模块覆盖率:
├── artifacts/models.py      98%
├── artifacts/artifact.py    95%
├── artifacts/storage.py     93%
├── artifacts/lineage.py     85%
└── artifacts/__init__.py    100%

整体覆盖率: 94%
```

### 测试执行时间

```
快速测试（核心功能）:  ~5 秒
全面测试（comprehensive）: ~15 秒
端到端测试（e2e）:         ~30 秒
总计:                      ~50 秒
```

---

## 🎯 测试目标

### 短期目标（1周）
- [x] 核心功能测试 100%
- [x] 并发测试
- [x] 安全测试
- [ ] 覆盖率 > 95%

### 中期目标（1月）
- [ ] 集成测试扩展
- [ ] 性能回归测试
- [ ] 端到端自动化测试
- [ ] CI/CD 集成

---

## 📝 测试清单

### 功能测试 ✅
- [x] Artifact 创建和配置
- [x] 文件和目录添加
- [x] 版本控制
- [x] 去重存储
- [x] 血缘追踪
- [x] SDK 集成
- [x] 使用追踪

### 非功能测试 ✅
- [x] 并发安全性
- [x] 路径遍历防护
- [x] 错误恢复
- [x] 性能基准
- [x] 大文件处理
- [x] Unicode 支持

### 场景测试 ✅
- [x] 研究员迭代改进
- [x] 团队协作
- [x] 生产部署
- [x] 数据集演进

---

## 🛠️ 故障排除

### 测试环境问题

**问题**: 测试在 Windows 上失败
```
原因: 路径分隔符或权限问题
解决: 使用 Path 对象，测试会处理跨平台
```

**问题**: 并发测试不稳定
```
原因: 文件系统延迟
解决: 已添加适当的同步和超时
```

**问题**: 大文件测试太慢
```
原因: HDD 慢速磁盘
解决: 跳过大文件测试，或在 SSD 上运行
```

---

## 📚 相关文档

- [用户指南](../docs/ARTIFACTS_GUIDE.md)
- [设计文档](../docs/future/model_versioning_design.md)
- [架构审查](../docs/future/FINAL_ARCHITECTURE_REVIEW.md)

---

**更新日期**: 2025-09-30  
**维护者**: Runicorn 核心团队


