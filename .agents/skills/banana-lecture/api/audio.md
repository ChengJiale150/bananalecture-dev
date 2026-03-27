## 音频接口

音频是对话的子资源，每个对话项可以生成对应的音频文件。

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/projects/{project_id}/slides/{slide_id}/audio/generate` | 生成幻灯片音频 |
| POST | `/api/v1/projects/{project_id}/audio/batch-generate` | 批量生成音频 |
| GET | `/api/v1/projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}/audio/file` | 获取音频文件（按对话） |
| GET | `/api/v1/projects/{project_id}/slides/{slide_id}/audio/file` | 获取音频文件（按页） |

### 生成幻灯片音频

为幻灯片下所有对话生成音频文件, 并为幻灯片更新音频路径。

```http
POST /api/v1/projects/{project_id}/slides/{slide_id}/audio/generate
```

**响应示例**

```json
{
  "code": 200,
  "message": "幻灯片音频生成成功",
  "data": null
}
```

### 批量生成音频

批量为项目下所有幻灯片生成音频。

```http
POST /api/v1/projects/{project_id}/audio/batch-generate
```

**响应示例**

```json
{
  "code": 202,
  "message": "批量生成音频任务已创建",
  "data": {
    "task_id": "task-550e8400-0004",
    "project_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 获取音频文件（按对话）

获取指定对话项的音频文件。

```http
GET /api/v1/projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}/audio/file
```

**响应**

```
Content-Type: audio/mpeg
Content-Disposition: attachment; filename="dialogue-001.mp3"

[binary audio data]
```

### 获取音频文件（按页）

获取指定幻灯片的合并音频文件。

```http
GET /api/v1/projects/{project_id}/slides/{slide_id}/audio/file
```

**响应**

```
Content-Type: audio/mpeg
Content-Disposition: attachment; filename="slide-002.mp3"

[binary audio data]
```
