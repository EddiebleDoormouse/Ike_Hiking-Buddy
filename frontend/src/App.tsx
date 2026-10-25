import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import HikeFolder from './pages/HikeFolder'
import HikesGallery from './pages/HikesGallery'
import NewHike from './pages/NewHike'
import Search from './pages/Search'

function App() {
  return (
    <BrowserRouter>
      <div className="app-frame">
        <header className="topbar">
          <Link className="brand" to="/">
            <span className="brand-mark" aria-hidden="true">⌁</span>
            <span>Hiking Buddy</span>
          </Link>
          <nav className="topnav" aria-label="Main navigation">
            <NavLink to="/search" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Search
            </NavLink>
            <Link className="button button-small" to="/new">Plan a hike <span aria-hidden="true">↗</span></Link>
          </nav>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<HikesGallery />} />
            <Route path="/hikes/:id" element={<HikeFolder />} />
            <Route path="/new" element={<NewHike />} />
            <Route path="/search" element={<Search />} />
            <Route path="*" element={<HikesGallery />} />
          </Routes>
        </main>
        <footer className="site-footer">A quieter place for days outside <span>·</span> Plans are suggestions, not a substitute for local judgement.</footer>
      </div>
    </BrowserRouter>
  )
}

export default App
