# 工作台演示项目

这里是手工构造的 Harness 界面演示，题目、节点和文件仅用于展示，不是真实比赛记录，也没有人工批准或真实角色会话。

安装 [工作台依赖](../../tools/harness-workbench/README.md) 后，在仓库根目录运行：

```powershell
py -3.13 tools/harness-workbench/app.py --project "examples/workbench-demo/演示项目" --open
```

macOS 或 Linux 可将 `py -3.13` 换成已安装依赖的 `python3`。打开后可以点击阶段、小问和文件；角色会话需要用户自行登记真实会话。这个演示不执行建模、不提交审批，正式比赛请使用独立项目目录。
