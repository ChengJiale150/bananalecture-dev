# BananaLecture 存储方案

## 概述

BananaLecture 当前使用本地文件系统存储生成的图片、音频和视频，但对外和数据库中保存的不是绝对路径，而是稳定的逻辑存储键。

目标：

- 平台无关：数据库和 API 中不出现 Windows 反斜杠或绝对路径。
- 易迁移：逻辑存储键与物理根目录分离，便于理解和调整部署位置。
- 结构清晰：所有持久化文件都落在统一命名空间 `projects/` 下，布局由基础设施层集中定义。

## 核心约定

- 存储根目录由 `STORAGE.DATA_DIR` 配置。
- `StorageService` 在启动时将 `DATA_DIR` 解析为本机绝对路径，但该绝对路径不会写入数据库。
- 业务层、数据库模型、API schema 中的 `image_path`、`audio_path`、`video_path` 都表示逻辑存储键。
- 逻辑存储键必须使用 POSIX 风格 `/` 分隔。
- 逻辑存储键必须是相对路径，不允许绝对路径、反斜杠、`.`、`..` 或空路径段。

## Canonical Key 布局

所有持久化媒体文件统一使用以下布局：

```text
projects/{project_id}/slides/{slide_id}/image/original.png
projects/{project_id}/slides/{slide_id}/audio/slide.mp3
projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}/audio.mp3
projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}/audio.raw.mp3
projects/{project_id}/video/project-video.mp4
```

其中：

- `original.png` 是幻灯片当前图片文件。
- `audio.mp3` 是单条对话音频。
- `audio.raw.mp3` 是“道具”角色音频处理前的临时持久化输入。
- `slide.mp3` 是整页合并音频。
- `project-video.mp4` 是项目最终视频。

## 代码职责

### `StorageLayout`

`src/bananalecture_backend/infrastructure/storage_layout.py`

职责：

- 作为逻辑存储键的唯一构造入口。
- 统一定义图片、对话音频、幻灯片音频、项目视频的 key 规则。
- 业务层不得手写 `f"projects/{...}"` 形式的路径字符串。

### `StorageService`

`src/bananalecture_backend/infrastructure/storage.py`

职责：

- 校验并规范化逻辑存储键。
- 将逻辑存储键映射到 `DATA_DIR` 下的真实文件路径。
- 提供统一的读写与输出准备接口。
- 管理内部临时目录 `_tmp/`，供视频等流程创建临时工作目录。

关键接口：

- `write_bytes(key, content) -> str`
- `read_bytes(key) -> bytes`
- `resolve_file(key) -> Path`
- `prepare_output_file(key) -> Path`
- `create_temp_dir(prefix) -> Path`

## 服务层使用方式

正确做法：

- 图片服务通过 `StorageLayout.slide_image()` 获取 key，并用 `StorageService.write_bytes()` 写入。
- 音频服务通过 `StorageLayout.dialogue_audio()` / `slide_audio()` 获取 key，并在需要 ffmpeg 输出文件时使用 `prepare_output_file()`。
- 视频服务通过 `StorageLayout.project_video()` 获取最终 key，并通过 `create_temp_dir()` 申请临时工作目录。

错误做法：

- 直接访问 `storage.root` 拼接业务路径。
- 在服务层手写目录结构。
- 将绝对路径保存到数据库字段。

## API 与数据库语义

以下字段继续保留字符串类型，但语义已经统一为“逻辑存储键”：

- `Slide.image_path`
- `Slide.audio_path`
- `Dialogue.audio_path`
- `Project.video_path`

文件下载接口依然通过这些字段查到 key，再由 `StorageService.resolve_file()` 解析成真实文件。

## 开发约束

- 新增媒体类型时，先扩展 `StorageLayout`，再修改服务层。
- 不要在测试中手工拼接物理路径，优先通过 `StorageLayout` 或 `StorageService.resolve_file()` 断言。
- 临时文件和持久化文件必须分开；临时工作目录不应写入数据库。
