## 视频接口

视频是项目的子资源，存储最终生成的讲解视频。

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/projects/{project_id}/video/generate` | 生成视频 |
| GET | `/api/v1/projects/{project_id}/video/file` | 获取视频文件 |

### 生成视频

将所有图片和音频合成为最终视频。

```http
POST /api/v1/projects/{project_id}/video/generate
```

**响应示例**

```json
{
  "code": 202,
  "message": "视频生成任务已创建",
  "data": {
    "task_id": "task-550e8400-0004",
    "project_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 获取视频文件

获取生成完成的视频文件。

```http
GET /api/v1/projects/{project_id}/video/file
```

**响应**

```
Content-Type: video/mp4
Content-Disposition: attachment; filename="project-video.mp4"

[binary video data]
```
