## 任务接口

任务用于跟踪长时间运行的操作。

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/tasks/{task_id}` | 获取任务信息 |
| DELETE | `/api/v1/tasks/{task_id}` | 取消任务 |

### 获取任务信息

获取指定任务的详细信息和进度。

```http
GET /api/v1/tasks/{task_id}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "task-550e8400-0003",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "audio_generation",
    "status": "running",
    "current_step": 30,
    "total_steps": 50,
    "error_message": null,
    "created_at": "2026-03-24T10:00:00.000Z",
    "updated_at": "2026-03-24T10:05:00.000Z"
  }
}
```

### 取消任务

取消正在运行的任务。

```http
DELETE /api/v1/tasks/{task_id}
```

**响应示例**

```json
{
  "code": 200,
  "message": "任务已取消",
  "data": {
    "id": "task-550e8400-0003",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "audio_generation",
    "status": "cancelled",
    "current_step": 30,
    "total_steps": 50,
    "error_message": "Task cancelled",
    "created_at": "2026-03-24T10:00:00.000Z",
    "updated_at": "2026-03-24T10:05:00.000Z"
  }
}
```
