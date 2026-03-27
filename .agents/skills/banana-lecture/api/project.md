## 项目接口

项目是整个系统的核心实体，一个项目对应一个 PPT 讲解视频的生成任务。

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/projects` | 创建一个新的项目 |
| GET | `/api/v1/{user_id}/projects` | 获取指定用户的所有项目列表 |
| GET | `/api/v1/projects/{project_id}` | 获取指定项目的详细信息，包括关联的幻灯片 |
| PUT | `/api/v1/projects/{project_id}` | 更新项目的基本信息或消息内容 |
| DELETE | `/api/v1/projects/{project_id}` | 删除指定项目及其关联的所有资源 |

### 创建项目

创建一个新的项目。

```http
POST /api/v1/projects
```

**请求体**

```json
{
  "name": "我的PPT讲解视频",
  "user_id": "admin"
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `name` | string | 是 | 项目名称，长度1-255 |
| `user_id` | string | 否 | 用户ID；当前推荐显式传入 `admin`，因为系统尚未实现用户认证 |

**响应示例**

```json
{
  "code": 201,
  "message": "项目创建成功",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "admin",
    "name": "我的PPT讲解视频",
    "messages": null,
    "video_path": null,
    "created_at": "2026-03-26T10:00:00Z",
    "updated_at": "2026-03-26T10:00:00Z"
  }
}
```

**说明**

- 当前项目接口仍接受省略 `user_id` 的请求
- 由于系统尚未实现用户认证，当前推荐调用方显式传入 `admin`

### 获取项目列表

获取指定用户的所有项目列表。

```http
GET /api/v1/{user_id}/projects
```

**查询参数**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `page` | integer | 否 | 页码，默认1 |
| `page_size` | integer | 否 | 每页数量，默认20，最大100 |
| `sort_by` | string | 否 | 排序字段，默认 created_at |
| `order` | string | 否 | 排序方向，asc 或 desc，默认 desc |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "我的PPT讲解视频",
        "created_at": "2026-03-26T10:00:00Z",
        "updated_at": "2026-03-26T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 1,
      "total_pages": 1
    }
  }
}
```

### 获取项目详情

获取指定项目的详细信息，包括关联的幻灯片。

```http
GET /api/v1/projects/{project_id}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "admin",
    "name": "我的PPT讲解视频",
    "messages": "[]",
    "video_path": null,
    "created_at": "2026-03-26T10:00:00Z",
    "updated_at": "2026-03-26T10:00:00Z",
    "slides": [
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

### 更新项目

更新项目的基本信息或消息内容。

```http
PUT /api/v1/projects/{project_id}
```

**请求体**

```json
{
  "name": "新的项目名称",
  "messages": "[]"
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `name` | string | 否 | 新的项目名称，长度1-255 |
| `messages` | string | 否 | 聊天消息内容，存储为 JSON 格式 |

**响应示例**

```json
{
  "code": 200,
  "message": "项目更新成功",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "新的项目名称",
    "messages": "[]",
    "updated_at": "2026-03-26T10:05:00Z"
  }
}
```

**说明**

- `name` 和 `messages` 字段至少需要提供一个
- `messages` 字段用于存储项目的对话历史，格式为 JSON 数组
- `created_at` 和 `updated_at` 均为 UTC ISO 8601 时间字符串

### 删除项目

删除指定项目及其关联的所有资源。

```http
DELETE /api/v1/projects/{project_id}
```

**响应示例**

```json
{
  "code": 200,
  "message": "项目删除成功",
  "data": null
}
```

**说明**

- 删除项目时会级联删除关联的幻灯片和对话
- 删除项目时不会自动清理磁盘中的历史生成文件；接口保证数据库资源与当前 API 行为一致
