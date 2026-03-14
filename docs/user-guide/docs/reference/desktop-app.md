# Desktop App

Runicorn's desktop build is a native wrapper around the local viewer. It is most useful if you want a packaged, windowed workflow instead of manually opening a browser tab.

---

## Current status

The desktop app is Windows-oriented and built on Tauri. Availability depends on how your team distributes Runicorn, so not every installation will ship with it.

If you do not have the desktop build, the browser-based viewer remains the primary supported workflow.

---

## What the desktop app adds

- starts the local backend for you
- opens the viewer in a native window
- can open remote sessions in separate native windows
- sends external links to the system browser instead of trapping everything inside the app

---

## Shared behavior with the browser version

The desktop build still uses the same:

- storage root
- local viewer APIs
- experiments page
- assets page
- performance page
- remote page

So the user guide for the browser UI still applies almost entirely.

---

## When to use it

| Use the desktop build when... | Use the browser viewer when... |
|-------------------------------|--------------------------------|
| you want a native app window | you only need the local web UI |
| you manage multiple remote sessions | you are on a machine without the packaged app |
| you prefer desktop-style task switching | you want the simplest setup |

---

## Remote sessions in the desktop build

One of the main improvements in 0.7.0 is that Remote Viewer sessions can open in dedicated native windows rather than forcing every session into the same browser context.

This is especially useful when:

- you monitor multiple servers
- you want one remote session per desktop window
- you keep local and remote browsing separate

---

## If you do not have the desktop build

You are not missing any core tracking capability. The browser workflow is still the reference implementation for the user docs.

Start with:

```bash
runicorn viewer
```

---

## Next steps

- [Remote Viewer](../getting-started/remote-viewer.md)
- [Web UI Overview](../ui/overview.md)
- [Remote Workflow Tutorial](../tutorials/remote-workflow.md)
