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
