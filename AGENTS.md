# BananaLecture Monorepo

AI-powered PPT lecture video generation platform.

## Project Overview

BananaLecture is a full-stack application that enables users to create engaging lecture videos from PowerPoint presentations. It combines AI-driven content generation, dialogue creation, image synthesis, and video rendering into a seamless workflow.

## Tech Stack

| Layer | Technology | Details |
|-------|------------|---------|
| **Frontend** | Next.js 15 (App Router) | React 18, Tailwind CSS, TypeScript, Bun |
| **Backend** | FastAPI | Python 3.12, SQLAlchemy 2.0, Pydantic v2 |
| **Media** | FFmpeg | Audio processing, video composition |
| **Database** | SQLite (aiosqlite) | Async SQLAlchemy ORM |
| **Container** | Docker Compose | Alpine-based images |

## Monorepo Structure

```
bananalecture/
├── backend/                    # FastAPI backend API
├── frontend/                   # Next.js frontend
├── .github/                    # GitHub config (CI/CD, issue templates, PR templates)
├── .agents/skills/             # AI agent skill definitions
│   └── banana-lecture/         # Project-specific skills
│       ├── SKILL.md            # Skill entry point
│       ├── api/                # API documentation (project, slide, dialogue, media, task, audio, image, video)
│       ├── DB.md               # Database schema documentation
│       └── storage.md          # Storage layout documentation
├── config.yaml                 # Backend production configuration
├── docker-compose.yml          # Container orchestration
├── .env.frontend.example       # Frontend environment variables template
└── .env.backend.example        # Backend environment variables template
```

## References

- **Backend Architecture**: [backend/AGENTS.md](backend/AGENTS.md) - FastAPI layered architecture, dependency injection, port/adapter pattern
- **Frontend Architecture**: [frontend/AGENTS.md](frontend/AGENTS.md) - Next.js feature modules, API client layer, AI agent integration
- **Commit Guidelines**: [docs/commit.md](docs/commit.md) - Conventional commits format and quality checks. MUST read this document before committing any code
