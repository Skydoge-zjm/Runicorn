/**
 * Tauri environment utilities
 *
 * Provides helpers to detect the Tauri runtime and open URLs
 * in a way that works both in browser and Tauri desktop contexts.
 *
 * - Remote Viewer sessions → open in a new Tauri WebviewWindow (native window)
 * - Downloads / external links → open in system browser (Tauri) or new tab (browser)
 */

/**
 * Returns true when running inside a Tauri WebView (v2).
 */
export function isTauri(): boolean {
  return (
    typeof window !== 'undefined' &&
    '__TAURI_INTERNALS__' in window
  )
}

/**
 * Open a URL in a **new native Tauri window** (WebviewWindow).
 *
 * Use this for pages that should stay inside the desktop app
 * (e.g. a Remote Viewer session running on a local port).
 *
 * Falls back to `window.open` in a browser environment.
 *
 * @param url   The full URL to load (e.g. `http://localhost:12345`)
 * @param label A unique label for the Tauri window (no spaces / special chars)
 * @param title Window title shown in the title bar
 */
export async function openInTauriWindow(
  url: string,
  label: string,
  title: string,
): Promise<void> {
  if (!isTauri()) {
    window.open(url, '_blank')
    return
  }

  try {
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('open_remote_window', { url, label, title })
  } catch (err) {
    console.warn('[tauri] Failed to create window, falling back to browser:', err)
    window.open(url, '_blank')
  }
}

/**
 * Open a URL in the **system default browser**.
 *
 * In Tauri: uses the shell plugin (`shell:allow-open` required).
 * In browser: falls back to `window.open`.
 */
export async function openExternal(url: string): Promise<void> {
  if (!isTauri()) {
    window.open(url, '_blank')
    return
  }

  try {
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('open_in_browser', { url })
  } catch (err) {
    console.warn('[tauri] open_in_browser failed:', err)
    window.open(url, '_blank')
  }
}
