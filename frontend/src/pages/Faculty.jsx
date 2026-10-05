import { useEffect, useState } from 'react'
import { api } from '../api'
import { Alert, ResultTable, SemSelect } from '../components'

export default function Faculty({ page, go }) {
  const [student, setStudent] = useState(null)
  const pick = (s) => { setStudent(s); go('Enter Marks') }
  if (page === 'Enter Marks') return <EnterMarks student={student} setStudent={setStudent} />
  return <Students onPick={pick} />
}

export function Students({ onPick }) {
  const [list, setList] = useState([])
  const [search, setSearch] = useState('')
  const [dept, setDept] = useState('')

  useEffect(() => {
    const t = setTimeout(() => {
      api(`/faculty/students?search=${encodeURIComponent(search)}&department=${dept}`).then(setList)
    }, 250)
    return () => clearTimeout(t)
  }, [search, dept])

  return (
    <div className="card">
      <div className="toolbar">
        <input placeholder="Search name or SAP ID" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select value={dept} onChange={(e) => setDept(e.target.value)}>
          <option value="">All departments</option><option value="csds">CSDS</option><option value="ce">CE</option>
        </select>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>SAP ID</th><th>Name</th><th>Dept</th><th>Category</th><th>Sem</th><th></th></tr></thead>
          <tbody>{list.map((s) => (
            <tr key={s.id}>
              <td>{s.sap_id}</td><td>{s.name}</td><td>{s.department.toUpperCase()}</td><td>{s.category}</td>
              <td>{s.current_sem}</td><td><button onClick={() => onPick(s)}>Enter marks</button></td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  )
}

export function EnterMarks({ student, setStudent }) {
  const [students, setStudents] = useState([])
  const [sem, setSem] = useState(student?.current_sem || 1)
  const [layout, setLayout] = useState([])
  const [ica, setIca] = useState([])
  const [tee, setTee] = useState([])
  const [result, setResult] = useState(null)
  const [published, setPublished] = useState(false)
  const [msg, setMsg] = useState({})
  const [busy, setBusy] = useState(false)

  useEffect(() => { api('/faculty/students').then(setStudents) }, [])
  useEffect(() => {
    if (!student) return
    setMsg({})
    api(`/faculty/marks/${student.student_id}/${sem}`).then((d) => {
      setLayout(d.layout)
      setResult(d.result)
      setPublished(d.published)
      setIca(d.result?.ica || d.layout.map(() => ''))
      setTee(d.result?.tee || d.layout.filter((s) => s.has_tee).map(() => ''))
    })
  }, [student, sem])

  const save = async () => {
    setBusy(true)
    setMsg({})
    try {
      const body = { ica: ica.map(Number), tee: tee.map(Number) }
      setResult(await api(`/faculty/marks/${student.student_id}/${sem}`, { method: 'POST', body }))
      setMsg({ ok: 'Marks saved and result calculated.' })
    } catch (e) { setMsg({ err: e.message }) } finally { setBusy(false) }
  }

  const togglePublish = async () => {
    try {
      const r = await api(`/faculty/results/${student.student_id}/${sem}/publish`, { method: 'POST', body: { published: !published } })
      setPublished(r.published)
      setMsg({ ok: r.published ? 'Result published to the student.' : 'Result unpublished.' })
    } catch (e) { setMsg({ err: e.message }) }
  }

  const set = (arr, setArr, i, v) => setArr(arr.map((x, j) => (j === i ? v : x)))

  return (
    <div className="card">
      <div className="toolbar">
        <select value={student?.student_id || ''} onChange={(e) => setStudent(students.find((s) => s.student_id === Number(e.target.value)))}>
          <option value="">Select student…</option>
          {students.map((s) => <option key={s.student_id} value={s.student_id}>{s.sap_id} – {s.name} ({s.department.toUpperCase()})</option>)}
        </select>
        <SemSelect value={sem} onChange={setSem} />
      </div>

      {student && (
        <>
          <p className="muted">ICA out of 50 for every subject. TEE out of 100 only for subjects with a term-end exam.</p>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Subject</th><th>Type</th><th>ICA / 50</th><th>TEE / 100</th></tr></thead>
              <tbody>{layout.map((s, i) => (
                <tr key={s.subject}>
                  <td>{s.subject}</td>
                  <td><span className="badge">{s.has_tee ? 'ICA + TEE' : 'ICA only'}</span></td>
                  <td><input type="number" min="0" max="50" value={ica[i] ?? ''} onChange={(e) => set(ica, setIca, i, e.target.value)} /></td>
                  <td>{s.has_tee ? <input type="number" min="0" max="100" value={tee[i] ?? ''} onChange={(e) => set(tee, setTee, i, e.target.value)} /> : '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          <Alert msg={msg.err} />
          <Alert msg={msg.ok} type="success" />
          <div className="actions">
            <button className="primary" onClick={save} disabled={busy}>{busy ? 'Calculating…' : 'Save & Calculate'}</button>
            {result && <button onClick={togglePublish}>{published ? 'Unpublish' : 'Publish result'}</button>}
          </div>
          {result && <><h3>Result {published ? <span className="badge ok">Published</span> : <span className="badge">Draft</span>}</h3><ResultTable result={result} /></>}
        </>
      )}
    </div>
  )
}
