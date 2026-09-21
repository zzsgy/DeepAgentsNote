# 第三章实验实际运行记录

结果：85/85 检查通过。

这是代码行为验证，不是学习者掌握度评分。

Python: 3.12.13；依赖: {'deepagents': '0.7.13', 'langchain': '1.4.2', 'langchain-core': '1.6.3', 'langgraph': '1.2.11'}

## tools

- PASS：State: write_file

```text
Updated file /notes/demo.md
```

- PASS：State: read_file 读回原文

```text
1  第1行：学习 Backend
2  第2行：TODO 阅读
3  第3行：TODO 实验
4  第4行：完成
```

- PASS：State: offset=1 从第2行读两行

```text
2  第2行：TODO 阅读
3  第3行：TODO 实验

[Read 2 lines (lines 2-3 of 4 total). 1 line remaining from offset 3.]
```

- PASS：State: ls

```text
['/notes/demo.md']
```

- PASS：State: glob

```text
['/notes/demo.md']
```

- PASS：State: grep/files_with_matches

```text
/notes/demo.md
```

- PASS：State: grep/content

```text
/notes/demo.md:
  2: 第2行：TODO 阅读
  3: 第3行：TODO 实验
```

- PASS：State: grep/count

```text
/notes/demo.md: 2
```

- PASS：State: edit_file

```text
Successfully replaced 1 instance(s) of the string in '/notes/demo.md'
```

- PASS：State: 编辑确实改变内容

```text
1  第1行：学习 Backend
2  第2行：DONE 阅读
3  第3行：TODO 实验
4  第4行：完成
```

- PASS：State: 不存在的替换目标被拒绝且原文不变

```text
Error: String not found in file: 'NOT_PRESENT'
```

- PASS：State: v0.7 write_file 是覆盖而非追加

```text
1  完整覆盖后的新内容
```

- PASS：State: delete 后读不到测试文件

```text
Error: File '/notes/disposable.txt' not found
```

- PASS：State: 文件确实存在 Agent State.files

```text
{'/notes/demo.md': {'content': '完整覆盖后的新内容', 'encoding': 'utf-8', 'created_at': '2026-09-21T01:09:51.953812+00:00', 'modified_at': '2026-09-21T01:09:52.147292+00:00'}}
```

- PASS：Filesystem: write_file

```text
Updated file /notes/demo.md
```

- PASS：Filesystem: read_file 读回原文

```text
1  第1行：学习 Backend
2  第2行：TODO 阅读
3  第3行：TODO 实验
4  第4行：完成
```

- PASS：Filesystem: offset=1 从第2行读两行

```text
2  第2行：TODO 阅读
3  第3行：TODO 实验

[Read 2 lines (lines 2-3 of 4 total). 1 line remaining from offset 3.]
```

- PASS：Filesystem: ls

```text
['/notes/demo.md']
```

- PASS：Filesystem: glob

```text
['/notes/demo.md']
```

- PASS：Filesystem: grep/files_with_matches

```text
/notes/demo.md
```

- PASS：Filesystem: grep/content

```text
/notes/demo.md:
  2: 第2行：TODO 阅读
  3: 第3行：TODO 实验
```

- PASS：Filesystem: grep/count

```text
/notes/demo.md: 2
```

- PASS：Filesystem: edit_file

```text
Successfully replaced 1 instance(s) of the string in '/notes/demo.md'
```

- PASS：Filesystem: 编辑确实改变内容

```text
1  第1行：学习 Backend
2  第2行：DONE 阅读
3  第3行：TODO 实验
4  第4行：完成
```

- PASS：Filesystem: 不存在的替换目标被拒绝且原文不变

```text
Error: String not found in file: 'NOT_PRESENT'
```

- PASS：Filesystem: v0.7 write_file 是覆盖而非追加

```text
1  完整覆盖后的新内容
```

- PASS：Filesystem: delete 后读不到测试文件

```text
Error: File '/notes/disposable.txt' not found
```

- PASS：Filesystem: 实际文件落在指定磁盘目录

```text
<LAB_ROOT>\runs\20260921-090951-7e16cd0d\tool-filesystem\notes\demo.md
```

- PASS：Store: write_file

```text
Updated file /notes/demo.md
```

- PASS：Store: read_file 读回原文

