## 图片接口

图片是幻灯片的子资源，存储幻灯片的视觉内容。

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/projects/{project_id}/slides/{slide_id}/image/generate` | AI生成图片 |
| POST | `/api/v1/projects/{project_id}/slides/{slide_id}/image/modify` | AI修改图片 |
| POST | `/api/v1/projects/{project_id}/images/batch-generate` | 批量生成图片 |
| GET | `/api/v1/projects/{project_id}/slides/{slide_id}/image/file` | 获取图片文件 |

### AI生成图片

使用 AI 根据幻灯片内容生成新的图片。

```http
POST /api/v1/projects/{project_id}/slides/{slide_id}/image/generate
```

**响应示例**

```json
{
  "code": 200,
  "message": "图片生成成功",
  "data": null
}
```

### AI修改图片

使用 AI 根据新的提示词修改现有的图片。

```http
POST /api/v1/projects/{project_id}/slides/{slide_id}/image/modify
```

**请求体**

```json
{
  "prompt": "将背景改为户外公园场景",
}
```

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `prompt` | string | 是 | 图片修改提示词 |

**响应示例**

```json
{
  "code": 200,
  "message": "图片修改成功",
  "data": null
}
```

### 获取图片文件

获取幻灯片的配图文件。

```http
GET /api/v1/projects/{project_id}/slides/{slide_id}/image/file
```

**响应**

```
Content-Type: image/webp
Content-Disposition: attachment; filename="slide-002.webp"

[binary image data]
```

### 批量生成图片

批量为项目下所有幻灯片生成图片。

```http
POST /api/v1/projects/{project_id}/images/batch-generate
```

**响应示例**

```json
{
  "code": 202,
  "message": "批量生成图片任务已创建",
  "data": {
    "task_id": "task-550e8400-0003",
    "project_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```
