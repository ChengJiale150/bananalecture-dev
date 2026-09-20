# 存量媒体迁移（音频响度 + 视频重生成，运维手册）

把历史上生成的幻灯片音频重建为一致的响度，并可一并重新生成 `project-video.mp4`。
用于修复「旁白、各角色、音效之间音量不一致」的问题，**不需要重新调用 TTS**，
因此不消耗额度、不改变任何台词内容。

脚本位置：`backend/scripts/renormalize_project_audio.py`

它是**刻意做成单文件、只用 Python 标准库**的，因为生产环境跑的是预构建 Docker 镜像，
运维侧既没有仓库源码也无法使用项目虚拟环境。把这一个文件拷进去就能运行。

---

## 1. 必要依赖

| 依赖 | 要求 | 说明 |
|------|------|------|
| **Python** | 3.8 及以上 | 只使用标准库（`argparse`/`sqlite3`/`subprocess`/`shutil`/`tempfile`…），**不需要 pip install，不需要项目虚拟环境** |
| **ffmpeg** | 需带 `loudnorm`、`ebur128` 滤镜与 `libmp3lame` 编码器 | 标准 ffmpeg 构建自 3.1 起全部满足；项目镜像 `python:3.12-alpine` 已通过 `apk add ffmpeg` 安装 |
| **数据库** | 对 SQLite 文件有读权限 | 需要 `projects`/`slides`/`dialogues` 三张表；脚本只执行 `SELECT` |
| **数据目录** | `DATA_DIR` 可读写 | 需要写入新的 `slide.mp3` 与 `.bak` 备份 |
| **磁盘空间** | 可容纳单页音频的临时副本 | 通常几 MB，脚本结束后自动清理 |
| **网络** | **不需要** | 全程离线，不访问任何外部服务 |
| **第三方包** | **不需要** | 无 pip / 无 uv / 无源码依赖 |

> 若使用 `--regenerate-video`，还需 `libx264` 编码器与 `aac` 编码器（标准 ffmpeg 构建均含，
> 且项目镜像已满足）。

脚本自带依赖自检，会逐项检查并给出结论：

```bash
python3 renormalize_project_audio.py --check
```

自检覆盖：Python 版本、ffmpeg 可执行性、`loudnorm`/`ebur128` 滤镜、`concat` 解复用器、
`libmp3lame` 编码器、数据目录与数据库是否可达。

---

## 2. 生产环境（Docker）执行

项目镜像内已具备 Python、ffmpeg，并且 `assets/`（音效资源）就在镜像里，
数据卷挂载在 `/app/data`，因此**在容器内执行是最省事、依赖最完整的路径**。

```bash
# 0. 确认服务名（compose 前缀可能不同）
docker compose ps

# 1. 把脚本拷进正在运行的容器
docker cp backend/scripts/renormalize_project_audio.py <backend容器名>:/tmp/

# 2. 依赖自检：只读，不改任何文件
docker compose exec backend python /tmp/renormalize_project_audio.py --check

# 3. 预演：打印每一页的 before/after 响度，不改任何文件
docker compose exec backend python /tmp/renormalize_project_audio.py

# 4. 正式执行（默认保留 .bak 备份）
docker compose exec backend python /tmp/renormalize_project_audio.py --apply
```

> 请在**没有生成任务运行**时执行，因为脚本会重写 API 正在对外提供的音频文件。

### 2.1 连视频一起更新

替换音频**不会**自动刷新已渲染的 `project-video.mp4`。有两种方式更新视频：

**方式 A：让脚本一并重建（推荐用于批量/离线）**

```bash
# 音频与视频一起处理
docker compose exec backend python /tmp/renormalize_project_audio.py --apply --regenerate-video

# 音频此前已修好、本次只重建视频
docker compose exec backend python /tmp/renormalize_project_audio.py --apply --video-only
```

