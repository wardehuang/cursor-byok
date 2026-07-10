#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
LOG_PATH = SCRIPT_DIR / "build.log"
BUILD_ZIP = PROJECT_ROOT / "bin" / "windows-64.zip"
RAW_EXE = PROJECT_ROOT / "bin" / "windows-64.exe"
RELEASE_DIR = PROJECT_ROOT / "release"
OUTPUT_EXE = RELEASE_DIR / "cursor-byok.exe"
TASK_COMMAND = ["task", "build"]


def clean_logs() -> None:
    for path in SCRIPT_DIR.glob("*.log"):
        if path.is_file():
            path.unlink()


def ensure_task_available() -> None:
    if shutil.which(TASK_COMMAND[0]) is None:
        raise RuntimeError("未检测到 task，请先安装 Task CLI，并确保 task 在 PATH 中。")


def write_log(line: str) -> None:
    with LOG_PATH.open("a", encoding="utf-8", errors="replace") as log:
        log.write(line)
        log.flush()


def run_build() -> None:
    ensure_task_available()
    write_log(f"$ {' '.join(TASK_COMMAND)}\n")

    process = subprocess.Popen(
        TASK_COMMAND,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
        write_log(line)

    return_code = process.wait()
    if return_code == 0:
        return

    if RAW_EXE.is_file():
        write_log(
            "\nWARNING: task build 未完成 ZIP 阶段，但 Windows exe 已生成，"
            "继续复制 exe 到 release。\n"
        )
        return

    raise RuntimeError(f"编译打包失败，退出码：{return_code}。日志：{LOG_PATH}")


def publish_exe() -> None:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    temp_output = OUTPUT_EXE.with_suffix(".exe.tmp")

    if RAW_EXE.is_file():
        shutil.copyfile(RAW_EXE, temp_output)
        temp_output.replace(OUTPUT_EXE)
        return

    extract_exe_from_zip(temp_output)


def extract_exe_from_zip(temp_output: Path) -> None:
    if not BUILD_ZIP.is_file():
        raise FileNotFoundError(f"未找到构建产物：{BUILD_ZIP}")

    with zipfile.ZipFile(BUILD_ZIP) as archive:
        exe_entries = [name for name in archive.namelist() if name.lower().endswith(".exe")]
        if not exe_entries:
            raise RuntimeError(f"构建包内没有 exe：{BUILD_ZIP}")

        preferred = "windows-64.exe"
        exe_entry = preferred if preferred in exe_entries else exe_entries[0]
        with archive.open(exe_entry) as source, temp_output.open("wb") as target:
            shutil.copyfileobj(source, target)

    temp_output.replace(OUTPUT_EXE)


def main() -> int:
    clean_logs()
    try:
        run_build()
        publish_exe()
    except Exception as error:
        message = f"\nERROR: {error}\n"
        print(message, file=sys.stderr)
        write_log(message)
        return 1

    message = f"\n完成：{OUTPUT_EXE}\n"
    print(message)
    write_log(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())