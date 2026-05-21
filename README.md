# PetFlow

PetFlow is a Python desktop workflow manager built around a task graph and an in-graph desktop pet.

## Stack

- Python 3.12
- Tkinter
- JSON persistence
- requests for API integration
- Pillow for image assets

The current codebase is the baseline for team development and is documented in:

- `docs/architecture.md`
- `docs/development.md`
- `docs/roadmap.md`

## Project layout

```text
src/petflow/        application package
docs/               design notes
data/               local graph files
tests/              unit tests
```

The architecture rules are documented in `docs/architecture.md`.
The implementation roadmap is documented in `docs/roadmap.md`.

## Run

```bash
PYTHONPATH=src python -m petflow.main
```

Or after installing the package:

```bash
petflow
```

## Development environment

Use the `petflow` Conda environment for team development. Python 3.13 can expose
Tcl/Tk compatibility issues on macOS, so it is not the recommended interpreter
for this project.

```bash
conda env create -f environment.yml
conda activate petflow
```

Run core checks with the standard library:

```bash
PYTHONPATH=src python -m compileall src tests
PYTHONPATH=src python -m unittest discover -s tests
```

More collaboration rules are documented in `docs/development.md`.

## Current scope

- Editable Tkinter Canvas task graph.
- Node and edge creation, editing, deletion, dragging, save/load.
- Dependency cycle rejection with Routine / Recommendation / Trigger edge support.
- Workspace navigation: layout, zoom, pan, reset view.
- Node detail fields: tags, actual time, resource type/path, checklist, attachments.
- Local recommendation engine with dependency checks, Routine weighting, and reasons.
- In-graph pet assistant with speech bubbles and lightweight movement animation.
- Agent graph generation and node splitting with mock/API mode and structured preview.
- Review summary, clipboard capture, resource copy, and focus mode fallback.
- JSON sample graph for demos and regression checks.

## Demo flow

1. Run `PYTHONPATH=src python -m petflow.main`.
2. Click `Sample` to load `data/sample_graph.json`.
3. Try `Layout`, zoom, pan, create/edit nodes, and create a Dependency edge.
4. Mark a node done and click `Recommend Next` to see the reason and pet response.
5. Use `Agent` to generate or split a task graph; mock mode works without an API key.
6. Select a Resource node and use `Copy Resource`.
7. Open `Review` for a local progress summary.

## Team workflow

- Keep `main` green.
- Use feature branches for one focused change at a time.
- Update tests when changing domain rules or JSON fields.
- Keep `data/settings.json` local and uncommitted.
