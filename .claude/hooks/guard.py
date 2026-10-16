#!/usr/bin/env python3
"""PreToolUse 守門：依角色限制能讀寫的路徑。

用法：guard.py <role>
  role = main | prompt-builder | coder | test-designer | consistency-checker
  main 由 settings.json 呼叫，對主對話（/spec-draft、/senior-flow 指揮）生效；
  其他角色由各 subagent 的 frontmatter 呼叫。
每次判定都寫入 .flow/audit.jsonl，阻擋時 exit 2。
"""
import json
import os
import re
import sys
import time

ROLES = {"prompt-builder", "coder", "test-designer", "consistency-checker"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SEARCH_TOOLS = {"Glob", "Grep"}
MAIN_BASH = re.compile(r"^bash \.claude/flow/[a-z_]+\.sh( [0-9]+)?$")
# 只有人能執行的腳本：確認 spec
HUMAN_ONLY_BASH = {"approve_spec.sh"}
CONFIG = "flow.config.json"
APPROVED = ".approved"


def flow_running(root):
    try:
        with open(os.path.join(root, ".flow", "state.json"), encoding="utf-8") as f:
            return json.load(f).get("status") == "running"
    except (OSError, ValueError):
        return False


def load_config(root):
    try:
        with open(os.path.join(root, CONFIG), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def dirs(cfg, key, default):
    """config 中的目錄設定，統一成以 / 結尾的相對路徑清單。"""
    v = cfg.get(key, default)
    if isinstance(v, str):
        v = [v]
    out = []
    for d in v:
        d = os.path.normpath(d).strip("/")
        # "." 或空字串代表整個專案，不允許當成程式／測試目錄
        if d and d != "." and not d.startswith(".."):
            out.append(d + "/")
    return out


def rules_for(role, cfg, running=False):
    """回傳 (可讀前綴, 可寫前綴)。前綴以專案根目錄為基準；"" 代表整個專案。"""
    spec = dirs(cfg, "spec_dir", "spec/")
    src = dirs(cfg, "src_dirs", ["src/"])
    tests = dirs(cfg, "test_dirs", ["tests/"])
    if role == "prompt-builder":
        return (spec + [".flow/prompts/", ".flow/runs/", ".flow/report.md", CONFIG],
                [".flow/prompts/"])
    if role == "coder":
        read = spec + [".flow/prompts/coder.md", CONFIG] + src
        if cfg.get("coder_can_read_tests"):
            read += tests
        return read, src
    if role == "test-designer":
        return spec + [".flow/prompts/tester.md", CONFIG] + tests, tests
    if role == "consistency-checker":
        return [""], []
    # examples/ 只供 /spec-draft 參考規格格式（唯讀）
    read = spec + [".flow/", CONFIG, ".claude/flow/", "examples/"]
    if role == "main" and not running:
        # ⓪ /spec-draft：流程沒在跑時，主對話可以寫 spec 與 config
        return read, spec + [CONFIG]
    # 指揮（流程執行中）與未知的 subagent：只讀流程檔，不寫任何檔案
    return read, []


def rel(root, cwd, p):
    if not p:
        return None
    full = os.path.realpath(p if os.path.isabs(p) else os.path.join(cwd, p))
    root = os.path.realpath(root)
    if full != root and not full.startswith(root + os.sep):
        return "<outside>"
    r = os.path.relpath(full, root)
    return "" if r == "." else r


def allowed(r, prefixes):
    if r is None or r == "<outside>":
        return False
    for pre in prefixes:
        if pre == "":
            return True
        if pre.endswith("/"):
            if r.startswith(pre) or r == pre[:-1]:
                return True
        elif r == pre:
            return True
    return False


def decide(role, tool, ti, root, cwd, cfg):
    read, write = rules_for(role, cfg, flow_running(root))

    if role == "main" and tool == "Agent":
        st = ti.get("subagent_type", "")
        return (st in ROLES, "subagent_type=%s" % st)
    if tool == "Bash":
        cmd = ti.get("command", "").strip()
        if role == "main" and MAIN_BASH.match(cmd) and os.path.basename(cmd.split()[1]) not in HUMAN_ONLY_BASH:
            return True, cmd
        return False, cmd
    if tool in WRITE_TOOLS:
        r = rel(root, cwd, ti.get("file_path") or ti.get("notebook_path"))
        if r and os.path.basename(r) == APPROVED:
            return False, r  # 確認紀錄只能由人執行 approve_spec.sh 產生
        return allowed(r, write), r
    if tool == "Read":
        r = rel(root, cwd, ti.get("file_path"))
        return allowed(r, read), r
    if tool in SEARCH_TOOLS:
        # 沒給 path 等於搜尋整個專案
        r = rel(root, cwd, ti.get("path") or cwd)
        if r == "":
            return ("" in read), "<project root>"
        return allowed(r, read), r
    return True, "-"


def main():
    role = sys.argv[1] if len(sys.argv) > 1 else "main"
    data = json.load(sys.stdin)
    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    cwd = data.get("cwd") or root
    agent_type = data.get("agent_type")
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}

    # settings.json 的守門也會在 subagent 內觸發。已知角色直接套用該角色的規則，
    # 不依賴 frontmatter hook（資料夾未信任時 frontmatter hook 可能不執行）；
    # 未知的 subagent（例如 general-purpose、Explore）套用只讀的 other 規則。
    source = "frontmatter"
    if role == "main":
        source = "settings"
        if agent_type in ROLES:
            role = agent_type
        elif agent_type:
            role = "other"

    ok, target = decide(role, tool, ti, root, cwd, load_config(root))

    os.makedirs(os.path.join(root, ".flow"), exist_ok=True)
    with open(os.path.join(root, ".flow", "audit.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": time.strftime("%H:%M:%S"), "source": source, "guard": role, "agent_type": agent_type,
            "tool": tool, "target": target, "decision": "allow" if ok else "deny",
        }, ensure_ascii=False) + "\n")

    if not ok:
        hint = ""
        if target and os.path.basename(str(target).split()[-1] if tool == "Bash" else str(target)) in HUMAN_ONLY_BASH | {APPROVED}:
            hint = "（spec 確認只能由人執行：在終端機或 Claude Code 輸入 `! bash .claude/flow/approve_spec.sh`）"
        elif role == "main" and tool == "Bash":
            hint = "（主對話只能單獨執行 `bash .claude/flow/<名稱>.sh [輪次]`，不可加 cd、&&、管線或其他指令）"
        elif role == "main" and tool in WRITE_TOOLS and flow_running(root):
            hint = "（流程執行中，spec 與 config 已鎖定；若流程中斷，人可刪除 .flow/ 解鎖）"
        elif role == "main":
            hint = "（主對話只能讀寫規格目錄與 flow.config.json，不能讀寫程式與測試目錄）"
        sys.stderr.write("[guard:%s] 不允許 %s %s%s\n" % (role, tool, target, hint))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
