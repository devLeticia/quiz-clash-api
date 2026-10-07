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
