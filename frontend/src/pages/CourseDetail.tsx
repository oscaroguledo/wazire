import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BookOpen, 
  FileText, 
  Calendar, 
  Trash2, 
  Edit, 
  GraduationCap, 
  ChevronRight,
  AlertCircle,
  Users,
  UserPlus,
  Filter,
  X,
} from 'lucide-react';
import Button from '@/components/Button';
import { useAuth } from '@/contexts/AuthContext';
import Icon from '@/components/Icon';
import { EmptyState } from '@/components/EmptyState';
import * as courseApi from '@/apis/course';
import * as examApi from '@/apis/exam';
import * as enrollmentApi from '@/apis/enrollment';
import * as authApi from '@/apis/auth';
import type { Exam } from '@/apis/exam';
import type { Enrollment, Semester } from '@/apis/enrollment';
import { Modal } from '@/components/Modal';
import Breadcrumbs from '@/components/Breadcrumbs';
import Pagination from '@/components/Pagination';
import Dropdown from '@/components/Dropdown';
import CourseDetailSkeleton from '@/pages/CourseDetailSkeleton';
import Card from '@/components/Card';
import Tabs from '@/components/Tabs';
import type { Course } from '@/apis/course';

export function CourseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [course, setCourse] = useState<Course | null>(null);
  const [exams, setExams] = useState<Exam[]>([]);
  const [examsLoading, setExamsLoading] = useState(false);
  const [examsError, setExamsError] = useState<string | null>(null);
  const [examsPage, setExamsPage] = useState(1);
  const [examsPerPage] = useState(10);
  const [examsHasNext, setExamsHasNext] = useState(false);
  const [examsYear, setExamsYear] = useState<number | ''>('');
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [enrollmentsLoading, setEnrollmentsLoading] = useState(false);
  const [enrollmentsPage, setEnrollmentsPage] = useState(1);
  const [enrollmentsPerPage] = useState(10);
  const [enrollmentsHasNext, setEnrollmentsHasNext] = useState(false);
  const [enrollmentsSemester, setEnrollmentsSemester] = useState<Semester | ''>('');
  const [enrollmentsYear, setEnrollmentsYear] = useState<number | ''>('');
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState(false);
  const [students, setStudents] = useState<{id: string, name: string, email: string, institution_id?: string}[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<string>('');
  const [selectedSemester, setSelectedSemester] = useState<Semester>('fall');
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear());
  const [enrollLoading, setEnrollLoading] = useState(false);
  const [enrollError, setEnrollError] = useState<string | null>(null);
  const [enrollSuccess, setEnrollSuccess] = useState<string | null>(null);
  const [unenrollLoading, setUnenrollLoading] = useState<string | null>(null);
  const [showUnenrollConfirm, setShowUnenrollConfirm] = useState(false);
  const [selectedEnrollmentId, setSelectedEnrollmentId] = useState<string | null>(null);
  
  // Filter modal state
  const [isFilterModalOpen, setIsFilterModalOpen] = useState(false);
  const [tempFilterSemester, setTempFilterSemester] = useState<Semester | ''>('');
  const [tempFilterYear, setTempFilterYear] = useState<number | ''>('');
  
  const { user } = useAuth();

  // Ref to prevent duplicate course load in React 18 Strict Mode
  const initialLoadDone = useRef(false);

  useEffect(() => {
    // Prevent duplicate fetches in React 18 Strict Mode
    if (initialLoadDone.current) return;
    initialLoadDone.current = true;

    const loadData = async () => {
      if (!id) {
        setError('Course ID is required');
        setLoading(false);
        return;
      }
      
      setLoading(true);
      setExamsLoading(true);
      setEnrollmentsLoading(true);
      setError(null);
      
      try {
        // Fetch course, exams, and enrollments in parallel
        const [courseData, examsResponse, enrollmentsResponse, years] = await Promise.all([
          courseApi.getCourse(id),
          examApi.listExams({ course_id: id, page: 1, per_page: examsPerPage }),
          enrollmentApi.getCourseEnrollment(id, { 
            page: 1, 
            per_page: enrollmentsPerPage,
            semester: enrollmentsSemester || undefined,
            year: enrollmentsYear || undefined
          }),
          examApi.getExamYears().catch(() => [] as number[])
        ]);
        
        setCourse(courseData);
        setExams(examsResponse.items);
        setExamsHasNext(examsResponse.pagination.has_next);
        setAvailableYears(years.sort((a, b) => b - a));
        
        const enrollmentItems = enrollmentsResponse?.items ?? [];
        setEnrollments(enrollmentItems);
        setEnrollmentsHasNext(enrollmentsResponse?.pagination?.has_next ?? false);
      } catch (err: unknown) {
        console.error('Failed to load data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load course details');
      } finally {
        setLoading(false);
        setExamsLoading(false);
        setEnrollmentsLoading(false);
      }
    };

    loadData();
  }, [id]);

  // Fetch exams when page params change (pagination, year filter)
  useEffect(() => {
    const fetchExams = async () => {
      if (!id) return;
      
      setExamsLoading(true);
      setExamsError(null);
      
      try {
        const response = await examApi.listExams({ 
          course_id: id,
          page: examsPage,
          per_page: examsPerPage,
          year: examsYear || undefined
        });
        setExams(response.items);
        setExamsHasNext(response.pagination.has_next);
      } catch (err: unknown) {
        console.error('Failed to fetch exams:', err);
        setExamsError(err instanceof Error ? err.message : 'Failed to load exams');
      } finally {
        setExamsLoading(false);
      }
    };

    // Skip initial load since data is already fetched in the main loadData effect
    if (examsPage > 1 || examsYear) {
      fetchExams();
    }
  }, [id, examsPage, examsYear]);

  // Fetch available years on mount
  useEffect(() => {
    examApi.getExamYears()
      .then(years => setAvailableYears(years.sort((a, b) => b - a)))
      .catch(() => setAvailableYears([]))
  }, []);

  // Fetch enrollments when pagination or filters change
  useEffect(() => {
    const fetchEnrollments = async () => {
      if (!id) return;
      
      setEnrollmentsLoading(true);
      try {
        const response = await enrollmentApi.getCourseEnrollment(id, { 
          page: enrollmentsPage, 
          per_page: enrollmentsPerPage,
          semester: enrollmentsSemester || undefined,
          year: enrollmentsYear || undefined
        });
        const items = response?.items ?? [];
        setEnrollments(items);
        setEnrollmentsHasNext(response?.pagination?.has_next ?? false);
      } catch (err: unknown) {
        console.error('Failed to fetch enrollments:', err);
        setEnrollments([]);
      } finally {
        setEnrollmentsLoading(false);
      }
    };

    // Skip initial load if on page 1 and no filters (already loaded in main effect)
    if (enrollmentsPage > 1 || enrollmentsSemester || enrollmentsYear) {
      fetchEnrollments();
    }
  }, [id, enrollmentsPage, enrollmentsSemester, enrollmentsYear]);

  // Fetch students list for enrollment dropdown — filter out already enrolled
  useEffect(() => {
    const fetchStudents = async () => {
      if (!isEnrollModalOpen) return;
      try {
        const response = await authApi.listUsers({ per_page: 100 });
        const enrolledIds = new Set(enrollments.map((e: Enrollment) => e.student.id))
        const studentList = response.items
          .filter((u: { role: string; id: string }) => u.role === 'student' && !enrolledIds.has(u.id))
          .map((u: { id: string; first_name: string; last_name: string; email: string }) => ({
            id: u.id,
            name: `${u.first_name} ${u.last_name}`,
            email: u.email,
          }))
        setStudents(studentList)
      } catch (err) {
        console.error('Failed to fetch students:', err)
      }
    }
    fetchStudents()
  }, [isEnrollModalOpen, enrollments])

  const handleDelete = async () => {
    if (!id || !course) return;

    setIsDeleting(true);
    try {
      await courseApi.deleteCourse(id);
      navigate('/courses', { replace: true });
    } catch (err: unknown) {
      console.error('Failed to delete course:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete course');
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const handleEnrollStudent = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !selectedStudentId) return

    setEnrollLoading(true)
    setEnrollError(null)
    setEnrollSuccess(null)

    try {
      await enrollmentApi.enrollStudent({
        student_id: selectedStudentId,
        course_id: id,
        semester: selectedSemester
      })

      setEnrollSuccess('Student enrolled successfully!')
      setSelectedStudentId('')

      // Refresh enrollments list with current filters
      const response = await enrollmentApi.getCourseEnrollment(id, { 
        page: enrollmentsPage, 
        per_page: enrollmentsPerPage,
        semester: enrollmentsSemester || undefined,
        year: enrollmentsYear || undefined
      })
      const items = response?.items ?? [];
      setEnrollments(items);
      setEnrollmentsHasNext(response?.pagination?.has_next ?? false);

      setTimeout(() => setEnrollSuccess(null), 3000)
    } catch (error: unknown) {
      console.error('Failed to enroll student:', error);
      // Extract error message from various possible locations
      let errorMessage = 'Failed to enroll student';

      if (error && typeof error === 'object' && 'response' in error) {
        const errResponse = (error as { response?: { data?: { detail?: string; error?: string; message?: string } } }).response;
        if (errResponse?.data?.detail) {
          // FastAPI HTTPException detail
          errorMessage = errResponse.data.detail;
        } else if (errResponse?.data?.error) {
          // Custom error field
          errorMessage = errResponse.data.error;
        } else if (errResponse?.data?.message) {
          // Standard message field
          errorMessage = errResponse.data.message;
        }
      } else if (error instanceof Error) {
        errorMessage = error.message;
      } else if (error && typeof error === 'object' && 'message' in error) {
        errorMessage = (error as { message: string }).message;
      }
      
      setEnrollError(errorMessage);
    } finally {
      setEnrollLoading(false)
    }
  }

  // Close enroll modal
  const closeEnrollModal = () => {
    setIsEnrollModalOpen(false);
    setSelectedStudentId('');
    setEnrollError(null);
    setEnrollSuccess(null);
  };

  const handleUnenrollStudent = async () => {
    if (!selectedEnrollmentId) return;
    
    setUnenrollLoading(selectedEnrollmentId);
    try {
      await enrollmentApi.removeEnrollment(selectedEnrollmentId);
      // Refresh enrollments list with current filters
      const response = await enrollmentApi.getCourseEnrollment(id!, { 
        page: enrollmentsPage, 
        per_page: enrollmentsPerPage,
        semester: enrollmentsSemester || undefined,
        year: enrollmentsYear || undefined
      });
      const items = response?.items ?? [];
      setEnrollments(items);
      setEnrollmentsHasNext(response?.pagination?.has_next ?? false);
      setShowUnenrollConfirm(false);
      setSelectedEnrollmentId(null);
    } catch (err: unknown) {
      console.error('Failed to unenroll student:', err);
      alert(err instanceof Error ? err.message : 'Failed to unenroll student');
    } finally {
      setUnenrollLoading(null);
    }
  };

  const openFilterModal = () => {
    setTempFilterSemester(enrollmentsSemester);
    setTempFilterYear(enrollmentsYear);
    setIsFilterModalOpen(true);
  };

  const closeFilterModal = () => {
    setIsFilterModalOpen(false);
  };

  const applyFilters = () => {
    setEnrollmentsSemester(tempFilterSemester);
    setEnrollmentsYear(tempFilterYear);
    setEnrollmentsPage(1);
    setIsFilterModalOpen(false);
  };

  const clearFilters = () => {
    setTempFilterSemester('');
    setTempFilterYear('');
    setEnrollmentsSemester('');
    setEnrollmentsYear('');
    setEnrollmentsPage(1);
    setIsFilterModalOpen(false);
  };

  const openUnenrollConfirm = (enrollmentId: string) => {
    setSelectedEnrollmentId(enrollmentId);
    setShowUnenrollConfirm(true);
  };

  const canEdit = user?.role === 'admin' || (user?.role === 'lecturer' && course?.lecturer?.id === user?.id);
  const canDelete = user?.role === 'admin' || (user?.role === 'lecturer' && course?.lecturer?.id === user?.id);

  if (loading) {
    return <CourseDetailSkeleton />;
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <Breadcrumbs />
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-8"
        >
          <EmptyState
            icon={AlertCircle}
            title="Failed to Load Course"
            description={error}
            action={{
              label: 'Try Again',
              onClick: () => window.location.reload()
            }}
          />
        </motion.div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="max-w-4xl mx-auto">
        <Breadcrumbs />
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-8"
        >
          <EmptyState
            icon={BookOpen}
            title="Course Not Found"
            description="The course you're looking for doesn't exist or has been removed."
            action={{
              label: 'Back to Courses',
              onClick: () => navigate('/courses')
            }}
          />
        </motion.div>
      </div>
    );
  }

  // Tab content components
  const OverviewContent = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-4">Course Details</h3>
          <dl className="space-y-3">
            <div className="flex justify-between py-2 border-b border-[var(--color-border-light)]">
              <dt className="text-sm text-[var(--color-text-muted)]">Course Code</dt>
              <dd className="text-sm font-medium text-[var(--color-text-primary)]">{course.course_code}</dd>
            </div>
            <div className="flex justify-between py-2 border-b border-[var(--color-border-light)]">
              <dt className="text-sm text-[var(--color-text-muted)]">Created</dt>
              <dd className="text-sm font-medium text-[var(--color-text-primary)]">{formatDate(course.created_at)}</dd>
            </div>
            <div className="flex justify-between py-2 border-b border-[var(--color-border-light)]">
              <dt className="text-sm text-[var(--color-text-muted)]">Last Updated</dt>
              <dd className="text-sm font-medium text-[var(--color-text-primary)]">{formatDate(course.updated_at)}</dd>
            </div>
            <div className="flex justify-between py-2">
              <dt className="text-sm text-[var(--color-text-muted)]">Instructor</dt>
              <dd className="text-sm font-medium text-[var(--color-text-primary)]">{course.lecturer ? `${course.lecturer.first_name} ${course.lecturer.last_name}` : 'No lecturer assigned'}</dd>
            </div>
          </dl>
        </div>
        
        <div>
          <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <button 
              onClick={() => setActiveTab('exams')}
              className="w-full flex items-center justify-between p-3 rounded-lg border border-[var(--color-border-light)] hover:border-[var(--color-accent-coral-400)] hover:bg-[var(--color-accent-coral-50)]/30 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-[var(--color-accent-coral-50)]/50 flex items-center justify-center group-hover:bg-[var(--color-accent-coral-100)]/50 transition-colors">
                  <Icon as={FileText} size={18} className="text-[var(--color-accent-coral-500)]" />
                </div>
                <div className="text-left">
                  <p className="font-medium text-[var(--color-text-primary)]">Manage Exams</p>
                  <p className="text-sm text-[var(--color-text-muted)]">Create and manage course exams</p>
                </div>
              </div>
              <Icon as={ChevronRight} size={18} className="text-[var(--color-text-muted)]" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const ExamsContent = () => {
    if (examsLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-primary-600)]"></div>
          <span className="ml-3 text-[var(--color-text-secondary)]">Loading exams...</span>
        </div>
      );
    }

    if (examsError) {
      return (
        <div className="p-4 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg">
          <p className="text-[var(--color-error-600)]">{examsError}</p>
        </div>
      );
    }

    if (exams.length === 0) {
      return (
        <EmptyState
          icon={FileText}
          title="No Exams Yet"
          description="Exams will appear here once they are created for this course."
          action={canEdit ? {
            label: 'Create Exam',
            onClick: () => navigate(`/courses/${course.id}/exams/create`)
          } : undefined}
        />
      );
    }

    return (
      <div className="space-y-4">
        {/* Year Filter */}
        <div className="flex items-center gap-4 mb-4">
          <div className="w-48">
            <Dropdown
              options={[
                { value: '', label: 'All Years' },
                ...availableYears.map(y => ({ value: y.toString(), label: y.toString() }))
              ]}
              value={examsYear?.toString() || ''}
              onChange={(value) => setExamsYear(value ? parseInt(value) : '')}
              placeholder="Filter by year..."
            />
          </div>
        </div>
        {exams.map((exam) => (
          <Card key={exam.id} className="p-4 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h3 className="font-semibold text-[var(--color-text-primary)]">{exam.title}</h3>
                <p className="text-sm text-[var(--color-text-muted)] mt-1">
                  Duration: {exam.duration_hours}h {exam.duration_minutes}m • {exam.total_marks} marks
                </p>
                {exam.start_time && (
                  <p className="text-sm text-[var(--color-text-muted)]">
                    Starts: {new Date(exam.start_time).toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true })}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="coral"
                  onClick={() => navigate(`/exams/${exam.id}`)}
                >
                  View
                </Button>
                {canEdit && (
                  <Button
                    variant="ghost"
                    onClick={() => navigate(`/exams/${exam.id}/edit`)}
                  >
                    <Icon as={Edit} size={16} />
                  </Button>
                )}
              </div>
            </div>
          </Card>
        ))}
        
        {/* Pagination */}
        {(examsHasNext || examsPage > 1) && (
          <div className="mt-6">
            <Pagination
              currentPage={examsPage}
              hasNext={examsHasNext}
              hasPrev={examsPage > 1}
              onNext={() => setExamsPage(p => p + 1)}
              onPrev={() => setExamsPage(p => Math.max(1, p - 1))}
            />
          </div>
        )}
      </div>
    );
  };

  const StudentsContent = () => {
    if (enrollmentsLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-primary-600)]"></div>
          <span className="ml-3 text-[var(--color-text-secondary)]">Loading students...</span>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {/* Filters and Add Students Button */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div className="flex flex-wrap items-center gap-4">
            {/* Filters Button with Active Filter Badges */}
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                onClick={openFilterModal}
                className="flex items-center gap-2"
              >
                <Icon as={Filter} size={16} />
                Filters
                {(enrollmentsSemester || enrollmentsYear) && (
                  <span className="ml-1 px-1.5 py-0.5 bg-[var(--color-primary-100)] text-[var(--color-primary-700)] text-xs rounded-full">
                    {[enrollmentsSemester, enrollmentsYear].filter(Boolean).length}
                  </span>
                )}
              </Button>
              
              {/* Active Filter Chips */}
              {enrollmentsSemester && (
                <span className="inline-flex items-center gap-1 px-2 py-1 bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] text-sm rounded-lg">
                  Semester: <span className="capitalize font-medium">{enrollmentsSemester}</span>
                  <button 
                    onClick={() => { setEnrollmentsSemester(''); setEnrollmentsPage(1); }}
                    className="ml-1 text-[var(--color-text-muted)] hover:text-[var(--color-error-600)]"
                  >
                    <Icon as={X} size={14} />
                  </button>
                </span>
              )}
              {enrollmentsYear && (
                <span className="inline-flex items-center gap-1 px-2 py-1 bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] text-sm rounded-lg">
                  Year: <span className="font-medium">{enrollmentsYear}</span>
                  <button 
                    onClick={() => { setEnrollmentsYear(''); setEnrollmentsPage(1); }}
                    className="ml-1 text-[var(--color-text-muted)] hover:text-[var(--color-error-600)]"
                  >
                    <Icon as={X} size={14} />
                  </button>
                </span>
              )}
            </div>
          </div>
          {(user?.role === 'lecturer' || user?.role === 'admin') && (
            <Button
              variant="primary"
              onClick={() => setIsEnrollModalOpen(true)}
              className="flex items-center gap-2"
            >
              <Icon as={UserPlus} size={16} />
              Add Students
            </Button>
          )}
        </div>

        {enrollments?.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No Students Enrolled"
            description="No students are currently enrolled in this course."
            action={(user?.role === 'lecturer' || user?.role === 'admin') ? {
              label: 'Add Students',
              onClick: () => setIsEnrollModalOpen(true)
            } : undefined}
          />
        ) : (
          <div className="space-y-3">
            {(Array.isArray(enrollments) ? enrollments : []).map((enrollment) => (
              <Card key={enrollment.id} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-[var(--color-primary-50)] flex items-center justify-center">
                      <Icon as={Users} size={18} className="text-[var(--color-primary-600)]" />
                    </div>
                    <div>
                      <p className="font-medium text-[var(--color-text-primary)]">
                        {enrollment.student ? `${enrollment.student.first_name} ${enrollment.student.last_name}` : 'Unknown Student'}
                      </p>
                      {enrollment.student?.institution_id ? (
                        <p className="text-sm text-[var(--color-text-muted)]">
                          Matric/Reg No: <span className="font-medium text-[var(--color-primary-600)]">{enrollment.student.institution_id}</span>
                        </p>
                      ) : (
                        <p className="text-sm text-[var(--color-text-muted)]">
                          Matric/Reg No: <span className="text-[var(--color-text-muted)] italic">-</span>
                        </p>
                      )}
                      <p className="text-sm text-[var(--color-text-muted)]">
                        Status: <span className={`capitalize ${enrollment.status === 'active' ? 'text-[var(--color-success-600)]' : 'text-[var(--color-text-secondary)]'}`}>{enrollment.status}</span>
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <p className="text-sm text-[var(--color-text-muted)]">
                      Enrolled: {formatDate(enrollment.created_at)}
                    </p>
                    {(user?.role === 'lecturer' || user?.role === 'admin') && (
                      <Button
                        variant="ghost"
                        onClick={() => openUnenrollConfirm(enrollment.id)}
                        loading={unenrollLoading === enrollment.id}
                        disabled={unenrollLoading === enrollment.id}
                        className="text-[var(--color-error-600)] hover:bg-[var(--color-error-50)] p-2"
                      >
                        <Icon as={Trash2} size={16} />
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            ))}
            
            {/* Pagination */}
            {(enrollmentsHasNext || enrollmentsPage > 1) && (
              <div className="mt-6">
                <Pagination
                  currentPage={enrollmentsPage}
                  hasNext={enrollmentsHasNext}
                  hasPrev={enrollmentsPage > 1}
                  onNext={() => setEnrollmentsPage(p => p + 1)}
                  onPrev={() => setEnrollmentsPage(p => Math.max(1, p - 1))}
                />
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BookOpen, content: <OverviewContent /> },
    { id: 'exams', label: 'Exams', icon: FileText, content: <ExamsContent /> },
    ...(user?.role !== 'student' ? [{ id: 'students', label: 'Students', icon: Users, content: <StudentsContent /> }] : []),
  ];

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header with Breadcrumbs and Actions */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6"
      >
        <div className="flex items-center gap-3">
          <Breadcrumbs />
        </div>
        
        <div className="flex items-center gap-2">
          {canEdit && (
            <Button
              variant="secondary"
              onClick={() => navigate(`/courses/${course.id}/edit`)}
              className="flex items-center gap-2"
            >
              <Icon as={Edit} size={16} />
              Edit Course
            </Button>
          )}
          {canDelete && (
            <Button
              variant="danger"
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-2"
            >
              <Icon as={Trash2} size={16} />
              Delete
            </Button>
          )}
        </div>
      </motion.div>

      {/* Course Hero Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="bg-[var(--color-bg-card)] rounded-2xl shadow-lg border border-[var(--color-border-light)] overflow-hidden mb-6"
      >
        {/* Hero Header with Gradient */}
        <div className="relative bg-gradient-to-br from-[var(--color-primary-600)] via-[var(--color-primary-600)] to-[var(--color-primary-700)] px-6 py-8 md:px-8 md:py-10">
          <div className="absolute inset-0 opacity-10">
            <div className="absolute inset-0" style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
            }} />
          </div>
          
          <div className="relative z-10">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
              <div className="flex-1">
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                  className="inline-flex items-center px-3 py-1 bg-[var(--color-bg-card)]/20 backdrop-blur-sm text-white text-sm font-semibold rounded-full mb-4"
                >
                  <Icon as={BookOpen} size={14} className="mr-2" />
                  {course.course_code}
                </motion.div>
                
                <motion.h1
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="text-3xl md:text-4xl font-bold text-white mb-3"
                >
                  {course.name}
                </motion.h1>
                
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.4 }}
                  className="flex flex-wrap items-center gap-4 text-white/80 text-sm"
                >
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-[var(--color-bg-card)]/20 flex items-center justify-center">
                      <Icon as={GraduationCap} size={14} className="text-white" />
                    </div>
                    <div>
                      <p className="text-white/75 text-xs">Instructor</p>
                      <p className="text-white font-medium">{course.lecturer ? `${course.lecturer.first_name} ${course.lecturer.last_name}` : 'No lecturer assigned'}</p>
                    </div>
                  </div>
                  
                  {user?.role !== 'student' && (
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-[var(--color-bg-card)]/20 flex items-center justify-center">
                        <Icon as={Calendar} size={14} className="text-white" />
                      </div>
                      <div>
                        <p className="text-white/75 text-xs">Created</p>
                        <p className="text-white font-medium">{formatDate(course.created_at)}</p>
                      </div>
                    </div>
                  )}
                </motion.div>
              </div>
              
              {/* Status Badge */}
              {/* <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.5 }}
                className="flex items-center gap-2 px-4 py-2 bg-[var(--color-bg-card)]/10 backdrop-blur-sm rounded-lg"
              >
                <div className="w-2 h-2 rounded-full bg-[var(--color-success-500)] animate-pulse" />
                <span className="text-white text-sm font-medium">Active</span>
              </motion.div> */}
            </div>
          </div>
        </div>
        
        {/* Course Description */}
        <div className="p-6 md:p-8">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            <h2 className="text-sm font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
              About This Course
            </h2>
            <p className="text-[var(--color-text-secondary)] leading-relaxed">
              {course.description || 'No description available for this course.'}
            </p>
          </motion.div>
        </div>
      </motion.div>

      {/* Stats Grid - Hidden for students */}
      {user?.role !== 'student' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="grid grid-cols-2 md:grid-cols-2 gap-4 mb-6"
        >
          {[
            { label: 'Exams', value: (exams?.length ?? 0).toString(), icon: FileText, color: 'indigo' },
            { label: 'Students', value: (enrollments?.length ?? 0).toString(), icon: Users, color: 'emerald' },
          ].map((stat, idx) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + idx * 0.1 }}
            >
              <Card className="p-4 hover:shadow-md transition-shadow">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl bg-${stat.color}-50 flex items-center justify-center`}>
                    <Icon as={stat.icon} size={20} className={`text-${stat.color}-600`} />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-[var(--color-text-primary)]">{stat.value}</p>
                    <p className="text-sm text-[var(--color-text-muted)]">{stat.label}</p>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
      </motion.div>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {showDeleteConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowDeleteConfirm(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-[var(--color-bg-card)] rounded-xl shadow-xl max-w-md w-full p-6"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-[var(--color-error-100)] flex items-center justify-center">
                  <Icon as={AlertCircle} size={20} className="text-[var(--color-error-600)]" />
                </div>
                <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Delete Course?</h3>
              </div>
              
              <p className="text-[var(--color-text-secondary)] mb-6">
                Are you sure you want to delete <strong>{course.name}</strong>? This action cannot be undone and all associated data will be permanently removed.
              </p>
              
              <div className="flex gap-3">
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={isDeleting}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  className="flex-1"
                  onClick={handleDelete}
                  loading={isDeleting}
                >
                  Delete Course
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Enroll Student Modal */}
      <Modal
        isOpen={isEnrollModalOpen}
        onClose={closeEnrollModal}
        title={`Add Students to ${course?.name || 'Course'}`}
      >
        <form onSubmit={handleEnrollStudent} className="space-y-4">
          {enrollError && (
            <div className="p-3 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg">
              <p className="text-sm text-[var(--color-error-600)]">{enrollError}</p>
            </div>
          )}
          {enrollSuccess && (
            <div className="p-3 bg-[var(--color-success-100)] border border-[var(--color-success-100)] rounded-lg">
              <p className="text-sm text-[var(--color-success-600)]">{enrollSuccess}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Select Student *
            </label>
            {students.filter((s: { id: string }) => !(Array.isArray(enrollments) ? enrollments : []).some(e => e.student.id === s.id)).length === 0 ? (
              <div className="p-3 bg-[var(--color-bg-hover)] rounded-lg text-sm text-[var(--color-text-muted)] text-center">
                All students in this institution are already enrolled in this course.
              </div>
            ) : (
              <Dropdown
                options={students
                  .filter((s: { id: string }) => !(Array.isArray(enrollments) ? enrollments : []).some(e => e.student.id === s.id))
                  .map((s: { id: string; name: string; email: string; institution_id?: string }) => ({
                    value: s.id,
                    label: s.institution_id
                      ? `${s.name} (${s.institution_id})`
                      : s.name,
                    subtitle: s.email,
                  }))}
                value={selectedStudentId}
                onChange={setSelectedStudentId}
                searchable={true}
                placeholder="Search students..."
                className="w-full"
              />
            )}
          </div>

          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Semester *
              </label>
              <Dropdown
                options={[
                  { value: 'fall', label: 'Fall' },
                  { value: 'spring', label: 'Spring' },
                  { value: 'summer', label: 'Summer' },
                  { value: 'winter', label: 'Winter' },
                  { value: 'interim', label: 'Interim' },
                  { value: 'first', label: 'First' },
                  { value: 'second', label: 'Second' },
                  { value: 'third', label: 'Third' },
                  { value: 'fourth', label: 'Fourth' },
                  { value: 'fifth', label: 'Fifth' },
                  { value: 'sixth', label: 'Sixth' },
                  { value: 'seventh', label: 'Seventh' },
                  { value: 'eighth', label: 'Eighth' }
                ]}
                value={selectedSemester}
                onChange={(value) => setSelectedSemester(value as Semester)}
                placeholder="Select semester..."
                className="w-full"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <Button 
              variant="secondary" 
              className="flex-1" 
              type="button" 
              onClick={closeEnrollModal}
              disabled={enrollLoading}
            >
              Close
            </Button>
            <Button 
              className="flex-1" 
              type="submit"
              loading={enrollLoading}
              disabled={!selectedStudentId || students.filter((s: { id: string }) => !(Array.isArray(enrollments) ? enrollments : []).some(e => e.student.id === s.id)).length === 0}
            >
              Enroll Student
            </Button>
          </div>
        </form>
      </Modal>

      {/* Unenroll Confirmation Modal */}
      <AnimatePresence>
        {showUnenrollConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowUnenrollConfirm(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-[var(--color-bg-card)] rounded-xl shadow-xl max-w-md w-full p-6"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-[var(--color-error-100)] flex items-center justify-center">
                  <Icon as={AlertCircle} size={20} className="text-[var(--color-error-600)]" />
                </div>
                <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Unenroll Student?</h3>
              </div>
              
              <p className="text-[var(--color-text-secondary)] mb-6">
                Are you sure you want to unenroll this student from the course? This action cannot be undone.
              </p>
              
              <div className="flex gap-3">
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => setShowUnenrollConfirm(false)}
                  disabled={!!unenrollLoading}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  className="flex-1"
                  onClick={handleUnenrollStudent}
                  loading={!!unenrollLoading}
                >
                  Unenroll
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Filter Modal */}
      <AnimatePresence>
        {isFilterModalOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            onClick={closeFilterModal}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-[var(--color-bg-card)] rounded-xl shadow-xl max-w-md w-full p-6"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-full bg-[var(--color-primary-100)] flex items-center justify-center">
                  <Icon as={Filter} size={20} className="text-[var(--color-primary-600)]" />
                </div>
                <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Filter Students</h3>
              </div>
              
              <div className="space-y-4 mb-6">
                {/* Semester Filter */}
                <div>
                  <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                    Semester
                  </label>
                  <Dropdown
                    options={[
                      { value: '', label: 'All Semesters' },
                      { value: 'fall', label: 'Fall' },
                      { value: 'spring', label: 'Spring' },
                      { value: 'summer', label: 'Summer' },
                      { value: 'winter', label: 'Winter' },
                      { value: 'interim', label: 'Interim' },
                      { value: 'first', label: 'First' },
                      { value: 'second', label: 'Second' },
                      { value: 'third', label: 'Third' },
                      { value: 'fourth', label: 'Fourth' },
                      { value: 'fifth', label: 'Fifth' },
                      { value: 'sixth', label: 'Sixth' },
                      { value: 'seventh', label: 'Seventh' },
                      { value: 'eighth', label: 'Eighth' }
                    ]}
                    value={tempFilterSemester}
                    onChange={(value) => setTempFilterSemester(value as Semester | '')}
                    placeholder="Select semester..."
                    className="w-full"
                  />
                </div>

                {/* Year Filter */}
                <div>
                  <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                    Year
                  </label>
                  <Dropdown
                    options={[
                      { value: '', label: 'All Years' },
                      ...availableYears.map(y => ({ value: y.toString(), label: y.toString() }))
                    ]}
                    value={tempFilterYear?.toString() || ''}
                    onChange={(value) => setTempFilterYear(value ? parseInt(value) : '')}
                    placeholder="Select year..."
                    className="w-full"
                  />
                </div>
              </div>
              
              <div className="flex gap-3">
                <Button
                  variant="ghost"
                  className="flex-1"
                  onClick={clearFilters}
                  disabled={!tempFilterSemester && !tempFilterYear}
                >
                  Clear All
                </Button>
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={closeFilterModal}
                >
                  Cancel
                </Button>
                <Button
                  className="flex-1"
                  onClick={applyFilters}
                >
                  Apply
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default CourseDetail;
