# PetFlow

PetFlow is a Python desktop workflow manager built around a task graph, a 7-day agenda sidebar, and a right-side workspace for editing or companion chat.

The app combines:

- a graph canvas for tasks, dependencies, resources, and rewards
- a collapsible "Next 7 days" list on the left
- a right-side panel with an inline inspector and a desktop companion
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
- Use `New Node` for quick task creation at the visible canvas center.
- Use `New Edge` to connect two selected nodes, then refine the edge in the inspector.
- Store task metadata such as status, priority, estimate, tags, checklist, attachments, resource type, repeat settings, and due dates.
- Render dependency, routine, recommendation, trigger, and reward-style relationships.
- Show a collapsible 7-day agenda list on the left.
- Show a right-side panel with `Edit` and `Companion` tabs.
- Edit selected nodes and edges inline from the `Edit` inspector.
- Use a recommendation engine to pick the next task.
- Animate task completion with a subtle path-flow effect.
- Auto-fit the graph after sample loading, layout changes, recommendation updates, and Agent-generated inserts.

## UI Notes

- The top toolbar exposes graph, view, panel, clipboard, review, settings, Agent, and focus actions as icon buttons.
- Hover any toolbar icon to see its action name.
- Use the theme icon in the top-right command bar to switch between the light workspace and the WeChat-style dark workspace.
- The left agenda panel and right panel are both resizable and can be collapsed.
- The agenda and right panel icons stay visible after a panel is hidden, so either panel can be restored from the toolbar.
- The graph canvas is the center focus; side panels are designed to stay out of the way.
- The right panel has two tabs:
  - `Edit` for the selected node or edge inspector
  - `Companion` for chat and Agent-assisted graph generation
- `Edit Mode` opens the right panel on the inspector and keeps selections focused there.
- `Edit Mode` also switches the mission canvas into an infinite grid background so node placement feels precise without boxing the graph into a visible boundary.
- Focus mode shows an elapsed timer in the recommendation banner. On narrower windows, the timer moves below the recommendation text instead of covering it.
- Double-clicking a node opens the inspector and focuses its title field.
- Clicking empty canvas space clears the current selection and starts canvas panning.
- `New Node` creates an `Untitled Task` with default status `todo`, priority `3`, and a 30-minute estimate, then focuses the inspector so it can be renamed immediately.
- `New Edge` enters edge mode. Click a source node, then a target node. The app creates a dependency edge by default; use the inspector to change the edge type or label.
- Press `Esc` to cancel edge mode.
- The companion tab has two actions:
  - `Ask` for normal conversation
  - `Plan Flow` for graph generation

## Inspector Editing

The `Edit` tab replaces most routine modal editing. Select a node or edge to edit it inline.

For nodes, the inspector can update:

- title, type, status, priority, estimate, and actual time
- due date presets (`Today`, `Tomorrow`, `+7 Days`, `Clear`) or a custom date value
- repeat type and repeat interval
- description, tags, resource type, and resource path

For edges, the inspector can update:

- edge type
- edge label

Use `Advanced...` when you need the older dialog-based editor. Use `Delete Node` or `Delete Edge` from the inspector for destructive edits.

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
2. Click `Load sample graph` to load the roadshow mission: `Prepare my dog for a weekend trip`.
3. Watch the mission map reveal: eight checkpoints, dependency routes, a current focus checkpoint, and a suggested next checkpoint.
4. Open `Generate Mission Map`, enter `Prepare my dog for a weekend trip`, click `Generate Preview`, then click `Apply Mission`.
5. Click the suggested checkpoint in the canvas to show node highlighting and Companion context.
6. Click `Start focus mode` to show the Mission Timer and focused node state.
7. Click `Complete selected checkpoint` to show the Done badge, path update, next recommendation, and Companion feedback.
8. Click `Edit Mode` to show the infinite grid editing background and use the right inspector.
9. Click the theme icon to switch into dark mode; the toolbar, side panels, canvas, inputs, and Agent dialog should all move into the dark palette.
10. Use `Ask` for a normal question or `Plan Flow` to ask the Agent to build or extend a task graph.

For a 60-90 second roadshow video, follow steps 2-9 in order. The key story is that PetFlow turns a natural-language pet-care goal into a navigable mission map, recommends the next checkpoint, tracks focus, and advances the workflow when a task is completed.

## Team Workflow

- Keep `main` green.
- Use feature branches for focused changes.
- Update tests when changing graph rules, JSON fields, or Agent behavior.
- Keep `data/settings.json` local and uncommitted if it contains real API credentials.

## Notes

- If no API key is configured, the Agent path falls back to mock mode.
- The current codebase includes compatibility for both planning responses and conversational responses.
- The project is designed so that teammates can later swap in their own Agent deployment without changing the graph JSON contract.
