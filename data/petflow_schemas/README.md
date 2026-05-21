# PetFlow JSON Schema 文件索引

本目录收录了 PetFlow 项目所有需要预定义的 JSON 接口契约文件。
开发前请先阅读对应 schema，实现时严格对齐字段定义。

---

## 目录结构

```
petflow_schemas/
  agent/
    graph_generation_input.json     Agent 生成任务图 — 输入契约
    graph_generation_output.json    Agent 生成任务图 — 输出契约
    node_splitting_input.json       Agent 拆分节点   — 输入契约
    node_splitting_output.json      Agent 拆分节点   — 输出契约
    pet_speech_input.json           桌宠气泡语言生成 — 输入契约
    pet_speech_output.json          桌宠气泡语言生成 — 输出契约
    review_generation_input.json    复盘文本生成     — 输入契约
    review_generation_output.json   复盘文本生成     — 输出契约
  storage/
    graph.json                      主图持久化结构（含所有节点/边类型示例）
    sample_graph.json               演示样例图（可提交到仓库）
  config/
    settings.json                   本地运行时配置模板（.gitignore 忽略实例）
  events/
    event_schemas.json              EventBus 所有事件的 payload 结构
```

---

## 各文件用途速查

| 文件 | 谁写入 | 谁读取 | 可提交到仓库 |
|------|--------|--------|------------|
| graph_generation_input.json | PromptBuilder | AgentClient | ✅（文档用） |
| graph_generation_output.json | LLM → AgentExecutor | AgentDialog | ✅（文档用） |
| node_splitting_input.json | PromptBuilder | AgentClient | ✅（文档用） |
| node_splitting_output.json | LLM → AgentExecutor | AgentDialog | ✅（文档用） |
| pet_speech_input.json | PetService → PromptBuilder | AgentClient | ✅（文档用） |
| pet_speech_output.json | LLM → AgentExecutor | PetService | ✅（文档用） |
| review_generation_input.json | ReviewService → PromptBuilder | AgentClient | ✅（文档用） |
| review_generation_output.json | LLM → AgentExecutor | ReviewDialog | ✅（文档用） |
| storage/graph.json | StorageService | JsonGraphRepository | ❌（用户数据） |
| storage/sample_graph.json | 手动维护 | StorageService.load_sample() | ✅ |
| config/settings.json | 用户/开发者本地配置 | config.py | ❌（含 API Key） |
| events/event_schemas.json | 文档用途 | 开发者参考 | ✅ |

---

## 核心约束（所有 Agent 接口通用）

1. **LLM 输出流水线**：原始输出 → JSON 解析 → 字段校验 → AgentDialog 预览 → 用户确认 → GraphService 写入，不得跳过任何环节。
2. **ID 前缀规则**：图生成节点用 `agent_gen_` 前缀，拆分节点用 `agent_split_` 前缀，避免与用户节点冲突。
3. **拆分 output 不含已有节点**：`prerequisites` 中的节点 id 不得出现在 output nodes 中。
4. **结构化输入**：`pet_speech` 和 `review_generation` 的上下文必须是结构化字段，由 `PromptBuilder` 组装成自然语言 Prompt，调用方不得预拼自然语言字符串。
5. **layout_hint 不是坐标**：Agent 返回 `layer` + `order`，由 `GraphLayoutService` 换算为实际 `x`/`y`，Agent 不负责绝对坐标。
6. **schema_version**：所有文件包含 `schema_version` 字段，`AgentExecutor` 读取后用于向后兼容校验。
