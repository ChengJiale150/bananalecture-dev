# 变更日志

BananaLecture 的行为变更记录。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)。

## 记录约定

- **记录范围**：只登记影响行为的提交，即 `feat`、`fix`、`refactor`、`perf`。
  `docs`、`style`、`test`、`chore`、`ci`、`build`、`revert` 无需登记。
- **同一个提交**：条目必须与它所描述的代码改动放在同一个提交里，不要事后单独补交。
- **写入位置**：追加到 `## [未发布]` 下对应的分类中，分类依次为
  `新增`（feat）、`修复`（fix）、`优化`（perf）、`重构`（refactor）。
- **发版时**：将 `## [未发布]` 改名为 `## [<版本号>] - <YYYY-MM-DD>`，
  并在其上方新建一个空的 `## [未发布]`。
- 本文件启用之前的历史变更，请查阅提交历史（`git log`）。

## [未发布]

### 新增

- **feat(scripts): 存量项目音频批量重归一化脚本** —— [2138f30](https://github.com/ChengJiale150/bananalecture-dev/commit/2138f30)
  - 复用已生成的 TTS 音频重建 `slide.mp3`，无需重跑语音合成或对话生成。
  - 默认 dry run；替换前保留 `*.bak` 且跨次运行不被覆盖；单页失败不影响其余页。
  - 新增 `just renormalize-audio` 命令入口。

### 修复

- **fix(audio): 拼接幻灯片音频前统一响度** —— [5821e85](https://github.com/ChengJiale150/bananalecture-dev/commit/5821e85)
  - 修复旁白、大雄、哆啦A梦与音效之间音量不一致：同一页内响度极差由 24 LU 收敛到 0.5 LU。
  - 修复封面页音效导致的削波：真峰值由 +3.2 dBTP 降至 -3.5 dBTP，响度范围由 22.1 LU 降至 1.7 LU。
  - 统一对齐到 -16 LUFS / -1.5 dBTP，可通过 `AUDIO_GENERATION.NORMALIZATION` 调整目标或整体关闭。

<!-- 新条目请追加到上方 [未发布] 段落内对应的分类下；分类不存在时自行新增。 -->
