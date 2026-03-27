## 对话接口

对话是幻灯片的子资源，每个幻灯片可以包含多个对话项，定义角色的台词和配音参数。

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/projects/{project_id}/slides/{slide_id}/dialogues/generate` | AI生成对话 |
| GET | `/api/v1/projects/{project_id}/slides/{slide_id}/dialogues` | 获取对话列表 |
| PUT | `/api/v1/projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}` | 更新对话 |
| DELETE | `/api/v1/projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}` | 删除对话 |
| POST | `/api/v1/projects/{project_id}/slides/{slide_id}/dialogues/reorder` | 重新排序对话 |
| POST | `/api/v1/projects/{project_id}/slides/{slide_id}/dialogues/add` | 添加对话 |
| POST | `/api/v1/projects/{project_id}/dialogues/batch-generate` | 批量生成对话 |

### AI生成对话

使用 AI 自动生成指定幻灯片的对话内容。

```http
POST /api/v1/projects/{project_id}/slides/{slide_id}/dialogues/generate
```

**响应示例**

```json
{
  "code": 200,
  "message": "对话生成成功",
  "data": {
    "slide_id": "slide-002",
    "dialogues": [
      {
        "id": "dialogue-001",
        "slide_id": "slide-002",
        "role": "大雄",
        "content": "哆啦A梦，今天要学什么呀？",
        "emotion": "开心的",
        "speed": "中速",
        "idx": 1,
        "audio_path": null,
        "created_at": "2026-03-26T10:00:00Z",
        "updated_at": "2026-03-26T10:00:00Z"
      },
      {
        "id": "dialogue-002",
        "slide_id": "slide-002",
        "role": "哆啦A梦",
        "content": "今天我们要学习一个新知识哦！",
        "emotion": "开心的",
        "speed": "中速",
        "idx": 2,
        "audio_path": null,
        "created_at": "2026-03-26T10:00:00Z",
        "updated_at": "2026-03-26T10:00:00Z"
      }
    ]
  }
}
```

### 批量生成对话

批量为项目下所有幻灯片生成对话。

```http
POST /api/v1/projects/{project_id}/dialogues/batch-generate
```

**响应示例**

```json
{
  "code": 202,
  "message": "批量生成对话任务已创建",
  "data": {
    "task_id": "task-550e8400-0002",
    "project_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**说明**: 已有的对话会被覆盖

### 添加对话

在对话列表末尾添加单个对话。

```http
POST /api/v1/projects/{project_id}/slides/{slide_id}/dialogues/add
```

**请求体**

```json
{
  "role": "大雄",
  "content": "哆啦A梦，今天要学什么呀？",
  "emotion": "开心的",
  "speed": "中速"
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `role` | string | 否 | 角色名称 |
| `content` | string | 否 | 对话文本内容 |
| `emotion` | string | 否 | 情感状态：开心的、悲伤的、生气的、害怕的、惊讶的、无明显情感 |
| `speed` | string | 否 | 语速设置：慢速、中速、快速 |

**响应示例**

```json
{
  "code": 201,
  "message": "对话添加成功",
  "data": {
    "id": "dialogue-003",
    "slide_id": "slide-002",
    "role": "大雄",
    "content": "哆啦A梦，今天要学什么呀？",
    "emotion": "开心的",
    "speed": "中速",
    "idx": 3,
    "audio_path": null,
    "created_at": "2026-03-26T10:00:00Z",
    "updated_at": "2026-03-26T10:00:00Z"
  }
}
```

**说明**: 新对话会自动添加到列表末尾，对话的 `audio_path` 初始值为 null，`created_at` 和 `updated_at` 为 UTC ISO 8601 时间字符串

### 获取对话列表

```http
GET /api/v1/projects/{project_id}/slides/{slide_id}/dialogues
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "dialogue-001",
        "slide_id": "slide-002",
        "role": "大雄",
        "content": "哆啦A梦，今天要学什么呀？",
        "emotion": "开心的",
        "speed": "中速",
        "idx": 1,
        "audio_path": null,
        "created_at": "2026-03-26T10:00:00Z",
        "updated_at": "2026-03-26T10:00:00Z"
      }
    ],
    "total": 2
  }
}
```

### 更新对话

更新对话项的内容和参数。

```http
PUT /api/v1/projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}
```

**请求体**

```json
{
  "role": "哆啦A梦",
  "content": "今天我们要学习一个很有趣的知识！",
  "emotion": "惊讶的",
  "speed": "快速"
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "对话更新成功",
  "data": {
    "id": "dialogue-001",
    "slide_id": "slide-002",
    "role": "哆啦A梦",
    "content": "今天我们要学习一个很有趣的知识！",
    "emotion": "惊讶的",
    "speed": "快速",
    "idx": 1,
    "audio_path": null,
    "created_at": "2026-03-26T10:00:00Z",
    "updated_at": "2026-03-26T10:05:00Z"
  }
}
```

### 删除对话

```http
DELETE /api/v1/projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}
```

**响应示例**

```json
{
  "code": 200,
  "message": "对话删除成功",
  "data": null
}
```

### 重新排序对话

```http
POST /api/v1/projects/{project_id}/slides/{slide_id}/dialogues/reorder
```

**请求体**

```json
{
  "dialogue_ids": ["dialogue-002", "dialogue-001", "dialogue-003"]
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "对话排序更新成功",
  "data": {
    "dialogues": [
      { "id": "dialogue-002", "idx": 1 },
      { "id": "dialogue-001", "idx": 2 },
      { "id": "dialogue-003", "idx": 3 }
    ]
  }
}
```
