# MeterSphere API 参考（混合模式版）

## 1. 推荐策略

推荐采用三段式：

1. **本地生成 JSON 草稿**
2. **AI 模型增强草稿**
3. **批量写入 MeterSphere**

## 2. 真实鉴权

请求头：

```http
accessKey: <AK>
signature: <动态签名>
```

## 3. 功能用例混合流程

### 生成草稿

```bash
./scripts/ms.sh functional-case generate <projectId> <moduleId> <requirement-file>
```

### AI 增强模板

```text
references/ai-functional-case-prompt.md
```

### 批量写入

```bash
./scripts/ms.sh functional-case batch-create <json-file>
```

说明：

- `functional-template list` 仅用于查看项目模板元数据，不参与 2.x 功能用例创建请求

## 4. 接口定义 / 接口用例混合流程

### 生成草稿 bundle

```bash
./scripts/ms.sh api import-generate <projectId> <moduleId> <openapi-file-or-url>
```

### AI 增强模板

```text
references/ai-api-bundle-prompt.md
```

### 批量写入

```bash
./scripts/ms.sh api batch-create <json-file>
```

## 5. 当前本地生成能力

### 功能用例
- 主流程
- 异常场景
- 边界场景
- 基础优先级 / 标签

### 接口用例
- 成功场景（200）
- 必填缺失（400）
- 边界场景（200）
- example/schema 自动带值
- 基础状态码断言自动挂载

## 6. 查询辅助接口（MeterSphere 2.x）

- `GET /project/workspace/list/userworkspace`
- `GET /project/project/list/all`
- `GET /track/case/node/list/{projectId}`
- `GET /setting/project/field/template/case/option/{projectId}`
- `GET /api/api/module/list/{projectId}/{protocol}`

## 7. 功能用例评审相关接口

已确认可用的 2.x 评审相关接口包括：

- `POST /track/test/case/review/list/{goPage}/{pageSize}`
  - 查询项目下评审单列表
- `GET /track/test/case/review/get/{reviewId}`
  - 查询单个评审单详情
- `POST /track/test/review/case/list/{goPage}/{pageSize}`
  - 通过 `reviewId` 查询某个评审单下的用例列表
  - 当前实例上按 `caseId` 直查会触发 500，不建议直接依赖
- `POST /track/case/review/node/list/{projectId}`
  - 查询评审模块树
- `GET /track/user/project/member/{projectId}`
  - 返回项目成员，可作为评审候选用户近似集合

## 8. 如何判断“哪些用例被评审过”

推荐两种口径：

### 口径 A：功能用例维度（最适合用户问答）

推荐组合查询：

- `POST /track/test/case/review/list/{goPage}/{pageSize}`
- `POST /track/test/review/case/list/{goPage}/{pageSize}`
- `GET /track/test/case/get/{testCaseId}`

其中：

- 先查项目下评审单列表，再逐个用 `reviewId` 查询评审单里的用例列表
- 通过 `caseId` 对评审单用例列表做反向索引，用于判断该用例是否参与过评审
- `test/case/get/{testCaseId}` 返回详情字段，可直接读取步骤、备注、标签等

若反向索引结果非空，则该用例**被评审过**；否则可视为**未被评审过**。

### 口径 B：评审单维度

先查：

- `POST /track/test/case/review/list/{goPage}/{pageSize}`

再对评审单查：

- `POST /track/test/review/case/list/{goPage}/{pageSize}`

可以得到“某个评审单里有哪些用例、每条用例当前评审状态”。

## 9. 当前限制

- 更细粒度 JSONPath 断言仍建议由 AI 增强阶段补充
- 当前本地生成仍以稳定、可落库为优先
- 当前实例的 `POST /track/test/case/issues/list` 存在 500 情况，报告类脚本已回退用例详情中的 `issueList`
