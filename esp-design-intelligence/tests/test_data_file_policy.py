"""Safeguards for the repository's preventive data-file policy."""

import subprocess

from tools import check_repository_data as guard


def test_blocks_common_data_files_case_insensitively():
    names = [
        "exports/Well001.XLSX", "well.csv", "results.parquet",
        "storage.SQLITE", "backup.ZIP", "history.jsonl",
    ]
    assert guard.blocked_paths(names) == sorted(names)


def test_allows_normal_source_docs_and_generated_code():
    names = [
        "esp-design-intelligence/app.py",
        "esp-design-intelligence/README.md",
        ".github/workflows/esp-tests.yml",
    ]
    assert guard.blocked_paths(names) == []


def test_staged_check_catches_data_file_before_push(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "app.py").write_text("print('synthetic')\n")
    (tmp_path / "private.XLSX").write_text("test fixture, not real data\n")
    subprocess.run(["git", "add", "app.py", "private.XLSX"], cwd=tmp_path, check=True)
    monkeypatch.setattr(guard, "REPOSITORY_ROOT", tmp_path)
    assert guard.blocked_paths(
        guard.git_paths("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    ) == ["private.XLSX"]
    assert guard.main(["--staged"]) == 1