`--video-only` 完全不触碰音频（已实测音频 md5 不变）。默认只刷新**已登记过视频**的项目
（`--video-scope existing`）；加 `--video-scope all` 还会为「每页都同时具备图片和音频」
但尚未生成过视频的项目创建视频。

> **编码开销**：视频用 libx264 逐页渲染，实测 3.2 分钟成片约需 **2 分钟**（多核），
> 大致是成片时长的 **0.5～1 倍**。因此干跑**只列出计划、不做编码**，不会浪费 CPU。

**方式 B：走应用自身的接口（后端可用且未被改动时的规范路径）**

脚本内的视频渲染是为了「离线也能跑」而用 ffmpeg 复刻的等价实现。如果后端可正常访问，
直接调用它自己的视频生成接口是更保险的选择——不会与应用管线产生分叉。
缺点是每个项目都要单独触发并轮询任务，项目多时不如方式 A 方便。

---

## 2.2 宿主机执行（可选）

宿主机通常没有 ffmpeg，且 `assets/` 只在镜像里，因此**不推荐**；确有需要时：

```bash
python3 scripts/renormalize_project_audio.py \
    --data-dir ./data \
    --assets-root /path/to/copied/assets \
    --check
```

若确认没有任何封面页使用音效，可用 `--no-cue-assets` 跳过音效（**会丢失封面音效**，见 §5）。

---

## 3. 参数说明

| 参数 | 默认 | 说明 |
|------|------|------|
| `--apply` | 关 | 真正写入；不加则为预演 |
| `--check` | — | 只做依赖与路径自检 |
| `--data-dir` | 探测 | 存储根目录（生产为 `/app/data`） |
| `--database` | `<data-dir>/data.db` | SQLite 文件路径 |
| `--assets-root` | 自动探测 | 含各模板子目录的资源根（生产为 `/app/assets`） |
| `--config` | 自动探测 | 尽力读取目标响度；CLI 参数优先 |
| `--target-lufs` | `-16.0` | 响度目标 |
| `--target-true-peak` | `-1.5` | 真峰值上限（dBTP） |
| `--target-lra` | `11.0` | 响度范围目标 |
| `--tolerance` | `0.5` | 已在目标 ±该值内的片段直接复用，不重复编码 |
| `--force` | 关 | 忽略上面的复用判断，强制重新归一化 |
| `--no-backup` | 关 | 不生成 `.bak` |
| `--update-dialogue-audio` | 关 | 同时归一化单条对话预览音频 |
| `--no-cue-assets` | 关 | 不添加封面音效（显式接受丢失） |
| `--project-id` / `--slide-id` | 全部 | 限定范围，可重复 |
| `--cover-cue` | 内置 | 声明 `模板=文件名`，如 `doraemon=cues.mp3`；`模板=` 表示无音效 |
| `--regenerate-video` | 关 | 音频处理完后，一并重建各项目的 `project-video.mp4` |
| `--video-only` | 关 | 跳过全部音频处理，只重建视频（隐含 `--regenerate-video`） |
| `--video-scope` | `existing` | `existing` 只刷新已登记视频的项目；`all` 也为资产完整的项目新建视频 |

视频编码参数（分辨率/帧率/编码器/码率/像素格式/背景色/输出文件名）会**尽力从 `config.yaml`
读取**，读不到则使用与应用一致的默认值（1366x768 @ 25fps、libx264/aac、yuv420p、192k、
输出 `project-video.mp4`），并在启动信息里打印实际取值。

内置模板音效表与 `core/templates.py` 保持一致：`doraemon → cues.mp3`，`xiyouji → 无`。
遇到未知模板会打印提示并按"无音效"处理。

---

## 4. 安全性与回滚

