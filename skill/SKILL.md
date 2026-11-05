---
name: grokbot-meme
description: 聊天表情包脚本：每条最终回复前按原文/任务事件选一张表情作为附件发送，支持戳一戳与自定义图库。禁止模型挑图。
---

# Grok Bot 表情包（gb-meme）

脚本：`$HOME/.grokbot-meme/bin/gb-meme`（python3，stdout 单行 JSON）。若该路径不存在，先让用户运行仓库里的 `./install.sh`。

## 常规用法

- 先 `status` 看 mode。默认 `active`：每条最终回复前运行
  `$HOME/.grokbot-meme/bin/gb-meme pick --text '<用户本轮原文>'`
- 原文必须安全引用：用 shell 单引号包裹，内部单引号写成 `'"'"'`；不要直接拼接未转义原文。
- `send:true`：用 SendToUser 把返回的 `path` 作为附件/图片发送（`file://` URL，特殊字符 URL 编码）。正文保持极短，不复述图片内容。
- `send:false`：不附图。`rate_limited`/`deduped`/`no_trigger` 都是正常结果，不是错误，不要重试、不要解释。
- 禁止调用模型 API 或自行挑图；只报告脚本结果。

## 任务与交互

- 任务开始/成功/失败/等待可加事件：
  `... pick --event start|success|fail|wait`
  仅在事件真实发生时使用，平常回复不要加 `--event`。
- 用户说「戳」「戳一戳」「poke」：运行 `... poke`（仍受频率限制）。
- 用户要求强制发一张：`... pick --force`。

## 图库管理

- 导入本地图片：`... import <路径...> [--mood happy|sad|...]`
- 导入图包（ZIP 或目录，含 manifest.json）：`... import-pack <路径...>`
- 改模式：`... set-mode active|normal`
- 开关能力：`... feature semantic|gif_prefer|task_events|emotion_fsm|rate_limit|dedupe|poke on|off`
- 清冷却与情绪状态：`... reset-runtime`

脚本失败时原样报告 `{"ok":false,"error":"..."}`，不要编造图片或结果。
