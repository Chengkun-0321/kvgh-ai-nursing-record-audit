#!/usr/bin/env python3
"""PreToolUse 守門：依角色限制能讀寫的路徑。

用法：guard.py <role>
  role = main | prompt-builder | coder | test-designer | consistency-checker
  main 由 settings.json 呼叫，對主對話（/spec-draft、/senior-flow 指揮）生效；
  其他角色由各 subagent 的 frontmatter 呼叫。
主對話與其他 subagent 只在流程執行中（.flow/state.json 為 running）受限，平常開發不受影響；
流程角色（prompt-builder、coder、test-designer、consistency-checker）一律受限。
確認 spec（approve_spec.sh、.approved）不論何時都只能由人執行；Bash 以指令結構判斷，只防誤操作。
路徑設定：結尾有 / 的是目錄，沒有 / 的是單一檔案（精確比對）。
流程執行中、流程角色或被阻擋的判定寫入 .flow/audit.jsonl，阻擋時 exit 2。
"""
import json
import os
import re
import shlex
import sys
import time

ROLES = {"prompt-builder", "coder", "test-designer", "consistency-checker"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SEARCH_TOOLS = {"Glob", "Grep"}
MAIN_BASH = re.compile(r"^bash \.claude/flow/[a-z_]+\.sh( [0-9]+)?$")
GLOB_CHARS = re.compile(r"[*?\[{]")
SHELLS = {"bash", "sh", "zsh", "source", "."}
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n.*?\n\s*\2[ \t]*(?=\n|$)", re.S)
SEPARATORS = set(";&|()")
COPY_LIKE = {"cp", "mv", "ln", "install"}
FILE_WRITERS = {"tee", "touch", "rm", "truncate"}
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


def dirs(cfg, key, default, force_dir=False):
    """config 中的路徑設定轉成相對路徑清單：結尾有 / 的是目錄（保留 /），沒有 / 的是單一檔案（精確比對）。"""
    v = cfg.get(key, default)
    if isinstance(v, str):
        v = [v]
    out = []
    for d in v:
        is_dir = force_dir or d.endswith("/")
        d = os.path.normpath(d).strip("/")
        # "." 或空字串代表整個專案，不允許當成程式／測試目錄
        if d and d != "." and not d.startswith(".."):
            out.append(d + "/" if is_dir else d)
    return out


def strip_heredocs(cmd):
    """heredoc 內容是資料（例如寫進文件的說明文字），不當成指令分析。
    未加引號的 heredoc 會執行 $(...) 與反引號，所以保留其中的命令替換。"""
    def keep_substitutions(m):
        if m.group(1):
            return "<<" + m.group(3)
        subs = re.findall(r"\$\(([^)]*)\)|`([^`]*)`", m.group(0))
        return "<<" + m.group(3) + "".join("\n" + (a or b) for a, b in subs)
    return HEREDOC.sub(keep_substitutions, cmd)


def command_segments(cmd):
    """把指令切成一段段簡單指令的 token（處理引號；括號、反引號、管線、;、&& 都視為分隔）。"""
    cmd = cmd.replace("\n", " ; ")  # 換行也是指令分隔
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()<>")
        lex.whitespace_split = True
        lex.commenters = ""
        tokens = list(lex)
    except ValueError:  # 引號不成對：退回以空白切
        tokens = cmd.split()
    seg = []
    for tok in tokens + [";"]:
        for i, part in enumerate(tok.split("`")):
            if i > 0 and seg:  # 反引號是命令替換的邊界
                yield seg
                seg = []
            if not part or part == "$":
                continue
            if set(part) <= SEPARATORS:
                if seg:
                    yield seg
                seg = []
            else:
                seg.append(part)


def touches_approval(cmd):
    """Bash 指令是否會執行 spec 確認或寫入確認紀錄。只防誤操作，不是安全邊界（例如 python -c 仍可繞過）。"""
    cmd = strip_heredocs(cmd)
    for toks in command_segments(cmd):
        # 重導向寫入：> 或 >> 之後的檔名
        if any(t in (">", ">>", ">|") and os.path.basename(n) == APPROVED for t, n in zip(toks, toks[1:])):
            return True
        toks = [t for i, t in enumerate(toks) if not (t.startswith((">", "<")) or (i and toks[i - 1].startswith((">", "<"))))]
        while toks and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[0]):
            toks = toks[1:]  # 略過 VAR=value 前綴
        if not toks:
            continue
        head = os.path.basename(toks[0])
        args = [a for a in toks[1:] if not a.startswith("-")]  # 略過 -x、-B 等選項
        if head.endswith("approve_spec.sh"):
            return True
        if head in SHELLS and args and args[0].endswith("approve_spec.sh"):
            return True
        if head.startswith("python") and len(args) >= 2 and args[0].endswith("state.py") and args[1] == "approve":
            return True
        # 會寫入或刪除的指令：cp／mv／ln／install 只看目的地（最後一個參數），其餘看所有參數
        targets = args[-1:] if head in COPY_LIKE else args if head in FILE_WRITERS else []
        if any(os.path.basename(a) == APPROVED for a in targets):
            return True
    return False


def glob_base(path, pattern):
    """Glob 實際搜尋的目錄：path 加上 pattern 在第一個萬用字元之前的目錄部分（pattern 可能是絕對路徑或含 ..）。"""
    m = GLOB_CHARS.search(pattern)
    if not m:  # 沒有萬用字元：就是指定的那個路徑
        return pattern if pattern.startswith("/") else os.path.join(path, pattern)
    static = pattern[:m.start()]
    static = static.rsplit("/", 1)[0] if "/" in static else ""
    if pattern.startswith("/"):
        return static or "/"
    return os.path.join(path, static) if static else path


