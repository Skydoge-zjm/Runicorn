# Import, Export & Recycle Bin

The import/export and deletion flow changed substantially in 0.7.0. This page reflects the current user model.

---

## Export

The current UI exports selected runs as a ZIP archive containing full run directories.

Typical flow:

1. select one or more runs
2. click **Export**
3. download a timestamped ZIP archive

---

## Import preview

Import is now a two-step flow:

1. preview the archive
2. confirm the import mode

During preview, Runicorn can detect:

- duplicate run IDs
- path conflicts
- whether runs will merge into existing paths

Available modes:

- **merge**
- **isolate**

---

## Recycle bin

Soft deletion now flows through a unified recycle-bin model.

Important behaviors:

- deleted runs move into a recycle area
- restores try to return runs to their original path
- restore conflicts are surfaced clearly
- folder-level deletes also use the same recycle model

---

## When to use CLI instead

Use the CLI when you need scripted or headless behavior:

- `runicorn export`
- `runicorn import`
- `runicorn delete`

---

## Next steps

- [CLI Common Workflows](../cli/common-workflows.md)
- [Experiments & Paths](experiments-and-paths.md)
- [Troubleshooting](../reference/troubleshooting.md)
