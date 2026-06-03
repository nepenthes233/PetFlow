# Mascot Themes

Each mascot theme lives in its own folder. Built-in themes live under
`assets/mascots`; user-installed themes can live under `data/mascots`.

Required structure:

```text
data/mascots/my_anime_pet/
  mascot.json
  idle.png
  focused.png
  complete.png
```

`mascot.json`:

```json
{
  "id": "my_anime_pet",
  "name": "My Anime Pet",
  "type": "image",
  "size": [88, 108],
  "states": {
    "idle": "idle.png",
    "focused": "focused.png",
    "complete": "complete.png"
  }
}
```

Images should be transparent PNG files with a consistent character position. A
larger source such as `352x432` works well because the UI renders it at
`88x108`.
