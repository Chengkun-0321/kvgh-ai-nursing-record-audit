"""guard.py 與 state.py check_config 的測試。

以專案實際的 flow.config.json 建立暫存專案，透過子行程呼叫 guard.py（與 hook 相同的呼叫方式）。
執行：python3 -m unittest discover -s .claude/flow/tests -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
GUARD = os.path.join(ROOT, ".claude", "hooks", "guard.py")


class GuardTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        shutil.copy(os.path.join(ROOT, "flow.config.json"), self.root)

    def tearDown(self):
        shutil.rmtree(self.root)

    def set_running(self, running):
        os.makedirs(os.path.join(self.root, ".flow"), exist_ok=True)
        with open(os.path.join(self.root, ".flow", "state.json"), "w", encoding="utf-8") as f:
            json.dump({"status": "running" if running else "done"}, f)

    def guard(self, tool, tool_input, role="main", agent_type=None):
        """回傳 True 表示允許（exit 0），False 表示阻擋（exit 2）。"""
        data = {"tool_name": tool, "tool_input": tool_input, "cwd": self.root}
        if agent_type:
            data["agent_type"] = agent_type
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.root)
        rc = subprocess.run([sys.executable, GUARD, role], input=json.dumps(data), text=True,
                            capture_output=True, env=env).returncode
        self.assertIn(rc, (0, 2))
        return rc == 0

    def read(self, path, **kw):
        return self.guard("Read", {"file_path": path}, **kw)

    def write(self, path, **kw):
        return self.guard("Write", {"file_path": path, "content": ""}, **kw)

    def bash(self, cmd, **kw):
        return self.guard("Bash", {"command": cmd}, **kw)


class MainNotRunningTest(GuardTestCase):
    """流程沒在跑：主對話照常開發，只有確認 spec 受限。"""

    def test_main_can_run_any_bash(self):
        self.assertTrue(self.bash("ls -la && git status"))

    def test_main_can_read_and_write_code(self):
        self.assertTrue(self.read("backend/app/main.py"))
        self.assertTrue(self.write("frontend/src/app/page.tsx"))

    def test_main_can_spawn_any_subagent(self):
        self.assertTrue(self.guard("Agent", {"subagent_type": "Explore"}))

    def test_other_subagent_unrestricted(self):
        self.assertTrue(self.read("backend/app/main.py", agent_type="Explore"))

    def test_finished_flow_counts_as_not_running(self):
        self.set_running(False)
        self.assertTrue(self.bash("ls"))

    def test_main_cannot_approve_spec(self):
        self.assertFalse(self.bash("bash .claude/flow/approve_spec.sh"))
        self.assertFalse(self.bash("cd x && ./.claude/flow/approve_spec.sh"))
        self.assertFalse(self.bash("FOO=1 sh .claude/flow/approve_spec.sh"))
        self.assertFalse(self.bash("python3 .claude/flow/state.py approve"))
        self.assertFalse(self.bash("echo x > spec/.approved"))
        self.assertFalse(self.bash("cp /tmp/a spec/.approved"))
        self.assertFalse(self.write("spec/.approved"))

    def test_main_cannot_approve_with_quotes_options_or_substitution(self):
        """引號、選項、命令替換、換行都要辨識（Codex 第二輪審查）。"""
        self.assertFalse(self.bash('bash ".claude/flow/approve_spec.sh"'))
        self.assertFalse(self.bash("bash -x .claude/flow/approve_spec.sh"))
        self.assertFalse(self.bash("python3 -B .claude/flow/state.py approve"))
        self.assertFalse(self.bash("echo $(bash .claude/flow/approve_spec.sh)"))
        self.assertFalse(self.bash("echo `bash .claude/flow/approve_spec.sh`"))
        self.assertFalse(self.bash("cd x\nbash .claude/flow/approve_spec.sh"))
        # 未加引號的 heredoc 會執行命令替換
        self.assertFalse(self.bash("cat <<EOF\n$(bash .claude/flow/approve_spec.sh)\nEOF"))

    def test_main_can_read_approval_files(self):
        """唯讀操作不擋（Codex 審查第 7 點）；加引號的 heredoc 內容是資料。"""
        self.assertTrue(self.bash("cat spec/.approved"))
        self.assertTrue(self.bash("cp spec/.approved /tmp/approval-backup"))
        self.assertTrue(self.bash('echo "cp spec/.approved backup"'))
        self.assertTrue(self.bash("git diff HEAD -- .claude/flow/approve_spec.sh"))
        self.assertTrue(self.bash("python3 - <<'EOF'\ntext = '`approve_spec.sh` 只能由人執行'\nEOF"))


class MainRunningTest(GuardTestCase):
    """流程執行中：主對話只能指揮。"""

    def setUp(self):
        super().setUp()
        self.set_running(True)

    def test_main_bash_limited_to_flow_scripts(self):
        self.assertFalse(self.bash("ls"))
        self.assertTrue(self.bash("bash .claude/flow/run_tests.sh 1"))
        self.assertFalse(self.bash("bash .claude/flow/approve_spec.sh"))

    def test_main_cannot_read_code_or_write_spec(self):
        self.assertFalse(self.read("backend/app/main.py"))
        self.assertTrue(self.read("spec/rules.md"))
        self.assertFalse(self.write("spec/rules.md"))

    def test_main_glob_uses_pattern_directory(self):
        """Glob 依 pattern 的目錄部分判斷（Codex 審查第 6 點）。"""
        self.assertTrue(self.guard("Glob", {"pattern": "spec/*.md"}))
        self.assertFalse(self.guard("Glob", {"path": "spec/", "pattern": "../backend/tests/**"}))
        self.assertFalse(self.guard("Glob", {"path": "spec/", "pattern": self.root + "/backend/tests/*.py"}))

    def test_main_can_only_spawn_flow_roles(self):
        self.assertFalse(self.guard("Agent", {"subagent_type": "Explore"}))
        self.assertTrue(self.guard("Agent", {"subagent_type": "coder"}))


class FlowRoleTest(GuardTestCase):
    """流程角色不論是否執行中都受限（以 settings 層的 agent_type 判斷）。"""

    def test_coder_reads_reference_and_code_but_not_tests(self):
        kw = {"agent_type": "coder"}
        self.assertTrue(self.read("docs/conventions/audit-rules.md", **kw))
        self.assertTrue(self.read("CLAUDE.md", **kw))
        self.assertTrue(self.read("backend/app/services/llm/gateway.py", **kw))
        self.assertFalse(self.read("backend/tests/conftest.py", **kw))
        self.assertFalse(self.read("frontend/tests/lib/sse.test.ts", **kw))
        self.assertFalse(self.bash("ls", **kw))

    def test_coder_cannot_write_lint_or_migration(self):
        kw = {"agent_type": "coder"}
        self.assertTrue(self.write("backend/app/services/audit/base.py", **kw))
        self.assertFalse(self.write("backend/pyproject.toml", **kw))
        self.assertFalse(self.write("backend/requirements-dev.txt", **kw))
        self.assertFalse(self.write("backend/alembic/versions/x.py", **kw))
        self.assertFalse(self.write("frontend/eslint.config.mjs", **kw))

    def test_single_file_path_is_exact(self):
        """沒有尾斜線的設定是單一檔案（Codex 審查第 11 點）。"""
        kw = {"agent_type": "coder"}
        self.assertTrue(self.write("frontend/package.json", **kw))
        self.assertFalse(self.write("frontend/package.json/extra", **kw))
        self.assertFalse(self.read("CLAUDE.md.bak", **kw))

    def test_glob_exact_file_uses_file_rule(self):
        """沒有萬用字元的 Glob 就是該檔案，依單檔權限判斷（Codex 第二輪審查）。"""
        with open(os.path.join(self.root, "CLAUDE.md"), "w", encoding="utf-8"):
            pass
        self.assertTrue(self.guard("Glob", {"pattern": "CLAUDE.md"}, agent_type="coder"))

    def test_search_directory_declared_as_file_is_denied(self):
        """目錄被寫成單一檔案（沒有尾斜線）時，搜尋該目錄不放行：Grep 會遞迴（Codex 第二輪審查）。"""
        os.makedirs(os.path.join(self.root, "backend", "app"))
        cfg_path = os.path.join(self.root, "flow.config.json")
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["tester_read_paths"] = ["backend/app"]
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        kw = {"agent_type": "test-designer"}
        self.assertFalse(self.guard("Grep", {"pattern": "x", "path": "backend/app"}, **kw))
        self.assertFalse(self.guard("Glob", {"pattern": "backend/app"}, **kw))

    def test_tester_cannot_read_code(self):
        kw = {"agent_type": "test-designer"}
        self.assertFalse(self.read("backend/app/main.py", **kw))
        self.assertFalse(self.read("frontend/src/lib/sse.ts", **kw))
        self.assertTrue(self.read("backend/tests/conftest.py", **kw))
        self.assertTrue(self.read("docs/conventions/testing.md", **kw))
        self.assertTrue(self.write("frontend/vitest.config.mts", **kw))

    def test_tester_read_paths(self):
        cfg_path = os.path.join(self.root, "flow.config.json")
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["test_dirs"] = ["backend/tests/services/audit/"]
        cfg["tester_read_paths"] = ["backend/tests/conftest.py"]
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        kw = {"agent_type": "test-designer"}
        self.assertTrue(self.read("backend/tests/conftest.py", **kw))
        self.assertFalse(self.write("backend/tests/conftest.py", **kw))
        self.assertFalse(self.read("backend/tests/core/test_security.py", **kw))


class CheckConfigTest(unittest.TestCase):
    """state.py check_config：讀寫範圍不得破壞隔離。"""

    def passes(self, dirs_to_create=(), **overrides):
        """在暫存專案（複製 state.py、guard.py）執行 check_config，回傳是否通過。"""
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        for sub in (".claude/flow", ".claude/hooks", *dirs_to_create):
            os.makedirs(os.path.join(root, sub))
        shutil.copy(os.path.join(ROOT, ".claude", "flow", "state.py"), os.path.join(root, ".claude", "flow"))
        shutil.copy(GUARD, os.path.join(root, ".claude", "hooks"))
        with open(os.path.join(ROOT, "flow.config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        cfg.update(overrides)
        with open(os.path.join(root, "flow.config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        rc = subprocess.run([sys.executable, os.path.join(root, ".claude", "flow", "state.py"), "check_config"],
                            capture_output=True, text=True).returncode
        return rc == 0

    def test_project_config_passes(self):
        self.assertTrue(self.passes())

    def test_tester_reading_code_is_rejected(self):
        self.assertFalse(self.passes(tester_read_paths=["backend/app/core/"]))

    def test_reference_overlapping_tests_is_rejected(self):
        self.assertFalse(self.passes(reference_paths=["backend/"]))

    def test_src_and_tests_overlap_is_rejected(self):
        self.assertFalse(self.passes(test_dirs=["backend/app/tests/"]))

    def test_root_as_src_is_rejected(self):
        self.assertFalse(self.passes(src_dirs=["."]))

    def test_spec_dir_counts_as_readable(self):
        """規格目錄所有角色都可讀，不得與程式重疊（Codex 審查第 1 點）。"""
        self.assertFalse(self.passes(spec_dir="backend/app/"))

    def test_writable_control_files_are_rejected(self):
        """可寫範圍不得碰到流程控制檔（Codex 審查第 2 點）。"""
        self.assertFalse(self.passes(src_dirs=["backend/app/", "flow.config.json"]))
        self.assertFalse(self.passes(test_dirs=["backend/tests/", ".claude/"]))
        self.assertFalse(self.passes(src_dirs=["backend/app/", "spec/rules.md"]))
        # 尾斜線不影響重疊判定（Codex 第二輪審查）
        self.assertFalse(self.passes(src_dirs=["backend/app/", "flow.config.json/"]))

    def test_directory_without_trailing_slash_is_rejected(self):
        """實際是目錄卻沒加 /（Codex 第二輪審查）。"""
        self.assertFalse(self.passes(dirs_to_create=["backend/app"], tester_read_paths=["backend/app"]))
        self.assertFalse(self.passes(dirs_to_create=["backend/tests"], reference_paths=["backend/tests"]))


if __name__ == "__main__":
    unittest.main()
