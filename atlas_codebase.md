# Codebase: atlas

## Directory Tree
```text
atlas
├── apps
│   ├── admin
│   │   └── .gitkeep
│   └── web
│       └── .gitkeep
├── benchmarks
│   ├── coding
│   │   └── .gitkeep
│   ├── mathematics
│   │   └── .gitkeep
│   ├── planning
│   │   └── .gitkeep
│   ├── reasoning
│   │   └── .gitkeep
│   ├── registry
│   │   └── .gitkeep
│   ├── safety
│   │   └── .gitkeep
│   ├── tool_use
│   │   └── .gitkeep
│   └── .gitkeep
├── cli
│   ├── commands
│   │   └── .gitkeep
│   ├── templates
│   │   └── .gitkeep
│   └── .gitkeep
├── configs
│   ├── development
│   │   └── .gitkeep
│   ├── production
│   │   └── .gitkeep
│   ├── staging
│   │   └── .gitkeep
│   ├── testing
│   │   └── .gitkeep
│   └── .gitkeep
├── datasets
│   ├── importers
│   │   └── .gitkeep
│   ├── licenses
│   │   └── .gitkeep
│   ├── metadata
│   │   └── .gitkeep
│   ├── processed
│   │   └── .gitkeep
│   ├── raw
│   │   └── .gitkeep
│   └── .gitkeep
├── docker
│   ├── backend
│   │   └── .gitkeep
│   ├── base-images
│   │   └── .gitkeep
│   ├── benchmark
│   │   └── .gitkeep
│   ├── frontend
│   │   └── .gitkeep
│   ├── ollama
│   │   └── .gitkeep
│   ├── postgres
│   │   └── .gitkeep
│   ├── redis
│   │   └── .gitkeep
│   ├── sandboxes
│   │   └── .gitkeep
│   └── .gitkeep
├── docs
│   ├── api
│   │   └── .gitkeep
│   ├── architecture
│   │   └── .gitkeep
│   ├── atlas-bible
│   │   └── .gitkeep
│   ├── diagrams
│   │   └── .gitkeep
│   ├── handbook
│   │   └── .gitkeep
│   ├── meeting-notes
│   │   └── .gitkeep
│   ├── roadmap
│   │   └── .gitkeep
│   └── scratchpad
│       └── .gitkeep
├── infrastructure
│   ├── compose
│   │   └── .gitkeep
│   ├── deployment
│   │   └── .gitkeep
│   ├── monitoring
│   │   └── .gitkeep
│   ├── nginx
│   │   └── .gitkeep
│   └── .gitkeep
├── packages
│   ├── adapters
│   │   └── .gitkeep
│   ├── auth
│   │   └── .gitkeep
│   ├── capability
│   │   └── .gitkeep
│   ├── config
│   │   └── .gitkeep
│   ├── database
│   │   └── .gitkeep
│   ├── logger
│   │   └── .gitkeep
│   ├── metrics
│   │   └── .gitkeep
│   ├── ui
│   │   └── .gitkeep
│   ├── utilities
│   │   └── .gitkeep
│   └── validation
│       └── .gitkeep
├── scripts
│   ├── benchmark
│   │   └── .gitkeep
│   ├── database
│   │   └── .gitkeep
│   ├── deployment
│   │   └── .gitkeep
│   ├── setup
│   │   └── .gitkeep
│   ├── utilities
│   │   └── .gitkeep
│   └── .gitkeep
├── sdk
│   ├── python
│   │   └── .gitkeep
│   ├── typescript
│   │   └── .gitkeep
│   └── .gitkeep
├── services
│   ├── auth
│   │   └── .gitkeep
│   ├── auth-service
│   │   └── .gitkeep
│   ├── benchmark
│   │   └── .gitkeep
│   ├── dataset
│   │   └── .gitkeep
│   ├── evaluation
│   │   └── .gitkeep
│   ├── evaluation-service
│   │   └── .gitkeep
│   ├── execution-service
│   │   └── .gitkeep
│   ├── leaderboard
│   │   └── .gitkeep
│   ├── notification
│   │   └── .gitkeep
│   ├── project
│   │   └── .gitkeep
│   ├── report
│   │   └── .gitkeep
│   ├── storage
│   │   └── .gitkeep
│   └── user
│       └── .gitkeep
├── tests
│   ├── backend
│   │   └── .gitkeep
│   ├── evaluation
│   │   └── .gitkeep
│   ├── frontend
│   │   └── .gitkeep
│   ├── integration
│   │   └── .gitkeep
│   ├── performance
│   │   └── .gitkeep
│   └── .gitkeep
├── .gitignore
├── docker-compose.yml
├── LICENSE
├── Makefile
└── README.md
```

## Files and Contents

### File: `.gitignore`

```
__pycache__/
.env
.venv/
node_modules/
.next/
pnpm-lock.yaml
poetry.lock
```

### File: `README.md`

```md
# Project Atlas

Project Atlas is an AI Evaluation Operating System built from scratch as a modular monorepo.

- **Organization:** [Synthesis-works](https://github.com/Synthesis-works)
- **Repository:** [atlas](https://github.com/Synthesis-works/atlas)

## Repository Structure

The monorepo follows the Atlas V1 Repository Architecture:

- `apps/` - Main frontend applications (e.g., `web/`)
- `services/` - Backend microservices (e.g., `auth-service/`, `execution-service/`, `evaluation-service/`)
- `packages/` - Reusable internal code and libraries (e.g., `database/`)
- `benchmarks/` - AI evaluation benchmarks
- `datasets/` - Raw and processed data
- `infrastructure/` - Deployment and hosting configuration
- `docker/` - Containerization files
- `scripts/` - Automation and setup utilities
- `docs/` - Project documentation (e.g., `scratchpad/`)
- `tests/` - System-wide testing
- `configs/` - Environment configurations
- `sdk/` - Future SDK development
- `cli/` - Future Command Line Interface
- `.github/` - CI/CD and repository automation
```

