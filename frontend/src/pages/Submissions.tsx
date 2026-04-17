import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FileText, TrendingUp, Award, Calendar, Filter, ChevronDown, AlertCircle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import Icon from '@/components/Icon'
import { useAuth } from '@/contexts/AuthContext'
import * as submissionApi from '@/apis/submission'
import Pagination from '@/components/Pagination'
import SearchInput from '@/components/SearchInput'
import Dropdown from '@/components/Dropdown'
import Button from '@/components/Button'
import { StatusBadge } from '@/components/StatusBadge'
import Breadcrumbs from '@/components/Breadcrumbs'
import SubmissionsSkeleton from './SubmissionsSkeleton'
import { EmptyState } from '@/components/EmptyState'
import Table from '@/components/Table'
import { config } from '@/config';

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  delay?: number;
}

function StatCard({ label, value, icon, iconBg, iconColor, delay = 0 }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="surface-card p-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-[var(--color-text-secondary)]">{label}</p>
          <p className="text-3xl font-bold text-[var(--color-text-primary)] mt-2">{value}</p>
        </div>
        <div className={`${iconBg} p-3 rounded-xl flex-shrink-0`}>
          <Icon as={icon} size={28} className={iconColor} />
        </div>
      </div>
    </motion.div>
  );
}

function scoreColor(score: number) {
  if (score >= 80) return 'text-[var(--color-success-600)]';
  if (score >= 60) return 'text-[var(--color-primary-600)]';
  if (score >= 40) return 'text-[var(--color-warning-600)]';
  return 'text-[var(--color-error-600)]';
}

