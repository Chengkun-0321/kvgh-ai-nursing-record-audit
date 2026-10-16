#!/usr/bin/env python3
"""流程狀態 .flow/state.json 的唯一寫入者（AI 不直接寫）。

  state.py init
  state.py test <N> <exit_code>
  state.py finish
  state.py config <key>   印出 flow.config.json 的欄位（缺少時印空字串）
  state.py approve        人確認 spec：記錄 spec 與 config 的雜湊到 <spec_dir>/.approved
  state.py check_spec     檢查 spec 已確認且確認後未被修改，否則 exit 1
  state.py check_config   檢查 flow.config.json 的角色讀寫範圍不會破壞隔離，否則 exit 1
  state.py check_deps     依 flow.config.json 的 deps_check 檢查套件白名單，有未允許的套件則 exit 1
"""
import hashlib
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FLOW = os.path.join(ROOT, ".flow")
PATH = os.path.join(FLOW, "state.json")


def load():
    with open(PATH, encoding="utf-8") as f:
        return json.load(f)


def save(st):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)


def config():
    with open(os.path.join(ROOT, "flow.config.json"), encoding="utf-8") as f:
        return json.load(f)


APPROVED = ".approved"
SPEC_FILES = ["architecture.md", "boundaries.md", "rules.md"]


def spec_dir():
    return os.path.join(ROOT, config().get("spec_dir", "spec/"))


def spec_hash():
    """architecture.md、boundaries.md、rules.md、flow.config.json 的內容雜湊；缺檔時回傳 (None, 缺少的檔案)。"""
    paths = [os.path.join(spec_dir(), f) for f in SPEC_FILES] + [os.path.join(ROOT, "flow.config.json")]
    missing = [os.path.relpath(p, ROOT) for p in paths if not os.path.exists(p)]
    if missing:
        return None, missing
    h = hashlib.sha256()
    for p in paths:
        h.update(os.path.relpath(p, ROOT).encode() + b"\0")
        with open(p, "rb") as f:
            h.update(f.read() + b"\0")
    return h.hexdigest(), []


def norm_pip(name):
    """PEP 503：pip 套件名稱不分大小寫，_ . - 視為相同。"""
    return re.sub(r"[-_.]+", "-", name).lower()


def declared_deps(kind, path):
    """回傳套件檔宣告的套件名稱（小寫）。kind = pip | npm。"""
    if kind == "npm":
        with open(path, encoding="utf-8") as f:
            pkg = json.load(f)
        return [n.lower() for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
                for n in (pkg.get(key) or {})]
    names = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("-"):
                # -r、-e、--index-url 等選項可能引入白名單外的來源，一律視為違規
                names.append(line)
                continue
            names.append(norm_pip(re.split(r"[\s\[<>=!~;@]", line, maxsplit=1)[0]))
    return names


def config_problems(cfg):
    """檢查角色的讀寫範圍不會破壞隔離；回傳問題清單（空清單表示通過）。前綴邏輯與 guard 相同。"""
    sys.path.insert(0, os.path.join(ROOT, ".claude", "hooks"))
    import guard

    def hit(x, y):
        """兩個路徑是否重疊：去掉尾斜線後相同（guard 允許目錄前綴本身），或其中一個是目錄且包含另一個。"""
        return (x.rstrip("/") == y.rstrip("/") or (x.endswith("/") and y.startswith(x))
                or (y.endswith("/") and x.startswith(y)))

    def overlaps(a, b):
        return sorted({"%s ↔ %s" % (x, y) for x in a for y in b if hit(x, y)})

    problems = []
    # 沒有尾斜線代表單一檔案；實際是目錄卻沒加 / 會讓 guard 與本檢查的判斷不一致
    for key in ("src_dirs", "test_dirs", "reference_paths", "coder_read_paths", "tester_read_paths"):
        raw = cfg.get(key) or []
        for d in [raw] if isinstance(raw, str) else raw:
            if not d.endswith("/") and os.path.isdir(os.path.join(ROOT, d)):
                problems.append("%s 的 %s 是目錄，結尾要加 /" % (key, d))
    for key in ("src_dirs", "test_dirs"):
        raw = cfg.get(key) or []
        raw = [raw] if isinstance(raw, str) else raw
        if not guard.dirs(cfg, key, []):
            problems.append("%s 不可為空" % key)
        if any(os.path.normpath(d).strip("/") in ("", ".") for d in raw):
            problems.append("%s 不可設為專案根目錄" % key)
    spec = guard.dirs(cfg, "spec_dir", "spec/", force_dir=True)
    src = guard.dirs(cfg, "src_dirs", [])
    tests = guard.dirs(cfg, "test_dirs", [])
    ref = guard.dirs(cfg, "reference_paths", [])
    coder_extra = guard.dirs(cfg, "coder_read_paths", [])
    tester_extra = guard.dirs(cfg, "tester_read_paths", [])
    # 角色的有效讀取範圍與 guard.rules_for() 相同：規格目錄、參考文件、自己的目錄與額外可讀路徑
    coder_read = spec + ref + src + coder_extra
    tester_read = spec + ref + tests + tester_extra
    # 流程控制檔：寫得到就能在執行中擴權或改規格
    control = spec + [guard.CONFIG, ".claude/", ".flow/", ".git/"]
    for pair in overlaps(src + tests, control):
        problems.append("可寫範圍包含流程控制檔：" + pair)
    for pair in overlaps(src, tests):
        problems.append("src_dirs 與 test_dirs 重疊：" + pair)
    for pair in overlaps(tester_read, src + coder_extra):
        problems.append("test-designer 可讀到程式：" + pair)
    if not cfg.get("coder_can_read_tests"):
        for pair in overlaps(coder_read, tests + tester_extra):
            problems.append("coder 可讀到測試：" + pair)
    return problems


