import React, { useState, useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Plus,
  Edit,
  Trash2,
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  ArrowLeft,
  Upload,
  Award
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import Icon from '@/components/Icon'
import { useAuth } from '@/contexts/AuthContext'
import examApi from '@/apis/exam'
import questionApi from '@/apis/question'
import { config } from '@/config'
import { compressImageToWebP, validateImageFile } from '@/lib/imageUtils'
import { processDocument } from '@/lib/pdfConverter'
import type { Exam, ExamQuestion, QuestionCreate } from '@/apis/exam'
import { errorTracker } from '@/utils/errorTracking'
import { Modal } from '@/components/Modal'
import Button from '@/components/Button'
import Card from '@/components/Card'
import Input from '@/components/Input'
import SearchInput from '@/components/SearchInput'
import Dropdown from '@/components/Dropdown'
import Pagination from '@/components/Pagination'
import { EmptyState } from '@/components/EmptyState'
import { StatusBadge } from '@/components/StatusBadge'
import Breadcrumbs from '@/components/Breadcrumbs'
import { ExamQuestionsSkeleton } from './ExamQuestionsSkeleton'

export default function ExamQuestions() {
  const { examId } = useParams<{ examId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  
  // Check if user can manage questions
  const canManageQuestions = user?.role === 'lecturer' || user?.role === 'admin'
  
  // State
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [processingProgress, setProcessingProgress] = useState<{current: number, total: number} | null>(null)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [questionToDelete, setQuestionToDelete] = useState<ExamQuestion | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [qtypeFilter, setQtypeFilter] = useState<string>('all')
  const [pageSize] = useState(10)
  const [currentPage, setCurrentPage] = useState(1)
  
  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editingQuestion, setEditingQuestion] = useState<ExamQuestion | null>(null)
  
  // Form states
  const [formData, setFormData] = useState<QuestionCreate>({
    question_text: '',
    question_type: 'multiple_choice',
    options: ['', '', '', ''],
    correct_answer: '',
    marks: 1,
    order: 1,
    images: [],
    industry: 'general'
  })
  const [objectiveType, setObjectiveType] = useState<'multiple_choice' | 'fill_in_blanks'>('multiple_choice')
  const [questionNumber, setQuestionNumber] = useState(1)
  const [formLoading, setFormLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [imagePreviews, setImagePreviews] = useState<string[]>([])

  // React Query hook for fetching exam and questions in parallel using Promise.all
  const { data, isLoading, error: fetchError, refetch } = useQuery({
    queryKey: ['exam-and-questions', examId, user?.tenant_id],
    queryFn: async () => {
      if (!examId) throw new Error('No exam ID')
      // Fetch both exam and questions in parallel
      const [examData, questionsResponse] = await Promise.all([
        examApi.getExam(examId),
        questionApi.listQuestions({
          exam_id: examId,
          tenant_id: user?.tenant_id
        })
      ])
      return {
        exam: examData,
        questions: questionsResponse
      };
    },
    enabled: !!examId && !!user,
    staleTime: config.QUERY_CACHE_STATIC, // 5 minutes - questions are relatively static
  })

  const exam = data?.exam
  const questions = data?.questions?.items || []
  const examLoading = isLoading
  const questionsLoading = isLoading
  const examError = fetchError
  const questionsError = fetchError
  const refetchQuestions = refetch

  // Filter questions by type and search query
  const filteredQuestions = useMemo(() => {
    return questions.filter((q: ExamQuestion) => {
      const matchesType = qtypeFilter === 'all' || 
        (qtypeFilter === 'objective' && (q.qtype === 'multiple_choice' || q.qtype === 'fill_in_blanks')) ||
        (qtypeFilter === 'theory' && q.qtype === 'theory') ||
        q.qtype === qtypeFilter
      const matchesSearch = !searchQuery || 
        q.text?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        q.number?.toString().includes(searchQuery)
      return matchesType && matchesSearch
    })
  }, [questions, qtypeFilter, searchQuery])
  
  // Calculate marks statistics using ALL questions
  const marksStats = useMemo(() => {
    const totalAllocated = exam?.total_marks || 0
    const currentMarks = questions.reduce((sum: number, q: ExamQuestion) => sum + (q.mark || 0), 0)
    const marksLeft = totalAllocated - currentMarks
    return {
      totalAllocated,
      currentMarks,
      marksLeft
    }
  }, [exam?.total_marks, questions])
  
  const loading = examLoading || questionsLoading
  const error = examError?.message || questionsError?.message || null

  // Background processing will extract questions on the server.
  // The UI will refresh shortly after upload to show created questions.


  // Client-side pagination for filtered questions
  const totalItems = filteredQuestions.length
  const totalPages = Math.ceil(totalItems / pageSize) || 1
  const startIndex = (currentPage - 1) * pageSize
  const endIndex = startIndex + pageSize
  const paginatedQuestions = filteredQuestions.slice(startIndex, endIndex)
  const hasNext = currentPage < totalPages
  const hasPrev = currentPage > 1

  // Handle pagination
  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage)
    }
  }

  const handleNextPage = () => {
    if (hasNext) {
      setCurrentPage(prev => prev + 1)
    }
  }

  const handlePrevPage = () => {
    if (hasPrev) {
      setCurrentPage(prev => prev - 1)
    }
  }

  // Question type options
  const questionTypeOptions = [
    { value: 'objective', label: 'Objective' },
    { value: 'theory', label: 'Theory' }
  ]

  const objectiveSubTypeOptions = [
    { value: 'multiple_choice', label: 'Multiple Choice (MCQ)' },
    { value: 'fill_in_blanks', label: 'Fill in Blanks (FITB)' }
  ]

  // Handle image upload
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    // Validate image file
    if (!validateImageFile(file, 5)) {
      setFormError('Please upload a valid image file (JPEG, PNG, etc.) under 5MB')
      return
    }
    
    try {
      // Compress and convert to WebP
      const compressedImage = await compressImageToWebP(file, {
        maxWidth: 1920,
        maxHeight: 1080,
        quality: 0.8
      })
      
      // Add compressed image to the images array
      setFormData(prev => ({ 
        ...prev, 
        images: [...(prev.images || []), compressedImage] 
      }))
      setImagePreviews(prev => [...prev, compressedImage])
    } catch (error: unknown) {
      setFormError(error instanceof Error ? error.message : 'Failed to process image')
    }
  }
  
  const clearImages = () => {
    setFormData(prev => ({ ...prev, images: [] }))
    setImagePreviews([])
  }

  // Handle document upload for bulk question creation
  const handleDocumentUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    // Check file type (PDF, images)
    const allowedTypes = [
      'application/pdf',
      'image/jpeg',
      'image/png',
      'image/webp'
    ]
    if (!allowedTypes.includes(file.type) && !file.name.toLowerCase().endsWith('.pdf')) {
      setFormError('Please upload a PDF or image (.pdf, .jpg, .png, .webp)')
      return
    }
    
    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setFormError('Document size must be less than 10MB')
      return
    }
    
    try {
      setFormLoading(true)
      setIsProcessing(true)
      setProcessingProgress(null)
      setSuccessMessage('Converting document to images...')
      
      // Convert PDF/images to base64 images
      const pages = await processDocument(file)
      
      if (!examId) return
      if (pages.length === 0) {
        setFormError('No pages could be extracted from document')
        setFormLoading(false)
        return
      }
      
      setSuccessMessage(`Extracted ${pages.length} page(s). Uploading to server...`)
      
      // Call API to process document
      await questionApi.uploadQuestions({
        pages,
        exam_id: examId,
        industry: 'general',
        mark_per_question: 1
      })
      
      setSuccessMessage('Document uploaded successfully! Questions will be extracted in background.')
      // Stop local processing indicator; server will process in background.
      setIsProcessing(false)
      setProcessingProgress(null)
      // Refresh questions shortly after upload to pick up created items.
      setTimeout(() => refetchQuestions(), 2000)
      setFormLoading(false)
    } catch (error: unknown) {
      if (error instanceof Error) {
        errorTracker.track(error, { action: 'upload_document', component: 'ExamQuestions' });
      }
      setFormError(error instanceof Error ? error.message : 'Failed to upload document')
      setIsProcessing(false)
      setProcessingProgress(null)
    } finally {
      setFormLoading(false)
    }
  }

  // Handle form changes
  const handleFormChange = (field: string, value: string | number | boolean | File | null) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    setFormError(null)
  }

  // Create question
  const handleCreateQuestion = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormLoading(true)
    setFormError(null)
    
    try {
      if (!examId) return
      
      // Calculate next question number to avoid race conditions
      const existingNumbers = questions.map(q => parseInt(q.number) || 0).filter(n => n > 0)
      const nextNumber = existingNumbers.length > 0 ? Math.max(...existingNumbers) + 1 : 1
      
      // Prepare data according to backend schema
      const questionData: Record<string, unknown> = {
        number: nextNumber.toString(),
        text: formData.question_text,
        qtype: formData.question_type,
        industry: formData.industry || 'general',
        mark: formData.marks,
        images: formData.images || []
      }
      
      // Add options and answer for multiple choice questions
      if (formData.question_type === 'multiple_choice') {
        const validOptions = formData.options?.filter(o => o.trim()) || []
        if (validOptions.length < 2) {
          setFormError('Multiple choice questions require at least 2 options')
          setFormLoading(false)
          return
        }
        
        // Format options as required by backend: [{label: "a", text: "Option A"}]
        const formattedOptions = validOptions.map((option, index) => ({
          label: String.fromCharCode(97 + index), // a, b, c, d...
          text: option.trim()
        }))
        
        questionData.options = formattedOptions
        
        // Find the correct answer index and convert to letter
        const correctAnswerIndex = validOptions.findIndex(opt => opt === formData.correct_answer)
        if (correctAnswerIndex === -1) {
          setFormError('Please select a correct answer from the options')
          setFormLoading(false)
          return
        }
        
        const answerLetter = String.fromCharCode(97 + correctAnswerIndex)
        // Only send answer if it's a valid letter a-z
        if (/^[a-z]$/.test(answerLetter)) {
          questionData.answer = answerLetter
        }
      } else {
        // For theory questions, correct_answer is optional model answer
        if (formData.correct_answer && typeof formData.correct_answer === 'string' && formData.correct_answer.trim()) {
          questionData.rules = JSON.stringify({ model_answer: formData.correct_answer })
        }
      }
      
      // Link to exam
      questionData.exam_ids = [examId]
      
      await questionApi.createQuestion(questionData)
      
      setSuccessMessage('Question created successfully!')
      
      // Reset form and close modal
      setFormData({
        question_text: '',
        question_type: 'multiple_choice',
        options: ['', '', '', ''],
        correct_answer: '',
        marks: 1,
        order: 1,
        images: [],
        industry: 'general'
      })
      setQuestionNumber(nextNumber + 1)
      setImagePreviews([])
      setIsCreateModalOpen(false)
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000)
      
      // Refresh questions
      refetchQuestions()
      setCurrentPage(1)
    } catch (error: unknown) {
      setFormError(error instanceof Error ? error.message : 'Failed to create question')
    } finally {
      setFormLoading(false)
    }
  }

  // Update question
  const handleUpdateQuestion = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormLoading(true)
    setFormError(null)
    
    try {
      if (!examId || !editingQuestion) return
      
      // Prepare data according to backend schema
      const questionData: Record<string, unknown> = {
        number: (formData.order || 1).toString(),
        text: formData.question_text,
        qtype: formData.question_type,
        industry: formData.industry || 'general',
        mark: formData.marks,
        images: formData.images || []
      }
      
      // Add options and answer for multiple choice questions
      if (formData.question_type === 'multiple_choice') {
        const validOptions = formData.options?.filter(o => o.trim()) || []
        if (validOptions.length < 2) {
          setFormError('Multiple choice questions require at least 2 options')
          setFormLoading(false)
          return
        }
        
        // Format options as required by backend: [{label: "a", text: "Option A"}]
        const formattedOptions = validOptions.map((option, index) => ({
          label: String.fromCharCode(97 + index), // a, b, c, d...
          text: option.trim()
        }))
        
        questionData.options = formattedOptions
        
        // Find the correct answer index and convert to letter
        const correctAnswerIndex = validOptions.findIndex(opt => opt === formData.correct_answer)
        if (correctAnswerIndex === -1) {
          setFormError('Please select a correct answer from the options')
          setFormLoading(false)
          return
        }
        
        const answerLetter = String.fromCharCode(97 + correctAnswerIndex)
        // Only send answer if it's a valid letter a-z
        if (/^[a-z]$/.test(answerLetter)) {
          questionData.answer = answerLetter
        }
      } else {
        // For theory questions, correct_answer is optional model answer
        if (formData.correct_answer && typeof formData.correct_answer === 'string' && formData.correct_answer.trim()) {
          questionData.rules = JSON.stringify({ model_answer: formData.correct_answer })
        }
      }

      await questionApi.updateQuestion(editingQuestion.id, questionData)
      
      setSuccessMessage('Question updated successfully!')
      
      // Reset form and close modal
      setFormData({
        question_text: '',
        question_type: 'multiple_choice',
        options: ['', '', '', ''],
        correct_answer: '',
        marks: 1,
        order: 1,
        images: [],
        industry: 'general'
      })
      setImagePreviews([])
      setIsEditModalOpen(false)
      setEditingQuestion(null)
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000)
      
      // Refresh questions
      refetchQuestions()
      setCurrentPage(1)
    } catch (error: unknown) {
      setFormError(error instanceof Error ? error.message : 'Failed to update question')
    } finally {
      setFormLoading(false)
    }
  }

  // Delete question
  const handleDeleteQuestion = async (question: ExamQuestion) => {
    if (!examId) return
    
    // Set the question to delete and open confirmation modal
    setQuestionToDelete(question)
    setDeleteConfirmOpen(true)
  }

  // Confirm delete question
  const confirmDeleteQuestion = async () => {
    if (!questionToDelete || !examId) return
    
    try {
      await examApi.deleteQuestion(examId, questionToDelete.id)
      setSuccessMessage('Question deleted successfully!')
      refetchQuestions()
      setCurrentPage(1)
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (error: unknown) {
      if (error instanceof Error) {
        errorTracker.track(error, { action: 'delete_question', component: 'ExamQuestions' });
      }
    } finally {
      setDeleteConfirmOpen(false)
      setQuestionToDelete(null)
    }
  }

  // Cancel delete
  const cancelDelete = () => {
    setDeleteConfirmOpen(false)
    setQuestionToDelete(null)
  }

  // Edit question
  const handleEditQuestion = (question: ExamQuestion) => {
    setEditingQuestion(question)
    
    // Calculate next question number based on existing questions
    const nextNumber = questions.length > 0 ? Math.max(...questions.map(q => parseInt(q.number) || 0)) + 1 : 1
    setQuestionNumber(nextNumber)
    
    // Map backend data to frontend form
    const options = (question as ExamQuestion & { parsed_options?: Array<{ text: string }> }).parsed_options || question.options || []
    const optionTexts = options.map((opt: { text?: string } | string) => typeof opt === 'string' ? opt : opt.text || opt) as string[]

    // Find correct answer
    let correctAnswer = ''
    if (question.qtype === 'multiple_choice' && question.answer) {
      const answerIndex = options.findIndex((opt: { label?: string } | string) => {
        const optLabel = typeof opt === 'string' ? opt : opt.label
        return optLabel === question.answer?.value
      })
      if (answerIndex !== -1 && optionTexts[answerIndex]) {
        correctAnswer = optionTexts[answerIndex]
      }
    } else if (question.qtype === 'fill_in_blanks' && question.answer) {
      // For FITB: answer is stored in text_value
      correctAnswer = question.answer?.text_value || ''
    } else if (question.qtype === 'theory' && question.rules) {
      try {
        const rules = JSON.parse(question.rules)
        correctAnswer = rules.model_answer || ''
      } catch {
        correctAnswer = ''
      }
    }
    
    setFormData({
      question_text: question.text,
      question_type: question.qtype,
      options: optionTexts.length >= 4 ? optionTexts.slice(0, 4) : [...optionTexts, ...Array(4 - optionTexts.length).fill('')],
      correct_answer: correctAnswer,
      marks: question.mark || 1,
      order: parseInt(question.number) || 1,
      images: question.images || [],
      industry: question.industry || 'general'
    })
    setImagePreviews(question.images || [])
    setIsEditModalOpen(true)
  }

  // Tab content
  const renderQuestionsList = (questions: ExamQuestion[]) => {
    if (questions.length === 0) {
      return (
        <EmptyState
          icon={FileText}
          title="No Questions Found"
          description={
            searchQuery 
              ? "No questions match your search criteria."
              : "No questions have been added to this exam yet."
          }
          action={canManageQuestions ? {
            label: "Create Question",
            onClick: () => setIsCreateModalOpen(true)
          } : undefined}
        />
      )
    }

    // Calculate separate counters for objective and theory questions
    let objCounter = 1
    let theoryCounter = 1

    return (
      <div className="space-y-4">
        {questions.map((question, index) => (
          <Card key={question.id} className="p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-sm font-medium text-[var(--color-text-muted)]">
                    {(() => {
                      if (question.qtype === 'multiple_choice' || question.qtype === 'fill_in_blanks') {
                        const num = objCounter++
                        return `OBJ${num}`
                      } else {
                        const num = theoryCounter++
                        return `THE${num}`
                      }
                    })()}
                  </span>
                  <span className="text-sm text-[var(--color-text-secondary)]">{question.mark} marks</span>
                  {question.industry && (
                    <span className="text-xs px-2 py-1 bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] rounded-full">
                      {question.industry}
                    </span>
                  )}
                  
                </div>
                
                <p className="text-[var(--color-text-primary)] font-medium mb-3">{question.text}</p>
                
                {/* Display question metadata */}
                <div className="flex flex-wrap gap-2 mb-3 text-xs text-[var(--color-text-secondary)]">
                  {question.qtype && (
                    <span className="px-2 py-1 bg-[var(--color-bg-subtle)] rounded">
                      Type: {question.qtype === 'multiple_choice' ? 'Multiple Choice' : question.qtype === 'fill_in_blanks' ? 'Fill in Blanks' : 'Theory'}
                    </span>
                  )}
                  {question.rules && (
                    <span className="px-2 py-1 bg-[var(--color-bg-subtle)] rounded">
                      Rules: {question.rules}
                    </span>
                  )}
                </div>
                
                {/* Display question images if available */}
                {question.images && question.images.length > 0 && (
                  <div className="mb-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {question.images.map((imgUrl, imgIndex) => (
                      <div key={imgIndex} className="relative group">
                        <img 
                          src={imgUrl} 
                          alt={`Question image ${imgIndex + 1}`} 
                          className="w-full h-32 sm:h-40 md:h-48 object-cover rounded-lg border border-[var(--color-border-light)] cursor-pointer hover:opacity-90 transition-all duration-200 hover:scale-[1.02]"
                          onClick={() => window.open(imgUrl, '_blank')}
                          loading="lazy"
                        />
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors rounded-lg" />
                        <span className="absolute bottom-2 right-2 bg-black/50 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                          {imgIndex + 1}/{question.images?.length}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                
                {question.qtype === 'multiple_choice' && question.options && (
                  <div className="space-y-2 mb-3">
                    {question.options.map((option, optIndex) => (
                      <div 
                        key={optIndex}
                        className={`flex items-center gap-2 p-2 rounded ${
                          question.answer?.value === option.label ? 'bg-[var(--color-success-100)] text-[var(--color-success-700)]' : 'bg-[var(--color-bg-hover)]'
                        }`}
                      >
                        <span className="text-sm font-medium">
                          {option.label.toUpperCase()}.
                        </span>
                        <span className="text-sm">{option.text}</span>
                        {question.answer?.value === option.label && (
                          <Icon as={CheckCircle} size={16} className="text-[var(--color-success-600)]" />
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              {canManageQuestions && (
                <div className="flex items-center gap-2 ml-4">
                  <Button
                    variant="ghost"
                    onClick={() => handleEditQuestion(question)}
                  >
                    <Icon as={Edit} size={16} />
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => handleDeleteQuestion(question)}
                  >
                    <Icon as={Trash2} size={16} />
                  </Button>
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>
    )
  }

  if (loading) {
    return <ExamQuestionsSkeleton />;
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="p-4 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg">
          <p className="text-[var(--color-error-600)]">{error}</p>
        </div>
      </div>
    )
  }

  if (!exam) {
    return <div className="p-8">Exam not found</div>
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6 sm:mb-8">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 sm:gap-3 mb-2">
            <Button
              variant="ghost"
              onClick={() => navigate('/exams')}
              className="p-2 sm:p-3"
            >
              <Icon as={ArrowLeft} size={16} />
            </Button>
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-[var(--color-text-primary)] truncate">{exam.title}</h1>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm sm:text-base text-[var(--color-text-secondary)]">
              {canManageQuestions ? 'Manage exam questions' : 'View exam questions'}
            </span>
            <span className="text-[var(--color-text-muted)]">•</span>
            <span className="px-2 py-0.5 bg-[var(--color-primary-50)] text-[var(--color-primary-700)] text-sm font-medium rounded-md border border-[var(--color-primary-200)]">
              {exam.course_name || 'No Course'}
            </span>
            <span className="text-[var(--color-text-muted)]">•</span>
            <span className="px-2 py-0.5 bg-[var(--color-success-50)] text-[var(--color-success-700)] text-sm font-medium rounded-md border border-[var(--color-success-200)]">
              {(() => {
                const hours = exam.duration_hours || 0
                const minutes = exam.duration_minutes || 0
                const parts: string[] = []
                if (hours > 0) parts.push(`${hours} hr${hours > 1 ? 's' : ''}`)
                if (minutes > 0) parts.push(`${minutes} mins`)
                return parts.join(' ') || '0 mins'
              })()}
            </span>
          </div>
          
          {/* Real-time Marks Statistics */}
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${
              marksStats.currentMarks === marksStats.totalAllocated 
                ? 'bg-[var(--color-success-100)] text-[var(--color-success-700)] border border-[var(--color-success-200)]' 
                : marksStats.currentMarks > marksStats.totalAllocated
                ? 'bg-[var(--color-error-100)] text-[var(--color-error-700)] border border-[var(--color-error-200)]'
                : 'bg-[var(--color-primary-50)] text-[var(--color-primary-700)] border border-[var(--color-primary-200)]'
            }`}>
              <Icon as={Award} size={12} />
              <span>Allocated: {marksStats.totalAllocated}</span>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] border border-[var(--color-border-light)]">
              <span>Current: {marksStats.currentMarks}</span>
            </div>
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${
              marksStats.marksLeft === 0 
                ? 'bg-[var(--color-success-100)] text-[var(--color-success-700)] border border-[var(--color-success-200)]'
                : marksStats.marksLeft < 0
                ? 'bg-[var(--color-error-100)] text-[var(--color-error-700)] border border-[var(--color-error-200)]'
                : 'bg-[var(--color-warning-50)] text-[var(--color-warning-700)] border border-[var(--color-warning-200)]'
            }`}>
              <span>Left: {marksStats.marksLeft}</span>
            </div>
          </div>
        </div>
        
        {canManageQuestions && (
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
            {/* Document Upload */}
            <div className="relative w-full sm:w-auto">
              <input
                type="file"
                accept=".pdf,.doc,.docx"
                onChange={handleDocumentUpload}
                className="hidden"
                id="document-upload"
              />
              <label 
                htmlFor="document-upload"
                className="flex items-center justify-center w-full px-4 py-1.5 bg-[var(--color-bg-card)] border-2 border-[var(--color-border-medium)] text-[var(--color-text-secondary)] rounded-lg hover:bg-[var(--color-bg-hover)] hover:border-[var(--color-primary-500)] cursor-pointer transition-all shadow-sm"
              >
                <Icon as={FileText} size={16} className="mr-2" />
                <span>Upload Doc</span>
              </label>
            </div>
            
            <Button onClick={() => setIsCreateModalOpen(true)} className="text-sm">
              <Icon as={Plus} size={16} className="mr-2" />
              <span className="hidden sm:inline">Add Question</span>
              <span className="sm:hidden">Add</span>
            </Button>
          </div>
        )}
      </div>

      <Breadcrumbs />

      {/* Processing Indicator */}
      {isProcessing && (
        <div className="mb-4 sm:mb-6 p-4 bg-[var(--color-primary-50)] border border-[var(--color-primary-200)] rounded-lg">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-8 h-8 border-2 border-[var(--color-primary-200)] border-t-[var(--color-primary-500)] rounded-full animate-spin" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-[var(--color-primary-700)]">
                {processingProgress 
                  ? `Processing questions... ${processingProgress.current}/${processingProgress.total}`
                  : 'Processing document...'}
              </p>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                Please wait while we extract questions from your document
              </p>
            </div>
            {processingProgress && processingProgress.total > 0 && (
              <div className="w-24 h-2 bg-[var(--color-primary-200)] rounded-full overflow-hidden">
                <div 
                  className="h-full bg-[var(--color-primary-500)] transition-all duration-300"
                  style={{ width: `${(processingProgress.current / processingProgress.total) * 100}%` }}
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-4 mb-4 sm:mb-6 px-2 sm:px-0">
        <SearchInput
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder="Search questions..."
          className="flex-1 max-w-full sm:max-w-md"
        />
        <Dropdown
          options={[
            { value: 'all', label: 'All Types' },
            { value: 'objective', label: 'Objective (MCQ & FITB)' },
            // { value: 'multiple_choice', label: 'Multiple Choice' },
            // { value: 'fill_in_blanks', label: 'Fill in Blanks' },
            { value: 'theory', label: 'Theory' }
          ]}
          value={qtypeFilter}
          onChange={(v) => setQtypeFilter(v)}
          placeholder="Filter by type"
          className="w-full sm:w-48"
        />
      </div>

      {/* Questions List */}
      {renderQuestionsList(paginatedQuestions)}

      {/* Pagination - always show when there are filtered questions */}
      {!loading && !error && filteredQuestions.length > 0 && (
        <div className="mt-6">
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            hasNext={hasNext}
            hasPrev={hasPrev}
            onNext={handleNextPage}
            onPrev={handlePrevPage}
            onPageChange={handlePageChange}
          />
        </div>
      )}

      {/* Create/Edit Question Modal */}
      <Modal
        isOpen={isCreateModalOpen || isEditModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false)
          setIsEditModalOpen(false)
          setEditingQuestion(null)
          setFormData({
            question_text: '',
            question_type: 'multiple_choice',
            options: ['', '', '', ''],
            correct_answer: '',
            marks: 1,
            order: 1,
            images: [],
            industry: 'general'
          })
          setQuestionNumber(1)
        }}
        title={isEditModalOpen ? 'Edit Question' : 'Create Question'}
      >
        <form onSubmit={isEditModalOpen ? handleUpdateQuestion : handleCreateQuestion} className="space-y-4">
          {formError && (
            <div className="p-3 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg">
              <p className="text-sm text-[var(--color-error-600)]">{formError}</p>
            </div>
          )}
          {successMessage && (
            <div className="p-3 bg-[var(--color-success-100)] border border-[var(--color-success-100)] rounded-lg">
              <p className="text-sm text-[var(--color-success-600)]">{successMessage}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Question Category *
            </label>
            <Dropdown
              options={questionTypeOptions}
              value={formData.question_type === 'multiple_choice' || formData.question_type === 'fill_in_blanks' ? 'objective' : 'theory'}
              onChange={(v) => {
                if (v === 'objective') {
                  handleFormChange('question_type', objectiveType)
                } else {
                  handleFormChange('question_type', 'theory')
                }
              }}
              className="w-full"
            />
          </div>

          {(formData.question_type === 'multiple_choice' || formData.question_type === 'fill_in_blanks') && (
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Objective Type *
              </label>
              <Dropdown
                options={objectiveSubTypeOptions}
                value={formData.question_type}
                onChange={(v) => {
                  setObjectiveType(v as 'multiple_choice' | 'fill_in_blanks')
                  handleFormChange('question_type', v)
                }}
                className="w-full"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Question Text *
            </label>
            <textarea
              value={formData.question_text}
              onChange={(e) => handleFormChange('question_text', e.target.value)}
              placeholder="Enter your question here..."
              rows={3}
              className="w-full px-3 py-2 border border-[var(--color-border-light)] rounded-md focus:outline-none focus:border-[var(--color-primary-500)]"
              required
            />
          </div>

          {/* Image Upload */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Question Images (Optional)
            </label>
            {imagePreviews.length > 0 ? (
              <div className="space-y-2">
                {imagePreviews.map((preview, index) => (
                  <div key={index} className="relative">
                    <img 
                      src={preview} 
                      alt={`Question preview ${index + 1}`} 
                      className="max-h-48 rounded-lg border border-[var(--color-border-light)]"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        setImagePreviews(prev => prev.filter((_, i) => i !== index))
                        setFormData(prev => ({ 
                          ...prev, 
                          images: prev.images?.filter((_, i) => i !== index) 
                        }))
                      }}
                      className="absolute top-2 right-2 p-1 bg-[var(--color-error-600)] text-white rounded-full hover:bg-[var(--color-error-600)]"
                    >
                      <Icon as={XCircle} size={16} />
                    </button>
                  </div>
                ))}
                <div className="relative">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageUpload}
                    className="hidden"
                    id="image-upload-more"
                  />
                  <label
                    htmlFor="image-upload-more"
                    className="flex items-center justify-center gap-2 w-full px-4 py-2 border-2 border-dashed border-[var(--color-border-medium)] rounded-lg cursor-pointer hover:border-[var(--color-primary-500)] hover:bg-[var(--color-bg-hover)] transition-colors"
                  >
                    <Icon as={Upload} size={18} className="text-[var(--color-text-muted)]" />
                    <span className="text-sm text-[var(--color-text-secondary)]">Add another image</span>
                  </label>
                </div>
                <button
                  type="button"
                  onClick={clearImages}
                  className="text-sm text-[var(--color-error-600)] hover:text-[var(--color-error-600)]"
                >
                  Clear all images
                </button>
              </div>
            ) : (
              <div className="relative">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageUpload}
                  className="hidden"
                  id="image-upload"
                />
                <label
                  htmlFor="image-upload"
                  className="flex items-center justify-center gap-2 w-full px-4 py-3 border-2 border-dashed border-[var(--color-border-medium)] rounded-lg cursor-pointer hover:border-[var(--color-primary-500)] hover:bg-[var(--color-bg-hover)] transition-colors"
                >
                  <Icon as={Upload} size={20} className="text-[var(--color-text-muted)]" />
                  <span className="text-sm text-[var(--color-text-secondary)]">Click to upload image (max 5MB)</span>
                </label>
              </div>
            )}
          </div>

          {formData.question_type === 'multiple_choice' && (
            <>
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                  Options *
                </label>
                <div className="space-y-2">
                  {formData.options?.map((option, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--color-text-muted)] w-8">
                        {String.fromCharCode(65 + index)}.
                      </span>
                      <Input
                        type="text"
                        value={option}
                        onChange={(e:any) => {
                          const newOptions = [...(formData.options || [])]
                          newOptions[index] = e.target.value
                          handleFormChange('options', newOptions)
                        }}
                        placeholder={`Option ${index + 1}`}
                        className="flex-1"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                  Correct Answer *
                </label>
                <Dropdown
                  options={formData.options?.filter(o => o.trim()).map((opt, idx) => ({
                    value: opt,
                    label: `${String.fromCharCode(65 + idx)}. ${opt}`
                  })) || []}
                  value={formData.correct_answer}
                  onChange={(v) => handleFormChange('correct_answer', v)}
                  placeholder="Select correct answer"
                  className="w-full"
                />
              </div>
            </>
          )}

          {formData.question_type === 'theory' && (
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Model Answer (Optional)
              </label>
              <textarea
                value={formData.correct_answer}
                onChange={(e:any) => handleFormChange('correct_answer', e.target.value)}
                placeholder="Enter model answer or key points..."
                rows={2}
                className="w-full px-3 py-2 border border-[var(--color-border-light)] rounded-md focus:outline-none focus:border-[var(--color-primary-500)]"
              />
            </div>
          )}

          {formData.question_type === 'fill_in_blanks' && (
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Correct Answer *
              </label>
              <textarea
                value={formData.correct_answer}
                onChange={(e:any) => handleFormChange('correct_answer', e.target.value)}
                placeholder="Enter the correct answer for the blank..."
                rows={2}
                className="w-full px-3 py-2 border border-[var(--color-border-light)] rounded-md focus:outline-none focus:border-[var(--color-primary-500)]"
                required
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Marks *
              </label>
              <Input
                type="number"
                value={formData.marks}
                onChange={(e:any) => handleFormChange('marks', parseInt(e.target.value) || 1)}
                min="1"
                className="w-full"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Order
              </label>
              <Input
                type="number"
                value={formData.order}
                onChange={(e:any) => handleFormChange('order', parseInt(e.target.value) || 1)}
                min="1"
                className="w-full"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setIsCreateModalOpen(false)
                setIsEditModalOpen(false)
                setEditingQuestion(null)
              }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              loading={formLoading}
              disabled={!formData.question_text || !formData.question_type || !formData.marks}
            >
              {isEditModalOpen ? 'Update Question' : 'Create Question'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteConfirmOpen}
        onClose={cancelDelete}
        title="Delete Question"
      >
        <div className="space-y-4">
          <p className="text-[var(--color-text-secondary)]">
            Are you sure you want to delete this question?
          </p>
          {questionToDelete && (
            <div className="p-3 bg-[var(--color-bg-subtle)] border border-[var(--color-border-light)] rounded-lg">
              <p className="text-sm font-medium text-[var(--color-text-primary)]">
                Question: {questionToDelete.text?.substring(0, 100)}{questionToDelete.text?.length > 100 ? '...' : ''}
              </p>
              <p className="text-sm text-[var(--color-text-secondary)]">
                Type: {questionToDelete.qtype === 'multiple_choice' ? 'Multiple Choice' : questionToDelete.qtype === 'fill_in_blanks' ? 'Fill in Blanks' : 'Theory'}
              </p>
            </div>
          )}
          <div className="flex gap-3 justify-end">
            <Button
              variant="secondary"
              onClick={cancelDelete}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={confirmDeleteQuestion}
            >
              Delete Question
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
