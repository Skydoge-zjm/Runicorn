const BASE_URL: string = (import.meta as any).env?.VITE_API_BASE || '/api'
const url = (p: string) => `${BASE_URL}${p}`

export async function listRuns() {
  const res = await fetch(url('/runs'))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getRunDetail(id: string) {
  const res = await fetch(url(`/runs/${id}`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getMetrics(id: string) {
  const res = await fetch(url(`/runs/${id}/metrics`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getStepMetrics(id: string) {
  const res = await fetch(url(`/runs/${id}/metrics_step`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getProgress(id: string) {
  const res = await fetch(url(`/runs/${id}/progress`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function health() {
  const res = await fetch(url('/health'))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getGpuTelemetry() {
  const res = await fetch(url('/gpu/telemetry'))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ----- New hierarchy helpers -----
export async function listProjects() {
  const res = await fetch(url('/projects'))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ projects: string[] }>
}

export async function listNames(project: string) {
  const res = await fetch(url(`/projects/${encodeURIComponent(project)}/names`))
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ names: string[] }>
}

export async function listRunsByName(project: string, name: string) {
  const res = await fetch(url(`/projects/${encodeURIComponent(project)}/names/${encodeURIComponent(name)}/runs`))
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
