## Development

This project uses [uv](https://github.com/astral-sh/uv) for dependency and virtual environment management.

### Setup
\`\`\`bash
uv sync
\`\`\`

### Lint and formatting
\`\`\`bash
uv run ruff check .      # lint
uv run ruff format .     # formatting
\`\`\`

### Pre-commit hooks
\`\`\`bash
uv run pre-commit install
\`\`\`
This ensures linting and formatting checks run automatically before every commit.

### Testing without the LLM
Set `FAKE_QUIZ=true` in `.env` to return fixed questions instead of reading files and calling OpenAI. No tokens are spent, and rate limiting is turned off. Set it back to `false` to generate real quizzes.

## Observability

### Logs
Every log line carries the `request_id` of the HTTP request that produced it, including work done in background threads.

- `LOG_FORMAT=text` (default): colored, human-readable lines for local development.
- `LOG_FORMAT=json`: one JSON object per line, used in production (set in the `Dockerfile`).
- `LOG_LEVEL`: defaults to `INFO`.

Main events: `request`, `quiz_created`, `generation_round`, `question_rejected` (with a `reason`), `asked_questions_reset`, `next_round` and `question_generation_failed`.

### Traces and metrics (LangSmith)
Quiz generation is traced with [LangSmith](https://smith.langchain.com). Each quiz creation is one trace: ingestion, `build_texts`, each `generate_round` and `generation_round`, the LLM calls, and the `prefetch_next_round` that runs in the background.

Metrics are recorded as feedback scores on the traces:

| Key | Run | Meaning |
|---|---|---|
| `fill_rate` | `generate_round` | Generated questions ÷ requested questions |
| `rejection_rate` | `generation_round` | Share of LLM questions rejected by the quality checks |
| `prefetch_hit` | `create_next_quiz` | 1 if the next round was ready when requested |
| `prefetch_wait_ms` | `create_next_quiz` | How long the player waited for the next round |

To enable it, set in `.env`:
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=quiz-clash-dev
```
Without these variables nothing is sent and the app works the same.