```text
1  第1行：学习 Backend
2  第2行：TODO 阅读
3  第3行：TODO 实验
4  第4行：完成
```

- PASS：Store: offset=1 从第2行读两行

```text
2  第2行：TODO 阅读
3  第3行：TODO 实验

[Read 2 lines (lines 2-3 of 4 total). 1 line remaining from offset 3.]
```

- PASS：Store: ls

```text
['/notes/demo.md']
```

- PASS：Store: glob

```text
['/notes/demo.md']
```

- PASS：Store: grep/files_with_matches

```text
/notes/demo.md
```

- PASS：Store: grep/content

```text
/notes/demo.md:
  2: 第2行：TODO 阅读
  3: 第3行：TODO 实验
```

- PASS：Store: grep/count

```text
/notes/demo.md: 2
```

- PASS：Store: edit_file

```text
Successfully replaced 1 instance(s) of the string in '/notes/demo.md'
```

- PASS：Store: 编辑确实改变内容

```text
1  第1行：学习 Backend
2  第2行：DONE 阅读
3  第3行：TODO 实验
4  第4行：完成
```

- PASS：Store: 不存在的替换目标被拒绝且原文不变

```text
Error: String not found in file: 'NOT_PRESENT'
```

- PASS：Store: v0.7 write_file 是覆盖而非追加

```text
1  完整覆盖后的新内容
```

- PASS：Store: delete 后读不到测试文件

```text
Error: File '/notes/disposable.txt' not found
```

- PASS：Store: 文件确实写入 Store namespace

```text
['/notes/demo.md']
```

## lifecycle

- PASS：State: 同线程下一轮可读

```text
1  STATE_MARKER
```

- PASS：State: 新线程看不到 A 的文件

```text
Error: File '/memo.txt' not found
```

- PASS：State: 新 Agent + 同一 Checkpointer + 原 thread 可恢复

```text
1  STATE_MARKER
```

- PASS：State: 相同 thread_id + 新内存 Checkpointer 不能恢复

```text
Error: File '/memo.txt' not found
```

- PASS：Filesystem: 共享 root_dir 的新线程可读

```text
1  DISK_MARKER
```

- PASS：Filesystem: 新 Agent 指向原磁盘目录仍可读

```text
1  DISK_MARKER
```

- PASS：Store: 同一 Store/namespace 可跨线程

```text
1  STORE_MARKER
```

- PASS：Store: 不同 namespace 隔离

```text
Error: File '/memo.txt' not found
```

- PASS：Store: 新 Agent 复用相同 Store/namespace 可读

```text
1  STORE_MARKER
```

- PASS：Store: 新 InMemoryStore 不含旧数据

```text
Error: File '/memo.txt' not found
```

- PASS：独立进程探针正常完成

```text
{"disk_found": true, "state_found": false, "store_found": false}

```

- PASS：真正的新进程: 磁盘保留、内存 State/Store 不保留

```text
{'disk_found': True, 'state_found': False, 'store_found': False}
```

## composite

- PASS：Composite: 只有默认路由文件进入 State.files

```text
{'/scratch/plan.md': {'content': 'TEMP_MARKER', 'encoding': 'utf-8', 'created_at': '2026-09-21T01:09:57.066272+00:00', 'modified_at': '2026-09-21T01:09:57.066272+00:00'}}
```

- PASS：Composite: /project/ 前缀剥离后映射磁盘

```text
<LAB_ROOT>\runs\20260921-090951-7e16cd0d\composite-project
```

- PASS：Composite: /memories/ 进入 Store

```text
['/preferences.md']
```

- PASS：Composite: 新线程读取 /scratch/plan.md，预期不可见

```text
Error: File '/scratch/plan.md' not found
```

- PASS：Composite: 新线程读取 /memories/preferences.md，预期可见

```text
1  MEMORY_MARKER
```

- PASS：Composite: 新线程读取 /project/report.md，预期可见

```text
1  PROJECT_MARKER
```

- PASS：Composite: glob 聚合并保留外部路径

```text
['/memories/preferences.md', '/project/report.md', '/scratch/plan.md']
```

- PASS：Composite: grep 跨路由聚合

```text
/memories/preferences.md
/project/report.md
/scratch/plan.md
```

