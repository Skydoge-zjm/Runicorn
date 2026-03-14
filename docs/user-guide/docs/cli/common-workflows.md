# Common Workflows

This page collects the command-line tasks you are likely to repeat in daily use.

---

## Set up a machine

```bash
pip install -U runicorn
runicorn config --set-user-root "E:\RunicornData"
runicorn config --show
runicorn viewer
```

---

## Export runs for backup

```bash
runicorn export --project cv --out backups/cv_runs.tar.gz
```

Use this when you want an archive for transfer or backup outside the viewer.

---

## Import a transferred archive

```bash
runicorn import --archive backups/cv_runs.tar.gz
```

The current Web UI also offers a richer import-preview flow, but the CLI is still useful for scripted transfers.

---

## Export metrics for reports

```bash
runicorn export-data --run-id 20260115_100000_abc123 --format csv
runicorn export-data --run-id 20260115_100000_abc123 --format html --output report.html
```

---

## Tag, search, and clean up

```bash
runicorn manage --action tag --run-id 20260115_100000_abc123 --tags baseline,resnet50
runicorn manage --action search --project cv --text baseline
runicorn manage --action cleanup --days 30 --dry-run
```

---

## Permanently delete runs

Preview first:

```bash
runicorn delete --run-id 20260115_100000_abc123 --dry-run
```

Then confirm:

```bash
runicorn delete --run-id 20260115_100000_abc123 --force
```

---

## Rate-limit inspection

```bash
runicorn rate-limit --action show
runicorn rate-limit --action list
```

Most users do not need to change this, but it matters when you package Runicorn into a more controlled environment.

---

## Next steps

- [CLI Overview](overview.md)
- [CLI Reference](../reference/cli-reference.md)
- [Import, Export & Recycle Bin](../ui/import-export-recycle-bin.md)
