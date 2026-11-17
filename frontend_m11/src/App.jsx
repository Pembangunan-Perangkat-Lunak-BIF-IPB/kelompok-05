
import { useEffect, useRef, useState } from 'react'
import {
  Routes,
  Route,
  Navigate,
  useLocation,
} from 'react-router-dom'

import Landing from './pages/Landing'
import Layout from './layouts/Layout'
import Placeholder from './pages/Placeholder'
import Guide from './pages/Guide'
import NewAnalysis from './pages/NewAnalysis'
import Progress from './pages/Progress'
import Result from './pages/Result'
import History from './pages/History'
import Login from './pages/Login'
import Register from './pages/Register'

import PublicFiles from './pages/PublicFiles'
import PublicResults from './pages/PublicResults'
import PublicResult from './pages/PublicResult'

import RequireAuth from './layouts/RequireAuth'
import Accounts from './pages/admin/Accounts'
import HealthCheck from './pages/admin/HealthCheck'
import AdminHistory from './pages/admin/AdminHistory'

import './pageTransition.css'

// Hanya halaman Landing dan Auth yang dianimasikan.
const AUTH_ROUTES = new Set([
  '/',
  '/login',
  '/register',
  '/public/login',
  '/admin/login',
])

function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia?.(
      '(prefers-reduced-motion: reduce)'
    ).matches
  )
}

export default function App() {
  const location = useLocation()

  const [displayLocation, setDisplayLocation] =
    useState(location)

  const [phase, setPhase] = useState('idle')
  const currentLocation = useRef(location)

  useEffect(() => {
    const from = currentLocation.current.pathname
    const to = location.pathname

    const animate =
      AUTH_ROUTES.has(from) &&
      AUTH_ROUTES.has(to) &&
      from !== to &&
      !prefersReducedMotion()

    if (!animate) {
      currentLocation.current = location
      setDisplayLocation(location)

      setPhase(
        AUTH_ROUTES.has(to) &&
          !prefersReducedMotion() &&
          from !== to
          ? 'enter'
          : 'idle'
      )

      return
    }

    setPhase('exit')

    const timer = window.setTimeout(() => {
      currentLocation.current = location
      setDisplayLocation(location)
      setPhase('enter')
    }, 160)

    return () => window.clearTimeout(timer)
  }, [location])

  const routes = (
    <Routes location={displayLocation}>

      {/* ================================== */}
      {/* LANDING PAGE */}
      {/* ================================== */}

      <Route
        path="/"
        element={<Landing />}
      />

      {/* ================================== */}
      {/* AUTHENTICATION */}
      {/* ================================== */}

      <Route
        path="/login"
        element={<Login />}
      />

      <Route
        path="/register"
        element={<Register />}
      />

      <Route
        path="/public/login"
        element={<Login role="reader" />}
      />

      <Route
        path="/admin/login"
        element={<Login role="admin" />}
      />

      {/* ================================== */}
      {/* PENELITI - RESEARCHER */}
      {/* ================================== */}

      <Route
        element={
          <RequireAuth
            role="RESEARCHER"
            to="/login"
          />
        }
      >
        <Route
          element={<Layout variant="researcher" />}
        >
          <Route
            path="/guide"
            element={<Guide />}
          />

          <Route
            path="/analysis/new"
            element={<NewAnalysis />}
          />

          <Route
            path="/analysis/:runId/progress"
            element={<Progress />}
          />

          <Route
            path="/analysis/:runId/result"
            element={<Result />}
          />

          <Route
            path="/history"
            element={<History />}
          />
        </Route>
      </Route>

      {/* ================================== */}
      {/* PEMBACA PUBLIK / GUEST */}
      {/* ================================== */}

      <Route
        element={<Layout variant="reader" />}
      >

        {/* Menu Berkas Publik */}
        <Route
          path="/public"
          element={<PublicFiles />}
        />

        {/* Menu Hasil: daftar seluruh hasil PUBLIC */}
        <Route
          path="/public/results"
          element={<PublicResults />}
        />

        {/* Detail hasil setelah memilih Run ID */}
        <Route
          path="/public/:runId/result"
          element={<PublicResult />}
        />

        {/* Redirect URL lama */}
        <Route
          path="/public/result"
          element={
            <Navigate
              to="/public/results"
              replace
            />
          }
        />

        <Route
          path="/public/history"
          element={
            <Navigate
              to="/public"
              replace
            />
          }
        />

      </Route>

      {/* ================================== */}
      {/* ADMINISTRATOR */}
      {/* ================================== */}

      <Route
        element={
          <RequireAuth
            role="ADMIN"
            to="/admin/login"
          />
        }
      >
        <Route
          element={<Layout variant="admin" />}
        >
          <Route
            path="/admin/accounts"
            element={<Accounts />}
          />

          <Route
            path="/admin/health"
            element={<HealthCheck />}
          />

          <Route
            path="/admin/history"
            element={<AdminHistory />}
          />
        </Route>
      </Route>

      {/* ================================== */}
      {/* KOMPATIBILITAS URL LAMA */}
      {/* ================================== */}

      <Route
        path="/results"
        element={
          <Navigate
            to="/public/results"
            replace
          />
        }
      />

      {/* ================================== */}
      {/* 404 */}
      {/* ================================== */}

      <Route
        path="*"
        element={
          <Placeholder
            title="Halaman tidak ditemukan"
          />
        }
      />

    </Routes>
  )

  const isAuthPage =
    AUTH_ROUTES.has(displayLocation.pathname)

  // Dashboard tidak menggunakan animasi Landing/Auth.
  if (!isAuthPage) {
    return routes
  }

  return (
    <div
      key={displayLocation.key}
      className={`ve-public-transition ${
        phase === 'exit'
          ? 'is-exiting'
          : phase === 'enter'
            ? 'is-entering'
            : ''
      }`}
    >
      {routes}
    </div>
  )
}
