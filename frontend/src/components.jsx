import { fmt } from './api'

export function ResultTable({ result }) {
  return (
    <>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>S.No.</th><th>Subject</th><th>Credits</th><th>Final Marks</th><th>Grade</th><th>Grade Point</th><th>Total</th></tr>
          </thead>
          <tbody>
            {result.rows.map((r, i) => (
              <tr key={i}>
                <td>{i + 1}</td><td>{r.subject}</td><td>{r.credits}</td><td>{r.final_marks}</td>
                <td><b>{r.grade}</b></td><td>{r.grade_point}</td><td>{r.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="gpa-row">
        <span>Semester GPA: <b>{fmt(result.sgpa)}</b></span>
        <span>CGPA: <b>{fmt(result.cgpa)}</b></span>
      </div>
    </>
  )
}

export function Stat({ label, value }) {
  return <div className="card stat"><div className="muted">{label}</div><div className="value">{value}</div></div>
}

export function Alert({ msg, type = 'error' }) {
  return msg ? <div className={`alert ${type}`}>{msg}</div> : null
}

export function SemSelect({ value, onChange }) {
  return (
    <select value={value} onChange={(e) => onChange(Number(e.target.value))}>
      {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => <option key={s} value={s}>Semester {s}</option>)}
    </select>
  )
}
