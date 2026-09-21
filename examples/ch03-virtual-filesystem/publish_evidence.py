"""把本项目一次离线运行的结果脱敏到 evidence；不读取 .env 或其他目录。"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", help="verify_offline.py 打印的本次 runs 子目录")
    args = parser.parse_args()
    project = Path(__file__).resolve().parent
    source = Path(args.run_directory).resolve()
    if not source.is_relative_to((project / "runs").resolve()):
        raise ValueError("只接受本项目 runs 内的结果")
    data = json.loads((source / "results.json").read_text(encoding="utf-8"))
    report = (source / "REPORT.md").read_text(encoding="utf-8")
    replacements = sorted(
        {str(project): "<LAB_ROOT>", project.as_posix(): "<LAB_ROOT>"}.items(),
        key=lambda item: len(item[0]), reverse=True,
    )

    def sanitize(value):
        if isinstance(value, str):
            for old, new in replacements:
                value = value.replace(old, new)
            return value
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        if isinstance(value, dict):
            return {key: sanitize(item) for key, item in value.items()}
        return value

    data = sanitize(data)
    data["evidence_type"] = "scripted-model-real-tools-and-backends"
    data["exported_at_utc"] = datetime.now(timezone.utc).isoformat()
    data["source_run"] = source.name
    data["redaction"] = "Only the local project path is replaced by <LAB_ROOT>."
    output = project / "evidence"
    output.mkdir(exist_ok=True)
    (output / "offline-results.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    (output / "offline-report.md").write_text(
        sanitize(report) + "\n", encoding="utf-8",
    )
    print(f"Published sanitized evidence: {data['passed']}/{data['total']}")


if __name__ == "__main__":
    main()