export function Submissions() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['submissions', currentPage, pageSize, user?.role, user?.id],
    queryFn: async () => {
      if (user?.role === 'student') {
        const response = await submissionApi.getAllMySubmissions()
        const items = Array.isArray(response) ? response : (response as any).items || []
        return {
          items,
          pagination: { page: 1, per_page: items.length, total: items.length, pages: 1, has_next: false, has_prev: false },
        }
      }
      // lecturer or admin — use the /lecturer endpoint via listSubmissions
      const result = await submissionApi.listSubmissions({
        page: currentPage,
        per_page: pageSize,
        lecturer_id: user?.id, // triggers /lecturer endpoint in the API client
      })
      // Normalize fields from backend to_dict() to match frontend expectations
      const items = (result.items || []).map((s: any) => ({
        ...s,
        score: s.score ?? s.latest_score,
        max_score: s.max_score ?? 100, // Default if not provided by backend
        submitted_at: s.submitted_at ?? s.created_at, // Use created_at if submitted_at not available
        status: s.status || (s.graded_at ? 'graded' : s.attempts_count > 0 ? 'submitted' : 'pending'),
      }))
      return { items, pagination: result.pagination }
    },
    enabled: !!user,
    staleTime: config.QUERY_CACHE_DYNAMIC, // 30 seconds - submissions change more frequently
  })

  const submissions = data?.items || [];
  const pagination = data?.pagination || { page: 1, per_page: pageSize, total: 0, pages: 0, has_next: false, has_prev: false };

  const avgScore = submissions.length > 0
    ? (submissions.reduce((a, s) => a + (s.score || 0), 0) / (submissions.filter((s) => s.score).length || 1)).toFixed(1)
    : '0';

  const renderTable = (cols: string[], rows: React.ReactNode) => (
    <div className="surface-card overflow-hidden">
      <div className="hidden lg:block">
        <Table>
          <thead className="bg-[var(--color-bg-hover)] border-b border-[var(--color-border-light)]">
            <tr>
              {cols.map((c) => (
                <th key={c} className="px-6 py-4 text-left text-sm font-semibold text-[var(--color-text-primary)]">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border-light)]">{rows}</tbody>
        </Table>
      </div>
    </div>
  );

  const renderStudentView = () => (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
        <StatCard label="Total Submissions" value={pagination.total} icon={FileText} iconBg="bg-[var(--color-primary-50)]" iconColor="text-[var(--color-primary-600)]" delay={0} />
        <StatCard label="Average Score" value={avgScore} icon={TrendingUp} iconBg="bg-[var(--color-primary-50)]" iconColor="text-[var(--color-primary-600)]" delay={0.05} />
        <StatCard label="Passed Exams" value={submissions.filter((s) => s.score && s.score >= 60).length} icon={Award} iconBg="bg-[var(--color-success-100)]" iconColor="text-[var(--color-success-600)]" delay={0.1} />
        <StatCard label="Pending" value={submissions.filter((s) => s.status === 'pending' || s.status === 'submitted').length} icon={Calendar} iconBg="bg-[var(--color-warning-100)]" iconColor="text-[var(--color-warning-600)]" delay={0.15} />
      </div>

      {renderTable(
        ['Exam', 'Submitted', 'Score', 'Status', 'Action'],
        submissions.map((s, idx) => (
          <motion.tr
            key={s.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.04 }}
            className="hover:bg-[var(--color-bg-hover)] transition-colors"
          >
            <td className="px-6 py-4">
              <div className="flex items-center gap-3">
                <div className="bg-[var(--color-primary-50)] p-2 rounded-lg flex-shrink-0">
                  <Icon as={FileText} size={18} className="text-[var(--color-primary-600)]" />
                </div>
                <div>
                  <p className="font-medium text-[var(--color-text-primary)]">{s.exam_title || 'N/A'}</p>
                  <p className="text-xs text-[var(--color-text-muted)]">{s.max_marks} marks</p>
                </div>
              </div>
            </td>
            <td className="px-6 py-4 text-sm text-[var(--color-text-secondary)]">
              {s.submitted_at ? new Date(s.submitted_at).toLocaleDateString() : 'Not submitted'}
            </td>
            <td className="px-6 py-4">
              {s.score !== undefined ? (
                <span className={`font-medium ${scoreColor(s.score)}`}>
                  {s.score}/{s.max_score}
                  <span className="text-xs text-[var(--color-text-muted)] ml-1">
                    ({((s.score / s.max_score) * 100).toFixed(0)}%)
                  </span>
                </span>
              ) : (
                <span className="text-[var(--color-text-muted)] text-sm">Not graded</span>
              )}
            </td>
            <td className="px-6 py-4"><StatusBadge status={s.status} /></td>
            <td className="px-6 py-4">
              <Button variant="secondary" className="px-3 py-1.5 text-xs">View Details</Button>
            </td>
          </motion.tr>
        ))
      )}

      {/* Mobile cards */}
      <div className="lg:hidden space-y-3 mt-4">
        {submissions.map((s, idx) => (
          <motion.div key={s.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.04 }}>
            <Card className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="bg-[var(--color-primary-50)] p-2 rounded-lg">
                    <Icon as={FileText} size={18} className="text-[var(--color-primary-600)]" />
                  </div>
                  <div>
                    <p className="font-medium text-[var(--color-text-primary)]">{s.exam_title || 'N/A'}</p>
                    <p className="text-xs text-[var(--color-text-muted)]">{s.max_marks} marks</p>
                  </div>
                </div>
                <StatusBadge status={s.status} />
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-[var(--color-text-secondary)]">
                  {s.submitted_at ? new Date(s.submitted_at).toLocaleDateString() : 'Not submitted'}
                </span>
                {s.score !== undefined && (
                  <span className={`font-medium ${scoreColor(s.score)}`}>{s.score}/{s.max_score}</span>
                )}
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </>
  );

  const renderLecturerView = () => (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
        <StatCard label="Total Submissions" value={pagination.total} icon={FileText} iconBg="bg-[var(--color-primary-50)]" iconColor="text-[var(--color-primary-600)]" delay={0} />
        <StatCard label="To Grade" value={submissions.filter((s) => s.status === 'submitted').length} icon={Calendar} iconBg="bg-[var(--color-warning-100)]" iconColor="text-[var(--color-warning-600)]" delay={0.05} />
        <StatCard label="Average Score" value={avgScore} icon={TrendingUp} iconBg="bg-[var(--color-primary-50)]" iconColor="text-[var(--color-primary-600)]" delay={0.1} />
        <StatCard
          label="Pass Rate"
          value={`${submissions.filter((s) => s.score).length > 0
            ? ((submissions.filter((s) => s.score && s.score >= 60).length / submissions.filter((s) => s.score).length) * 100).toFixed(0)
            : 0}%`}
          icon={Award}
          iconBg="bg-[var(--color-success-100)]"
          iconColor="text-[var(--color-success-600)]"
          delay={0.15}
        />
      </div>

      {renderTable(
        ['Student', 'Exam', 'Submitted', 'Score', 'Status', 'Action'],
        submissions.map((s, idx) => (
          <motion.tr
            key={s.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.04 }}
            className="hover:bg-[var(--color-bg-hover)] transition-colors"
          >
            <td className="px-6 py-4">
              <p className="font-medium text-[var(--color-text-primary)]">{s.student_name || 'N/A'}</p>
            </td>
            <td className="px-6 py-4">
              <div className="flex items-center gap-3">
                <div className="bg-[var(--color-primary-50)] p-2 rounded-lg flex-shrink-0">
                  <Icon as={FileText} size={18} className="text-[var(--color-primary-600)]" />
                </div>
                <div>
                  <p className="font-medium text-[var(--color-text-primary)]">{s.exam_title || 'N/A'}</p>
                  <p className="text-xs text-[var(--color-text-muted)]">{s.max_marks} marks</p>
                </div>
              </div>
            </td>
            <td className="px-6 py-4 text-sm text-[var(--color-text-secondary)]">
              {s.submitted_at ? new Date(s.submitted_at).toLocaleDateString() : 'Not submitted'}
            </td>
            <td className="px-6 py-4">
              {s.score !== undefined ? (
                <span className={`font-medium ${scoreColor(s.score)}`}>
                  {s.score}/{s.max_score}
                  <span className="text-xs text-[var(--color-text-muted)] ml-1">
                    ({((s.score / s.max_score) * 100).toFixed(0)}%)
                  </span>
                </span>
              ) : (
                <span className="text-[var(--color-text-muted)] text-sm">Not graded</span>
              )}
            </td>
            <td className="px-6 py-4"><StatusBadge status={s.status} /></td>
            <td className="px-6 py-4">
              <div className="flex gap-2">
                {s.status === 'submitted' && <Button className="px-3 py-1.5 text-xs">Grade</Button>}
                <Button variant="secondary" className="px-3 py-1.5 text-xs">View</Button>
              </div>
            </td>
          </motion.tr>
        ))
      )}

      {/* Mobile cards */}
      <div className="lg:hidden space-y-3 mt-4">
        {submissions.map((s, idx) => (
          <motion.div key={s.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.04 }}>
            <Card className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="font-medium text-[var(--color-text-primary)]">{s.student_name || 'N/A'}</p>
                  <p className="text-sm text-[var(--color-text-secondary)]">{s.exam_title || 'N/A'}</p>
                </div>
                <StatusBadge status={s.status} />
              </div>
              <div className="flex items-center justify-between text-sm mb-3">
                <span className="text-[var(--color-text-secondary)]">
                  {s.submitted_at ? new Date(s.submitted_at).toLocaleDateString() : 'Not submitted'}
                </span>
                {s.score !== undefined && (
                  <span className={`font-medium ${scoreColor(s.score)}`}>{s.score}/{s.max_score}</span>
                )}
              </div>
              <div className="flex gap-2 pt-2 border-t border-[var(--color-border-light)]">
                {s.status === 'submitted' && <Button className="px-3 py-1.5 text-xs">Grade</Button>}
                <Button variant="secondary" className="px-3 py-1.5 text-xs">View</Button>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </>
  );

  return (
    <div>
      <div className="mb-6">
        <Breadcrumbs />
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-6 p-4 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-xl flex items-center gap-3">
          <Icon as={AlertCircle} size={16} className="text-[var(--color-error-600)] flex-shrink-0" />
          <p className="text-sm text-[var(--color-error-600)] flex-1">{error.message || 'Failed to load submissions'}</p>
          <Button variant="ghost" onClick={() => refetch()} className="text-xs">Retry</Button>
        </div>
      )}

      {isLoading && <SubmissionsSkeleton />}

      {!isLoading && !error && submissions.length === 0 && (
        <EmptyState
          icon={FileText}
          title="No Submissions Yet"
          description={
            user?.role === 'student'
              ? "You haven't submitted any exams yet. Start by taking an exam."
              : 'No student submissions available yet.'
          }
          action={user?.role === 'student' ? { label: 'Browse Exams', onClick: () => navigate('/exams') } : undefined}
        />
      )}

      {!isLoading && !error && submissions.length > 0 && (
        <>
          {user?.role === 'student' ? renderStudentView() : renderLecturerView()}

          {pagination.pages > 1 && (
            <div className="mt-6">
              <Pagination
                currentPage={pagination.page}
                totalPages={pagination.pages}
                hasNext={pagination.has_next}
                hasPrev={pagination.has_prev}
                onNext={() => setCurrentPage((p) => p + 1)}
                onPrev={() => setCurrentPage((p) => Math.max(1, p - 1))}
                onPageChange={setCurrentPage}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
