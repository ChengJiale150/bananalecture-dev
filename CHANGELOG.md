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

- **feat(scripts): 迁移脚本支持一并重新生成 project-video.mp4**
  - 替换音频不会刷新已渲染的视频，新增 `--regenerate-video` 在音频处理完后重建视频；`--video-only` 用于音频已修好、本次只重建视频（实测不触碰音频）。
  - 视频参数（分辨率/帧率/编码器/码率/像素格式/背景色/输出名）尽力从 `config.yaml` 读取，缺失时用与应用一致的默认值。
  - `--video-scope existing`（默认）只刷新已登记视频的项目，`all` 也为「每页图片与音频齐全」的项目新建视频；资产不完整的项目会跳过并说明原因。
  - 用单次 ffmpeg `scale+pad` 复刻应用的 Pillow 预处理，因此无需图像库；项目原本未登记视频时回写 `projects.video_path`，`updated_at` 不改。
  - 视频编码开销大，干跑只列计划不编码（约 0.2 秒完成）。
  - 实测旧视频由 `-23.1 LUFS / LRA 11.0 / 峰值 +3.1 dBFS(削波)` 变为 `-16.9 LUFS / LRA 2.4 / 峰值 -3.5 dBFS`，与修复后的 `slide.mp3` 一致。

- **feat(scripts): 存量项目音频批量重归一化脚本** —— [2138f30](https://github.com/ChengJiale150/bananalecture-dev/commit/2138f30)
  - 复用已生成的 TTS 音频重建 `slide.mp3`，无需重跑语音合成或对话生成。
  - 默认 dry run；替换前保留 `*.bak` 且跨次运行不被覆盖；单页失败不影响其余页。
  - 新增 `just renormalize-audio` 命令入口。

### 修复

- **fix(scripts): 迁移脚本改为单文件独立运行，可在无源码的生产环境执行**
  - 原实现依赖项目包与虚拟环境，而生产跑的是预构建 Docker 镜像、运维侧没有源码，导致无法使用。
  - 改为仅用 Python 标准库 + ffmpeg 的单文件脚本，新增 `--check` 依赖自检，并支持从 `config.yaml` 尽力读取目标响度。
  - 修正封面音效只应作用于 `cover` 页：此前会误加到同一项目的所有页；音效文件缺失时明确失败而非静默丢弃。
  - 新增运维手册 [docs/renormalize-audio.md](docs/renormalize-audio.md)，说明必要依赖与生产执行步骤。

- **fix(audio): 拼接幻灯片音频前统一响度** —— [5821e85](https://github.com/ChengJiale150/bananalecture-dev/commit/5821e85)
  - 修复旁白、大雄、哆啦A梦与音效之间音量不一致：同一页内响度极差由 24 LU 收敛到 0.5 LU。
  - 修复封面页音效导致的削波：真峰值由 +3.2 dBTP 降至 -3.5 dBTP，响度范围由 22.1 LU 降至 1.7 LU。
  - 统一对齐到 -16 LUFS / -1.5 dBTP，可通过 `AUDIO_GENERATION.NORMALIZATION` 调整目标或整体关闭。

<!-- 新条目请追加到上方 [未发布] 段落内对应的分类下；分类不存在时自行新增。 -->
