import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BookOpen, Search, Plus, AlertCircle, Users, FileText, Trash2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import Icon from '@/components/Icon';
import Input from '@/components/Input';
import SearchInput from '@/components/SearchInput';
import Button from '@/components/Button';
import { Modal } from '@/components/Modal';
import { useAuth } from '@/contexts/AuthContext';
import Card from '@/components/Card';
import Pagination from '@/components/Pagination';
import { EmptyState } from '@/components/EmptyState';
import Breadcrumbs from '@/components/Breadcrumbs';
import CoursesSkeleton from './CoursesSkeleton';
import Dropdown from '@/components/Dropdown';
import * as courseApi from '@/apis/course';
import * as enrollmentApi from '@/apis/enrollment';
import * as authApi from '@/apis/auth';
import resourceCache from '@/lib/resourceCache';
import { config } from '@/config';
import type { Course } from '@/lib/types';
import type { CourseListParams } from '@/apis/course';
import type { Enrollment } from '@/apis/enrollment';
import type { User } from '@/apis/auth';

export function Courses() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(6);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [courseToDelete, setCourseToDelete] = useState<Course | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Form state for creating course
  const [createFormData, setCreateFormData] = useState({
    name: '',
    course_code: '',
    description: '',
    lecturer: {},
  });
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [lecturerNames, setLecturerNames] = useState<Record<string,string>>({});

  // Filter states
  const [selectedLecturer, setSelectedLecturer] = useState<string>('all');
  const [lecturers, setLecturers] = useState<{id: string, name: string}[]>([]);

  // React Query hook for fetching courses and lecturers
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['courses-and-lecturers', currentPage, pageSize, searchQuery, selectedLecturer, user?.tenant_id, user?.role, user?.id],
    queryFn: async () => {
      // For admin users, fetch courses and lecturers in parallel
      if (user?.role === 'admin') {
        const [coursesResult, lecturersResponse] = await Promise.all([
          (async () => {
            const params: CourseListParams = {
              page: currentPage,
              per_page: pageSize,
              search: searchQuery || undefined,
              tenant_id: user?.tenant_id || undefined,
            };

            // Admin can filter by lecturer via dropdown
            if (selectedLecturer && selectedLecturer !== 'all') {
              params.lecturer_id = selectedLecturer;
            }

            const response = await courseApi.listCourses(params);
            return response;
          })(),
          (async () => {
            const response = await authApi.listUsers({ per_page: 100 })
            return response.items
              .filter((u: User) => u.role === 'lecturer')
              .map((u: User) => ({ id: u.id, name: `${u.first_name} ${u.last_name}` }))
          })()
        ]);

        return {
          courses: coursesResult,
          lecturers: lecturersResponse
        };
      }

      // For non-admin users, only fetch courses
      const params: CourseListParams = {
        page: currentPage,
        per_page: pageSize,
        search: searchQuery || undefined,
        tenant_id: user?.tenant_id || undefined,
      };

      const response = await courseApi.listCourses(params);

      // Filter courses for students using enrollment API
      let filteredCourses = response.items;
      let adjustedPagination = response.pagination;

      if (user?.role === 'student') {
        try {
          const enrollmentsResponse = await enrollmentApi.listEnrollment({ student_id: user.id });
          const enrolledCourseIds = enrollmentsResponse.items.map((e: Enrollment) => e.course.id);

          filteredCourses = response.items.filter(course =>
            enrolledCourseIds.includes(course.id)
          );

          adjustedPagination = {
            page: currentPage,
            per_page: pageSize,
            total: filteredCourses.length,
            pages: Math.ceil(filteredCourses.length / pageSize),
            has_next: currentPage < Math.ceil(filteredCourses.length / pageSize),
            has_prev: currentPage > 1
          };
        } catch (enrollmentError) {
          console.error('Failed to fetch enrollments:', enrollmentError);
          filteredCourses = [];
          adjustedPagination = {
            page: 1,
            per_page: pageSize,
            total: 0,
            pages: 0,
            has_next: false,
            has_prev: false
          };
        }
      }

      return {
        courses: { items: filteredCourses, pagination: adjustedPagination },
        lecturers: []
      };
    },
    enabled: !!user,
    staleTime: config.QUERY_CACHE_STATIC, // 5 minutes - courses are relatively static
  });

  const courses = data?.courses?.items || [];
  const pagination = data?.courses?.pagination || {
    page: 1,
    per_page: pageSize,
    total: 0,
    pages: 0,
    has_next: false,
    has_prev: false
  };
  const loading = isLoading;

  useEffect(() => {
    if (data?.lecturers) {
      setLecturers(data.lecturers)
    }
  }, [data?.lecturers])

  // Resolve lecturer names for any courses where lecturer is an id
  useEffect(() => {
    let mounted = true
    const idsToFetch: string[] = []
    courses.forEach((course: any) => {
      const lect = course.lecturer
      if (!lect) return
      if (typeof lect === 'string' && !lecturerNames[lect]) idsToFetch.push(lect)
      if (lect && typeof lect === 'object' && !lecturerNames[lect.id]) {
        lecturerNames[lect.id] = [lect.first_name, lect.middle_name, lect.last_name].filter(Boolean).join(' ') || lect.email || lect.id
      }
    })
    if (idsToFetch.length === 0) return
    Promise.all(idsToFetch.map(id => resourceCache.getUserFullName(id).catch(() => `User ${id}`)))
      .then(results => {
        if (!mounted) return
        const map: Record<string,string> = {}
        idsToFetch.forEach((id, idx) => { map[id] = results[idx] })
        setLecturerNames(prev => ({ ...prev, ...map }))
      })
    return () => { mounted = false }
  }, [courses])

  // Handle course creation
  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    setCreateError(null);

    try {
      const courseData = {
        name: createFormData.name,
        course_code: createFormData.course_code,
        tenant_id: user?.tenant_id || undefined,
        description: createFormData.description,
        lecturer: createFormData.lecturer || undefined,
      };

      await courseApi.createCourse(courseData);

      // Reset form and close modal
      setCreateFormData({ name: '', course_code: '', description: '', lecturer_id: '' });
      setIsCreateModalOpen(false);

      // Refresh courses list
      refetch();
    } catch (error: unknown) {
      console.error('Failed to create course:', error);

      // Preserve the specific backend error message if available
      let errorMessage = 'Failed to create course';
      if (error && typeof error === 'object' && 'response' in error) {
        const errResponse = (error as { response?: { data?: { error?: string; message?: string } } }).response;
        if (errResponse?.data?.error) {
          errorMessage = errResponse.data.error;
        } else if (errResponse?.data?.message) {
          errorMessage = errResponse.data.message;
        }
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      setCreateError(errorMessage);
    } finally {
      setCreateLoading(false);
    }
  };

  // Handle pagination
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleNextPage = () => {
    if (pagination.has_next) {
      setCurrentPage(prev => prev + 1);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  // Handle form input changes
  const handleCreateFormChange = (field: string, value: string) => {
    setCreateFormData(prev => ({ ...prev, [field]: value }));
    setCreateError(null);
  };

  // Handle delete course
  const handleDeleteCourse = async () => {
    if (!courseToDelete) return;

    setDeleteLoading(true);
    try {
      await courseApi.deleteCourse(courseToDelete.id);
      setDeleteModalOpen(false);
      setCourseToDelete(null);
      // Refresh courses list
      refetch();
    } catch (error: unknown) {
      console.error('Failed to delete course:', error);
      // Show error message to user
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete course';
      // Note: In a real app, you might want to show this error in the modal
      console.error(errorMessage);
      setDeleteModalOpen(false);
      setCourseToDelete(null);
    } finally {
      setDeleteLoading(false);
    }
  };

  // Open delete modal
  const openDeleteModal = (course: Course) => {
    setCourseToDelete(course);
    setDeleteModalOpen(true);
  };

  // Close delete modal
  const closeDeleteModal = () => {
    setDeleteModalOpen(false);
    setCourseToDelete(null);
  };

  const handleCloseCreateModal = useCallback(() => {
    setIsCreateModalOpen(false);
    setCreateFormData({ name: '', course_code: '', description: '', lecturer_id: '' });
    setCreateError(null);
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <Breadcrumbs />
        {(user?.role === 'admin' || user?.role === 'lecturer') && (
          <Button variant="primary" onClick={() => setIsCreateModalOpen(true)} className="flex items-center gap-2 px-4 py-2">
            <Icon as={Plus} size={16} />
            Create Course
          </Button>
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
          placeholder="Search courses..."
          disabled={loading}
          className="flex-1 max-w-md"
        />
        {/* Admin can filter by lecturer; lecturers always see only their own */}
        {user?.role === 'admin' && (
          <Dropdown
            options={[
              { value: 'all', label: 'All Lecturers' },
              ...lecturers.map(l => ({ value: l.id, label: l.name }))
            ]}
            value={selectedLecturer}
            onChange={(value) => {
              setSelectedLecturer(value);
              setCurrentPage(1);
            }}
            placeholder="Filter by lecturer"
            className="w-full sm:w-56"
          />
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-6 p-4 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg">
          <div className="flex items-center gap-2">
            <Icon as={AlertCircle} size={16} className="text-[var(--color-error-600)]" />
            <p className="text-sm text-[var(--color-error-600)]">{error.message || 'Failed to load courses'}</p>
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
      {(loading) && <CoursesSkeleton />}

      {/* Empty state */}
      {!loading && !error && courses.length === 0 && (
        <EmptyState
          icon={BookOpen}
          title={
            user?.role === 'student' 
              ? "No Enrolled Courses" 
              : "No Courses Available"
          }
          description={
            searchQuery 
              ? "No courses found matching your search. Try different keywords."
              : user?.role === 'student'
                ? "You haven't enrolled in any courses yet. Browse available courses and enroll to start learning."
                : "No courses have been created yet. Start by creating your first course."
          }
          action={
            user?.role === 'admin' ? {
              label: "Create Course",
              onClick: () => setIsCreateModalOpen(true)
            } : undefined
          }
        />
      )}

      {/* Courses list */}
      {!loading && !error && courses.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {courses.map((course, idx) => (
              <motion.div
                key={course.id}
                initial={{
                  opacity: 0,
                  y: 20
                }}
                animate={{
                  opacity: 1,
                  y: 0
                }}
                transition={{
                  delay: idx * 0.1
                }}
                className="cursor-pointer group">
                <div className="surface-card h-full overflow-hidden group cursor-pointer hover:shadow-[var(--shadow-lg)] hover:-translate-y-0.5 transition-all duration-200">
                  {/* Main clickable area */}
                  <div 
                    onClick={() => navigate(`/courses/${course.id}`)}
                    className="flex-1 cursor-pointer"
                  >
                    {/* Header with icon and course code */}
                    <div className="p-6 pb-4">
                      <div className="flex items-start justify-between mb-4">
                        <div className="bg-[var(--color-primary-50)] p-3 rounded-xl group-hover:bg-[var(--color-primary-100)] transition-all duration-300">
                          <Icon as={BookOpen} size={24} className="text-[var(--color-primary-600)]" />
                        </div>
                        <span className="px-3 py-1 bg-[var(--color-primary-100)] text-[var(--color-primary-700)] rounded-full text-xs font-semibold">
                          {course.course_code}
                        </span>
                      </div>

                      {/* Course title and description */}
                      <h3 className="text-lg font-bold text-[var(--color-text-primary)] mb-2 group-hover:text-[var(--color-primary-600)] transition-colors line-clamp-2">
                        {course.name}
                      </h3>
                      <p className="text-sm text-[var(--color-text-secondary)] mb-4 line-clamp-3 leading-relaxed">
                        {course.description || 'No description available'}
                      </p>

                      {/* Lecturer info */}
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-8 h-8 bg-[var(--color-primary-50)] rounded-full flex items-center justify-center">
                          <Icon as={Users} size={14} className="text-[var(--color-primary-600)]" />
                        </div>
                        <div>
                          <p className="text-xs text-[var(--color-text-muted)]">Lecturer</p>
                          <p className="text-sm font-medium text-[var(--color-text-primary)]">
                            {(() => {
                              const lect = (course as any).lecturer
                              if (!lect) return 'No lecturer assigned'
                              if (typeof lect === 'string') return lecturerNames[lect] || `User ${lect}`
                              return `${lect.first_name} ${lect.last_name}`
                            })()}
                          </p>
                        </div>
                      </div>

                      {/* Description only - stats removed since backend doesn't return them */}
                      <div className="mt-4 pt-4 border-t border-[var(--color-border-light)]">
                        <p className="text-xs text-[var(--color-text-muted)]">
                          Click to view course details
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Footer with actions only - not clickable for navigation */}
                  <div className="px-1 py-2 bg-[var(--color-bg-subtle)] border-t border-[var(--color-border-light)]">
                    <div className="flex items-center justify-end">
                      {/* Role-based action buttons */}
                      <div className="flex gap-2">
                        {user?.role === 'lecturer' && (
                          <>
                            <Button 
                              variant="secondary" 
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/courses/${course.id}/edit`);
                              }}
                              className="px-3 py-1.5 text-xs"
                            >
                              <Icon as={FileText} size={12} className="mr-1" />
                              Edit
                            </Button>
                            {!course.exam_count && (
                              <Button 
                                variant="danger" 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openDeleteModal(course);
                                }}
                                className="px-3 py-1.5 text-xs"
                              >
                                <Icon as={Trash2} size={12} className="mr-1" />
                                Delete
                              </Button>
                            )}
                          </>
                        )}
                        {user?.role === 'admin' && (
                          <>
                            <Button 
                              variant="secondary" 
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/courses/${course.id}/edit`);
                              }}
                              className="px-3 py-1.5 text-xs"
                            >
                              <Icon as={FileText} size={12} className="mr-1" />
                              Edit
                            </Button>
                            {!course.exam_count && (
                              <Button 
                                variant="danger" 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openDeleteModal(course);
                                }}
                                className="px-3 py-1.5 text-xs"
                              >
                                <Icon as={Trash2} size={12} className="mr-1" />
                                Delete
                              </Button>
                            )}
                          </>
                        )}
                        {user?.role === 'student' && (
                          <Button 
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/courses/${course.id}`);
                            }}
                            className="px-4 py-1.5 text-xs"
                          >
                            <Icon as={BookOpen} size={12} className="mr-1" />
                            View Course
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Pagination */}
          {pagination.pages > 1 && (
            <Pagination
              currentPage={pagination.page}
              totalPages={pagination.pages}
              hasNext={pagination.has_next}
              hasPrev={pagination.has_prev}
              onNext={handleNextPage}
              onPrev={handlePrevPage}
              onPageChange={handlePageChange}
            />
          )}
        </>
      )}

      {/* Create Course Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={handleCloseCreateModal}
        title="Create New Course">
        
        <form onSubmit={handleCreateCourse} className="space-y-4">
          {createError && (
            <div className="p-3 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg">
              <p className="text-sm text-[var(--color-error-600)]">{createError}</p>
            </div>
          )}
          
          <div>
            <label htmlFor="courseTitle" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Course Name *
            </label>
            <Input 
              id="courseTitle" 
              name="title" 
              type="text" 
              placeholder="Introduction to Computer Science"
              value={createFormData.name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleCreateFormChange('name', e.target.value)}
              required
              disabled={createLoading}
            />
          </div>

          <div>
            <label htmlFor="courseCode" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Course Code *
            </label>
            <Input 
              id="courseCode" 
              name="code" 
              type="text" 
              placeholder="CS101"
              value={createFormData.course_code}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleCreateFormChange('course_code', e.target.value)}
              required
              disabled={createLoading}
            />
          </div>

          {/* Admin can assign a lecturer */}
          {user?.role === 'admin' && (
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Assign Lecturer
              </label>
              <Dropdown
                options={[
                  { value: '', label: 'No lecturer assigned' },
                  ...lecturers.map(l => ({ value: l.id, label: l.name }))
                ]}
                value={createFormData.lecturer?.id}
                onChange={(v) => handleCreateFormChange('lecturer_id', v)}
                placeholder="Select a lecturer..."
                className="w-full"
              />
            </div>
          )}

          <div>
            <label htmlFor="courseDescription" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Description
            </label>
            <Input 
              as="textarea" 
              id="courseDescription" 
              name="description" 
              rows={3} 
              placeholder="Course description..." 
              className="min-h-[90px]"
              value={createFormData.description}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleCreateFormChange('description', e.target.value)}
              disabled={createLoading}
            />
          </div>

          <div className="flex gap-3 pt-4">
            <Button 
              variant="secondary" 
              className="flex-1" 
              type="button" 
              onClick={() => setIsCreateModalOpen(false)}
              disabled={createLoading}
            >
              Cancel
            </Button>
            <Button 
              className="flex-1" 
              type="submit"
              loading={createLoading}
              disabled={!createFormData.name || !createFormData.course_code}
            >
              Create Course
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Course Modal */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={closeDeleteModal}
        title="Delete Course"
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-3 bg-[var(--color-error-100)] rounded-lg">
            <Icon as={AlertCircle} size={20} className="text-[var(--color-error-600)]" />
            <div>
              <p className="font-medium text-[var(--color-error-800)]">Delete Course</p>
              <p className="text-sm text-[var(--color-error-600)]">
                Are you sure you want to delete <strong>{courseToDelete?.name}</strong>? This action cannot be undone and all associated data will be permanently removed.
              </p>
            </div>
          </div>
          
          <div className="flex gap-3 pt-4">
            <Button 
              variant="secondary" 
              className="flex-1" 
              onClick={closeDeleteModal}
              disabled={deleteLoading}
            >
              Cancel
            </Button>
            <Button 
              variant="danger" 
              className="flex-1" 
              onClick={handleDeleteCourse}
              loading={deleteLoading}
            >
              Delete Course
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}