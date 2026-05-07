import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { config } from './config';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
// Role-specific register pages use the main Register component with role props
import { Dashboard } from './pages/Dashboard';
import { Courses } from './pages/Courses';
import { CourseDetail } from './pages/CourseDetail';
import { EditCourse } from './pages/EditCourse';
import { EditExam } from './pages/EditExam';
import { Exams } from './pages/Exams';
import { ExamDetail } from './pages/ExamDetail';
import ExamQuestions from './pages/ExamQuestions';
import { TakeExam } from './pages/TakeExam';
import { Submissions } from './pages/Submissions';
import { AccessDenied } from './pages/AccessDenied';
import { UserManagement } from './pages/UserManagement';
import ProfilePage from './pages/Profile';
import TenantsPage from './pages/Tenants';
import CreateTenantPage from './pages/tenants/CreateTenant';
import EditTenantPage from './pages/tenants/EditTenant';
import BillingPage from './pages/Billing';
import { runAllApiTests } from './apis/test-apis';

// Create QueryClient instance with optimized staleTimes per data type
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: config.QUERY_CACHE_DEFAULT, // Default: 30 seconds for most data
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function AppRoutes() {
  const { isAuthenticated, user, authLoading } = useAuth();

  // Make testApis available in browser console
  useEffect(() => {
    (window as any).testApis = runAllApiTests;
  }, []);
  
  // While auth is resolving, show nothing (avoids flash redirects)
  if (authLoading) return null;
  
  // Role-based route components
  function PrivateRoute({ children }: { children: React.ReactNode }) {
    return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
  }

  function StudentRoute({ children }: { children: React.ReactNode }) {
    if (!isAuthenticated) return <Navigate to="/login" />;
    if (user?.role !== 'student') return <AccessDenied />;
    return <>{children}</>;
  }

  function AdminRoute({ children }: { children: React.ReactNode }) {
    if (!isAuthenticated) return <Navigate to="/login" />;
    if (user?.role !== 'admin') return <AccessDenied />;
    if (!user?.tenant_id) return <Navigate to="/institutions/create" replace />;
    return <>{children}</>;
  }

  function LecturerOrAdminRoute({ children }: { children: React.ReactNode }) {
    if (!isAuthenticated) return <Navigate to="/login" />;
    if (user?.role !== 'lecturer' && user?.role !== 'admin') return <AccessDenied />;
    return <>{children}</>;
  }
  
  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/dashboard" /> : <Login />} />
      
      <Route
        path="/register"
        element={isAuthenticated ? <Navigate to="/dashboard" /> : <Register />} />
      <Route path="/register/student" element={isAuthenticated ? <Navigate to="/dashboard" /> : <Register defaultRole="student" hideRoleSelector />} />
      <Route path="/register/lecturer" element={isAuthenticated ? <Navigate to="/dashboard" /> : <Register defaultRole="lecturer" hideRoleSelector />} />
      <Route path="/register/admin" element={isAuthenticated ? <Navigate to="/dashboard" /> : <Register defaultRole="admin" hideRoleSelector />} />
      <Route path="/register/superadmin" element={isAuthenticated ? <Navigate to="/dashboard" /> : <Register defaultRole="superadmin" hideRoleSelector />} />
      
      {/* Standalone tenant creation page - no Layout wrapper */}
      <Route
        path="/institutions/create"
        element={
          isAuthenticated && user?.role === 'admin' ? <CreateTenantPage /> : <Navigate to="/login" />
        } />
      
      <Route
        path="/access-denied"
        element={<AccessDenied />} />
      
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }>
        
        <Route index element={<Navigate to="/dashboard" />} />
        <Route path="dashboard" element={
          // Admin without tenant gets redirected to setup
          user?.role === 'admin' && !user?.tenant_id
            ? <Navigate to="/institutions/create" replace />
            : <Dashboard key={user?.id} />
        } />
        
        {/* All authenticated users can view courses and exams (with role-appropriate actions) */}
        <Route path="courses" element={<Courses />} />
        <Route path="courses/:id" element={<CourseDetail />} />
        <Route path="courses/:id/edit" element={
          <LecturerOrAdminRoute>
            <EditCourse />
          </LecturerOrAdminRoute>
        } />
        <Route path="courses/:id/exams/create" element={
          <LecturerOrAdminRoute>
            <EditExam />
          </LecturerOrAdminRoute>
        } />
        <Route path="exams" element={<Exams />} />
        <Route path="exams/:id/edit" element={
          <LecturerOrAdminRoute>
            <EditExam />
          </LecturerOrAdminRoute>
        } />
        <Route path="exams/:id" element={<ExamDetail />} />
        <Route path="exams/:examId/questions" element={<ExamQuestions />} />
        
        {/* Student-only routes */}
        <Route path="exams/:id/take" element={
          <StudentRoute>
            <TakeExam />
          </StudentRoute>
        } />
        <Route path="exams/:id/active" element={
          <StudentRoute>
            <TakeExam />
          </StudentRoute>
        } />
        
        {/* Admin-only routes */}
        <Route path="users" element={
          <AdminRoute>
            <UserManagement />
          </AdminRoute>
        } />
        <Route path="institutions" element={
          <AdminRoute>
            <TenantsPage />
          </AdminRoute>
        } />
        <Route path="institutions/:id/edit" element={
          <AdminRoute>
            <EditTenantPage />
          </AdminRoute>
        } />
        
        <Route path="submissions" element={<Submissions />} />
        
        {/* All authenticated users can view their profile */}
        <Route path="profile" element={<ProfilePage />} />
        
        {/* Billing - Admin only */}
        <Route path="billing" element={
          <AdminRoute>
            <BillingPage />
          </AdminRoute>
        } />
      </Route>
    </Routes>);
}

export function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </QueryClientProvider>
      </ErrorBoundary>
    </BrowserRouter>);
}