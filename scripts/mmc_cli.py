#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PEF MMC (Multi-Model Compiler) — 多模型方言偏差转换编译器
设计依据: PEF 第一性原理 (P主体 / E变量 / F结果) + π 锚定坐标系

问题: 同一任务, DeepSeek/GPT/Claude/豆包/GLM 输出方言不同
  (字段名不同: content/output/choices[].message.content/content[].text;
   术语不同: 推理/思考/reasoning; 承诺语气不同: 我认为/可能/一定)
方案: 方言 → π 锚编译 → PEF 标准 schema (统一审计坐标)

命令:
  python mmc_cli.py compile --input <模型输出.json> --source-model deepseek|openai|claude|doubao|glm|auto [--seq N]
  python mmc_cli.py dialects            # 列方言注册表
零第三方依赖 (stdlib only)
"""
import argparse, hashlib, json, os, re, sys, time

# ---- π 预置表 (前 120 位; 编译坐标不可自算, 只可查表) ----
PI_DIGITS = ("314159265358979323846264338327950288419716939937510582097494"
             "459230781640628620899862803482534211706798214808651328230664")

# ---- 方言注册表: 各模型响应中"正文提取路径" ----
DIALECTS = {
    "openai":  {"paths": [["choices", 0, "message", "content"], ["choices", 0, "text"], ["choices", 0, "message", "reasoning_content"]], "note": "OpenAI / 推理模型 (content空时回退reasoning_content)"},
    "deepseek": {"paths": [["choices", 0, "message", "content"], ["choices", 0, "text"], ["choices", 0, "message", "reasoning_content"]], "note": "DeepSeek API (OpenAI兼容, 含R1推理链)"},
    "claude":  {"paths": [["content", 0, "text"]], "note": "Anthropic Messages API"},
    "doubao":  {"paths": [["choices", 0, "message", "content"], ["choices", 0, "text"], ["choices", 0, "message", "reasoning_content"]], "note": "豆包/火山方舟 (OpenAI兼容)"},
    "glm":     {"paths": [["choices", 0, "message", "content"], ["choices", 0, "text"], ["choices", 0, "message", "reasoning_content"]], "note": "智谱 GLM (OpenAI兼容)"},
    "gemini":  {"paths": [["candidates", 0, "content", "parts", 0, "text"], ["candidates", 0, "content", "parts"]], "note": "Google Gemini"},
}

# ---- 术语方言: 异名同义 (概念归一) ----
TERM_MAP = {
    "推理": "reasoning", "思考": "reasoning", "思路": "reasoning", "reasoning": "reasoning",
    "结论": "result", "结果": "result", "输出": "result", "output": "result", "result": "result",
    "变量": "variable", "参数": "variable", "parameter": "variable", "variable": "variable",
    "主体": "subject", "主体识别": "subject", "entity": "subject",
}

# ---- 承诺语气 → PEF 判定 (语义方言) ----
HEDGE = r"可能|也许|或许|大概|据说|估计|possibly|maybe|perhaps"          # 不确定 → GREY
STRONG = r"一定|必须|绝对|必然|definitely|certainly|must"                  # 强断言 → JUDGMENT

def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _dig_get(obj, path):
    """按路径提取 (路径为 list: 键名或索引)"""
    cur = obj
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        elif isinstance(cur, list) and isinstance(p, int) and p < len(cur):
            cur = cur[p]
        elif isinstance(cur, list) and p == "parts" and cur:
            cur = cur[0].get("text", "") if isinstance(cur[0], dict) else str(cur[0])
        else:
            return None
    return cur

def extract_text(obj, source_model):
    """按方言路径提取正文; auto 模式遍历所有注册方言"""
    models = [source_model] if source_model != "auto" else list(DIALECTS)
    for m in models:
        if m not in DIALECTS:
            continue
        for path in DIALECTS[m]["paths"]:
            v = _dig_get(obj, path)
            if isinstance(v, str) and v.strip():
                return m, v
            if isinstance(v, list):
                txt = "".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in v)
                if txt.strip():
                    return m, txt
    # fallback: 遍历找最长字符串字段
    best, bestk = "", None
    def walk(o):
        nonlocal best, bestk
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and len(v) > len(best):
                    best, bestk = v, k
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(obj)
    if best:
        return "auto-fallback", best
    return None, ""

def _extract_vars(text):
    """变量提取: 模型输出 JSON 结构时结构化读取 (name/kind/value), 否则文本正则"""
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    cand = m.group(1) if m else text
    try:
        st = cand.index("{")
        en = cand.rindex("}")
        d = json.loads(cand[st:en+1])
    except (ValueError, json.JSONDecodeError):
        d = None
    if isinstance(d, dict) and isinstance(d.get("variables"), list):
        out = []
        for v in d["variables"]:
            if isinstance(v, dict) and v.get("name"):
                k = str(v.get("kind", ""))
                kind = "E_in" if ("E_in" in k or "可控" in k) else "E_out"
                out.append({"name": str(v["name"])[:40], "kind": kind,
                            "value": str(v.get("value", ""))[:30]})
        if out:
            return out
    out = []
    for mm in re.finditer(r"([\u4e00-\u9fffA-Za-z_]{2,12})\s*(?:=|:|为|是)\s*([-+]?\d+(?:\.\d+)?)", text):
        out.append({"name": mm.group(1), "kind": "E_out" if mm.group(2).startswith(("-", "0.")) else "E_in"})
    return out

def parse_claims(text):
    """论断拆解: 按句切分, 判定承诺等级"""
    sentences = re.split(r"(?<=[。！？!?；;])\s*|\n+", text)
    claims = []
    for s in sentences:
        s = s.strip()
        if len(s) < 4:
            continue
        if re.search(STRONG, s):
            level = "JUDGMENT"
        elif re.search(HEDGE, s):
            level = "GREY"
        else:
            level = "FACT"
        claims.append({"text": s[:120], "assertion_level": level, "origin_offset": text.index(s)})
    return claims[:30]

def compile_one(obj, source_model, seq):
    """方言编译: 提取正文 → 论断拆解 → 术语归一 → π 锚分配 → 审计链"""
    matched_model, text = extract_text(obj, source_model)
    claims = parse_claims(text)
    # π 锚: 编译坐标 = seq 单调分配
    pos = seq % len(PI_DIGITS)
    pi_anchor = f"π-{pos}-{PI_DIGITS[pos]}"
    # 术语归一: 从 claims 中找术语异名
    used_terms = {}
    for c in claims:
        for zh, en in TERM_MAP.items():
            if zh in c["text"] and en not in used_terms:
                used_terms[en] = zh
    # 变量分流 (E_in/E_out): 优先 JSON 结构化提取, 回退文本正则
    variables = _extract_vars(text)
    # 方言偏差率 ρ: 未映射字段 / 顶层字段数
    top_fields = list(obj.keys()) if isinstance(obj, dict) else []
    known = set()
    for m in DIALECTS:
        for path in DIALECTS[m]["paths"]:
            if path and isinstance(path[0], str):
                known.add(path[0])
    unmapped = [f for f in top_fields if f not in known and f not in ("choices", "content", "message", "candidates")]
    rho = round(len(unmapped) / max(1, len(top_fields)), 4)
    compiled = {
        "schema": "pef-mmc-1.0",
        "source_model": matched_model or source_model,
        "pi_anchor": pi_anchor,
        "seq": seq,
        "claims": claims,
        "variables": variables[:20],
        "terms_normalized": used_terms,
    }
    audit = {
        "rho_dialect_deviation": rho,
        "unmapped_fields": unmapped,
        "hash": _sha(json.dumps(compiled, sort_keys=True, ensure_ascii=False)),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    return {"compiled": compiled, "dialect": {"matched": matched_model, "paths_tried": DIALECTS.get(matched_model, {}).get("paths", [])}, "audit": audit}

def cmd_compile(a):
    if not os.path.exists(a.input):
        sys.exit(f"✗ 输入不存在: {a.input}")
    try:
        obj = json.load(open(a.input, encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as e:
        sys.exit(f"✗ 输入不是有效 JSON: {e}")
    seq = a.seq if a.seq is not None else int(time.time()) % 1000
    out = compile_one(obj, a.source_model, seq)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n已存: {a.out}")
    return 0

def cmd_dialects(a):
    print(f"{'模型':<12}{'提取路径':<48}{'说明'}")
    print("-" * 78)
    for m, d in DIALECTS.items():
        paths = "; ".join(".".join(str(x) for x in p) for p in d["paths"])
        print(f"{m:<12}{paths:<48}{d['note']}")
    return 0

def main():
    ap = argparse.ArgumentParser(description="PEF MMC 多模型方言编译器")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("compile", help="编译模型输出到 PEF 标准 schema")
    p.add_argument("--input", required=True, help="模型输出 JSON 文件")
    p.add_argument("--source-model", default="auto", choices=list(DIALECTS) + ["auto"], help="来源模型方言 (默认 auto 探测)")
    p.add_argument("--seq", type=int, default=None, help="π 锚序号 (默认按时间)")
    p.add_argument("--out", default=None, help="输出文件路径")
    p = sub.add_parser("dialects", help="列方言注册表")
    a = ap.parse_args()
    rc = {"compile": cmd_compile, "dialects": cmd_dialects}[a.cmd](a)
    sys.exit(rc or 0)

if __name__ == "__main__":
    main()