def last_line(path):
    with open(path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    return lines[-1] if lines else ""


cmd = sys.argv[1]
if cmd == "config":
    v = config().get(sys.argv[2], "")
    print(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))

elif cmd == "approve":
    digest, missing = spec_hash()
    if missing:
        print("無法確認：缺少 " + "、".join(missing))
        sys.exit(1)
    problems = config_problems(config())
    if problems:
        print("無法確認：flow.config.json 的讀寫範圍會破壞隔離。" + "；".join(problems))
        sys.exit(1)
    path = os.path.join(spec_dir(), APPROVED)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"sha256": digest, "approved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "files": [os.path.join(config().get("spec_dir", "spec/"), x) for x in SPEC_FILES]
                   + ["flow.config.json"]}, f, ensure_ascii=False, indent=2)
    print("spec 已確認：%s（%s）" % (os.path.relpath(path, ROOT), digest[:12]))

elif cmd == "check_spec":
    digest, missing = spec_hash()
    path = os.path.join(spec_dir(), APPROVED)
    if missing:
        print("無法開始：缺少 " + "、".join(missing) + "。請先用 /spec-draft 建立規格。")
        sys.exit(1)
    if not os.path.exists(path):
        print("無法開始：spec 尚未經人確認。請人執行 bash .claude/flow/approve_spec.sh。")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        if json.load(f).get("sha256") != digest:
            print("無法開始：spec 或 flow.config.json 在確認後被修改。請人重新檢查後執行 bash .claude/flow/approve_spec.sh。")
            sys.exit(1)
    print("spec 已確認（%s）" % digest[:12])

elif cmd == "check_config":
    problems = config_problems(config())
    if problems:
        print("無法開始：flow.config.json 的讀寫範圍會破壞隔離。" + "；".join(problems))
        sys.exit(1)
    print("flow.config.json 讀寫範圍檢查通過")

elif cmd == "check_deps":
    bad = []
    for item in config().get("deps_check") or []:
        path = os.path.join(ROOT, item["file"])
        if not os.path.exists(path):
            continue  # 檔案還沒產生時由 setup／test 自然失敗
        kind = item.get("type", "pip")
        allow = {norm_pip(a) if kind == "pip" else a.lower() for a in item.get("allow", [])}
        try:
            names = declared_deps(kind, path)
        except ValueError as e:
            bad.append("%s 無法解析（%s）" % (item["file"], e))
            continue
        bad += ["%s：%s" % (item["file"], n) for n in names if n not in allow]
    if bad:
        print("套件未經允許：" + "；".join(bad))
        sys.exit(1)
    print("套件白名單檢查通過")

elif cmd == "init":
    os.makedirs(os.path.join(FLOW, "prompts"), exist_ok=True)
    os.makedirs(os.path.join(FLOW, "runs"), exist_ok=True)
    save({"status": "running", "round": 0, "last_test": None, "history": [],
          "max_rounds": config()["max_rounds"], "started": time.strftime("%Y-%m-%d %H:%M:%S")})
    print("流程初始化完成，max_rounds=%d" % config()["max_rounds"])

elif cmd == "test":
    n, rc = int(sys.argv[2]), int(sys.argv[3])
    st = load()
    st["round"] = n
    st["last_test"] = "pass" if rc == 0 else "fail"
    st["last_test_time"] = time.time()
    st["history"].append({"round": n, "test": st["last_test"], "time": time.strftime("%H:%M:%S")})
    save(st)

elif cmd == "finish":
    st = load()
    report = os.path.join(FLOW, "report.md")
    problems = []
    if not os.path.exists(report):
        problems.append("缺少 .flow/report.md")
    elif os.path.getmtime(report) < st.get("last_test_time", 0):
        problems.append("report.md 比最後一輪測試舊")
    if st.get("last_test") is None:
        problems.append("沒有任何一輪測試紀錄")
    if problems:
        print("無法結束：" + "；".join(problems))
        sys.exit(1)
    summary = last_line(report)
    consistent = summary.replace(" ", "") == "總結：一致"
    # 測試通過且一致性報告為「一致」才算 done；其他情況交給人判斷
    st["status"] = "done" if st["last_test"] == "pass" and consistent else "needs_review"
    st["consistency"] = summary
    st["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save(st)
    print("流程結束：status=%s，共 %d 輪，最後測試=%s，%s。等待 ⑧ 人審。"
          % (st["status"], st["round"], st["last_test"], summary or "報告沒有總結行"))
