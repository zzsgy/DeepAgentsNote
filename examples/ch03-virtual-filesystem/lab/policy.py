"""教学包装器：路径保护 + 写入/编辑后大小检查 + 不含正文的审计。

范围：单进程、串行、UTF-8 文本实验。不是生产安全沙箱。
不提供 execute/upload/download；不靠 __getattr__ 盲目转发未检查的能力。
异步基本方法使用 BackendProtocol 的默认同步转接，仍经过本类的检查。
"""

from pathlib import PurePosixPath
from deepagents.backends.protocol import BackendProtocol, WriteResult, EditResult, DeleteResult


class PolicyWrapper(BackendProtocol):
    def __init__(self, inner, *, protected=("/policies",), max_bytes=80):
        self.inner = inner
        self.protected = tuple(self._normalize(p) for p in protected)
        self.max_bytes = max_bytes
        self.audit = []

    @staticmethod
    def _normalize(path):
        if not path.startswith("/") or "\\" in path:
            raise ValueError("教学包装器只接受 / 开头的 POSIX 虚拟路径")
        if any(part in {"..", "~"} for part in path.split("/")):
            raise ValueError("拒绝 .. 和 ~ 路径段")
        return PurePosixPath(path)

    def _reason(self, path, *, deleting=False):
        try:
            candidate = self._normalize(path)
        except ValueError as exc:
            return str(exc)
        for protected in self.protected:
            if candidate == protected or candidate.is_relative_to(protected):
                return "受保护路径不能变更"
            if deleting and protected.is_relative_to(candidate):
                return "不能通过删除父目录移除受保护路径"
        return None

    def _record(self, operation, path, result):
        self.audit.append({"operation": operation, "path": path,
                           "allowed": result.error is None, "error": result.error})
        return result

    def ls(self, path):
        return self.inner.ls(path)

    def read(self, file_path, offset=0, limit=2000):
        return self.inner.read(file_path, offset=offset, limit=limit)

    def glob(self, pattern, path="/"):
        return self.inner.glob(pattern, path)

    def grep(self, pattern, path=None, glob=None, *, max_count=None):
        return self.inner.grep(pattern, path, glob, max_count=max_count)

    def write(self, file_path, content):
        reason = self._reason(file_path)
        if reason is None and len(content.encode("utf-8")) > self.max_bytes:
            reason = f"写入超过 {self.max_bytes} 字节上限"
        result = WriteResult(error=reason) if reason else self.inner.write(file_path, content)
        return self._record("write", file_path, result)

    def edit(self, file_path, old_string, new_string, replace_all=False):
        reason = self._reason(file_path)
        if reason:
            return self._record("edit", file_path, EditResult(error=reason))
        # 本实验文件很小，读取完整文本并验证编辑后的大小；不只检查 new_string。
        current = self.inner.read(file_path, limit=2**31 - 1)
        if current.error:
            return self._record("edit", file_path, EditResult(error=current.error))
        data = current.file_data
        if not data or data.get("encoding") != "utf-8":
            return self._record("edit", file_path, EditResult(error="本示例只处理 UTF-8 文本"))
        original = data["content"]
        count = original.count(old_string) if old_string else 0
        if count == 0 or (not replace_all and count != 1):
            return self._record("edit", file_path, EditResult(error="替换目标不存在或不唯一"))
        updated = original.replace(old_string, new_string, -1 if replace_all else 1)
        if len(updated.encode("utf-8")) > self.max_bytes:
            return self._record("edit", file_path, EditResult(error=f"编辑后的完整文件超过 {self.max_bytes} 字节上限"))
        return self._record("edit", file_path, self.inner.edit(file_path, old_string, new_string, replace_all))

    def delete(self, file_path):
        reason = self._reason(file_path, deleting=True)
        result = DeleteResult(error=reason) if reason else self.inner.delete(file_path)
        return self._record("delete", file_path, result)
