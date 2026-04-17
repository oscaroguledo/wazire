import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  GraduationCap,
  BookOpen,
  FileText,
  TrendingUp,
  Calendar,
  Award,
  Users,
  Activity,
  AlertCircle,
} from 'lucide-react';
import Icon from '@/components/Icon';
import { useAuth } from '@/contexts/AuthContext';
import Button from '@/components/Button';
import Breadcrumbs from '@/components/Breadcrumbs';
import { EmptyState } from '@/components/EmptyState';
import DashboardSkeleton from './DashboardSkeleton';
import * as dashboardApi from '@/apis/dashboard';
import { errorTracker } from '@/utils/errorTracking';

interface AdminStats {
  totalUsers: number;
  studentUsers: number;
  lecturerUsers: number;
  adminUsers: number;
  totalCourses: number;
  totalExams: number;
  totalSubmissions: number;
  totalTenants: number;
  activeUsers: number;
  pendingApprovals: number;
}

interface StudentStats {
  enrolledCourses: number;
  upcomingExams: number;
  completedExams: number;
  missedExams: number;
  totalSubmissions: number;
  pendingGrades: number;
}

interface LecturerStats {
  totalCourses: number;
  totalExams: number;
  totalStudents: number;
  pendingSubmissions: number;
  gradedSubmissions: number;
  activeCourses: number;
}

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  delay?: number;
}

function StatCard({ label, value, sub, icon, iconBg, iconColor, delay = 0 }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.25 }}
      className="surface-card p-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-[var(--color-text-secondary)]">{label}</p>
          <p className="text-3xl font-bold text-[var(--color-text-primary)] mt-2">{value}</p>
          {sub && <p className="text-xs text-[var(--color-text-muted)] mt-1">{sub}</p>}
        </div>
        <div className={`${iconBg} p-3 rounded-xl flex-shrink-0`}>
          <Icon as={icon} size={24} className={iconColor} />
        </div>
      </div>
    </motion.div>
  );
}