- **默认预演**，必须显式加 `--apply` 才会写文件。
- 替换前生成 `<文件名>.bak`；**已存在的 `.bak` 永不被覆盖**，因此多次执行始终保留最初版本。
- **可重复执行且结果确定**：每次都从未被触碰的源片段重新生成，实测连续 3 次输出 md5 完全相同。
- 单页失败不影响其余页，结束时若有失败会返回非零退出码，便于告警。
- 回滚：`cp slide.mp3.bak slide.mp3`（确认无误后再删除 `.bak`）。

---

## 5. 已知限制

1. **封面音效依赖资源文件。** 封面页的 `slide.mp3` 由「音效 + 各条对话」组成，音效不在
   任何对话文件里。若模板配置了音效但文件缺失，该页会**明确失败**而不是静默丢音效——
   避免生成缺少片头的音频。确需跳过时用 `--no-cue-assets` 显式接受。
2. **道具音效无法拆分。** 道具角色的音效在生成时已并入该条对话文件，脚本不会再重复前置。
   用时若叠加 `--update-dialogue-audio`，音效与语音只能施加同一增益，该片段内部仍有小残差；
   彻底修正需重新生成该页音频。
3. **音频替换不会自动刷新视频。** 必须显式加 `--regenerate-video`（或 `--video-only`），
   否则已渲染的 `project-video.mp4` 仍是旧音频。
4. **视频渲染是复刻实现。** 应用用 Pillow 预处理图片再交给 ffmpeg，脚本用单次 ffmpeg
   `scale+pad` 得到等价结果（因此不需要图像库）。若应用的编码管线变化，需同步修改脚本里的
   `VideoBuilder`；后端可用且未被改动时，优先走应用自身的视频生成接口。
5. **`--regenerate-video` 会写数据库。** 仅当项目原本未登记视频时，才回写
   `projects.video_path`（否则 API 无法对外提供该文件）。`updated_at` 刻意不改，避免猜错
   应用的时间格式。
6. **资产不完整的项目会被跳过**，并在结尾用 `note:` 说明是哪一页缺图片或音频
   （应用自身的视频生成同样会拒绝这类项目）。
7. **`config.yaml` 为尽力解析。** 无第三方 YAML 库，只读取唯一命名的标量键并做范围校验；
   若生产改过目标值，建议直接显式传 `--target-lufs`。

---

## 6. 验证记录

在 `backend/data` 的副本上以 `--apply` 实测：

| 项目 | 结果 |
|------|------|
| 备份完整性 | `.bak` 与原件 md5 逐字节一致；多次运行不被覆盖 |
| 幂等性 | 连续 3 次 `--apply` 输出 md5 完全相同 |
| 封面音效 | 仅 `cover` 页加入音效（时长 4.50s = 音效 1.0 + 2.0 + 1.5）；`content` 页 3.50s、无音效模板的封面 3.00s，均未误加 |
| 缺失音效 | 报错并计为失败，其余页继续处理 |
| 响度收敛 | 全部页面落到 -16.8 LUFS 左右；`--update-dialogue-audio` 后单条预览音频 -16.4 LUFS |
| 依赖独立性 | 使用系统 `python3`（非项目虚拟环境）即可运行 |
| 视频重生成 | 3 页项目约 3.2 分钟成片，实测渲染耗时约 2 分钟，输出 1366x768/25fps/h264+aac |
| 视频音频 | 旧视频 `-23.1 LUFS / LRA 11.0 / 峰值 +3.1 dBFS(削波)` → 新视频 `-16.9 LUFS / LRA 2.4 / 峰值 -3.5 dBFS`，与源 `slide.mp3`(-16.8~-17.0) 一致 |
| 视频备份 | 旧视频保留为 `project-video.mp4.bak` |
| `--video-only` | 音频 md5 完全不变，确认不触碰音频 |
| video_path 回写 | 将 `video_path` 置空后运行，渲染完成即自动登记回规范路径；`updated_at` 保持不变 |
| 跳过原因可见 | 资产不完整的项目在结尾以 `note:` 逐条说明缺失页 |
