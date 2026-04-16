import React, { useEffect, useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { FileText } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import Card from '@/components/Card'
import Pagination from '@/components/Pagination'
import * as questionApi from '@/apis/question'
import Breadcrumbs from '@/components/Breadcrumbs'

export default function QuestionsPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [pageSize] = useState(10)
  const [currentPage, setCurrentPage] = useState(1)
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: pageSize,
    total: 0,
    pages: 0,
    has_next: false,
    has_prev: false,
  })

  // Ref to prevent duplicate API calls in React 18 Strict Mode
  const initialFetchDone = useRef(false)

  useEffect(() => {
    // Prevent duplicate fetches in React 18 Strict Mode
    if (initialFetchDone.current && currentPage === 1) return
    initialFetchDone.current = true
    fetchQuestions(currentPage, pageSize)
  }, [currentPage, pageSize])

  const fetchQuestions = async (page = 1, per_page = pageSize) => {
    setLoading(true)
    try {
      const res = await questionApi.listQuestions({ page, per_page })
      setItems(res.items || [])
      setPagination(res.pagination || {
        page: 1,
        per_page: per_page,
        total: res.items?.length || 0,
        pages: 1,
        has_next: false,
        has_prev: false,
      })
    } catch (e) { 
      console.error(e) 
      setItems([])
      setPagination({
        page: 1,
        per_page: per_page,
        total: 0,
        pages: 1,
        has_next: false,
        has_prev: false,
      })
    } finally {
      setLoading(false)
    }
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const handleNextPage = () => {
    if (pagination.has_next) {
      fetchQuestions(currentPage + 1, pageSize)
      setCurrentPage(currentPage + 1)
    }
  }

  const handlePrevPage = () => {
    if (currentPage > 1) {
      fetchQuestions(currentPage - 1, pageSize)
      setCurrentPage(currentPage - 1)
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Questions</h1>
        <p className="text-[var(--color-text-secondary)]">Manage question bank</p>
      </div>

      <Breadcrumbs />

      {items.length === 0 ? (
        <div className="p-12">
          <EmptyState
            icon={FileText}
            title="No Questions"
            description="No questions found. Create or import questions to populate the bank."
            action={{ label: 'Import Questions', onClick: () => navigate('/questions') }}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map((q) => (
            <motion.div key={q.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <Card>
                <h3 className="font-semibold text-[var(--color-text-primary)]">{q.number}. {q.text}</h3>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      <div className="mt-6">
        <Pagination
          currentPage={pagination.page}
          totalPages={pagination.pages}
          hasNext={pagination.has_next}
          hasPrev={pagination.has_prev}
          onNext={handleNextPage}
          onPrev={handlePrevPage}
          onPageChange={handlePageChange}
        />
      </div>
    </div>
  )
}