def rules_for(role, cfg, running=False):
    """回傳 (可讀前綴, 可寫前綴)。前綴以專案根目錄為基準；"" 代表整個專案。"""
    spec = dirs(cfg, "spec_dir", "spec/", force_dir=True)
    src = dirs(cfg, "src_dirs", ["src/"])
    tests = dirs(cfg, "test_dirs", ["tests/"])
    # 專案規範文件（CLAUDE.md、docs/conventions/…），所有流程角色唯讀
    ref = dirs(cfg, "reference_paths", [])
    if role == "prompt-builder":
        return (spec + ref + [".flow/prompts/", ".flow/runs/", ".flow/report.md", CONFIG],
                [".flow/prompts/"])
    if role == "coder":
        read = spec + ref + [".flow/prompts/coder.md", CONFIG] + src + dirs(cfg, "coder_read_paths", [])
        if cfg.get("coder_can_read_tests"):
            read += tests
        return read, src
    if role == "test-designer":
        read = spec + ref + [".flow/prompts/tester.md", CONFIG] + tests + dirs(cfg, "tester_read_paths", [])
        return read, tests
    if role == "consistency-checker":
        return [""], []
    if not running:
        # 流程沒在跑：主對話與其他 subagent 照常開發（含 /spec-draft 寫 spec 與 config）
        return [""], [""]
    # 指揮（流程執行中）與未知的 subagent：只讀流程檔，不寫任何檔案
    # examples/ 只供參考規格格式（唯讀）
    return spec + [".flow/", CONFIG, ".claude/flow/", "examples/"], []


def rel(root, cwd, p):
    if not p:
        return None
    full = os.path.realpath(p if os.path.isabs(p) else os.path.join(cwd, p))
    root = os.path.realpath(root)
    if full != root and not full.startswith(root + os.sep):
        return "<outside>"
    r = os.path.relpath(full, root)
    return "" if r == "." else r


def allowed(r, prefixes, is_dir=False):
    """r 是否在允許範圍內。is_dir 為 True（搜尋目錄）時，單一檔案的設定不算數：Grep 對目錄會遞迴搜尋。"""
    if r is None or r == "<outside>":
        return False
    for pre in prefixes:
        if pre == "":
            return True
        if pre.endswith("/"):
            if r.startswith(pre) or r == pre[:-1]:
                return True
        elif r == pre and not is_dir:
            return True
    return False


def decide(role, tool, ti, root, cwd, cfg, running):
    read, write = rules_for(role, cfg, running)
    free = role in {"main", "other"} and not running

    if role == "main" and tool == "Agent":
        st = ti.get("subagent_type", "")
        return (free or st in ROLES, "subagent_type=%s" % st)
    if tool == "Bash":
        cmd = ti.get("command", "").strip()
        if touches_approval(cmd):
            return False, cmd
        if free:
            return True, cmd
        if role == "main" and MAIN_BASH.match(cmd):
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
        # 沒給 path 等於搜尋整個專案；Glob 另外依 pattern 的目錄部分判斷實際搜尋範圍
        base = ti.get("path") or cwd
        if tool == "Glob":
            base = glob_base(base, ti.get("pattern", ""))
        r = rel(root, cwd, base)
        if r == "":
            return ("" in read), "<project root>"
        full = base if os.path.isabs(base) else os.path.join(cwd, base)
        return allowed(r, read, is_dir=not os.path.isfile(full)), r
    return True, "-"


def deny_hint(role, tool, target, running):
    if tool == "Bash" and touches_approval(str(target)) or (
            tool in WRITE_TOOLS and os.path.basename(str(target)) == APPROVED):
        return "（spec 確認只能由人執行：在終端機或 Claude Code 輸入 `! bash .claude/flow/approve_spec.sh`）"
    if role == "main" and tool == "Bash":
        return "（流程執行中，主對話只能單獨執行 `bash .claude/flow/<名稱>.sh [輪次]`，不可加 cd、&&、管線或其他指令）"
    if role == "main" and tool in WRITE_TOOLS and running:
        return "（流程執行中，spec 與 config 已鎖定；若流程中斷，人可刪除 .flow/ 解鎖）"
    if role == "main":
        return "（流程執行中，主對話只能讀規格目錄與流程檔，不能讀寫程式與測試目錄）"
    return ""


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
    # 未知的 subagent（例如 general-purpose、Explore）套用 other 規則。
    source = "frontmatter"
    if role == "main":
        source = "settings"
        if agent_type in ROLES:
            role = agent_type
        elif agent_type:
            role = "other"

    running = flow_running(root)
    ok, target = decide(role, tool, ti, root, cwd, load_config(root), running)

    # 平常開發不寫紀錄，避免 .flow/ 無限制成長
    if running or role in ROLES or not ok:
        os.makedirs(os.path.join(root, ".flow"), exist_ok=True)
        with open(os.path.join(root, ".flow", "audit.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": time.strftime("%H:%M:%S"), "source": source, "guard": role, "agent_type": agent_type,
                "tool": tool, "target": target, "decision": "allow" if ok else "deny",
            }, ensure_ascii=False) + "\n")

    if not ok:
        sys.stderr.write("[guard:%s] 不允許 %s %s%s\n" % (role, tool, target, deny_hint(role, tool, target, running)))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