export function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [studentStats, setStudentStats] = useState<StudentStats>({
    enrolledCourses: 0, upcomingExams: 0, completedExams: 0,
    missedExams: 0, totalSubmissions: 0, pendingGrades: 0,
  });

  const [lecturerStats, setLecturerStats] = useState<LecturerStats>({
    totalCourses: 0, totalExams: 0, totalStudents: 0,
    pendingSubmissions: 0, gradedSubmissions: 0, activeCourses: 0,
  });

  const [adminStats, setAdminStats] = useState<AdminStats>({
    totalUsers: 0, studentUsers: 0, lecturerUsers: 0, adminUsers: 0,
    totalCourses: 0, totalExams: 0, totalSubmissions: 0,
    totalTenants: 0, activeUsers: 0, pendingApprovals: 0,
  });

  const fetchData = async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      // Use the new unified dashboard API
      const dashboard = await dashboardApi.getMyDashboard();
      
      if (user.role === 'admin' && 'total_users' in dashboard) {
        // Admin dashboard
        const adminDash = dashboard as dashboardApi.AdminDashboard;
        setAdminStats({
          totalUsers: adminDash.total_users,
          studentUsers: adminDash.total_students,
          lecturerUsers: adminDash.total_lecturers,
          adminUsers: adminDash.total_users - adminDash.total_students - adminDash.total_lecturers,
          totalCourses: adminDash.total_courses,
          totalExams: adminDash.total_exams,
          totalSubmissions: adminDash.total_submissions,
          totalTenants: 0, // Not in current schema
          activeUsers: adminDash.total_users,
          pendingApprovals: 0, // Not in current schema
        });
      } else if (user.role === 'lecturer' && 'total_courses' in dashboard) {
        // Lecturer dashboard
        const lecturerDash = dashboard as dashboardApi.LecturerDashboard;
        setLecturerStats({
          totalCourses: lecturerDash.total_courses,
          totalExams: lecturerDash.total_exams,
          totalStudents: lecturerDash.total_students,
          pendingSubmissions: lecturerDash.pending_submissions,
          gradedSubmissions: lecturerDash.graded_submissions,
          activeCourses: lecturerDash.active_courses,
        });
      } else if (user.role === 'student' && 'total_courses' in dashboard) {
        // Student dashboard
        const studentDash = dashboard as dashboardApi.StudentDashboard;
        setStudentStats({
          enrolledCourses: studentDash.total_courses,
          upcomingExams: studentDash.upcoming_exams,
          completedExams: studentDash.total_graded_submissions,
          missedExams: studentDash.missed_exams,
          totalSubmissions: studentDash.total_submissions,
          pendingGrades: studentDash.total_pending_submissions,
        });
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        errorTracker.track(err, { action: 'fetch_dashboard', component: 'Dashboard' });
      }
      setError('Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!user) return;
    fetchData();
  }, [user?.id]); // Only re-fetch if user ID changes, not the entire user object

  if (loading) return <DashboardSkeleton />;

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Breadcrumbs />
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)] mt-3">
          Welcome back{user?.first_name ? `, ${user.first_name}` : ''}
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Here's your academic overview for today.
        </p>
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-6 p-4 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-xl flex items-center gap-3">
          <Icon as={AlertCircle} size={16} className="text-[var(--color-error-600)] flex-shrink-0" />
          <p className="text-sm text-[var(--color-error-600)] flex-1">{error}</p>
          <Button variant="ghost" onClick={fetchData} className="text-xs">Retry</Button>
        </div>
      )}

      {/* Student dashboard */}
      {user?.role === 'student' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <StatCard label="Enrolled Courses" value={studentStats.enrolledCourses} sub="Active courses" icon={BookOpen} iconBg="bg-[var(--color-primary-50)]" iconColor="text-[var(--color-primary-600)]" delay={0.05} />
            <StatCard label="Completed Exams" value={studentStats.completedExams} sub="Total taken" icon={FileText} iconBg="bg-[var(--color-success-100)]" iconColor="text-[var(--color-success-600)]" delay={0.1} />
            <StatCard label="Missed Exams" value={studentStats.missedExams} sub={studentStats.missedExams === 0 ? 'None missed' : 'Need attention'} icon={AlertCircle} iconBg="bg-[var(--color-error-100)]" iconColor="text-[var(--color-error-600)]" delay={0.15} />
            <StatCard label="Upcoming Exams" value={studentStats.upcomingExams} sub="Scheduled" icon={Calendar} iconBg="bg-[var(--color-premium-100)]" iconColor="text-[var(--color-premium-600)]" delay={0.2} />
            <StatCard label="Total Submissions" value={studentStats.totalSubmissions} sub="All time" icon={Activity} iconBg="bg-[var(--color-primary-50)]" iconColor="text-[var(--color-primary-600)]" delay={0.25} />
            <StatCard label="Pending Grades" value={studentStats.pendingGrades} sub={studentStats.pendingGrades === 0 ? 'All graded' : 'Awaiting review'} icon={TrendingUp} iconBg="bg-[var(--color-error-100)]" iconColor="text-[var(--color-error-600)]" delay={0.3} />
          </div>

          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }} className="surface-card p-6">
            <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-5">Quick Actions</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <Button className="justify-center" onClick={() => navigate('/courses')}>
                <Icon as={BookOpen} size={16} className="mr-2" /> Browse Courses
              </Button>
              <Button variant="secondary" className="justify-center" onClick={() => navigate('/exams')}>
                <Icon as={FileText} size={16} className="mr-2" /> View Exams
              </Button>
              <Button variant="secondary" className="justify-center" onClick={() => navigate('/submissions')}>
                <Icon as={Award} size={16} className="mr-2" /> My Submissions
              </Button>
            </div>
          </motion.div>

          {studentStats.enrolledCourses === 0 && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
              <EmptyState
                icon={GraduationCap}
                title="Ready to Start Learning!"
                description="You're not enrolled in any courses yet. Browse available courses to begin your journey."
                action={{ label: "Browse Courses", onClick: () => navigate('/courses') }}
              />
            </motion.div>
          )}
        </div>
      )}

      {/* Lecturer dashboard */}
      {user?.role === 'lecturer' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <StatCard label="Total Courses" value={lecturerStats.totalCourses} sub="Assigned to you" icon={BookOpen} iconBg="bg-[var(--color-primary-50)]" iconColor="text-[var(--color-primary-600)]" delay={0.05} />
            <StatCard label="Total Exams" value={lecturerStats.totalExams} sub="Exams created" icon={FileText} iconBg="bg-[var(--color-premium-100)]" iconColor="text-[var(--color-premium-600)]" delay={0.1} />
            <StatCard label="Total Students" value={lecturerStats.totalStudents} sub="Students enrolled" icon={Users} iconBg="bg-[var(--color-success-100)]" iconColor="text-[var(--color-success-600)]" delay={0.15} />
            <StatCard label="Pending Grading" value={lecturerStats.pendingSubmissions} sub="Awaiting review" icon={Calendar} iconBg="bg-[var(--color-warning-100)]" iconColor="text-[var(--color-warning-600)]" delay={0.2} />
            <StatCard label="Graded" value={lecturerStats.gradedSubmissions} sub="Completed" icon={Award} iconBg="bg-[var(--color-success-100)]" iconColor="text-[var(--color-success-600)]" delay={0.25} />
            <StatCard label="Active Courses" value={lecturerStats.activeCourses} sub="With recent activity" icon={Activity} iconBg="bg-[var(--color-primary-50)]" iconColor="text-[var(--color-primary-600)]" delay={0.3} />
          </div>

          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }} className="surface-card p-6">
            <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-5">Quick Actions</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <Button className="justify-center" onClick={() => navigate('/courses')}>
                <Icon as={BookOpen} size={16} className="mr-2" /> Manage Courses
              </Button>
              <Button variant="secondary" className="justify-center" onClick={() => navigate('/exams')}>
                <Icon as={FileText} size={16} className="mr-2" /> Create Exam
              </Button>
              <Button variant="secondary" className="justify-center" onClick={() => navigate('/submissions')}>
                <Icon as={Award} size={16} className="mr-2" /> Grade Submissions
              </Button>
            </div>
          </motion.div>

          {lecturerStats.totalCourses > 0 && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="surface-card p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-base font-semibold text-[var(--color-text-primary)]">Your Students</h2>
                <Button variant="ghost" onClick={() => navigate('/courses')} className="text-sm">
                  View All Courses
                </Button>
              </div>
              <p className="text-sm text-[var(--color-text-secondary)]">
                You have <span className="font-medium text-[var(--color-primary-600)]">{lecturerStats.totalStudents}</span> students enrolled across your courses. 
                Go to a specific course to manage enrollments and view detailed student information.
              </p>
            </motion.div>
          )}

          {lecturerStats.totalCourses === 0 && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="surface-card p-8 text-center">
              <div className="w-16 h-16 rounded-2xl bg-[var(--color-bg-hover)] flex items-center justify-center mx-auto mb-4">
                <Icon as={GraduationCap} size={28} className="text-[var(--color-text-muted)]" />
              </div>
              <h3 className="text-base font-semibold text-[var(--color-text-primary)] mb-2">No Courses Assigned</h3>
              <p className="text-sm text-[var(--color-text-secondary)] mb-5 max-w-sm mx-auto">
                You haven't been assigned to any courses yet. Contact your admin to get course assignments.
              </p>
              <Button onClick={() => navigate('/courses')}>View Courses</Button>
            </motion.div>
          )}
        </div>
      )}

      {/* Admin dashboard */}
      {user?.role === 'admin' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <StatCard label="Students" value={adminStats.studentUsers} sub="Enrolled students" icon={Users} iconBg="bg-[var(--color-primary-50)]" iconColor="text-[var(--color-primary-600)]" delay={0.05} />
            <StatCard label="Lecturers" value={adminStats.lecturerUsers} sub="Teaching staff" icon={BookOpen} iconBg="bg-[var(--color-premium-100)]" iconColor="text-[var(--color-premium-600)]" delay={0.1} />
            <StatCard label="Admins" value={adminStats.adminUsers} sub="System admins" icon={GraduationCap} iconBg="bg-[var(--color-success-100)]" iconColor="text-[var(--color-success-600)]" delay={0.15} />
            <StatCard label="Total Courses" value={adminStats.totalCourses} sub="All courses" icon={BookOpen} iconBg="bg-[var(--color-warning-100)]" iconColor="text-[var(--color-warning-600)]" delay={0.2} />
            <StatCard label="Total Exams" value={adminStats.totalExams} sub="All exams created" icon={FileText} iconBg="bg-[var(--color-primary-50)]" iconColor="text-[var(--color-primary-600)]" delay={0.25} />
            <StatCard label="Active Users" value={adminStats.activeUsers} sub="Currently active" icon={Activity} iconBg="bg-[var(--color-error-100)]" iconColor="text-[var(--color-error-600)]" delay={0.3} />
          </div>

          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }} className="surface-card p-6">
            <h2 className="text-base font-semibold text-[var(--color-text-primary)] mb-5">Admin Actions</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <Button className="justify-center" onClick={() => navigate('/courses')}>
                <Icon as={BookOpen} size={16} className="mr-2" /> Manage Courses
              </Button>
              <Button variant="secondary" className="justify-center" onClick={() => navigate('/users')}>
                <Icon as={Users} size={16} className="mr-2" /> Manage Users
              </Button>
              <Button variant="secondary" className="justify-center" onClick={() => navigate('/institutions')}>
                <Icon as={GraduationCap} size={16} className="mr-2" /> Manage Institutions
              </Button>
            </div>
          </motion.div>

          {adminStats.totalUsers === 0 && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="surface-card p-8 text-center">
              <div className="w-16 h-16 rounded-2xl bg-[var(--color-bg-hover)] flex items-center justify-center mx-auto mb-4">
                <Icon as={GraduationCap} size={28} className="text-[var(--color-text-muted)]" />
              </div>
              <h3 className="text-base font-semibold text-[var(--color-text-primary)] mb-2">Welcome to Admin Dashboard!</h3>
              <p className="text-sm text-[var(--color-text-secondary)] mb-5 max-w-sm mx-auto">
                The system is ready. Start by creating users and tenants to populate the platform.
              </p>
              <Button onClick={() => navigate('/users')}>Create First User</Button>
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
}
