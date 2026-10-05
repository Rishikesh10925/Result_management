import { useEffect, useState } from 'react'
import { api, fmt } from '../api'
import { Alert, ResultTable, SemSelect, Stat } from '../components'

export default function Student({ page, user, go }) {
  if (page === 'Results') return <Results />
  if (page === 'Goal Matrix') return <GoalMatrix user={user} />
  if (page === 'Target GPA') return <Planner user={user} />
  if (page === 'Profile') return <Profile user={user} />
  return <Dashboard user={user} go={go} />
}

function Dashboard({ user, go }) {
  const [results, setResults] = useState([])
  useEffect(() => { api('/student/results').then(setResults).catch(() => {}) }, [])
  const latest = results[results.length - 1]
  return (
    <>
      <h2>Welcome, {user.name}</h2>
      <div className="grid">
        <Stat label="SAP ID" value={user.sap_id} />
        <Stat label="Department" value={user.department.toUpperCase()} />
        <Stat label="Current Semester" value={user.current_sem} />
        <Stat label="Category" value={`${user.category} (${user.category === 'old' ? '4.0' : '10.0'} scale)`} />
        <Stat label="Latest SGPA" value={fmt(latest?.sgpa)} />
        <Stat label="Current CGPA" value={fmt(latest?.cgpa)} />
      </div>
      <div className="card">
        <h3>Semester Results</h3>
        {results.length === 0 ? <p className="muted">No published results yet.</p> : (
          <table>
            <thead><tr><th>Semester</th><th>SGPA</th><th>CGPA</th></tr></thead>
            <tbody>{results.map((r) => <tr key={r.sem}><td>Semester {r.sem}</td><td>{fmt(r.sgpa)}</td><td>{fmt(r.cgpa)}</td></tr>)}</tbody>
          </table>
        )}
        <div className="actions">
          <button onClick={() => go('Results')}>View results</button>
          <button onClick={() => go('Goal Matrix')}>Goal Matrix</button>
          <button onClick={() => go('Target GPA')}>Target GPA Planner</button>
        </div>
      </div>
    </>
  )
}

function Results() {
  const [list, setList] = useState([])
  const [sem, setSem] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/student/results').then((l) => { setList(l); if (l.length) setSem(l[l.length - 1].sem) })
  }, [])
  useEffect(() => {
    if (sem) api(`/student/results/${sem}`).then(setResult).catch((e) => setError(e.message))
  }, [sem])

  if (!list.length) return <div className="card muted">No published results yet.</div>
  return (
    <div className="card">
      <div className="toolbar">
        <select value={sem || ''} onChange={(e) => setSem(Number(e.target.value))}>
          {list.map((r) => <option key={r.sem} value={r.sem}>Semester {r.sem}</option>)}
        </select>
        <a className="button primary" href={`/api/student/results/${sem}/pdf`}>Download PDF</a>
      </div>
      <Alert msg={error} />
      {result && <ResultTable result={result} />}
    </div>
  )
}

function GoalMatrix({ user }) {
  const [sem, setSem] = useState(user.current_sem)
  const [layout, setLayout] = useState([])
  const [ica, setIca] = useState({})
  const [out, setOut] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => { setOut(null); api(`/student/layout/${sem}`).then(setLayout) }, [sem])
  const teeSubs = layout.filter((s) => s.has_tee)

  const run = async () => {
    setError('')
    try {
      const marks = teeSubs.map((s) => Number(ica[s.subject] ?? 0))
      setOut(await api('/student/goal-matrix', { method: 'POST', body: { sem, ica: marks } }))
    } catch (e) { setError(e.message) }
  }

  return (
    <div className="card">
      <p className="muted">Minimum TEE marks (out of 100) needed for each grade, based on your ICA marks. "-" means not reachable.</p>
      <div className="toolbar"><SemSelect value={sem} onChange={setSem} /></div>
      {teeSubs.length === 0 && <p className="muted">This semester has no TEE subjects.</p>}
      <div className="form-grid">
        {teeSubs.map((s) => (
          <label key={s.subject}>{s.subject}
            <input type="number" min="0" max="50" placeholder="ICA / 50" value={ica[s.subject] ?? ''}
              onChange={(e) => setIca({ ...ica, [s.subject]: e.target.value })} />
          </label>
        ))}
      </div>
      <Alert msg={error} />
      {teeSubs.length > 0 && <button className="primary" onClick={run}>Generate Goal Matrix</button>}
      {out && (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Subject</th>{out.grades.map((g) => <th key={g}>{g}</th>)}</tr></thead>
            <tbody>{out.matrix.map((row, i) => (
              <tr key={i}><td>{out.subjects[i]}</td>{row.map((v, j) => <td key={j}>{v}</td>)}</tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function Planner({ user }) {
  const max = user.category === 'old' ? 4 : 10
  const [sem, setSem] = useState(user.current_sem)
  const [layout, setLayout] = useState([])
  const [levels, setLevels] = useState({})
  const [target, setTarget] = useState(user.category === 'old' ? 3.5 : 7)
  const [plans, setPlans] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { setPlans(null); api(`/student/layout/${sem}`).then(setLayout) }, [sem])

  const run = async () => {
    setError('')
    setBusy(true)
    try {
      const body = { sem, target: Number(target), levels: layout.map((s) => levels[s.subject] || 'easy') }
      setPlans(await api('/student/planner', { method: 'POST', body }))
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="card">
      <p className="muted">Rate each subject. Four random study plans are generated; they are not guaranteed to reach the target (Beta, same as the original tool).</p>
      <div className="toolbar">
        <SemSelect value={sem} onChange={setSem} />
        <label className="inline">Target GPA
          <input type="number" min="0" max={max} step="0.1" value={target} onChange={(e) => setTarget(e.target.value)} />
        </label>
      </div>
      <div className="form-grid">
        {layout.map((s) => (
          <label key={s.subject}>{s.subject}
            <select value={levels[s.subject] || 'easy'} onChange={(e) => setLevels({ ...levels, [s.subject]: e.target.value })}>
              <option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option>
            </select>
          </label>
        ))}
      </div>
      <Alert msg={error} />
      <button className="primary" onClick={run} disabled={busy}>{busy ? 'Generating…' : 'Generate Study Plans'}</button>
      <div className="plans">
        {plans?.map((p, i) => (
          <div key={i} className="card plan">
            <h3>Plan {i + 1} <span className={p.meets_target ? 'badge ok' : 'badge'}>GPA {p.gpa}</span></h3>
            <table>
              <thead><tr><th>Subject</th><th>ICA</th><th>TEE</th></tr></thead>
              <tbody>{p.plan.map((r) => <tr key={r.subject}><td>{r.subject}</td><td>{r.ICA}</td><td>{r.TEE}</td></tr>)}</tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  )
}

function Profile({ user }) {
  return (
    <div className="card">
      <table><tbody>
        <tr><th>Name</th><td>{user.name}</td></tr>
        <tr><th>SAP ID</th><td>{user.sap_id}</td></tr>
        <tr><th>Department</th><td>{user.department.toUpperCase()}</td></tr>
        <tr><th>Category</th><td>{user.category}</td></tr>
        <tr><th>Current Semester</th><td>{user.current_sem}</td></tr>
      </tbody></table>
    </div>
  )
}
