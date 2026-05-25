# PetFlow

PetFlow is a Python desktop workflow manager built around a task graph, a 7-day agenda sidebar, and a fixed desktop companion panel.

The app combines:

- a graph canvas for tasks, dependencies, resources, and rewards
- a collapsible "Next 7 days" list on the left
- a desktop companion on the right that can chat or generate flows
- optional Agent integration for planning and graph generation

## Tech Stack

- Python 3.12
- Tkinter
- JSON persistence
- `requests` for API integration
- Pillow for image assets

## Project Layout

```text
src/petflow/        application package
data/               local graph and settings files
docs/               design notes
tests/              unit tests
```

## Run

From the repository root:

```bash
PYTHONPATH=src python -m petflow.main
```

If you install the package, you can also start it with:

```bash
petflow
```

## Development Environment

Use the `petflow` Conda environment for team development.

```bash
conda env create -f environment.yml
conda activate petflow
```

Recommended checks:

```bash
PYTHONPATH=src python -m compileall src tests
PYTHONPATH=src python -m unittest discover -s tests
```

## What the App Does

- Create, edit, delete, drag, and connect nodes on a canvas.
- Store task metadata such as status, priority, estimate, tags, checklist, attachments, resource type, repeat settings, and due dates.
- Render dependency, routine, recommendation, trigger, and reward-style relationships.
- Show a collapsible 7-day agenda list on the left.
- Show a desktop companion panel on the right.
- Use a recommendation engine to pick the next task.
- Animate task completion with a subtle path-flow effect.
- Auto-fit the graph after sample loading, layout changes, recommendation updates, and Agent-generated inserts.

## UI Notes

- `More` opens the app menu, including Settings, layout actions, clipboard capture, review, and panel toggles.
- The left agenda panel and right companion panel are both resizable and can be collapsed.
- The graph canvas is the center focus; side panels are designed to stay out of the way.
- The companion panel has two actions:
  - `Ask` for normal conversation
  - `Plan Flow` for graph generation

## Agent / DeepSeek Setup

PetFlow supports OpenAI-compatible providers. DeepSeek works with the same request shape used by the app.

Open:

```text
More -> Settings / API Key...
```

Then:

1. Click `Use DeepSeek Defaults`.
2. Paste your DeepSeek API key.
3. Keep `Use mock mode` off.
4. Click `Test API`.
5. Save when the test succeeds.

Default DeepSeek values used by the UI:

```text
Base URL: https://api.deepseek.com
Wire API: chat_completions
Model for Test API: deepseek-v4-flash
```

Notes:

- The app strips whitespace from the saved API key and base URL before sending requests.
- The request header is sent as `Authorization: Bearer <api_key>` with `Content-Type: application/json`.
- The API key is never placed in the request body.
- If the server returns a non-200 response, the UI shows the HTTP status code and response body so you can tell invalid key, invalid model, insufficient balance, and network problems apart.
- The full API key is never printed; diagnostics mask it as `sk-****last4`.

## Companion Modes

### Ask

Use `Ask` for plain conversation. The companion returns a JSON object with a single `reply` field and does not change the graph.

### Plan Flow

Use `Plan Flow` to generate or extend a task graph. The Agent must return the existing graph proposal contract:

```json
{
  "nodes": [],
  "edges": []
}
```

Supported node fields include:

- `id`
- `type`
- `title`
- `description`
- `status`
- `priority`
- `estimated_minutes`
- `repeat_type`
- `repeat_interval`
- `next_due_at`
- `x`
- `y`

Supported edge fields include:

- `source`
- `target`
- `type`
- `label`

## Sample Demo Flow

1. Launch the app.
2. Click `Sample` to load the demo graph.
3. Use `Fit View` if you want to center the graph.
4. Try dragging the canvas panel separators to resize the agenda and companion panels.
5. Click `Recommend` to see the current recommended task.
6. Mark a node `Done` to trigger the completion animation and companion reaction.
7. Use `Ask` for a normal question or `Plan Flow` to ask the Agent to build a task graph.

## Team Workflow

- Keep `main` green.
- Use feature branches for focused changes.
- Update tests when changing graph rules, JSON fields, or Agent behavior.
- Keep `data/settings.json` local and uncommitted if it contains real API credentials.

## Notes

- If no API key is configured, the Agent path falls back to mock mode.
- The current codebase includes compatibility for both planning responses and conversational responses.
- The project is designed so that teammates can later swap in their own Agent deployment without changing the graph JSON contract.
