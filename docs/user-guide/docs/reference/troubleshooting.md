# Troubleshooting

This page collects common issues for the current develop-branch workflow.

---

## The UI looks older than the docs

Check the installed package version first:

```bash
runicorn --version
```

If your environment is not actually on 0.7.0 yet, some pages and controls will differ.

---

## Viewer starts but shows the wrong storage root

Check:

```bash
runicorn config --show
```

Also remember the override order:

1. `rn.init(storage=...)`
2. `RUNICORN_DIR`
3. user config
4. `./.runicorn`

---

## I do not see my runs

Check:

- your training code used the storage root you expect
- the `path` is what you think it is
- you are browsing the correct local or remote storage root

---

## Remote authentication fails

Check:

- hostname
- username
- key path
- password
- whether the remote environment actually has Runicorn installed

---

## Remote host key warnings appear

A host key warning is a security check, not just an inconvenience. Verify the host key before accepting it if the machine is supposed to be familiar.

---

## Remote session is stuck in reconnecting or degraded

Wait briefly for automatic recovery first. If it does not recover:

1. stop the session
2. verify SSH access manually
3. start the session again

---

## Logs are too large or hard to follow

Use:

- `capture_console=True`
- `tqdm_mode="smart"`
- fewer noisy prints inside inner loops

The current UI handles large logs better than older releases, but cleaner logs are still easier to work with.

---

## Import reports conflicts

That usually means the archive contains run IDs or paths that already exist. Use the preview step to decide whether to merge or isolate the import.

---

## Need more detail?

- [FAQ](faq.md)
- [CLI Reference](cli-reference.md)
- [Remote Viewer Guide](../getting-started/remote-viewer.md)
