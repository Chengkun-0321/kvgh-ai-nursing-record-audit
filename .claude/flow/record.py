#!/usr/bin/env python3
"""流程節點紀錄：把每個節點的輸入、過程、輸出存到 flow-records/<開始時間>/，供事後報告使用。

  record.py init            flow_init.sh 呼叫：建立本次紀錄目錄，快照 spec 與 config，搬入 _pending/ 的檔案
  record.py tests <N> <rc>  run_tests.sh 呼叫：保存第 N 輪測試 log
  record.py index           finish.sh 呼叫：依 events.jsonl 產生 index.md
  record.py backfill <目錄名>  補齊舊紀錄中空白的「輸出」段

subagent 的紀錄由 .claude/hooks/capture_report.py 呼叫 record_subagent()。
紀錄目錄不在 .flow/ 底下，重跑流程不會被清掉；flow-records/ 不進版控。
"""
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FLOW = os.path.join(ROOT, ".flow")
RECORDS = os.path.join(ROOT, "flow-records")
PENDING = os.path.join(RECORDS, "_pending")

# 節點編號與名稱，對應 senior-flow 的步驟
NODES = {
    "prompt-builder": ("03", "③ Prompt Builder"),
    "coder": ("04", "④ Coding Agent"),
    "test-designer": ("05", "⑤ Test Design Agent"),
    "consistency-checker": ("07", "⑦ 一致性 Agent"),
}
# coder／test-designer 的 diff 範圍取自 flow.config.json 的這個欄位
DIFF_SCOPE = {"coder": "src_dirs", "test-designer": "test_dirs"}


