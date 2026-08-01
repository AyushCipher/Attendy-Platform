import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { AdminLayout } from './components/layout/AdminLayout'
import { LoginPage } from './routes/login/LoginPage'
import { DashboardPage } from './routes/admin/dashboard/DashboardPage'
import { AttendancePage } from './routes/admin/attendance/AttendancePage'
import { StudentsPage } from './routes/admin/students/StudentsPage'
import { ScanPage } from './routes/admin/scan/ScanPage'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin/dashboard" element={<DashboardPage />} />
          <Route path="/admin/attendance" element={<AttendancePage />} />
          <Route path="/admin/students" element={<StudentsPage />} />
          <Route path="/admin/scan" element={<ScanPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
