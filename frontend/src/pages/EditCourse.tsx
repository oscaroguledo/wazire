import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, ArrowLeft, Save, AlertCircle, ChevronDown } from 'lucide-react';
import Button from '@/components/Button';
import { useAuth } from '@/contexts/AuthContext';
import Icon from '@/components/Icon';
import Input from '@/components/Input';
import Breadcrumbs from '@/components/Breadcrumbs';
import * as courseApi from '@/apis/course';
import * as authApi from '@/apis/auth';
import { errorTracker } from '@/utils/errorTracking';
import type { Course } from '@/apis/course';
import type { User } from '@/apis/auth';
import SearchInput from '@/components/SearchInput';

// Searchable Dropdown Component
interface SearchableDropdownProps {
  options: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

function SearchableDropdown({ options, value, onChange, placeholder = 'Select...', disabled }: SearchableDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  
  const selectedOption = options.find(opt => opt.value === value);
  
  const filteredOptions = options.filter(opt => 
    opt.label.toLowerCase().includes(search.toLowerCase())
  );
  
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  
  const handleSelect = (val: string) => {
    onChange(val);
    setIsOpen(false);
    setSearch('');
  };
  
  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between px-3 py-2 border rounded-lg text-left transition-colors ${
          disabled 
            ? 'bg-[var(--color-bg-hover)] border-[var(--color-border-light)] text-[var(--color-text-muted)] cursor-not-allowed' 
            : 'border-[var(--color-border-medium)] hover:border-[var(--color-border-dark)] bg-[var(--color-bg-card)]'
        }`}
      >
        <span className={selectedOption ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}>
          {selectedOption?.label || placeholder}
        </span>
        <Icon as={ChevronDown} size={16} className={`text-[var(--color-text-muted)] transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute z-50 w-full mt-1 bg-[var(--color-bg-card)] border border-[var(--color-border-light)] rounded-lg shadow-lg overflow-hidden"
          >
            <div className="p-2 border-b border-[var(--color-border-light)]">
              <SearchInput
                value={search}
                onChange={setSearch}
                placeholder="Search..."
                className="w-full"
                inputClassName="py-1.5 text-sm"
              />
            </div>
            <div className="max-h-60 overflow-y-auto">
              {filteredOptions.length === 0 ? (
                <div className="p-3 text-sm text-[var(--color-text-muted)] text-center">No results found</div>
              ) : (
                filteredOptions.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleSelect(opt.value)}
                    className={`w-full px-3 py-2 text-left text-sm transition-colors ${
                      opt.value === value 
                        ? 'bg-[var(--color-primary-50)] text-[var(--color-primary-700)]' 
                        : 'hover:bg-[var(--color-bg-subtle)] text-[var(--color-text-secondary)]'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function EditCourse() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lecturers, setLecturers] = useState<any[]>([]);
  const [formData, setFormData] = useState({
    name: '',
    course_code: '',
    description: '',
    lecturer_id: '',
  });

  useEffect(() => {
    const loadCourse = async () => {
      if (!id) {
        setError('Course ID is required');
        setLoading(false);
        return;
      }

      try {
        // Fetch course and lecturers in parallel
        const [data, lecturersResponse] = await Promise.all([
          courseApi.getCourse(id),
          authApi.listUsers({ role: 'lecturer', per_page: 100 })
        ]);

        setCourse(data);
        setFormData({
          name: data.name || '',
          course_code: data.course_code || '',
          description: data.description || '',
          lecturer_id: data.lecturer?.id || '',
        });
        setLecturers(lecturersResponse.items);
      } catch (err: any) {
        setError(err?.message || 'Failed to load course');
      } finally {
        setLoading(false);
      }
    };

    loadCourse();
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    
    setSaving(true);
    setError(null);
    
    try {
      await courseApi.updateCourse(id, {
        name: formData.name,
        course_code: formData.course_code,
        description: formData.description,
        lecturer_id: formData.lecturer_id || undefined,
      });
      navigate(`/courses/${id}`);
    } catch (err: any) {
      setError(err?.message || 'Failed to update course');
      setSaving(false);
    }
  };

  const lecturerOptions = lecturers.map(l => ({
    value: l.id,
    label: `${l.first_name} ${l.last_name} (${l.email})`,
  }));

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError(null);
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto">
        <Breadcrumbs />
        <div className="mt-8 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-primary-600)]" />
        </div>
      </div>
    );
  }

  if (error && !course) {
    return (
      <div className="max-w-6xl mx-auto">
        <Breadcrumbs />
        <div className="mt-8 p-4 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg">
          <p className="text-[var(--color-error-600)]">{error}</p>
        </div>
      </div>
    );
  }

  const canEdit = user?.role === 'admin' || (user?.role === 'lecturer' && course?.lecturer?.id === user?.id);
  
  if (!canEdit) {
    return (
      <div className="max-w-6xl mx-auto">
        <Breadcrumbs />
        <div className="mt-8 p-4 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg">
          <p className="text-[var(--color-error-600)]">You don't have permission to edit this course.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3 mb-6"
      >
        <Button
          variant="ghost"
          noMotion
          onClick={() => navigate(`/courses/${id}`)}
          className="p-2 -ml-2 hover:bg-[var(--color-bg-hover)]"
        >
          <Icon as={ArrowLeft} size={20} className="text-[var(--color-text-secondary)]" />
        </Button>
        <Breadcrumbs />
      </motion.div>

      {/* Edit Form */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-[var(--color-bg-card)] rounded-xl shadow-sm border border-[var(--color-border-light)] overflow-hidden"
      >
        {/* Header */}
        <div className="bg-gradient-to-br from-primary-600 via-primary-600 to-primary-700 px-6 py-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
              <Icon as={BookOpen} size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Edit Course</h1>
              <p className="text-white/80 text-sm">{course?.name}</p>
            </div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="p-3 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg flex items-center gap-2">
              <Icon as={AlertCircle} size={16} className="text-[var(--color-error-600)]" />
              <p className="text-sm text-[var(--color-error-600)]">{error}</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Course Name *
              </label>
              <Input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange('name', e.target.value)}
                placeholder="Introduction to Computer Science"
                required
                disabled={saving}
              />
            </div>

            <div>
              <label htmlFor="course_code" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Course Code *
              </label>
              <Input
                id="course_code"
                type="text"
                value={formData.course_code}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange('course_code', e.target.value)}
                placeholder="CS101"
                required
                disabled={saving}
              />
            </div>
          </div>

          <div>
            <label htmlFor="lecturer" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Lecturer
            </label>
            <SearchableDropdown
              options={lecturerOptions}
              value={formData.lecturer_id}
              onChange={(value) => handleChange('lecturer_id', value)}
              placeholder="Select a lecturer..."
              disabled={saving || loading}
            />
            <p className="mt-1 text-xs text-[var(--color-text-muted)]">
              Search by name or email to find a lecturer
            </p>
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Description
            </label>
            <Input
              as="textarea"
              id="description"
              rows={4}
              value={formData.description}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleChange('description', e.target.value)}
              placeholder="Course description..."
              disabled={saving}
            />
          </div>

          <div className="flex gap-3 pt-4 border-t border-[var(--color-border-light)]">
            <Button
              variant="secondary"
              className="flex-1"
              type="button"
              onClick={() => navigate(`/courses/${id}`)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button
              className="flex-1"
              type="submit"
              loading={saving}
              disabled={!formData.name || !formData.course_code || saving}
            >
              <Icon as={Save} size={16} className="mr-2" />
              Save Changes
            </Button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}

export default EditCourse;
