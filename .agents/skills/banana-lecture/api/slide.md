## 幻灯片接口

幻灯片是项目的子资源，每个项目包含多个幻灯片。

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/projects/{project_id}/slides` | 创建幻灯片列表（批量创建或覆盖） |
| GET | `/api/v1/projects/{project_id}/slides` | 获取项目下所有幻灯片的列表 |
| PUT | `/api/v1/projects/{project_id}/slides/{slide_id}` | 更新指定幻灯片的基本信息 |
| DELETE | `/api/v1/projects/{project_id}/slides/{slide_id}` | 删除指定幻灯片 |
| POST | `/api/v1/projects/{project_id}/slides/reorder` | 调整幻灯片的显示顺序 |
| POST | `/api/v1/projects/{project_id}/slides/add` | 添加单个幻灯片到列表末尾 |

### 创建幻灯片列表

批量创建幻灯片列表，可直接覆盖项目下已有的幻灯片。

```http
POST /api/v1/projects/{project_id}/slides
```

**请求体**

```json
{
  "slides": [
    {
      "type": "cover",
      "title": "封面",
      "description": "欢迎观看",
      "content": "这是一个介绍性页面"
    },
    {
      "type": "content",
      "title": "第二页",
      "description": "介绍",
      "content": "内容..."
    }
  ]
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `slides` | array[object] | 是 | 幻灯片列表数组 |
| `slides[].type` | string | 否 | 幻灯片类型：cover、introduction、content、summary、ending |
| `slides[].title` | string | 否 | 幻灯片标题 |
| `slides[].description` | string | 否 | 幻灯片描述 |
| `slides[].content` | string | 否 | 幻灯片详细内容 |

**响应示例**

```json
{
  "code": 201,
  "message": "幻灯片列表创建成功",
  "data": {
    "items": [
      {
        "id": "slide-001",
        "project_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "cover",
        "title": "封面",
        "description": "欢迎观看",
        "content": "这是一个介绍性页面",
        "idx": 1,
        "image_path": null,
        "audio_path": null,
        "created_at": "2026-03-26T10:00:00Z",
        "updated_at": "2026-03-26T10:00:00Z"
      }
    ]
  }
}
```

**说明**

- 该接口会先删除项目下所有已有的幻灯片，然后创建新的幻灯片列表
- 每个幻灯片会自动分配唯一的ID，并按照数组顺序设置 `idx` 索引
- 幻灯片的 `image_path` 和 `audio_path` 初始值为 null，后续可通过图片生成和音频生成接口更新
- `created_at` 和 `updated_at` 均为 UTC ISO 8601 时间字符串

### 获取幻灯片列表

```http
GET /api/v1/projects/{project_id}/slides
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "slide-001",
        "project_id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "cover",
        "title": "封面",
        "description": "欢迎观看",
        "content": "这是一个介绍性页面",
        "idx": 1,
        "image_path": "projects/550e8400-e29b-41d4-a716-446655440000/slides/slide-001/image/original.png",
        "audio_path": null,
        "created_at": "2026-03-26T10:00:00Z",
        "updated_at": "2026-03-26T10:00:00Z"
      }
    ]
  }
}
```

### 更新幻灯片

更新幻灯片的基本信息。

```http
PUT /api/v1/projects/{project_id}/slides/{slide_id}
```

**请求体**

```json
{
  "type": "content",
  "title": "新的标题",
  "description": "新的描述",
  "content": "新的内容"
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "幻灯片更新成功",
  "data": {
    "id": "slide-002",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "content",
    "title": "新的标题",
    "description": "新的描述",
    "content": "新的内容",
    "idx": 2,
    "image_path": "projects/550e8400-e29b-41d4-a716-446655440000/slides/slide-002/image/original.png",
    "audio_path": null,
    "created_at": "2026-03-26T10:00:00Z",
    "updated_at": "2026-03-26T10:05:00Z"
  }
}
```

### 删除幻灯片

```http
DELETE /api/v1/projects/{project_id}/slides/{slide_id}
```

**响应示例**

```json
{
  "code": 200,
  "message": "幻灯片删除成功",
  "data": null
}
```

### 重新排序幻灯片

```http
POST /api/v1/projects/{project_id}/slides/reorder
```

**请求体**

```json
{
  "slide_ids": ["slide-003", "slide-001", "slide-002"]
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "幻灯片排序更新成功",
  "data": {
    "slides": [
      { "id": "slide-003", "idx": 1 },
      { "id": "slide-001", "idx": 2 },
      { "id": "slide-002", "idx": 3 }
    ]
  }
}
```

### 添加幻灯片

在幻灯片列表末尾添加单个幻灯片。

```http
POST /api/v1/projects/{project_id}/slides/add
```

**请求体**

```json
{
  "type": "content",
  "title": "新幻灯片标题",
  "description": "幻灯片描述",
  "content": "幻灯片详细内容"
}
```

**响应示例**

```json
{
  "code": 201,
  "message": "幻灯片添加成功",
  "data": {
    "id": "slide-003",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "content",
    "title": "新幻灯片标题",
    "description": "幻灯片描述",
    "content": "幻灯片详细内容",
    "idx": 3,
    "image_path": null,
    "audio_path": null,
    "created_at": "2026-03-26T10:00:00Z",
    "updated_at": "2026-03-26T10:00:00Z"
  }
}
```

**说明**

- 新幻灯片会自动添加到列表末尾，`idx` 值自动设置为当前最大索引 +1
- 幻灯片的 `image_path` 和 `audio_path` 初始值为 null
