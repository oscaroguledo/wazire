import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Clock,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  ArrowLeft,
  Calendar,
  Play,
  X,
  Check,
  SkipBack,
  Trash2,
} from 'lucide-react';
import Icon from '@/components/Icon';
import Button from '@/components/Button';
import Input from '@/components/Input';
import { Modal } from '@/components/Modal';
import * as examApi from '@/apis/exam';
import * as questionApi from '@/apis/question';
import * as submissionApi from '@/apis/submission';
import answerApi from '@/apis/answer';
import type { ExamQuestion } from '@/apis/exam';
import { formatDuration } from '@/utils/formatDuration';
import Breadcrumbs from '@/components/Breadcrumbs';
import TakeExamSkeleton from '@/pages/TakeExamSkeleton';

export function TakeExam() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  
  // Determine if we're on the active exam page based on URL
  const isActiveExam = location.pathname.endsWith('/active');
  
  const [exam, setExam] = useState<any | null>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingCount, setPendingCount] = useState(0);

  const [existingSubmission, setExistingSubmission] = useState<any>(null);
  const [checkingSubmission, setCheckingSubmission] = useState(false);
  const [totalDuration, setTotalDuration] = useState(0);

  // Determine view mode based on URL path
  const examStarted = isActiveExam;
  
  // Load exam data and check for existing submission
  useEffect(() => {
    if (!id) return;
    const loadExam = async () => {
      try {
        setLoading(true);
        setError(null);
        // Fetch exam and questions in parallel
        const [examData, qs] = await Promise.all([
          examApi.getExam(id as string),
          questionApi.listQuestions({ exam_id: id as string })
        ]);
        setExam(examData || null);
        setQuestions(qs?.items || []);

        // Check for existing submission
        try {
          const submission = await submissionApi.getMySubmission(id as string);
          if (submission) {
            setExistingSubmission(submission);
          }
        } catch (subError) {
          // No existing submission found
          setExistingSubmission(null);
        }

        // set timer if exam has duration
        if (examData?.duration_hours || examData?.duration_minutes) {
          const totalHours = (examData.duration_hours || 0) + (examData.duration_minutes || 0) / 60;
          setTotalDuration(totalHours * 3600);
          setTimeRemaining(totalHours * 3600);
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load exam');
      } finally {
        setLoading(false);
        setCheckingSubmission(false);
      }
    };

    void loadExam();
  }, [id, isActiveExam]);

  const pendingRef = useRef<Record<string, unknown>>({});
  const processingRef = useRef(false);

  const persistPending = useCallback(() => {
    if (!id) return;
    try {
      localStorage.setItem(`wazire.pending_answers.${id}`, JSON.stringify(pendingRef.current || {}));
      setPendingCount(Object.keys(pendingRef.current || {}).length);
    } catch (e) {
      // ignore
    }
  }, [id]);

  const enqueueSave = useCallback((questionId: string, answerValue: string | number | boolean | string[]) => {
    if (!id) return;
    const q = questions.find((qq: ExamQuestion) => qq.id === questionId);
    let payloadAnswer: { option?: string | number | boolean | string[]; text?: string | number | boolean | string[] } | string | number | boolean | string[] = answerValue;
    if (q) {
      if (q.qtype === 'multiple_choice' || q.qtype === 'true_false') {
        payloadAnswer = { option: answerValue };
      } else {
        payloadAnswer = { text: answerValue };
      }
    }
    const payload = { exam_id: id as string, question_id: questionId, answer: payloadAnswer };
    // Save to pending queue and persist
    pendingRef.current = { ...pendingRef.current, [questionId]: payload };
    persistPending();
    setPendingCount(Object.keys(pendingRef.current).length);
    // Fire off process (don't await)
    void processQueue();
  }, [id, questions, persistPending]);

  const processQueue = useCallback(async () => {
    if (processingRef.current) return;
    processingRef.current = true;
    try {
      const entries = Object.entries(pendingRef.current || {});
      if (entries.length === 0) return;
      // Attempt all pending saves in parallel
      await Promise.all(entries.map(async ([questionId, payload]) => {
        try {
          await answerApi.upsertAnswer(questionId, payload as any);
          // on success remove from pending
          delete pendingRef.current[questionId];
          persistPending();
        } catch (err) {
          // leave in queue for next attempt
        }
      }));
      // update count after attempted sends
      setPendingCount(Object.keys(pendingRef.current || {}).length);
    } finally {
      processingRef.current = false;
    }
  }, [persistPending]);

  const saveAnswerImmediate = useCallback(async (questionId: string, answerValue: string | number | boolean | string[]) => {
    try {
      await answerApi.upsertAnswer(questionId, {
        exam_id: id as string,
        question_id: questionId,
        answer: answerValue as unknown as Record<string, unknown>
      });
    } catch (err) {
      // Add to pending queue if save fails
      enqueueSave(questionId, answerValue);
    }
  }, [id, enqueueSave]);

  // Define submit handler early - before any conditional returns
  const handleSubmitExam = useCallback(async () => {
    if (!id || submitting) return;
    setSubmitting(true);
    try {
      // Save any pending answers before submitting
      const raw = localStorage.getItem(`wazire.pending_answers.${id}`);
      if (raw) pendingRef.current = JSON.parse(raw) || {};
    } catch (e) {
      pendingRef.current = {};
    }
    setPendingCount(Object.keys(pendingRef.current).length);
    
    try {
      // Submit the exam
      await submissionApi.submitExam({
        exam_id: id as string
      });
      
      // Navigate to success page
      navigate(`/exams/${id}/submitted`);
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : 'Failed to submit exam');
    } finally {
      setSubmitting(false);
    }
  }, [id, submitting, answers, navigate]);

  // Timer effect
  useEffect(() => {
    if (!examStarted || timeRemaining <= 0) return;

    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          // Auto-submit when time runs out
          void handleSubmitExam();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [examStarted, timeRemaining, handleSubmitExam]);

  // Retry when back online
  useEffect(() => {
    const onOnline = () => { void processQueue(); };
    window.addEventListener('online', onOnline);
    const iv = setInterval(() => { void processQueue(); }, 5000);
    return () => {
      window.removeEventListener('online', onOnline);
      clearInterval(iv);
    };
  }, [processQueue]);

  if (loading) {
    return (
      <TakeExamSkeleton />
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-primary)] p-6">
        <div className="max-w-2xl mx-auto">
          <div className="bg-[var(--color-error-50)] border border-[var(--color-error-200)] rounded-xl p-6 text-center">
            <Icon as={AlertCircle} size={48} className="text-[var(--color-error-500)] mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-[var(--color-error-700)] mb-2">Error</h2>
            <p className="text-[var(--color-error-600)] mb-4">{error}</p>
            <Button onClick={() => navigate('/exams')} variant="secondary">Back to Exams</Button>
          </div>
        </div>
      </div>
    );
  }

  if (!exam) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-primary)] p-6">
        <div className="max-w-2xl mx-auto">
          <div className="bg-[var(--color-bg-card)] rounded-xl p-8 text-center">
            <Icon as={AlertCircle} size={48} className="text-[var(--color-text-muted)] mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Exam Not Found</h2>
            <p className="text-[var(--color-text-secondary)] mb-4">The exam could not be found.</p>
            <Button onClick={() => navigate('/exams')}>Back to Exams</Button>
          </div>
        </div>
      </div>
    );
  }

  // Show start screen if exam hasn't started
  const handleStartExam = async () => {
    if (!id) return;
    setStarting(true);
    try {
      // Create a submission record (no attempt) when starting the exam
      const submission = await submissionApi.startSubmission({ exam_id: id });
      setExistingSubmission(submission);
      // Navigate to the active exam page
      navigate(`/exams/${id}/active`);
    } catch (err) {
      console.error('Failed to start exam:', err);
      setError('Failed to start exam. You may have already started this exam.');
    } finally {
      setStarting(false);
    }
  };

  if (!examStarted) {
    // Show submitted message only if submission is completed
    if (existingSubmission && existingSubmission.status === 'completed') {
      return (
        <div className="min-h-screen bg-[var(--color-bg-primary)] p-6">
          <div className="max-w-2xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-[var(--color-success-50)] border border-[var(--color-success-200)] rounded-2xl p-8 text-center"
            >
              <div className="w-16 h-16 bg-[var(--color-success-100)] rounded-full flex items-center justify-center mx-auto mb-4">
                <Icon as={CheckCircle} size={32} className="text-[var(--color-success-600)]" />
              </div>
              <h2 className="text-2xl font-bold text-[var(--color-success-700)] mb-2">
                Exam Already Submitted
              </h2>
              <p className="text-[var(--color-success-600)] mb-6">
                You have already submitted this exam.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button variant="secondary" onClick={() => navigate('/exams')}>
                  Back to Exams
                </Button>
                <Button onClick={() => navigate('/submissions')}>
                  View Submissions
                </Button>
              </div>
            </motion.div>
          </div>
        </div>
      );
    }

    // Show continue exam button if submission is in progress
    if (existingSubmission && existingSubmission.status === 'in_progress') {
      return (
        <div className="min-h-screen bg-[var(--color-bg-primary)] p-6">
          <div className="max-w-2xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-[var(--color-warning-50)] border border-[var(--color-warning-200)] rounded-2xl p-8 text-center"
            >
              <div className="w-16 h-16 bg-[var(--color-warning-100)] rounded-full flex items-center justify-center mx-auto mb-4">
                <Icon as={Clock} size={32} className="text-[var(--color-warning-600)]" />
              </div>
              <h2 className="text-2xl font-bold text-[var(--color-warning-700)] mb-2">
                Exam in Progress
              </h2>
              <p className="text-[var(--color-warning-600)] mb-6">
                You have an ongoing exam. Click below to continue.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button variant="secondary" onClick={() => navigate('/exams')}>
                  Back to Exams
                </Button>
                <Button onClick={() => navigate(`/exams/${id}/active`)}>
                  Continue Exam
                </Button>
              </div>
            </motion.div>
          </div>
        </div>
      );
    }

    // Show no questions available message
    if (!loading && !checkingSubmission && questions.length === 0) {
      return (
        <div className="min-h-screen bg-[var(--color-bg-primary)] p-6">
          <div className="max-w-2xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-[var(--color-warning-50)] border border-[var(--color-warning-200)] rounded-2xl p-8 text-center"
            >
              <div className="w-16 h-16 bg-[var(--color-warning-100)] rounded-full flex items-center justify-center mx-auto mb-4">
                <Icon as={AlertCircle} size={32} className="text-[var(--color-warning-600)]" />
              </div>
              <h2 className="text-2xl font-bold text-[var(--color-warning-700)] mb-2">
                No Questions Available
              </h2>
              <p className="text-[var(--color-warning-600)] mb-6">
                This exam doesn't have any questions yet. Please check back later or contact your lecturer.
              </p>
              <Button onClick={() => navigate('/exams')}>
                Back to Exams
              </Button>
            </motion.div>
          </div>
        </div>
      );
    }

    return (
      <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="bg-[var(--color-bg-card)] rounded-xl shadow-lg border border-[var(--color-border-light)] overflow-hidden"
          >
            {/* Header Section */}
            <div className="relative bg-gradient-to-r from-[var(--color-primary-600)] via-[var(--color-primary-700)] to-[var(--color-primary-800)] p-6 text-white">
              <div className="absolute inset-0 bg-black/10" />
              <div className="relative z-10">
                <Button
                  variant="ghost"
                  onClick={() => navigate('/exams')}
                  className="text-white/90 hover:text-white hover:bg-white/10 mb-4 transition-all duration-200 h-9 text-sm"
                >
                  <Icon as={ArrowLeft} size={18} className="mr-1" />
                  Back
                </Button>
                
                <div className="text-center">
                  <h1 className="text-xl font-bold mb-1 tracking-tight">{exam.title}</h1>
                  <p className="text-base text-white/90 font-medium">{exam.course_name || 'General Course'}</p>
                  {exam.description && (
                    <p className="text-white/70 mt-2 max-w-xl mx-auto text-sm line-clamp-2">{exam.description}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Stats Cards */}
            <div className="p-5">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                <div className="bg-[var(--color-primary-50)] rounded-xl p-3 border border-[var(--color-primary-200)]">
                  <Icon as={Clock} size={18} className="text-[var(--color-primary-600)] mb-1" />
                  <p className="text-xs text-[var(--color-primary-600)] font-medium">Duration</p>
                  <p className="text-lg font-bold text-[var(--color-primary-900)]">{formatDuration(exam.duration || 0)}</p>
                </div>

                <div className={`rounded-xl p-3 border transition-all duration-300 ${exam.start_time && new Date(exam.start_time).getTime() - Date.now() > 0 && new Date(exam.start_time).getTime() - Date.now() <= 30 * 60 * 1000 ? 'bg-[var(--color-error-50)] border-[var(--color-error-200)] animate-pulse' : 'bg-[var(--color-info-50)] border-[var(--color-info-200)]'}`}>
                  <Icon as={Calendar} size={18} className={exam.start_time && new Date(exam.start_time).getTime() - Date.now() > 0 && new Date(exam.start_time).getTime() - Date.now() <= 30 * 60 * 1000 ? 'text-[var(--color-error-600)] mb-1' : 'text-[var(--color-info-600)] mb-1'} />
                  <p className={`text-xs font-medium ${exam.start_time && new Date(exam.start_time).getTime() - Date.now() > 0 && new Date(exam.start_time).getTime() - Date.now() <= 30 * 60 * 1000 ? 'text-[var(--color-error-600)]' : 'text-[var(--color-info-600)]'}`}>{exam.start_time && new Date(exam.start_time).getTime() - Date.now() > 0 && new Date(exam.start_time).getTime() - Date.now() <= 30 * 60 * 1000 ? 'Starting Soon!' : 'Starts At'}</p>
                  <p className={`text-lg font-bold ${exam.start_time && new Date(exam.start_time).getTime() - Date.now() > 0 && new Date(exam.start_time).getTime() - Date.now() <= 30 * 60 * 1000 ? 'text-[var(--color-error-700)]' : 'text-[var(--color-info-900)]'}`}>
                    {exam.start_time ? new Date(exam.start_time).toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true }) : 'Not set'}
                  </p>
                </div>

                <div className="bg-[var(--color-success-50)] rounded-xl p-3 border border-[var(--color-success-200)]">
                  <Icon as={AlertCircle} size={18} className="text-[var(--color-success-600)] mb-1" />
                  <p className="text-xs text-[var(--color-success-600)] font-medium">Questions</p>
                  <p className="text-lg font-bold text-[var(--color-success-900)]">{questions.length}</p>
                </div>

                <div className="bg-[var(--color-premium-50)] rounded-xl p-3 border border-[var(--color-premium-200)]">
                  <Icon as={CheckCircle} size={18} className="text-[var(--color-premium-600)] mb-1" />
                  <p className="text-xs text-[var(--color-premium-600)] font-medium">Attempts</p>
                  <p className="text-lg font-bold text-[var(--color-premium-900)]">{exam.max_attempts || '∞'}</p>
                </div>
              </div>

              {/* Instructions */}
              <div className="bg-[var(--color-warning-50)] border border-[var(--color-warning-200)] rounded-xl p-4 mb-5">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-[var(--color-warning-200)] rounded-full flex items-center justify-center">
                      <Icon as={AlertCircle} size={16} className="text-[var(--color-warning-700)]" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-base font-semibold text-[var(--color-warning-900)] mb-2">Instructions</h3>
                    <ul className="space-y-1 text-sm text-[var(--color-warning-800)]">
                      <li className="flex items-start gap-2">
                        <span className="text-amber-600">•</span>
                        <span>Timer cannot be paused once started</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-amber-600">•</span>
                        <span>Navigate between questions using Previous/Next</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-amber-600">•</span>
                        <span>Review your answers before submission</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-amber-600">•</span>
                        <span>Auto-submitted when time expires</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3">
                <Button 
                  variant="secondary" 
                  onClick={() => navigate('/exams')} 
                  className="flex-1 h-11 text-sm font-semibold bg-[var(--color-error-100)] hover:bg-[var(--color-error-200)] text-[var(--color-error-700)] border-[var(--color-error-300)] flex items-center justify-center gap-2"
                >
                  <Icon as={X} size={18} />
                  Cancel
                </Button>
                <Button 
                  onClick={handleStartExam} 
                  loading={starting || checkingSubmission} 
                  className="flex-1 h-11 text-sm font-semibold bg-gradient-to-r from-[var(--color-success-500)] to-[var(--color-success-600)] hover:from-[var(--color-success-600)] hover:to-[var(--color-success-700)] text-white shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-50 flex items-center justify-center gap-2"
                  disabled={questions.length === 0}
                >
                  <Icon as={Play} size={18} className="fill-white" />
                  {questions.length === 0 ? 'No Questions' : 'Start Exam'}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
    );
  }

  const currentQuestion = questions[currentQuestionIndex];
  const progress = questions.length > 0 ? ((currentQuestionIndex + 1) / questions.length) * 100 : 0;
  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours > 0 ? hours + ':' : ''}${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleAnswer = (questionId: string, answer: string | number | boolean | string[]) => {
    setAnswers((prev: Record<string, unknown>) => {
      const next = { ...prev, [questionId]: answer };
      // Immediately persist the per-question answer
      void saveAnswerImmediate(questionId, questionIsRawAnswer(answer) ? answer : answer);
      return next;
    });
  };

  // Helper to detect if value is raw (we always save the frontend answer shape)
  const questionIsRawAnswer = (_v: unknown) => true

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
      <Breadcrumbs />
      
      {/* Exam Header */}
      <motion.div
        initial={{
          opacity: 0,
          y: -20
        }}
        animate={{
          opacity: 1,
          y: 0
        }}
        transition={{ duration: 0.5 }}
        className="bg-[var(--color-bg-card)] rounded-2xl shadow-lg border border-[var(--color-border-light)] p-6 mb-6"
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex-1">
            <h1 className="text-2xl lg:text-3xl font-bold text-[var(--color-text-primary)] mb-2">{exam.title}</h1>
            <p className="text-[var(--color-text-secondary)] font-medium">{exam.course_name}</p>
          </div>
          
          {/* Timer Display */}
          <div className="flex items-center gap-3 px-6 py-3 bg-[var(--color-primary-50)] rounded-xl border border-[var(--color-primary-200)]">
            <Icon as={Clock} size={20} className="text-[var(--color-primary-600)]" />
            <motion.span
              animate={timeRemaining > 0 && totalDuration > 0 && timeRemaining <= totalDuration / 8 ? { opacity: [1, 0.5, 1] } : {}}
              transition={timeRemaining > 0 && totalDuration > 0 && timeRemaining <= totalDuration / 8 ? { duration: 0.5, repeat: Infinity } : {}}
              className={`text-xl font-bold tabular-nums ${
                timeRemaining > 0 && totalDuration > 0 && timeRemaining <= totalDuration / 8
                  ? 'text-[var(--color-error-600)]'
                  : timeRemaining > 0 && totalDuration > 0 && timeRemaining <= totalDuration / 4
                  ? 'text-[var(--color-warning-600)]'
                  : 'text-[var(--color-primary-700)]'
              }`}>
              {formatTime(timeRemaining)}
            </motion.span>
            {pendingCount > 0 ? (
              <div className="ml-3 inline-flex items-center gap-2 px-3 py-1 bg-[var(--color-warning-100)] rounded-full text-sm text-[var(--color-warning-700)]">
                <span className="w-2 h-2 rounded-full bg-[var(--color-warning-500)] animate-pulse" />
                <span>Saving{pendingCount > 1 ? ` (${pendingCount})` : ''}</span>
              </div>
            ) : (
              <div className="ml-3 text-sm text-[var(--color-success-600)] font-medium">All saved</div>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-[var(--color-text-secondary)]">Progress</span>
            <span className="text-sm text-[var(--color-text-muted)]">
              Question {currentQuestionIndex + 1} of {questions.length}
            </span>
          </div>
          <div className="relative h-3 bg-[var(--color-bg-hover)] rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="absolute top-0 left-0 h-full bg-gradient-to-r from-[var(--color-info-500)] to-[var(--color-info-600)] rounded-full"
            />
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentQuestionIndex}
              initial={{
                opacity: 0,
                x: 20
              }}
              animate={{
                opacity: 1,
                x: 0
              }}
              exit={{
                opacity: 0,
                x: -20
              }}
              transition={{ duration: 0.3 }}
              className="bg-[var(--color-bg-card)] rounded-2xl shadow-lg border border-[var(--color-border-light)] p-8"
            >
              {/* Question Header */}
              <div className="mb-8">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-4">
                    <div className="px-4 py-2 bg-gradient-to-r from-[var(--color-info-500)] to-[var(--color-info-600)] text-white rounded-full font-semibold text-sm">
                      Question {currentQuestionIndex + 1}
                    </div>
                    {/* Per-question save indicator */}
                    {currentQuestion?.id && pendingRef.current && pendingRef.current[currentQuestion.id] ? (
                      <div className="inline-flex items-center gap-2 px-3 py-1 bg-[var(--color-warning-100)] text-[var(--color-warning-700)] rounded-full text-sm font-medium">
                        <span className="w-2 h-2 rounded-full bg-[var(--color-warning-500)] animate-pulse" />
                        <span>Saving...</span>
                      </div>
                    ) : (
                      <div className="inline-flex items-center gap-2 px-3 py-1 bg-[var(--color-success-100)] text-[var(--color-success-700)] rounded-full text-sm font-medium">
                        <span className="w-2 h-2 rounded-full bg-[var(--color-success-500)]" />
                        <span>Saved</span>
                      </div>
                    )}
                  </div>
                  <div className={`px-4 py-2 rounded-full text-sm font-semibold border-2 ${
                    (currentQuestion?.mark || 0) === 0 
                      ? 'bg-[var(--color-error-50)] text-[var(--color-error-600)] border-[var(--color-error-200)]' 
                      : 'bg-[var(--color-success-50)] text-[var(--color-success-600)] border-[var(--color-success-200)]'
                  }`}>
                    {currentQuestion?.mark || 0} marks
                  </div>
                </div>
                
                {/* Question Text */}
                <div className="bg-[var(--color-bg-subtle)] rounded-xl p-6 border border-[var(--color-border-light)]">
                  <p className="text-lg leading-relaxed text-[var(--color-text-primary)] font-medium">
                    {currentQuestion?.text || 'Question text not available'}
                  </p>
                </div>
              </div>

              {/* Answer Options */}
              {currentQuestion?.qtype === 'multiple_choice' && currentQuestion?.options ? (
                <div className="space-y-3">
                  {currentQuestion.options.map((option: { label: string; text: string }, index: number) => (
                    <motion.button
                      key={option.label}
                      type="button"
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      onClick={() => handleAnswer(currentQuestion?.id, option.label)}
                      className={`w-full p-4 border-2 rounded-2xl text-left transition-all duration-300 relative overflow-hidden group ${
                        answers[currentQuestion?.id] === option.label
                          ? 'bg-gradient-to-r from-[var(--color-primary-500)] to-[var(--color-primary-600)] border-[var(--color-primary-500)] text-white shadow-xl'
                          : 'bg-[var(--color-bg-card)] border-[var(--color-border-medium)] hover:border-[var(--color-primary-400)] hover:shadow-lg'
                      }`}
                    >
                      <div className="flex items-center gap-4 relative z-10">
                        <div className={`w-8 h-8 flex items-center justify-center rounded-lg font-bold text-sm transition-all ${
                          answers[currentQuestion?.id] === option.label
                            ? 'bg-white/20 text-white backdrop-blur-sm'
                            : 'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] group-hover:bg-[var(--color-primary-100)] group-hover:text-[var(--color-primary-600)]'
                        }`}>
                          {String.fromCharCode(65 + index)}
                        </div>
                        <span className={`font-medium text-base leading-relaxed flex-1 ${
                          answers[currentQuestion?.id] === option.label ? 'text-white' : 'text-[var(--color-text-primary)]'
                        }`}>
                          {option.text}
                        </span>
                        {answers[currentQuestion?.id] === option.label && (
                          <div className="flex items-center gap-2">
                            <motion.div
                              initial={{ scale: 0 }}
                              animate={{ scale: 1 }}
                              className="w-6 h-6 rounded-full bg-white/30 backdrop-blur-sm flex items-center justify-center"
                            >
                              <Icon as={Check} size={14} className="text-white" />
                            </motion.div>
                          </div>
                        )}
                      </div>
                      {answers[currentQuestion?.id] === option.label && (
                        <motion.div
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          className="absolute inset-0 bg-gradient-to-r from-[var(--color-primary-400)] to-transparent opacity-20"
                        />
                      )}
                    </motion.button>
                  ))}
                </div>
              ) : (
                <div className="space-y-4">
                  <label className="block text-sm font-semibold text-[var(--color-text-secondary)] mb-2">
                    Your Answer
                  </label>
                  <Input
                    as="textarea"
                    value={answers[currentQuestion?.id] || ''}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleAnswer(currentQuestion?.id, e.target.value)}
                    placeholder="Type your detailed answer here..."
                    rows={6}
                    className="border-2 border-[var(--color-border-medium)] focus:border-[var(--color-primary-500)] focus:ring-[var(--color-primary-500)] rounded-xl text-base leading-relaxed resize-none"
                  />
                </div>
              )}

              {/* Navigation Buttons */}
              <div className="flex items-center justify-between mt-10 pt-8 border-t border-[var(--color-border-light)]">
                <Button
                  variant="ghost"
                  noMotion
                  onClick={() => setCurrentQuestionIndex((prev) => Math.max(0, prev - 1))}
                  disabled={currentQuestionIndex === 0}
                  className="flex items-center gap-2 px-6 py-3 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                >
                  <Icon as={ChevronLeft} size={18} />
                  Previous
                </Button>

                {currentQuestionIndex === questions.length - 1 ? (
                  <Button 
                    onClick={() => setIsSubmitModalOpen(true)} 
                    className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-[var(--color-success-500)] to-[var(--color-success-600)] hover:from-[var(--color-success-600)] hover:to-[var(--color-success-700)] text-white font-semibold shadow-lg hover:shadow-xl transition-all duration-200"
                  >
                    <Icon as={CheckCircle} size={18} />
                    Submit Exam
                  </Button>
                ) : (
                  <Button
                    variant="ghost"
                    noMotion
                    onClick={() => setCurrentQuestionIndex((prev) => Math.min(questions.length - 1, prev + 1))}
                    className="flex items-center gap-2 px-6 py-3 text-[var(--color-info-600)] hover:text-[var(--color-info-700)] hover:bg-[var(--color-info-50)] transition-all duration-200"
                  >
                    Next
                    <Icon as={ChevronRight} size={18} />
                  </Button>
                )}
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="lg:col-span-1">
          <div className="bg-[var(--color-bg-card)] rounded-2xl shadow-lg border border-[var(--color-border-light)] p-4 lg:p-6 lg:sticky lg:top-6">
            <h3 className="text-base lg:text-lg font-bold text-[var(--color-text-primary)] mb-4 lg:mb-6 flex items-center gap-2">
              <Icon as={AlertCircle} size={18} className="text-[var(--color-info-600)]" />
              Question Navigator
            </h3>
            
            {/* Question Grid */}
            <div className="grid grid-cols-6 sm:grid-cols-7 lg:grid-cols-5 gap-1.5 mb-6">
              {questions.map((q: ExamQuestion, idx: number) => (
                <button
                  key={q.id}
                  onClick={() => setCurrentQuestionIndex(idx)}
                  className={`relative aspect-square rounded-md font-bold text-xs sm:text-sm transition-all duration-300 transform hover:scale-105 active:scale-95 ${
                    idx === currentQuestionIndex
                      ? 'bg-gradient-to-br from-[var(--color-primary-500)] to-[var(--color-primary-700)] text-white shadow-lg ring-2 ring-[var(--color-primary-300)]'
                      : answers[q.id]
                      ? 'bg-[var(--color-success-500)] text-white shadow-md hover:bg-[var(--color-success-600)] hover:shadow-lg'
                      : 'bg-[var(--color-bg-card)] text-[var(--color-text-secondary)] border-2 border-[var(--color-border-medium)] hover:border-[var(--color-primary-400)] hover:text-[var(--color-primary-600)] hover:shadow-md'
                  }`}
                >
                  {idx + 1}
                  {answers[q.id] && idx !== currentQuestionIndex && (
                    <div className="absolute -top-0.5 -right-0.5 w-2 h-2 sm:w-3 sm:h-3 bg-[var(--color-success-400)] rounded-full border-2 border-[var(--color-bg-card)]"></div>
                  )}
                </button>
              ))}
            </div>

            {/* Progress Summary */}
            <div className="bg-[var(--color-bg-subtle)] rounded-xl p-3 lg:p-4 border border-[var(--color-border-light)]">
              <h4 className="text-xs lg:text-sm font-semibold text-[var(--color-text-secondary)] mb-3 lg:mb-4">Progress Summary</h4>
              <div className="space-y-2 lg:space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 lg:w-3 lg:h-3 rounded-full bg-[var(--color-success-500)]" />
                    <span className="text-xs lg:text-sm text-[var(--color-text-muted)]">Answered</span>
                  </div>
                  <span className="text-xs lg:text-sm font-bold text-[var(--color-success-700)]">
                    {Object.keys(answers).length}/{questions.length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 lg:w-3 lg:h-3 rounded-full bg-[var(--color-text-muted)]" />
                    <span className="text-xs lg:text-sm text-[var(--color-text-muted)]">Remaining</span>
                  </div>
                  <span className="text-xs lg:text-sm font-bold text-[var(--color-text-secondary)]">
                    {questions.length - Object.keys(answers).length}
                  </span>
                </div>
                <div className="pt-2 lg:pt-3 mt-2 lg:mt-3 border-t border-[var(--color-border-light)]">
                  <div className="flex items-center justify-between">
                    <span className="text-xs lg:text-sm text-[var(--color-text-muted)]">Completion</span>
                    <span className="text-xs lg:text-sm font-bold text-[var(--color-info-700)]">
                      {Math.round((Object.keys(answers).length / questions.length) * 100)}%
                    </span>
                  </div>
                  <div className="mt-1.5 lg:mt-2 h-1.5 lg:h-2 bg-[var(--color-bg-hover)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-[var(--color-info-500)] to-[var(--color-info-600)] rounded-full transition-all duration-300"
                      style={{ width: `${(Object.keys(answers).length / questions.length) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="mt-4 lg:mt-6 space-y-2 lg:space-y-3">
              <Button
                variant="secondary"
                onClick={() => {
                  // Jump to first unanswered question
                  const firstUnanswered = questions.findIndex((q: ExamQuestion) => !answers[q.id]);
                  if (firstUnanswered !== -1) {
                    setCurrentQuestionIndex(firstUnanswered);
                  }
                }}
                className="w-full text-xs lg:text-sm py-2 lg:py-3"
              >
                <Icon as={SkipBack} size={16} className="mr-2" />
                Jump to First Unanswered
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  // Clear all answers
                  if (confirm('Are you sure you want to clear all answers? This cannot be undone.')) {
                    setAnswers({});
                    // Also clear from backend
                    Object.keys(answers).forEach(qid => {
                      void saveAnswerImmediate(qid, '');
                    });
                  }
                }}
                className="w-full text-xs lg:text-sm py-2 lg:py-3"
              >
                <Icon as={Trash2} size={16} className="mr-2" />
                Clear All Answers
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Submit Modal */}
      <Modal
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        title="Submit Exam"
        size="lg"
      >
        <div className="space-y-6">
          {/* Warning Section */}
          <div className="bg-[var(--color-warning-50)] border-2 border-[var(--color-warning-200)] rounded-xl p-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-[var(--color-warning-200)] rounded-full flex items-center justify-center">
                  <Icon as={AlertCircle} size={24} className="text-[var(--color-warning-700)]" />
                </div>
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-[var(--color-warning-900)] mb-2">
                  Ready to Submit?
                </h3>
                <p className="text-[var(--color-warning-800)] leading-relaxed">
                  You have answered <span className="font-bold">{Object.keys(answers).length}</span> out of{' '}
                  <span className="font-bold">{questions.length}</span> questions. Once submitted, you cannot
                  change your answers. Please review your responses before final submission.
                </p>

                {Object.keys(answers).length < questions.length && (
                  <div className="mt-4 p-3 bg-[var(--color-warning-100)] rounded-lg border border-[var(--color-warning-300)]">
                    <p className="text-sm text-[var(--color-warning-800)] font-medium">
                      ⚠️ You have {questions.length - Object.keys(answers).length} unanswered question(s).
                      Consider reviewing before submitting.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4">
            <Button
              variant="secondary"
              className="flex-1 h-12 text-base font-semibold bg-[var(--color-bg-hover)] hover:bg-[var(--color-bg-subtle)] text-[var(--color-text-secondary)] border-[var(--color-border-light)]"
              onClick={() => setIsSubmitModalOpen(false)}
            >
              Review Answers
            </Button>
            <Button
              className="flex-1 h-12 text-base font-semibold bg-gradient-to-r from-[var(--color-success-500)] to-[var(--color-success-600)] hover:from-[var(--color-success-600)] hover:to-[var(--color-success-700)] text-white shadow-lg hover:shadow-xl transition-all duration-200"
              onClick={handleSubmitExam}
              loading={submitting}
            >
              <Icon as={CheckCircle} size={18} className="mr-2" />
              {submitting ? 'Submitting...' : 'Submit Exam'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>);

}