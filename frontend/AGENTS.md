## Project Structure

```text
├── app/                    # Next.js App Router 入口、layout、route handlers
├── features/
│   ├── chat/               # 首页聊天工作台
│   ├── preview/            # 预览页与媒体生成流程
│   └── projects/           # 项目/幻灯片/对话领域模型与高层服务
├── shared/
│   └── api/banana/         # BananaLecture REST requester、client、DTO
├── server/
│   └── planner/            # 仅服务端使用的 agent、prompt、tool schema
├── tests/
│   └── unit/               # 单元测试
├── package.json
└── tsconfig.json
```

## Architecture

- **App Shape**: 这是一个按 feature 拆分的 Next.js 前端，不要把业务逻辑堆回 `app/` 路由文件。
- **Route Layer**: `app/` 只放页面入口、layout 和 API route handler。页面主体必须放在 `features/`。
- **Feature Boundary**: `features/projects` 是项目领域的唯一高层入口。项目、幻灯片、对话、任务相关逻辑统一从这里组织。
- **API Boundary**: 所有 BananaLecture 后端请求统一通过 `shared/api/banana` 发起。不要在 feature 或 route 中手写 REST URL。
- **Server Boundary**: `server/planner` 只能被服务端代码引用；client component 不得直接导入。
- **Proxy Contract**: 前端继续通过 `/api/v1/[...path]` 代理到后端，外部 API 路径与 DTO 结构必须与后端保持一致。

## Code Style

### Frontend

- **Thin Routes**: `app/page.tsx`、`app/preview/page.tsx` 只做挂载，不承载复杂状态机。
- **Feature First**: 新组件优先放到对应 `features/<domain>/components`
- **Pure Logic Extraction**: 可复用的纯函数、映射器、差异比较与分页工具放在 feature 内的 `utils.ts`、`plan-sync.ts` 等文件，不要留在大组件内部。
- **Types**: 尽量使用明确类型；只有在 AI SDK 消息结构不可避免时，才局部使用 `unknown`/`any`。
- **Client/Server Split**: 带 `'use client'` 的组件不得反向依赖 `server/` 下模块。

### API & Agent

- **Requester Layer**: `shared/api/banana/request.ts` 负责底层 fetch、错误包装、文件 URL 构建。
- **Client Layer**: `shared/api/banana/client.ts` 负责 REST 资源方法；不要在 UI 组件里直接操作 DTO。
- **Planner Layer**: prompt、style config、tool schema 分开维护；新增风格或 prompt 规则时先改 `server/planner/`。

## Development

### Common Commands

- `npm run dev`: 启动本地开发环境
- `npm run lint`: 运行 ESLint
- `npm run typecheck`: 先生成 Next 类型，再执行 TypeScript 检查
- `npm run test`: 运行单元测试
- `npm run build`: 运行生产构建
- `npm run check`: 依次执行 lint、typecheck、test

### Workflow

1. 先阅读相关 feature、shared、server 代码，确认变更落点。
2. 新增行为时优先补单元测试，至少覆盖纯逻辑和 API 映射。
3. 实现时保持目录边界，不要为省事跨层直接引用。
4. 完成后至少运行 `npm run test`、`npm run typecheck`；涉及页面或路由改动时再跑 `npm run build`。

## Guardrails

- 不要把后端返回 DTO 直接散播到 UI；先在 `features/projects` 做映射。
- 不要在组件中硬编码后端基础 URL、任务轮询协议或资源路径。

### Commit
Before committing your changes, please ensure that your code passes all quality checks and adheres to the commit message format. For detailed instructions, please refer to [commit.md](docs/commit.md).
