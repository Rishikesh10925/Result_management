import { useEffect, useState } from 'react'
import { api, fmt } from '../api'
import { Alert, Stat } from '../components'

export default function Admin({ page }) {
  if (page === 'Students') return <Users role="student" />
  if (page === 'Faculty') return <Users role="faculty" />
  if (page === 'Results') return <Results />
  if (page === 'Academic Config') return <Config />
  if (page === 'Audit Logs') return <AuditLogs />
  return <Dashboard />
}

function Dashboard() {
  const [s, setS] = useState({})
  useEffect(() => { api('/admin/stats').then(setS) }, [])
  return (
    <div className="grid">
      <Stat label="Students" value={s.students ?? '-'} />
      <Stat label="Faculty" value={s.faculty ?? '-'} />
      <Stat label="Results" value={s.results ?? '-'} />
      <Stat label="Published" value={s.published ?? '-'} />
    </div>
  )
}

function Users({ role }) {
  const empty = { name: '', username: '', sap_id: '', password: '', current_sem: 1 }
  const [list, setList] = useState([])
  const [form, setForm] = useState(empty)
  const [msg, setMsg] = useState({})

  const load = () => api(`/admin/users?role=${role}`).then(setList)
  useEffect(() => { load(); setForm(empty); setMsg({}) }, [role]) // eslint-disable-line

  const create = async (e) => {
    e.preventDefault()
    try {
      await api('/admin/users', { method: 'POST', body: { ...form, role } })
      setForm(empty)
      setMsg({ ok: `${role} created.` })
      load()
    } catch (err) { setMsg({ err: err.message }) }
  }
  const edit = async (u) => {
    const name = prompt('Name', u.name)
    if (name === null) return
    const password = prompt('New password (leave blank to keep)') || undefined
    const current_sem = role === 'student' ? Number(prompt('Current semester', u.current_sem)) || u.current_sem : undefined
    try { await api(`/admin/users/${u.id}`, { method: 'PUT', body: { name, password, current_sem } }); load() }
    catch (err) { setMsg({ err: err.message }) }
  }
  const remove = async (u) => {
    if (!confirm(`Delete ${u.username}? This also deletes their marks and results.`)) return
    await api(`/admin/users/${u.id}`, { method: 'DELETE' })
    load()
  }
  const f = (k) => ({ value: form[k], onChange: (e) => setForm({ ...form, [k]: e.target.value }) })

  return (
    <>
      <form className="card" onSubmit={create}>
        <h3>Add {role}</h3>
        <div className="form-grid">
          <label>Name<input {...f('name')} required /></label>
          {role === 'student'
            ? <label>SAP ID<input {...f('sap_id')} required maxLength="11" placeholder="11 digits, 7057… or 7002…" /></label>
            : <label>Username<input {...f('username')} required /></label>}
          {role === 'student' && <label>Current semester<input type="number" min="1" max="8" {...f('current_sem')} /></label>}
          <label>Password<input type="password" {...f('password')} required minLength="6" /></label>
        </div>
        <Alert msg={msg.err} /><Alert msg={msg.ok} type="success" />
        <button className="primary">Create</button>
      </form>
      <div className="card table-wrap">
        <table>
          <thead><tr><th>{role === 'student' ? 'SAP ID' : 'Username'}</th><th>Name</th>
            {role === 'student' && <><th>Dept</th><th>Category</th><th>Sem</th></>}<th></th></tr></thead>
          <tbody>{list.map((u) => (
            <tr key={u.id}>
              <td>{u.username}</td><td>{u.name}</td>
              {role === 'student' && <><td>{u.department.toUpperCase()}</td><td>{u.category}</td><td>{u.current_sem}</td></>}
              <td className="actions"><button onClick={() => edit(u)}>Edit</button><button className="danger" onClick={() => remove(u)}>Delete</button></td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </>
  )
}

function Results() {
  const [list, setList] = useState([])
  const load = () => api('/admin/results').then(setList)
  useEffect(() => { load() }, [])
  const toggle = async (r) => {
    await api(`/admin/results/${r.id}/publish`, { method: 'POST', body: { published: !r.published } })
    load()
  }
  return (
    <div className="card table-wrap">
      <table>
        <thead><tr><th>SAP ID</th><th>Name</th><th>Sem</th><th>SGPA</th><th>CGPA</th><th>Status</th><th>S3 PDF</th><th></th></tr></thead>
        <tbody>{list.map((r) => (
          <tr key={r.id}>
            <td>{r.sap_id}</td><td>{r.name}</td><td>{r.sem}</td><td>{fmt(r.sgpa)}</td><td>{fmt(r.cgpa)}</td>
            <td>{r.published ? <span className="badge ok">Published</span> : <span className="badge">Draft</span>}</td>
            <td className="muted small">{r.pdf_key || '-'}</td>
            <td><button onClick={() => toggle(r)}>{r.published ? 'Unpublish' : 'Publish'}</button></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  )
}

function Config() {
  const [cfg, setCfg] = useState(null)
  const [dept, setDept] = useState('csds')
  useEffect(() => { api('/admin/config').then(setCfg) }, [])
  if (!cfg) return null
  return (
    <div className="card">
      <p className="muted">Read-only. Subjects, credits and exam setup come from the calculation engine so results always match the reference logic.</p>
      <div className="toolbar">
        <select value={dept} onChange={(e) => setDept(e.target.value)}><option value="csds">CSDS</option><option value="ce">CE</option></select>
      </div>
      {Object.entries(cfg[dept]).map(([sem, c]) => (
        <details key={sem}>
          <summary>{sem.replace('sem', 'Semester ')} — {c.total_credits} credits, {c.exam_type[0]} TEE + {c.exam_type[1]} ICA-only</summary>
          <table>
            <thead><tr><th>Subject</th><th>Credits</th><th>Type</th></tr></thead>
            <tbody>{c.subjects.map((s, i) => (
              <tr key={i}><td>{s}</td><td>{c.credits[i] ?? '—'}</td><td>{i < c.exam_type[0] ? 'ICA + TEE' : 'ICA only'}</td></tr>
            ))}</tbody>
          </table>
        </details>
      ))}
    </div>
  )
}

function AuditLogs() {
  const [logs, setLogs] = useState([])
  useEffect(() => { api('/admin/audit-logs').then(setLogs) }, [])
  return (
    <div className="card table-wrap">
      <table>
        <thead><tr><th>Time (UTC)</th><th>User</th><th>Action</th></tr></thead>
        <tbody>{logs.map((l, i) => <tr key={i}><td>{l.time}</td><td>{l.username}</td><td>{l.action}</td></tr>)}</tbody>
      </table>
    </div>
  )
}
