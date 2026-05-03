# PetFlow

PetFlow is a Python desktop workflow manager built around a task graph and a desktop pet.

## Stack

- Python 3.10-3.12
- Tkinter
- JSON persistence
- requests / httpx for API integration
- Pillow for image assets

## Project layout

```text
src/petflow/        application package
docs/               design notes
data/               local graph files
tests/              test placeholders
```

The architecture rules are documented in `docs/architecture.md`.

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

Run core tests with the standard library:

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

More collaboration rules are documented in `docs/development.md`.

## Current scope

- Application shell
- Shared data model
- JSON storage
- Basic recommendation service
- Tkinter main window and canvas placeholder
