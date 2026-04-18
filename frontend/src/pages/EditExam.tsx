import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Save, AlertCircle, FileText, Clock, BookOpen } from 'lucide-react';
import Button from '@/components/Button';
import Icon from '@/components/Icon';
import Input from '@/components/Input';
import Dropdown from '@/components/Dropdown';
import Breadcrumbs from '@/components/Breadcrumbs';
import DateTimePicker from '@/components/DateTimePicker';
import * as examApi from '@/apis/exam';
import * as courseApi from '@/apis/course';
import type { Exam, ExamUpdate } from '@/apis/exam';
import type { Course } from '@/apis/course';

export function EditExam() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Detect mode: 'create' from /courses/:id/exams/create or 'edit' from /exams/:id/edit
  const isCreateMode = !id || id === 'create' || window.location.pathname.includes('/exams/create');
  const courseIdFromUrl = window.location.pathname.match(/\/courses\/([^/]+)\/exams\/create/)?.[1];
  
  const [exam, setExam] = useState<Exam | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(!isCreateMode);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form state
  const [formData, setFormData] = useState<ExamUpdate>({
    title: '',
    description: '',
    course_id: courseIdFromUrl || '',
    duration_hours: undefined,
    duration_minutes: 0,
    total_marks: undefined,
    passing_marks: undefined,
    status: 'not_started',
    start_time: undefined,
    max_attempts: 1,
  });

  // Load exam and courses
  useEffect(() => {
    const loadData = async () => {
      // For create mode, just load courses for dropdown
      if (isCreateMode) {
        try {
          const coursesResponse = await courseApi.listCourses({ per_page: 100 });
          setCourses(coursesResponse.items);
        } catch (err: unknown) {
          console.error('Failed to load courses:', err);
        } finally {
          setLoading(false);
        }
        return;
      }
      
      // For edit mode, load existing exam and courses in parallel
      if (!id) return;

      setLoading(true);
      setError(null);

      try {
        // Load exam details and courses in parallel
        const [examData, coursesResponse] = await Promise.all([
          examApi.getExam(id),
          courseApi.listCourses({ per_page: 100 })
        ]);

        setExam(examData);

        // Populate form
        setFormData({
          title: examData.title || '',
          description: examData.description || '',
          course_id: examData.course?.id || '',
          duration_hours: examData.duration_hours || 0,
          duration_minutes: examData.duration_minutes || 0,
          total_marks: examData.total_marks,
          passing_marks: examData.passing_marks,
          status: examData.status || 'not_started',
          start_time: examData.start_time,
          max_attempts: examData.max_attempts || 1,
        });

        setCourses(coursesResponse.items);
      } catch (err: unknown) {
        console.error('Failed to load exam:', err);
        setError(err instanceof Error ? err.message : 'Failed to load exam');
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, [id, isCreateMode]);

  const handleInputChange = (field: keyof ExamUpdate, value: string | number) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    setSaving(true);
    setError(null);
    
    try {
      if (isCreateMode) {
        // Create new exam
        const newExam = await examApi.createExam(formData as examApi.ExamCreate);
        navigate(`/exams/${newExam.id}`);
      } else if (id) {
        // Update existing exam
        await examApi.updateExam(id, formData);
        navigate(`/exams/${id}`);
      }
    } catch (err: unknown) {
      console.error('Failed to save exam:', err);
      setError(err instanceof Error ? err.message : 'Failed to save exam');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-[var(--color-bg-hover)] rounded w-1/3"></div>
          <div className="h-4 bg-[var(--color-bg-hover)] rounded w-1/2"></div>
          <div className="space-y-2">
            <div className="h-4 bg-[var(--color-bg-hover)] rounded"></div>
            <div className="h-4 bg-[var(--color-bg-hover)] rounded"></div>
            <div className="h-4 bg-[var(--color-bg-hover)] rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!exam && !loading && !isCreateMode) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="text-center">
          <Icon as={FileText} size={48} className="text-[var(--color-text-muted)] mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-[var(--color-text-primary)] mb-2">Exam Not Found</h2>
          <p className="text-[var(--color-text-secondary)] mb-4">The exam you're trying to edit doesn't exist.</p>
          <Button onClick={() => navigate('/exams')}>Back to Exams</Button>
        </div>
      </div>
    );
  }

  const courseOptions = courses.map(c => ({
    value: c.id,
    label: `${c.name} (${c.course_code})`
  }));

  return (
    <div >
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <Breadcrumbs />
          <motion.h1 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-2xl font-bold text-[var(--color-text-primary)] mt-2"
          >
            {isCreateMode ? 'Create Exam' : 'Edit Exam'}
          </motion.h1>
          <p className="text-[var(--color-text-secondary)] mt-1">
            {isCreateMode ? 'Create a new exam for this course' : 'Update exam details and settings'}
          </p>
        </div>
        <Button 
          variant="secondary" 
          onClick={() => isCreateMode ? navigate(`/courses/${courseIdFromUrl}`) : navigate(`/exams/${id}`)}
          className="flex items-center gap-2"
        >
          <Icon as={ArrowLeft} size={18} />
          {isCreateMode ? 'Back to Course' : 'Back to Exam'}
        </Button>
      </div>

      {/* Error Message */}
      {error && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 p-4 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg"
        >
          <div className="flex items-center gap-2">
            <Icon as={AlertCircle} size={18} className="text-[var(--color-error-600)]" />
            <p className="text-[var(--color-error-600)]">{error}</p>
          </div>
        </motion.div>
      )}

      {/* Form */}
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        onSubmit={handleSubmit}
        className="bg-[var(--color-bg-card)] rounded-xl shadow-lg border border-[var(--color-border-light)] overflow-hidden"
      >
        <div className="p-6 space-y-6">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Exam Title *
            </label>
            <div className="flex items-center gap-3">
              <div className="bg-[var(--color-primary-50)] p-2 rounded-lg">
                <Icon as={FileText} size={20} className="text-[var(--color-primary-600)]" />
              </div>
              <Input
                type="text"
                value={formData.title}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange('title', e.target.value)}
                placeholder="Enter exam title"
                required
                className="flex-1"
              />
            </div>
          </div>

          {/* Course */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Course *
            </label>
            <div className="flex items-center gap-3">
              <div className="bg-[var(--color-primary-50)] p-2 rounded-lg">
                <Icon as={BookOpen} size={20} className="text-[var(--color-primary-600)]" />
              </div>
              <Dropdown
                options={courseOptions}
                value={formData.course_id || ''}
                onChange={(value) => handleInputChange('course_id', value)}
                placeholder="Select a course"
                className="flex-1"
              />
            </div>
          </div>

          {/* Start Time */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Start Time
            </label>
            <DateTimePicker
              value={formData.start_time || ''}
              onChange={(value) => handleInputChange('start_time', value)}
              placeholder="Select start date and time"
            />
          </div>

          {/* Duration and Marks */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Duration (hours) *
              </label>
              <div className="flex items-center gap-3">
                <div className="bg-[var(--color-primary-50)] p-2 rounded-lg">
                  <Icon as={Clock} size={20} className="text-[var(--color-primary-600)]" />
                </div>
                <Input
                  type="number"
                  min="0"
                  max="24"
                  value={formData.duration_hours || ''}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange('duration_hours', parseInt(e.target.value))}
                  placeholder="e.g., 2"
                  required
                  className="flex-1"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Duration (minutes)
              </label>
              <Input
                type="number"
                min="0"
                max="59"
                value={formData.duration_minutes || 0}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange('duration_minutes', parseInt(e.target.value))}
                placeholder="e.g., 30"
                className="flex-1"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Total Marks
              </label>
              <Input
                type="number"
                value={formData.total_marks || ''}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange('total_marks', parseInt(e.target.value))}
                placeholder="e.g., 100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Passing Marks
              </label>
              <Input
                type="number"
                value={formData.passing_marks || ''}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleInputChange('passing_marks', parseInt(e.target.value))}
                placeholder="e.g., 50"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Description
            </label>
            <Input
              as="textarea"
              rows={4}
              value={formData.description || ''}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleInputChange('description', e.target.value)}
              placeholder="Enter exam description..."
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-[var(--color-bg-hover)] border-t border-[var(--color-border-light)] flex items-center justify-between">
          <Button
            variant="secondary"
            type="button"
            onClick={() => navigate(`/exams/${id}`)}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            loading={saving}
            disabled={!formData.title || !formData.course_id || !formData.duration_hours}
            className="flex items-center gap-2"
          >
            <Icon as={Save} size={18} />
            {isCreateMode ? 'Create Exam' : 'Save Changes'}
          </Button>
        </div>
      </motion.form>
    </div>
  );
}
