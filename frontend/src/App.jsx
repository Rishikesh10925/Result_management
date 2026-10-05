import { useEffect, useState } from 'react'
import { api } from './api'
import Login from './pages/Login'
import Student from './pages/Student'
import Faculty from './pages/Faculty'
import Admin from './pages/Admin'

const MENUS = {
  student: ['Dashboard', 'Results', 'Goal Matrix', 'Target GPA', 'Profile'],
  faculty: ['Students', 'Enter Marks'],
  admin: ['Dashboard', 'Students', 'Faculty', 'Results', 'Academic Config', 'Audit Logs'],
}
const PAGES = { student: Student, faculty: Faculty, admin: Admin }

export default function App() {
  const [user, setUser] = useState(undefined)
  const [page, setPage] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)

  const enter = (u) => { setUser(u); if (u) setPage(MENUS[u.role][0]) }
  useEffect(() => { api('/auth/me').then(enter).catch(() => enter(null)) }, [])

  if (user === undefined) return <div className="center muted">Loading…</div>
  if (!user) return <Login onLogin={enter} />

  const Page = PAGES[user.role]
  const logout = () => api('/auth/logout', { method: 'POST' }).finally(() => setUser(null))
  const go = (p) => { setPage(p); setMenuOpen(false) }

  return (
    <div className="layout">
      <aside className={menuOpen ? 'open' : ''}>
        <div className="brand">☁ ResultCloud</div>
        <div className="role">{user.role} portal</div>
        {MENUS[user.role].map((p) => (
          <button key={p} className={p === page ? 'nav active' : 'nav'} onClick={() => go(p)}>{p}</button>
        ))}
        <button className="nav logout" onClick={logout}>Logout</button>
      </aside>
      <main>
        <header>
          <button className="menu-btn" onClick={() => setMenuOpen(!menuOpen)}>☰</button>
          <h1>{page}</h1>
          <span className="muted">{user.name}</span>
        </header>
        <Page page={page} user={user} go={go} />
      </main>
    </div>
  )
}
