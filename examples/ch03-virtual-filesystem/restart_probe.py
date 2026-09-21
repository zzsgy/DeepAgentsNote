"""由 lifecycle 实验启动的独立 Python 进程；只读取指定测试目录。"""

import json
import sys
from pathlib import Path

from lab.driver import Driver
from lab.report import PROJECT
from deepagents.backends import FilesystemBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore


def main():
    root = Path(sys.argv[1]).resolve()
    if not root.is_relative_to((PROJECT / "runs").resolve()) or not root.is_dir():
        raise ValueError("独立进程只能读取本项目 runs 内的实验目录")
    fs = Driver(FilesystemBackend(root_dir=str(root), virtual_mode=True))
    state = Driver(StateBackend())
    store = Driver(StoreBackend(namespace=lambda _: ("alice",)), store=InMemoryStore())
    print(json.dumps({
        "disk_found": "DISK_MARKER" in str(fs.call("read_file", file_path="/memo.txt").content),
        "state_found": state.call("read_file", file_path="/memo.txt").status == "success",
        "store_found": store.call("read_file", file_path="/memo.txt").status == "success",
    }))


if __name__ == "__main__":
    main()
