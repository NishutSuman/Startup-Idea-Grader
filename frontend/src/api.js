const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function post(path, body) {
  const r = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok || data.error) throw new Error(data.error || `HTTP ${r.status}`)
  return data
}

export function expandIdea({ idea, provider, apiKey }) {
  return post('/expand', { idea, provider, api_key: apiKey || null })
}

export function evaluate({ mode, inputs, provider, apiKey, grounding }) {
  return post('/evaluate', {
    mode, inputs, provider, api_key: apiKey || null, grounding,
  })
}

export async function getHistory() {
  try {
    const r = await fetch(BASE + '/history')
    const d = await r.json()
    return d.items || []
  } catch {
    return []
  }
}

export async function getEvaluation(id) {
  const r = await fetch(BASE + '/history/' + id)
  const d = await r.json().catch(() => ({}))
  if (!r.ok || d.error) throw new Error(d.error || `HTTP ${r.status}`)
  return d
}
