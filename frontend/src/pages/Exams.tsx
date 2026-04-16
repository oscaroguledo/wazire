import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Plus, Edit, Trash2, Upload, Clock, Calendar, FileText, AlertCircle } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import Icon from '@/components/Icon';
import { useAuth } from '@/contexts/AuthContext';
import * as examApi from '@/apis/exam';
import * as courseApi from '@/apis/course';
import * as enrollmentApi from '@/apis/enrollment';
import type { Exam, ExamListParams } from '@/apis/exam';
import type { Enrollment } from '@/apis/enrollment';
import { errorTracker } from '@/utils/errorTracking';
import Breadcrumbs from '@/components/Breadcrumbs';
import { StatusBadge } from '@/components/StatusBadge';
import { Modal } from '@/components/Modal';
import Input from '@/components/Input';
import SearchInput from '@/components/SearchInput';
import Dropdown from '@/components/Dropdown';
import Button from '@/components/Button';
import { config } from '@/config';
import { EmptyState } from '@/components/EmptyState';
import DateTimePicker from '@/components/DateTimePicker';
import ExamsSkeleton from './ExamsSkeleton';
import Pagination from '@/components/Pagination';

export function Exams() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);
  
  // Form state for creating exam
  const [createFormData, setCreateFormData] = useState({
    title: '',
    courseId: '',
    durationHours: '',
    durationMinutes: 0,
    description: '',
    totalMarks: '',
    passingMarks: '',
    startTime: '',
  });
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Delete modal state
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [examToDelete, setExamToDelete] = useState<Exam | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Fetch student enrollments first (for student role filtering)
  const { data: enrollmentsData } = useQuery({
    queryKey: ['student-enrollments', user?.id],
    queryFn: async () => {
      if (user?.role !== 'student') return [];
      const response = await enrollmentApi.getStudentEnrollment(user.id);
      return Array.isArray(response) ? response : response.items;
    },
    enabled: !!user && user.role === 'student',
    staleTime: config.QUERY_CACHE_STATIC, // 5 minutes - exams are relatively static
  });

  const enrolledCourseIds = enrollmentsData?.map((e: Enrollment) => e.course_id) || [];

  // React Query hook for fetching exams and courses in parallel using Promise.all
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['exams-and-courses', currentPage, pageSize, searchQuery, selectedCourse, selectedStatus, user?.tenant_id, user?.role, enrolledCourseIds],
    queryFn: async () => {
      // Fetch both exams and courses in parallel
      const [examsResult, coursesResponse] = await Promise.all([
        (async () => {
          const params: ExamListParams = {
            page: currentPage,
            per_page: pageSize,
            search: searchQuery || undefined,
            course_id: selectedCourse || undefined,
            status: selectedStatus && selectedStatus !== 'all' ? selectedStatus as Exam['status'] : undefined,
            // tenant_id sent for non-admin users; backend handles lecturer filtering server-side
            tenant_id: user?.role !== 'admin' ? (user?.tenant_id || undefined) : undefined,
          }
          const result = await examApi.listExams(params);
          
          // For students, filter exams to only show those for enrolled courses
          if (user?.role === 'student' && enrolledCourseIds.length > 0) {
            const filteredItems = result.items.filter((exam: Exam) => 
              exam.course && enrolledCourseIds.includes(exam.course.id)
            );
            return {
              ...result,
              items: filteredItems,
              pagination: {
                ...result.pagination,
                total: filteredItems.length,
                pages: Math.ceil(filteredItems.length / pageSize),
                has_next: currentPage < Math.ceil(filteredItems.length / pageSize),
              }
            };
          }
          
          return result;
        })(),
        (async () => {
          const response = await courseApi.listCourses({
            per_page: 100,
            tenant_id: user?.tenant_id || undefined,
          })
          return response.items
        })()
      ]);

      return {
        exams: examsResult,
        courses: coursesResponse
      };
    },
    enabled: !!user && (user.role !== 'student' || enrolledCourseIds.length > 0),
    staleTime: config.QUERY_CACHE_STATIC, // 5 minutes - exams are relatively static
  });

  const exams = data?.exams?.items || [];
  console.log(exams,'-----')
  const pagination = data?.exams?.pagination || {
    page: 1,
    per_page: pageSize,
    total: 0,
    pages: 0,
    has_next: false,
    has_prev: false
  };
  const loading = isLoading;
  const initialLoading = isLoading;
  const courses = data?.courses || [];

  // Handle exam creation
  const handleCreateExam = (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    setCreateError(null);

    const examData = {
      title: createFormData.title,
      course_id: createFormData.courseId,
      duration_hours: parseInt(createFormData.durationHours),
      duration_minutes: parseInt(createFormData.durationMinutes.toString()) || 0,
      description: createFormData.description,
      total_marks: createFormData.totalMarks ? parseInt(createFormData.totalMarks) : undefined,
      passing_marks: createFormData.passingMarks ? parseInt(createFormData.passingMarks) : undefined,
      start_time: createFormData.startTime || undefined,
    };

    examApi.createExam(examData)
      .then(() => {
        // Reset form and close modal
        setCreateFormData({
          title: '',
          courseId: '',
          durationHours: '',
          durationMinutes: 0,
          description: '',
          totalMarks: '',
          passingMarks: '',
          startTime: '',
        });
        setIsCreateModalOpen(false);
        // Refresh exams list
        refetch();
      })
      .catch((err: unknown) => {
        if (err instanceof Error) {
          errorTracker.track(err, { action: 'create_exam', component: 'Exams' });
        }
        setCreateError(err instanceof Error ? err.message : 'Failed to create exam');
      })
      .finally(() => {
        setCreateLoading(false);
      });
  };

  // Handle form input changes
  const handleCreateFormChange = (field: string, value: string) => {
    setCreateFormData(prev => ({ ...prev, [field]: value }));
    setCreateError(null);
  };

  // Handle next page
  const handleNextPage = () => {
    if (pagination.has_next) {
      setCurrentPage(prev => prev + 1);
    }
  };

  // Handle previous page
  const handlePrevPage = () => {
    if (pagination.has_prev && currentPage > 1) {
      setCurrentPage(prev => prev - 1);
    }
  };

  // Handle page change
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // Handle exam deletion
  const handleDeleteExam = async () => {
    if (!examToDelete) return;
    
    setDeleteLoading(true);
    setDeleteError(null);
    
    try {
      await examApi.deleteExam(examToDelete.id);
      setIsDeleteModalOpen(false);
      setExamToDelete(null);
      
      // Refresh exams list
      refetch();
    } catch (err: unknown) {
      if (err instanceof Error) {
        errorTracker.track(err, { action: 'delete_exam', component: 'Exams' });
      }
      setDeleteError(err instanceof Error ? err.message : 'Failed to delete exam');
    } finally {
      setDeleteLoading(false);
    }
  };

  const closeDeleteModal = () => {
    setIsDeleteModalOpen(false);
    setExamToDelete(null);
    setDeleteError(null);
  };

  // Handle delete modal
  const openDeleteModal = (exam: Exam) => {
    setExamToDelete(exam);
    setDeleteError(null);
    setIsDeleteModalOpen(true);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <Breadcrumbs />
        {(user?.role === 'lecturer' || user?.role === 'admin') && (
          <div className="flex gap-3">
            <Button 
              variant="primary" 
              className="flex items-center gap-2 px-4 py-2" 
              onClick={() => setIsCreateModalOpen(true)}
            >
              <Icon as={Plus} size={18} />
              Create Exam
            </Button>
          </div>
        )}
      </div>

      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <SearchInput
          value={searchInput}
          onChange={setSearchInput}
          onSearch={(value) => {
            setSearchQuery(value);
            setCurrentPage(1);
          }}
          placeholder="Search exams..."
          disabled={loading}
          className="flex-1 max-w-md"
        />
        
        {/* Course Filter Dropdown */}
        <Dropdown
            options={[
              { value: '', label: 'All Courses' },
              ...courses.map(c => ({ value: c.id, label: c.name }))
            ]}
            value={selectedCourse}
            onChange={(value) => setSelectedCourse(value)}
            placeholder="Filter by course..."
            searchable={true}
            showClearButton={false}
            className='w-full sm:w-64'
          />
        
        {/* Status Filter Dropdown */}
        <Dropdown
          options={[
            { value: 'all', label: 'All Status' },
            { value: 'not_started', label: 'Not Started' },
            { value: 'in_progress', label: 'In Progress' },
            { value: 'finished', label: 'Finished' }
          ]}
          value={selectedStatus}
          onChange={(value) => setSelectedStatus(value)}
          placeholder="Filter by status..."
          className='w-full sm:w-40'
        />
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-6 p-4 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg">
          <div className="flex items-center gap-2">
            <Icon as={AlertCircle} size={16} className="text-[var(--color-error-600)]" />
            <p className="text-sm text-[var(--color-error-600)]">{error.message || 'Failed to load exams'}</p>
          </div>
          <Button 
            variant="ghost" 
            onClick={() => refetch()}
            className="mt-2"
          >
            Try Again
          </Button>
        </div>
      )}

      {/* Loading state - show skeleton during initial load or when loading */}
      {(initialLoading || loading) && <ExamsSkeleton />}

      {/* Empty state */}
      {!loading && !error && exams.length === 0 && (
        <EmptyState
          icon={FileText}
          title="No Exams Available"
          description={
            searchQuery 
              ? "No exams found matching your search. Try different keywords."
              : "No exams have been created yet. Start by creating your first exam."
          }
          action={
            (user?.role === 'lecturer' || user?.role === 'admin') ? {
              label: "Create Exam",
              onClick: () => setIsCreateModalOpen(true)
            } : {
              label: "Browse Available Courses",
              onClick: () => navigate('/courses')
            }
          }
        />
      )}

      {/* Exams list */}
      {!loading && !error && exams.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {exams.map((exam: Exam, idx: number) => (
            <motion.div
              key={exam.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className="cursor-pointer group"
            >
              <div className="surface-card h-full overflow-hidden group cursor-pointer hover:shadow-[var(--shadow-lg)] hover:-translate-y-0.5 transition-all duration-200">
                {/* Main clickable area */}
                <div 
                  onClick={() => navigate(`/exams/${exam.id}`)}
                  className="flex-1 cursor-pointer"
                >
                  <div className="p-6 pb-4">
                    {/* Header with icon and status */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="bg-[var(--color-primary-50)] p-3 rounded-xl group-hover:bg-[var(--color-primary-100)] transition-all duration-300">
                        <Icon as={FileText} size={24} className="text-[var(--color-primary-600)]" />
                      </div>
                      <StatusBadge status={exam.status} />
                    </div>

                    {/* Exam title and course */}
                    <h3 className="text-lg font-bold text-[var(--color-text-primary)] mb-2 group-hover:text-[var(--color-primary-600)] transition-colors line-clamp-2">
                      {exam.title}
                    </h3>
                    <p className="text-sm text-[var(--color-text-secondary)] mb-4 line-clamp-1">
                      {exam.course?.name || 'No course assigned'}
                    </p>

                    {/* Exam info */}
                    <div className="flex items-center gap-4 mb-4 text-sm text-[var(--color-text-secondary)] flex-wrap">
                      <div className="flex items-center gap-1">
                        <Icon as={Clock} size={14} />
                        <span>{exam.duration_hours}h {exam.duration_minutes}m</span>
                      </div>
                      {exam.start_time && (
                        <div className="flex items-center gap-1">
                          <Icon as={Calendar} size={14} />
                          <span>{new Date(exam.start_time).toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true })}</span>
                        </div>
                      )}
                      <div className="flex items-center gap-1">
                        <span>{exam.total_marks || 0} marks</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Footer with actions */}
                <div className="px-4 py-3 bg-[var(--color-bg-hover)] border-t border-[var(--color-border-light)]">
                  <div className="flex items-center justify-end gap-2">
                    {user?.role === 'student' && exam.status === 'in_progress' && (
                      <Button 
                        variant="primary" 
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/exams/${exam.id}/take`);
                        }}
                        className="px-3 py-1.5 text-xs"
                      >
                        Take Exam
                      </Button>
                    )}
                    {(user?.role === 'lecturer' || user?.role === 'admin') && exam.status !== 'finished' && (
                      <>
                        <Button 
                          variant="secondary" 
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/exams/${exam.id}/edit`);
                          }}
                          className="px-3 py-1.5 text-xs"
                        >
                          <Icon as={Edit} size={12} className="mr-1" />
                          Edit
                        </Button>
                        <Button 
                          variant="danger" 
                          onClick={(e) => {
                            e.stopPropagation();
                            openDeleteModal(exam);
                          }}
                          className="px-3 py-1.5 text-xs"
                        >
                          <Icon as={Trash2} size={12} className="mr-1" />
                          Delete
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && !error && exams.length > 0 && (
        <div className="mt-6">
          <Pagination
            currentPage={currentPage}
            totalPages={pagination.pages || 1}
            hasNext={pagination.has_next}
            hasPrev={pagination.has_prev}
            onNext={handleNextPage}
            onPrev={handlePrevPage}
            onPageChange={handlePageChange}
          />
        </div>
      )}

      {/* Create Exam Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          setCreateFormData({
            title: '',
            courseId: '',
            durationHours: '',
            durationMinutes: 0,
            description: '',
            totalMarks: '',
            passingMarks: '',
            startTime: ''
          });
          setSelectedCourse('');
          setCreateError(null);
        }}
        title="Create New Exam">
        
        <form onSubmit={handleCreateExam} className="space-y-4">
          {createError && (
            <div className="p-3 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg">
              <p className="text-sm text-[var(--color-error-600)]">{createError}</p>
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Exam Title *
            </label>
            <Input 
              type="text" 
              placeholder="Midterm Exam - Data Structures"
              value={createFormData.title}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleCreateFormChange('title', e.target.value)}
              required
              disabled={createLoading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Course *
            </label>
            <Dropdown
              options={courses.map(course => ({
                value: course.id,
                label: `${course.name} (${course.course_code})`,
                subtitle: course.course_code
              }))}
              value={createFormData.courseId}
              onChange={(v) => {
                handleCreateFormChange('courseId', v);
                setSelectedCourse(v);
              }}
              searchable={true}
              placeholder="Search courses..."
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Start Time
            </label>
            <DateTimePicker
              value={createFormData.startTime}
              onChange={(value) => handleCreateFormChange('startTime', value)}
              disabled={createLoading}
              placeholder="Date/time"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Duration (hours) *
              </label>
              <Input
                type="number"
                min="1"
                max="24"
                value={createFormData.durationHours}
                onChange={(e) => handleCreateFormChange('durationHours', e.target.value)}
                disabled={createLoading}
                placeholder="Hours"
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Duration (minutes)
              </label>
              <Input
                type="number"
                value={createFormData.durationMinutes}
                onChange={(e) => handleCreateFormChange('durationMinutes', e.target.value)}
                disabled={createLoading}
                placeholder="Minutes"
                min="0"
                max="59"
                className="w-full"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Total Marks
              </label>
              <Input
                type="number"
                value={createFormData.totalMarks}
                onChange={(e) => handleCreateFormChange('totalMarks', e.target.value)}
                disabled={createLoading}
                placeholder="Optional"
                min="0"
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Passing Marks
              </label>
              <Input
                type="number"
                value={createFormData.passingMarks}
                onChange={(e) => handleCreateFormChange('passingMarks', e.target.value)}
                disabled={createLoading}
                placeholder="Optional"
                min="0"
                className="w-full"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Description
            </label>
            <Input 
              as="textarea"
              rows={3}
              placeholder="Exam description..."
              value={createFormData.description}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleCreateFormChange('description', e.target.value)}
              disabled={createLoading}
              className="w-full"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button 
              type="button"
              variant="secondary" 
              onClick={() => {
                setIsCreateModalOpen(false);
                setCreateFormData({
                  title: '',
                  courseId: '',
                  durationHours: '',
                  durationMinutes: 0,
                  description: '',
                  totalMarks: '',
                  passingMarks: '',
                  startTime: ''
                });
                setSelectedCourse('');
                setCreateError(null);
              }}
              disabled={createLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={createLoading || !createFormData.title || !createFormData.courseId || !createFormData.durationHours}
              loading={createLoading}
            >
              Create Exam
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={closeDeleteModal}
        title="Delete Exam"
        size="md">
        
        <div className="space-y-4">
          <p className="text-[var(--color-text-secondary)]">
          Are you sure you want to delete <strong>{examToDelete?.title}</strong>?
          </p>
          <p className="text-sm text-[var(--color-text-muted)]">
            This action cannot be undone. All associated questions and submissions will also be deleted.
          </p>
          
          {deleteError && (
            <div className="p-3 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg">
              <p className="text-sm text-[var(--color-error-600)]">{deleteError}</p>
            </div>
          )}
          
          <div className="flex gap-3 pt-4">
            <Button 
              variant="secondary" 
              className="flex-1" 
              type="button" 
              onClick={closeDeleteModal}
              disabled={deleteLoading}
            >
              Cancel
            </Button>
            <Button 
              variant="danger"
              className="flex-1" 
              type="button"
              loading={deleteLoading}
              onClick={handleDeleteExam}
            >
              Delete
            </Button>
          </div>
        </div>
      </Modal>

      {/* Upload Modal */}
      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        title="Upload Exam Paper (AI Processing)"
        size="lg">
        
        <div className="space-y-4">
          <div className="border-2 border-dashed border-[var(--color-border-light)] rounded-lg p-8 text-center hover:border-[var(--color-primary-400)] transition-colors">
            <Icon as={Upload} size={48} className="text-[var(--color-text-muted)] mx-auto mb-4" />
            <p className="text-[var(--color-text-primary)] font-medium mb-2">
              Drop your PDF exam paper here
            </p>
            <p className="text-sm text-[var(--color-text-secondary)] mb-4">or click to browse</p>
            <Button variant="unstyled" noMotion noFocus>Select File</Button>
          </div>

          <div className="bg-[var(--color-primary-50)] border border-[var(--color-border-light)] rounded-lg p-4">
            <p className="text-sm text-[var(--color-text-primary)] font-medium mb-2">
              AI-Powered Processing
            </p>
            <p className="text-sm text-[var(--color-text-secondary)]">
              Our AI will automatically extract questions, detect question
              types, and identify correct answers for MCQs.
            </p>
          </div>
        </div>
      </Modal>
    </div>
  );
}