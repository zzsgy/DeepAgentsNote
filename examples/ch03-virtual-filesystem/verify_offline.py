"""PyCharm 中右键本文件 → Run。默认运行全部对比实验。"""

import argparse
import sys


def main():
    if sys.version_info[:2] != (3, 12):
        print("请在 PyCharm 中选择本项目 .venv/Scripts/python.exe（Python 3.12）。")
        return 2
    try:
        from lab.experiments import EXPERIMENTS, run_suite
    except ModuleNotFoundError as exc:
        print(f"缺少依赖：{exc}\n请在本项目目录执行 uv sync --frozen，再选择本项目的解释器。")
        return 2
    parser = argparse.ArgumentParser(description="Deep Agents 第三章离线对比实验")
    parser.add_argument("--only", choices=EXPERIMENTS, help="只运行一组实验；不填则全部运行")
    args = parser.parse_args()
    print("真实 Deep Agents 文件工具 / 无 API Key / 不调用外部大模型", flush=True)
    report, result = run_suite(args.only)
    print(f"\n结果：{result['passed']}/{result['total']} 检查通过")
    print(f"实验记录：{report.root / 'REPORT.md'}")
    print(f"原始工具调用：{report.root / 'results.json'}")
    print("每次运行新建独立目录；delete 仅删除本次新建的 disposable.txt 测试文件。")
    print("自动通过不代表已掌握；请完成 ../../notes/ch03-virtual-filesystem.md 的预测与修改题。")
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
