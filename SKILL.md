---
name: mmc-compiler
description: PEF 多模型方言编译器（MMC, Multi-Model Compiler）。把任意大模型（DeepSeek/OpenAI/Claude/豆包/GLM/Gemini）的输出方言统一编译到 PEF 标准 schema，用 π 锚分配编译坐标，记录方言偏差率。当用户需要"统一多模型输出格式"、"把不同 AI 的回复归一化"、"方言偏差转换"、"多模型对齐"、"把模型输出变成可审计标准 JSON"、"接入插件前的规范化层"时使用。触发词：多模型编译、方言转换、MMC、模型输出归一化、跨模型对齐。
---

# PEF MMC — 多模型方言编译器

设计依据: PEF 第一性原理（P 主体 / E 变量 / F 结果）+ π 锚定坐标系。
**问题**：同一任务，不同模型输出方言不同——字段名（content / output / choices[].message.content / content[].text）、术语（推理/思考/reasoning）、承诺语气（我认为/可能/一定）都不同，无法直接进入统一审计。
**方案**：方言 → π 锚编译 → PEF 标准 schema（统一审计坐标），偏差率 ρ 记录在审计链上。

## 核心机制

- **P（主体）** = 来源模型（deepseek / openai / claude / doubao / glm / gemini / auto 探测）
- **E（执行变量）** = 方言特征（提取路径、术语映射表、承诺语气正则）
- **F（结果）** = 编译后的 PEF 标准 schema（claims / variables / terms_normalized）
- **π 锚** = 每次编译按 seq 单调分配 π 数位（`π-<pos>-<digit>`），编译坐标不可自算、可复验
- **偏差率 ρ** = 未映射字段数 / 顶层字段数——量化"这个模型有多偏离标准"

## 快速开始

```bash
# 1. 编译任意模型输出 (auto 自动探测方言)
python scripts/mmc_cli.py compile --input <模型输出.json> --source-model auto

# 2. 指定方言 + 固定 π 锚序号 (可复现)
python scripts/mmc_cli.py compile --input out.json --source-model deepseek --seq 7 --out compiled.json

# 3. 查看方言注册表
python scripts/mmc_cli.py dialects
```

## 输出 schema (PEF 标准)

```json
{
  "compiled": {
    "schema": "pef-mmc-1.0",
    "source_model": "deepseek",
    "pi_anchor": "π-7-6",
    "claims": [{"text": "...", "assertion_level": "FACT|JUDGMENT|GREY", "origin_offset": 0}],
    "variables": [{"name": "延迟", "kind": "E_in|E_out"}],
    "terms_normalized": {"reasoning": "思考"}
  },
  "dialect": {"matched": "deepseek", "paths_tried": [...]},
  "audit": {"rho_dialect_deviation": 0.0, "unmapped_fields": [], "hash": "...", "ts": "..."}
}
```

## 命令速查

| 命令 | 用途 | 关键参数 |
|---|---|---|
| `compile` | 方言编译 | `--input --source-model auto\|deepseek\|openai\|claude\|doubao\|glm\|gemini --seq --out` |
| `dialects` | 列方言注册表 | — |

## 使用规则

1. **auto 模式**按注册表顺序探测提取路径，命中最长有效文本。
2. **承诺等级**：`可能/也许/或许` → GREY（灰色地带）；`一定/必须/绝对` → JUDGMENT；其余 → FACT。这是"语义方言"归一的核心——不同模型语气不同，编译后统一。
3. **术语归一**：推理/思考/思路/reasoning → reasoning；结论/结果/输出 → result；变量/参数 → variable；主体/entity → subject。
4. **π 锚不可重入**：同一 seq 不重复编译（与 PIMEM 锚规则一致）；编译坐标查表，不自算 π。
5. **诚实边界**：本工具做**结构 + 术语 + 承诺语气**三层方言归一，不做语义理解——claims 的准确性由后续 PEF 引擎（长文本/探针）审计。

## 典型场景

- **插件前置层**：把任意模型输出编译成统一 schema 再进 PEF 三引擎（探针/长文本/记忆）审计——插件不需要为每个模型写适配。
- **多模型对齐测试**：同一 prompt 发给 5 个模型，编译后对比 claims 等级分布（谁更爱用 GREY 模糊词）。
- **审计留痕**：每次编译记录 π 锚 + 偏差率 ρ + hash——"这个结论来自哪个模型、偏离标准多少"可追溯。
