import { useState } from 'react'
import { api } from '../api'

const ROLES = [
  { id: 'student', label: 'Student', hint: 'SAP ID' },
  { id: 'faculty', label: 'Faculty', hint: 'Username' },
  { id: 'admin', label: 'Admin', hint: 'Username' },
]

export default function Login({ onLogin }) {
  const [role, setRole] = useState('student')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      onLogin(await api('/auth/login', { method: 'POST', body: { username, password, role } }))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const hint = ROLES.find((r) => r.id === role).hint
  return (
    <div className="login-page">
      <form className="card login" onSubmit={submit}>
        <div className="brand big">☁ ResultCloud</div>
        <p className="muted">Cloud-Based Student Result Management System</p>
        <div className="tabs">
          {ROLES.map((r) => (
            <button type="button" key={r.id} className={r.id === role ? 'active' : ''}
              onClick={() => { setRole(r.id); setError('') }}>{r.label}</button>
          ))}
        </div>
        <label>{hint}
          <input value={username} onChange={(e) => setUsername(e.target.value)} required
            placeholder={role === 'student' ? 'e.g. 70572400001' : ''} autoFocus />
        </label>
        <label>Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <div className="alert error">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? 'Signing in…' : `Sign in as ${role}`}</button>
      </form>
    </div>
  )
}
