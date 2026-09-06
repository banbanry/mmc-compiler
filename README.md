# MMC Compiler — 多模型方言编译器（PEF0004）

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![PEF Architecture](https://img.shields.io/badge/PEF-Anchored%20Determinism-purple.svg)
![PEF ID](https://img.shields.io/badge/PEF0004-MMC%20Compiler-green.svg)

> **把任意大模型的输出方言统一编译到 PEF 标准格式的编译器**——支持 DeepSeek/OpenAI/Claude/豆包/GLM/智谱等多模型，消除方言偏差，统一主体/变量/结果三元结构，让多模型协作输出可比对、可验证、可审计。
>
> *Multi-Model Dialect Compiler. Unify arbitrary LLM outputs into PEF standard format. DeepSeek/OpenAI/Claude/GLM/Zhipu supported.*

© 2026 沈鹭 (banbanry) · 厦门恒元架构科技有限公司 · MIT License
来源：https://github.com/banbanry/mmc-compiler · PEF 架构：https://github.com/banbanry/pef-architecture

---

## ⚡ 30 秒上手

**一句话**：不同大模型的输出"方言"不一样——DeepSeek 写大函数、GLM 写超薄控制器、Trae 泛滥 DTO。MMC 编译器把这些方言统一编译成 PEF 标准格式（P主体/E变量/F结果），让多模型输出可比对、可验证、可审计。

**一条命令运行**：

```bash
# 克隆并运行多模型编译
git clone https://github.com/banbanry/mmc-compiler.git
cd mmc-compiler
pip install -r requirements.txt

# 编译单个模型输出到 PEF 标准格式
python mmc_cli.py compile --input deepseek_output.json --model deepseek --out-dir compiled

# 多模型对比编译（同一任务，不同模型输出）
python mmc_cli.py compare --inputs deepseek.json,glm.json,claude.json --out-dir compare_output

# 方言偏差检测
python mmc_cli.py dialect --input model_output.json --model auto
```

**预期输出**：

```
[MMC] Multi-Model Dialect Compiler
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Input: deepseek_output.json
Model: deepseek (auto-detected)
Dialect fingerprint: large-function / bare-try-catch / mutate-input
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Compilation] PEF Standard Format
  P (Primary Entity): RateLimiter
    - name: "RateLimiter"
    - type: "LOGICAL"
    - boundary: "接收请求并返回 ALLOW/DENY"
    - unit: "次/秒"
  E (Execution Variable):
    - E_in (controllable): [current_rate, limit_threshold]
    - E_out (uncontrollable): [system_clock, network_latency]
  F (Final Result):
    - verdict: ALLOW/DENY
    - traceable_to: (P, E, t)
    - hash: a1b2c3d4e5f6...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Dialect Deviation Detection]
  Architecture: large-function (DeepSeek fingerprint)
  Error handling: bare-try-catch (deviation from PEF standard)
  State side-effect: mutate-input (deviation from PEF standard)
  Naming: concise/minimal comments (DeepSeek fingerprint)
  Suggestion: split large function, add Result<T> wrapper, avoid mutation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Multi-Model Comparison]
  Task: "实现一个限流器"
  Models: deepseek, glm, claude, doubao, zhipu
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  deepseek:  大函数/裸try-catch/修改入参  → 编译成功
  glm:       超薄控制器/自定义异常/只读     → 编译成功
  claude:    平衡型/Result包装/不可变       → 编译成功
  doubao:    中文注释/工具函数/防御性       → 编译成功
  zhipu:     详细文档/类型注解/工厂模式     → 编译成功
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Consistency: P/E/F 三元结构 100% 对齐
  Deviation: 方言偏差全部检出，建议已生成
  Audit chain: 5 entries, tamper-evident
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Verdict: 5/5 models compiled successfully
Output: compiled/ (PEF standard format JSON)
Report: compare_output/report.html
```

**效果图**（典型模型方言指纹库）：

```
模型方言指纹库（基于训练数据特征推断）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
模型         架构风格        异常处理        状态副作用      命名风格
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DeepSeek     大函数/少文件   裸try-catch    倾向修改入参    简洁/少注释
GLM          超薄控制器      自定义异常枚举  倾向只读        详细/多注释
Claude       平衡型          Result<T>包装   倾向不可变      清晰/中等注释
Trae         DTO/适配器泛滥  Result<T>包装   倾向新建副本    冗长/过度抽象
Doubao       中文注释/工具   防御性编程      混合            中文/详细
Zhipu        详细文档/工厂   类型注解        混合            规范/完整
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PEF 标准：P主体/E变量/F结果 三元结构，方言无关
编译目标：消除方言偏差，统一到 PEF 标准格式
```

---

## 🎯 核心能力

| 能力 | 说明 |
|------|------|
| **多模型方言识别** | 自动识别 DeepSeek/GLM/Claude/Doubao/Zhipu/Trae 等模型的输出方言 |
| **PEF 标准编译** | 把任意模型输出编译成 PEF 标准格式（P主体/E变量/F结果 三元结构） |
| **方言偏差检测** | 检测架构风格、异常处理、状态副作用、命名风格等方言偏差 |
| **多模型对比** | 同一任务不同模型输出的横向对比，一致性分析，偏差可视化 |
| **主体/变量对齐** | 确保不同模型输出的 P/E/F 三元结构 100% 对齐，可比对 |
| **哈希链审计** | 编译事件只追加禁删除，SHA-256 哈希链，篡改可检测 |
| **API 集成** | 支持直接调用多模型 API（DeepSeek/智谱/硅基流动等），实时编译 |

---

## 📊 实测证据

| 测试 | 结果 |
|------|------|
| 5模型对比编译 | DeepSeek/GLM/Claude/Doubao/Zhipu 全部编译成功 |
| 方言偏差检测 | 6大维度偏差全部检出，建议已生成 |
| P/E/F 对齐率 | 三元结构 100% 对齐，可比对 |
| API 实时编译 | DeepSeek/智谱 API 调用成功，实时编译正常 |
| 哈希链完整性 | ✅ 完整，篡改检测正常 |

> **典型应用场景**：同一公开论文，接入不同大模型（千问/小米GLM/豆包/月之暗面），看 skill 是否有效。经过编译器内容是否统一偏移，有没有丢失主体变量组合，分析是否一致，结果是否相同。

---

## 📁 模块结构

```
mmc-compiler/
├── SKILL.md                    # Skill 定义（完整文档）
├── README.md                   # 本文件
├── LICENSE                     # MIT
├── requirements.txt            # 依赖
├── config/
│   └── model_dialects.json     # 模型方言指纹库（6大模型）
└── scripts/
    ├── mmc_cli.py              # 主入口（compile/compare/dialect/api）
    ├── dialect_detector.py     # 方言识别与偏差检测
    ├── pef_compiler.py         # PEF 标准格式编译器
    ├── model_adapter.py        # 多模型 API 适配器
    ├── alignment_checker.py    # P/E/F 对齐检查
    ├── comparison_engine.py    # 多模型对比引擎
    ├── audit_chain.py          # 哈希链审计
    └── report_generator.py     # 报告生成（HTML/JSON）
```

---

## 🔗 与 PEF 架构的关系

本项目是 PEF（锚定确定性）元架构在**多模型协作**领域的工程实例化。

| PEF 概念 | MMC 实现 |
|----------|---------|
| 锚（π） | 每个编译单元分配 π 锚，确保可追溯 |
| P（主体） | 统一主体定义（name/type/boundary/unit），方言无关 |
| E（执行变量） | 统一变量分流（E_in 可控 / E_out 不可控），消除方言偏差 |
| F（结果） | 统一结果格式（verdict/traceable/hash），可比对可验证 |
| MOD3（三态） | 宽松编译 / 中等校验 / 严苛熔断 |
| 公理（A1-A8） | 主体不可丢、变量必分流、结果必可追溯、时序不可倒 |

**理论仓库**：https://github.com/banbanry/pef-architecture
**三剑客整合**：https://github.com/banbanry/pef-core-reference

---

## 👤 个人指纹

本项目携带 5 层个人指纹：

1. **多模型方言编译机制** — 6大模型方言指纹库 + PEF 标准编译，独特工程实现
2. **来源水印** — 每个文件头：`Source: https://github.com/banbanry/mmc-compiler` + 作者 + 许可证
3. **独特术语** — PEFmod、MMC、方言编译、P/E/F 对齐、多模型偏差
4. **版本演化记录** — V1.0 设计理论 → 工程化落地，修复历史带时间戳
5. **π 位参考指纹** — 关键模块注释中的特定 π 位引用

---

## ⚠️ 诚实边界

1. **方言识别基于训练数据特征推断** — 不是 100% 准确，同一模型可能因 prompt 不同而输出不同风格
2. **PEF 编译是结构级转换** — 只能统一 P/E/F 三元结构，不能保证语义完全一致
3. **多模型对比需要相同任务** — 不同任务的输出不可直接对比，需要控制变量
4. **API 集成需要 API Key** — 直接调用模型 API 需要用户提供自己的 API Key
5. **编译器是辅助工具** — 最终判断需要人工审核，工具只提供结构对齐和偏差检测

---

## 📜 许可证

MIT License — 详见 [LICENSE](LICENSE)。

---

*MMC Compiler © 2026 banbanry. 多模型方言编译器。*
*把任意大模型的输出方言统一编译到 PEF 标准格式——"各说各话"不再是多模型协作的障碍，而是可编译、可比对、可审计的工程问题。*
*来源：https://github.com/banbanry/mmc-compiler*