- PASS：Composite: 拼错 /memories/ 会进入 default，不自动成为长期记忆

```text
Error: File '/memory/typo.md' not found
```

## permissions

- PASS：Permission: 可读制度

```text
1  ORIGINAL_POLICY
```

- PASS：Permission: 拒绝 write_file 且磁盘原文不变

```text
Error: permission denied for write on /policies/rule.md
```

- PASS：Permission: 拒绝 edit_file 且磁盘原文不变

```text
Error: permission denied for write on /policies/rule.md
```

- PASS：Permission: 拒绝 delete 且磁盘原文不变

```text
Error: permission denied for write on /policies/rule.md (matches deny rule(s): /policies/**)
```

- PASS：Permission: 拒绝读取假秘密

```text
Error: permission denied for read on /secrets/fake.txt
```

- PASS：Permission: 全局 grep 正常执行但不泄露被拒绝文件内容

```text
No matches found
```

- PASS：Permission: 没命中规则默认允许

```text
Updated file /other/open.txt
```

- PASS：反例: 宽泛 allow 放前面会覆盖后面的 deny

```text
Updated file /workspace/private/demo.txt
```

- PASS：纠正: 具体 deny 放前面

```text
Error: permission denied for write on /workspace/private/demo.txt
```

- PASS：Permission: 白名单末尾 deny 阻止其他路径

```text
Error: permission denied for write on /outside-blocked.txt
```

- PASS：Filesystem virtual_mode: 拒绝 .. 路径越界

```text
Path traversal not allowed
```

## policy

- PASS：PolicyWrapper: 合规写入与编辑真正落盘

```text
Successfully replaced 1 instance(s) of the string in '/notes/draft.txt'
```

- PASS：PolicyWrapper: write_file 超限被拒绝且原文不变

```text
写入超过 80 字节上限
```

- PASS：PolicyWrapper: edit_file 超限被拒绝且原文不变

```text
编辑后的完整文件超过 80 字节上限
```

- PASS：PolicyWrapper: 保护文件免于 write_file

```text
受保护路径不能变更
```

- PASS：PolicyWrapper: 保护文件免于 edit_file

```text
受保护路径不能变更
```

- PASS：PolicyWrapper: 保护文件免于 delete

```text
受保护路径不能变更
```

- PASS：PolicyWrapper: 拒绝目录本身（不依赖末尾斜杠）

```text
受保护路径不能变更
```

- PASS：PolicyWrapper: 父目录删除策略判定为拒绝

```text
只调用判断函数，没有删除根目录
```

- PASS：PolicyWrapper: 示例保护变更但不禁止读

```text
1  POLICY_ORIGINAL
```

- PASS：PolicyWrapper: Composite 路由内用 /policies 规则即可命中

```text
{'operation': 'write', 'path': '/policies/rule.md', 'allowed': False, 'error': '受保护路径不能变更'}
```

- PASS：PolicyWrapper: 留下成功/拒绝审计且不含正文

```text
[{'operation': 'write', 'path': '/notes/draft.txt', 'allowed': True, 'error': None}, {'operation': 'edit', 'path': '/notes/draft.txt', 'allowed': True, 'error': None}, {'operation': 'write', 'path': '/notes/draft.txt', 'allowed': False, 'error': '写入超过 80 字节上限'}, {'operation': 'edit', 'path': '/notes/draft.txt', 'allowed': False, 'error': '编辑后的完整文件超过 80 字节上限'}, {'operation': 'write', 'path': '/policies/rule.md', 'allowed': False, 'error': '受保护路径不能变更'}, {'operation': 'edit', 'path': '/policies/rule.md', 'allowed': False, 'error': '受保护路径不能变更'}, {'operation': 'delete', 'path': '/policies/rule.md', 'allowed': False, 'error': '受保护路径不能变更'}, {'operation': 'delete', 'path': '/policies', 'allowed': False, 'error': '受保护路径不能变更'}, {'operation': 'write', 'path': '/policies/rule.md', 'allowed': False, 'error': '受保护路径不能变更'}]
```

## 如何解读

只有 PASS 的观察才能用作本次行为证据；有 FAIL 时先看上方实际输出。
完整工具参数、状态和原始返回值见同目录 results.json。
预期对比与适用前提见项目 README；请在学习记录模板中写自己的结论。
