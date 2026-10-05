// Small fetch wrapper: JSON in/out, throws the server's error message.
export async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch('/api' + path, {
    method,
    credentials: 'same-origin',
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`)
  return data
}

export const fmt = (n) => (n === null || n === undefined ? '-' : Number(n).toFixed(2))
export const semesters = [1, 2, 3, 4, 5, 6, 7, 8]
