import { useState, useEffect, useRef } from 'react';
import resourceCache from '@/lib/resourceCache';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileText, Clock, Edit, Eye, Play, CheckCircle, Calendar } from 'lucide-react';
import Icon from '@/components/Icon';
import { StatusBadge } from '@/components/StatusBadge';
import { EmptyState } from '@/components/EmptyState';
import * as examApi from '@/apis/exam';
import * as questionApi from '@/apis/question';
import * as submissionApi from '@/apis/submission';
import Breadcrumbs from '@/components/Breadcrumbs';
import Button from '@/components/Button';
import { ExamDetailSkeleton } from './ExamDetailSkeleton';
import { useAuth } from '@/contexts/AuthContext';

export function ExamDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  // exam data loaded from API
  const [exam, setExam] = useState<any | null>(null);
  const [courseName, setCourseName] = useState<string | null>(null);
  const [questionCount, setQuestionCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [hasSubmission, setHasSubmission] = useState(false);
  const [submissionCount, setSubmissionCount] = useState(0);
  const [checkingSubmission, setCheckingSubmission] = useState(false);

  // Ref to prevent duplicate API calls in React 18 Strict Mode
  const initialFetchDone = useRef(false);

  useEffect(() => {
    // Prevent duplicate fetches in React 18 Strict Mode
    if (initialFetchDone.current) return;
    initialFetchDone.current = true;

    let mounted = true
    const load = async () => {
      if (!id) return
      setLoading(true)
      try {
        // Fetch exam details and questions in parallel
        const [examRes, questionsRes] = await Promise.all([
          examApi.getExam(id),
          questionApi.listQuestions({ exam_id: id, per_page: 100 })
        ])

        if (mounted) {
          setExam(examRes)
          const questionData = questionsRes?.items || []
          setQuestionCount(questionData.length)
          // Use submission_count from exam data
          setSubmissionCount(examRes.submission_count || 0)
        }

        if (mounted && examRes?.course_id) {
          resourceCache.getCourseName(examRes.course_id)
            .then(name => { if (mounted) setCourseName(name) })
            .catch(() => { if (mounted) setCourseName(`Course ${examRes.course_id}`) })
        } else if (mounted) {
          setCourseName(null)
        }

        // Check if student has already submitted (only for students)
        if (user?.role === 'student' && mounted) {
          setCheckingSubmission(true)
          try {
            const submission = await submissionApi.getMySubmission(id)
            // API returns null if no submission, submission object if exists
            // Check if submission has attempts (actually submitted) vs just started
            setHasSubmission(submission !== null && submission !== undefined && submission.attempts_count > 0)
          } catch (err: any) {
            console.error('Failed to check submission:', err)
            setHasSubmission(false)
          } finally {
            setCheckingSubmission(false)
          }
        }
      } catch (err) {
        console.error('load exam', err)
      } finally {
        setLoading(false)
      }
    }
    load()
    return () => { mounted = false }
  }, [id, user?.role])
  
  if (loading) {
    return <ExamDetailSkeleton />;
  }
  
  if (!exam) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <EmptyState
          icon={FileText}
          title="Exam Not Found"
          description="The exam you're looking for doesn't exist or you don't have permission to view it."
          action={{
            label: "Back to Exams",
            onClick: () => navigate('/exams')
          }}
        />
      </div>
    );
  }
  return (
    <div>
      <Breadcrumbs />

      <motion.div
        initial={{
          opacity: 0,
          y: 20
        }}
        animate={{
          opacity: 1,
          y: 0
        }}
        className="bg-[var(--color-bg-card)] rounded-xl p-4 sm:p-6 lg:p-8 shadow-card mb-6">
        
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-[var(--color-text-primary)] truncate">{exam.title}</h1>
              <StatusBadge status={exam.status} />
            </div>
            <p className="text-sm sm:text-base text-[var(--color-text-secondary)] truncate">{courseName || (exam.course_id ? `Course ${exam.course_id}` : '')}</p>
          </div>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
            {user?.role === 'student' ? (
              hasSubmission ? (
                <Button
                  variant="secondary"
                  onClick={() => navigate('/submissions')}
                  className="flex items-center justify-center gap-2 text-sm bg-[var(--color-success-100)] text-[var(--color-success-700)] border-[var(--color-success-200)]"
                >
                  <Icon as={CheckCircle} size={16} className="text-[var(--color-success-600)]" />
                  <span>Submitted</span>
                </Button>
              ) : exam.status !== 'finished' ? (
                <Button
                  onClick={() => navigate(`/exams/${id}/take`)}
                  className="flex items-center justify-center gap-2 text-sm"
                  disabled={checkingSubmission}
                >
                  <Icon as={Play} size={16} className="text-white" />
                  <span>{checkingSubmission ? 'Checking...' : 'Take Exam'}</span>
                </Button>
              ) : null
            ) : (
              exam.status !== 'finished' && (
                <>
                  <Button 
                    variant="secondary" 
                    onClick={() => navigate(`/exams/${id}/edit`)} 
                    className="flex items-center justify-center gap-2 text-sm"
                  >
                    <Icon as={Edit} size={16} className="text-[var(--color-text-secondary)]" />
                    <span className="hidden sm:inline">Edit Exam</span>
                    <span className="sm:hidden">Edit</span>
                  </Button>
                  <Button 
                    onClick={() => navigate(`/exams/${id}/questions`)} 
                    className="flex items-center justify-center gap-2 text-sm"
                  >
                    <Icon as={Eye} size={16} className="text-[var(--color-text-secondary)]" />
                    <span className="hidden sm:inline">Manage Questions</span>
                    <span className="sm:hidden">Questions</span>
                  </Button>
                </>
              )
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6">
          {/* Duration Card */}
          <div className="surface-card rounded-xl p-4 sm:p-5 border-l-4 border-l-[var(--color-accent-coral-500)]">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-[var(--color-accent-coral-100)] flex items-center justify-center">
                <Icon as={Clock} size={18} className="text-[var(--color-accent-coral-600)]" />
              </div>
              <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wide">Duration</span>
            </div>
            <p className="text-xl sm:text-2xl font-bold text-[var(--color-text-primary)]">
              {exam.duration_hours ? `${exam.duration_hours}h` : ''} {exam.duration_minutes ? `${exam.duration_minutes}m` : ''}
            </p>
          </div>

          {/* Start Time Card */}
          <div className={`surface-card rounded-xl p-4 sm:p-5 border-l-4 transition-all duration-300 ${exam.start_time && new Date(exam.start_time).getTime() - Date.now() > 0 && new Date(exam.start_time).getTime() - Date.now() <= 30 * 60 * 1000 ? 'border-l-[var(--color-error-500)] bg-[var(--color-error-50)] animate-pulse' : 'border-l-[var(--color-primary-500)]'}`}>
            <div className={`flex items-center gap-2 mb-2 ${exam.start_time && new Date(exam.start_time).getTime() - Date.now() > 0 && new Date(exam.start_time).getTime() - Date.now() <= 30 * 60 * 1000 ? 'text-[var(--color-error-600)]' : 'text-[var(--color-primary-600)]'}`}>
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${exam.start_time && new Date(exam.start_time).getTime() - Date.now() > 0 && new Date(exam.start_time).getTime() - Date.now() <= 30 * 60 * 1000 ? 'bg-[var(--color-error-100)]' : 'bg-[var(--color-primary-100)]'}`}>
                <Icon as={Calendar} size={18} className={exam.start_time && new Date(exam.start_time).getTime() - Date.now() > 0 && new Date(exam.start_time).getTime() - Date.now() <= 30 * 60 * 1000 ? 'text-[var(--color-error-600)]' : 'text-[var(--color-primary-600)]'} />
              </div>
              <span className="text-xs font-medium uppercase tracking-wide">{exam.start_time && new Date(exam.start_time).getTime() - Date.now() > 0 && new Date(exam.start_time).getTime() - Date.now() <= 30 * 60 * 1000 ? 'Starting Soon!' : 'Starts At'}</span>
            </div>
            <p className={`text-sm sm:text-base font-semibold ${exam.start_time && new Date(exam.start_time).getTime() - Date.now() > 0 && new Date(exam.start_time).getTime() - Date.now() <= 30 * 60 * 1000 ? 'text-[var(--color-error-700)]' : 'text-[var(--color-text-primary)]'}`}>
              {exam.start_time ? new Date(exam.start_time).toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true }) : 'Not scheduled'}
            </p>
          </div>

          {/* Questions Card */}
          <div className="surface-card rounded-xl p-4 sm:p-5 border-l-4 border-l-[var(--color-info-500)]">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-[var(--color-info-100)] flex items-center justify-center">
                <Icon as={FileText} size={18} className="text-[var(--color-info-600)]" />
              </div>
              <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wide">Questions</span>
            </div>
            <p className="text-xl sm:text-2xl font-bold text-[var(--color-text-primary)]">
              {questionCount}
            </p>
          </div>

          {/* Total Marks Card */}
          <div className="surface-card rounded-xl p-4 sm:p-5 border-l-4 border-l-[var(--color-warning-500)]">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-[var(--color-warning-100)] flex items-center justify-center">
                <Icon as={FileText} size={18} className="text-[var(--color-warning-600)]" />
              </div>
              <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wide">Total Marks</span>
            </div>
            <p className="text-xl sm:text-2xl font-bold text-[var(--color-text-primary)]">
              {exam.total_marks}
            </p>
          </div>

          {/* Submissions Card */}
          <div className="surface-card rounded-xl p-4 sm:p-5 border-l-4 border-l-[var(--color-success-500)]">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-[var(--color-success-100)] flex items-center justify-center">
                <Icon as={FileText} size={18} className="text-[var(--color-success-600)]" />
              </div>
              <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wide">Submissions</span>
            </div>
            <p className="text-xl sm:text-2xl font-bold text-[var(--color-text-primary)]">
              {submissionCount}
            </p>
          </div>
        </div>
      </motion.div>
    </div>);
}