def load_state():
    try:
        with open(os.path.join(FLOW, "state.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load_config():
    with open(os.path.join(ROOT, "flow.config.json"), encoding="utf-8") as f:
        return json.load(f)


def run_dir(st):
    """本次流程的紀錄目錄，以 state.json 的 started 命名，例：flow-records/20261017-153000/。"""
    stamp = st.get("started", "unknown").replace("-", "").replace(":", "").replace(" ", "-")
    path = os.path.join(RECORDS, stamp)
    os.makedirs(path, exist_ok=True)
    return path


def add_event(base, **event):
    event = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), **event}
    with open(os.path.join(base, "events.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def unique_path(path):
    """同一輪同一角色被呼叫多次時，加上序號避免覆寫。"""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    i = 2
    while os.path.exists("%s-%d%s" % (stem, i, ext)):
        i += 1
    return "%s-%d%s" % (stem, i, ext)


# ---------- transcript 解析 ----------

def read_transcript(path):
    entries = []
    if not path or not os.path.exists(path):
        return entries
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    return entries


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
    return ""


def tool_target(name, ti):
    for key in ("file_path", "notebook_path", "command", "pattern", "path", "url", "subagent_type"):
        if ti.get(key):
            value = str(ti[key]).replace("\n", " ⏎ ")
            return value[:200] + ("…" if len(value) > 200 else "")
    return ""


def summarize(entries):
    """回傳 (輸入文字, 過程步驟清單)。過程只含實際動作；transcript 不含模型內部思考。"""
    first_input = ""
    steps = []
    errors = {}
    for e in entries:
        msg = e.get("message") or {}
        content = msg.get("content")
        if e.get("type") == "user" and isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                    errors[c.get("tool_use_id")] = True
        if e.get("type") == "user" and not first_input:
            first_input = text_of(content)
        if e.get("type") == "assistant" and isinstance(content, list):
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_use":
                    steps.append([c.get("id"), c.get("name", ""), tool_target(c.get("name", ""), c.get("input") or {})])
                elif c.get("type") == "text" and c.get("text", "").strip():
                    steps.append([None, "說明", c["text"].strip().replace("\n", " ")[:200]])
    for s in steps:
        s.append(bool(s[0] and errors.get(s[0])))
    return first_input, steps


def handback_text(entries):
    """subagent 以交回工具（名稱含 Handback）回報時，最終輸出在該工具的輸入裡，不在最後回覆。"""
    found = ""
    for e in entries:
        content = (e.get("message") or {}).get("content")
        if e.get("type") != "assistant" or not isinstance(content, list):
            continue
        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_use" and "andback" in c.get("name", ""):
                texts = [v for v in (c.get("input") or {}).values() if isinstance(v, str)]
                found = max(texts, key=len, default=found)
    return found


def final_output(data, entries):
    return (data.get("last_assistant_message") or "").strip() or handback_text(entries).strip()


def git_diff(paths):
    """相對 HEAD 的累積 diff，加上未追蹤的新檔。"""
    if not paths:
        return ""
    run = lambda args: subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout
    out = run(["git", "diff", "HEAD", "--"] + paths)
    for f in run(["git", "ls-files", "--others", "--exclude-standard", "--"] + paths).splitlines():
        out += run(["git", "diff", "--no-index", "--", "/dev/null", f])
    return out


# ---------- 各節點 ----------

def record_subagent(data):
    st = load_state()
    if not st or st.get("status") != "running":
        return  # 只記錄流程執行中的節點
    agent_type = data.get("agent_type") or ""
    if agent_type not in NODES:
        return  # 只記錄流程角色；agent_type 為空的事件不是流程節點
    num, label = NODES[agent_type]
    rnd = st.get("round", 0) if agent_type == "consistency-checker" else st.get("round", 0) + 1
    base = run_dir(st)
    rdir = os.path.join(base, "round-%d" % rnd)
    os.makedirs(rdir, exist_ok=True)
    stem = unique_path(os.path.join(rdir, "%s-%s.md" % (num, agent_type)))[:-3]

    transcript = data.get("agent_transcript_path")
    entries = read_transcript(transcript)
    first_input, steps = summarize(entries)
    output = final_output(data, entries)
    files = []

    if transcript and os.path.exists(transcript):
        shutil.copyfile(transcript, stem + ".jsonl")
        files.append(os.path.basename(stem + ".jsonl"))
    if agent_type in DIFF_SCOPE:
        diff = git_diff(load_config().get(DIFF_SCOPE[agent_type], []))
        with open(stem + ".diff", "w", encoding="utf-8") as f:
            f.write(diff)
        files.append(os.path.basename(stem + ".diff"))
    if agent_type == "prompt-builder":
        src = os.path.join(FLOW, "prompts")
        dst = stem + "-prompts"
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
            files.append(os.path.basename(dst) + "/")

    lines = [
        "# %s（第 %d 輪）" % (label, rnd), "",
        "- 結束時間：%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "- 角色定義：`.claude/agents/%s.md`" % agent_type,
        "- 其他檔案：%s" % ("、".join("`%s`" % f for f in files) or "無"), "",
        "## 輸入（指揮傳給此角色的訊息）", "", "```text", first_input.strip(), "```", "",
        "## 過程（依序的動作；transcript 不含模型內部思考）", "",
        "| # | 動作 | 目標 | 錯誤 |", "|---|---|---|---|",
    ]
    for i, (_, name, target, err) in enumerate(steps, 1):
        lines.append("| %d | %s | `%s` | %s |" % (i, name, target.replace("|", "\\|").replace("`", "'"), "是" if err else ""))
    lines += ["", "## 輸出（最終回覆）", "", output.strip(), ""]
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    files.insert(0, os.path.basename(stem + ".md"))
    add_event(base, node=label, agent_type=agent_type, round=rnd,
              steps=len(steps), files=["round-%d/%s" % (rnd, f) for f in files])


def cmd_backfill(base):
    """補齊舊紀錄中空白的「輸出」段（交回工具的內容當時沒被擷取）。"""
    marker = "## 輸出（最終回覆）"
    fixed = 0
    for rdir in sorted(d for d in os.listdir(base) if d.startswith("round-")):
        for name in sorted(os.listdir(os.path.join(base, rdir))):
            if not name.endswith(".md"):
                continue
            md = os.path.join(base, rdir, name)
            jsonl = md[:-3] + ".jsonl"
            text = open(md, encoding="utf-8").read()
            head, sep, tail = text.partition(marker)
            if not sep or tail.strip() or not os.path.exists(jsonl):
                continue
            output = handback_text(read_transcript(jsonl)).strip()
            if output:
                with open(md, "w", encoding="utf-8") as f:
                    f.write(head + marker + "\n\n" + output + "\n")
                fixed += 1
    print("補齊 %d 份節點紀錄的輸出" % fixed)


def cmd_init():
    st = load_state()
    base = run_dir(st)
    snap = os.path.join(base, "00-spec-snapshot")
    os.makedirs(snap, exist_ok=True)
    spec = os.path.join(ROOT, load_config().get("spec_dir", "spec/"))
    for name in ("architecture.md", "boundaries.md", "rules.md", ".approved"):
        if os.path.exists(os.path.join(spec, name)):
            shutil.copyfile(os.path.join(spec, name), os.path.join(snap, name))
    shutil.copyfile(os.path.join(ROOT, "flow.config.json"), os.path.join(snap, "flow.config.json"))
    moved = []
    if os.path.isdir(PENDING):
        for name in sorted(os.listdir(PENDING)):
            shutil.move(os.path.join(PENDING, name), os.path.join(base, name))
            moved.append(name)
        os.rmdir(PENDING)
    add_event(base, node="⓪ 需求釐清＋② 人確認規格", round=0, files=moved + ["00-spec-snapshot/"])
    print("流程紀錄目錄：%s" % os.path.relpath(base, ROOT))


def cmd_tests(n, rc):
    st = load_state()
    base = run_dir(st)
    rdir = os.path.join(base, "round-%d" % n)
    os.makedirs(rdir, exist_ok=True)
    log = os.path.join(FLOW, "runs", "round-%d.log" % n)
    if os.path.exists(log):
        shutil.copyfile(log, os.path.join(rdir, "06-tests.log"))
    add_event(base, node="⑥ 跑測試", round=n, result="通過" if rc == 0 else "失敗",
              files=["round-%d/06-tests.log" % n])


def cmd_index():
    st = load_state()
    base = run_dir(st)
    events = []
    path = os.path.join(base, "events.jsonl")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            events = [json.loads(line) for line in f if line.strip()]
    lines = [
        "# 流程紀錄 %s" % os.path.basename(base), "",
        "- 開始：%s；結束：%s" % (st.get("started", "-"), st.get("finished", "-")),
        "- 狀態：%s；輪數：%s；最後測試：%s" % (st.get("status"), st.get("round"), st.get("last_test")),
        "- 一致性：%s" % (st.get("consistency") or "-"), "",
        "| # | 時間 | 輪次 | 節點 | 結果／動作數 | 檔案 |", "|---|---|---|---|---|---|",
    ]
    for i, e in enumerate(events, 1):
        result = e.get("result") or ("%s 個動作" % e["steps"] if "steps" in e else "")
        files = "<br>".join("[%s](%s)" % (f, f) for f in e.get("files", []))
        lines.append("| %d | %s | %s | %s | %s | %s |" % (i, e["ts"], e.get("round", ""), e["node"], result, files))
    lines += ["", "⑧ 人審：由人閱讀 `.flow/report.md` 後決定（結果請補記於此）。", ""]
    with open(os.path.join(base, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("流程紀錄索引：%s" % os.path.relpath(os.path.join(base, "index.md"), ROOT))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "init":
        cmd_init()
    elif cmd == "tests":
        cmd_tests(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "index":
        cmd_index()
    elif cmd == "backfill":
        cmd_backfill(os.path.join(RECORDS, sys.argv[2]))
    else:
        print(__doc__)
        sys.exit(1)
