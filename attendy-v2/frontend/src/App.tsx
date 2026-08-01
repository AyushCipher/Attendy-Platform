import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { AdminLayout } from './components/layout/AdminLayout'
import { LoginPage } from './routes/login/LoginPage'
import { DashboardPage } from './routes/admin/dashboard/DashboardPage'
import { AttendancePage } from './routes/admin/attendance/AttendancePage'
import { StudentsPage } from './routes/admin/students/StudentsPage'
import { ScanModePicker } from './routes/admin/scan/ScanModePicker'
import { AttendanceScanPage } from './routes/admin/scan/AttendanceScanPage'
import { MessScanPage } from './routes/admin/scan/MessScanPage'
import { LibraryScanPage } from './routes/admin/scan/LibraryScanPage'
import { MealsPage } from './routes/admin/meals/MealsPage'
import { LibraryPage } from './routes/admin/library/LibraryPage'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin/dashboard" element={<DashboardPage />} />
          <Route path="/admin/attendance" element={<AttendancePage />} />
          <Route path="/admin/meals" element={<MealsPage />} />
          <Route path="/admin/library" element={<LibraryPage />} />
          <Route path="/admin/students" element={<StudentsPage />} />
          <Route path="/admin/scan" element={<ScanModePicker />} />
          <Route path="/admin/scan/attendance" element={<AttendanceScanPage />} />
          <Route path="/admin/scan/mess" element={<MessScanPage />} />
          <Route path="/admin/scan/library" element={<LibraryScanPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
