import React from 'react'
import { motion } from 'framer-motion'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import Button from './Button'
import Icon from './Icon'

type Props = {
  currentPage?: number
  totalPages?: number
  hasNext: boolean
  hasPrev: boolean
  onNext: () => void
  onPrev: () => void
  onPageChange?: (page: number) => void
  loading?: boolean
}

export default function Pagination({ 
  currentPage = 1,
  totalPages = 1,
  hasNext, 
  hasPrev, 
  onNext, 
  onPrev, 
  onPageChange,
  loading = false, 
}: Props) {
  const getVisiblePages = () => {
    const pages: number[] = []
    const maxVisible = 5
    
    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i)
      }
    } else {
      // Calculate window to always show 5 pages
      let start = Math.max(1, currentPage - 2)
      let end = start + maxVisible - 1
      
      // Adjust if window exceeds total pages
      if (end > totalPages) {
        end = totalPages
        start = Math.max(1, end - maxVisible + 1)
      }
      
      for (let i = start; i <= end; i++) {
        pages.push(i)
      }
    }
    
    return pages
  }

  const visiblePages = getVisiblePages()

  return (
    <div className="flex items-center justify-center mt-6 gap-1">
      <div className="flex items-center gap-1">
          {/* Previous button */}
          <Button 
            variant="secondary" 
            onClick={onPrev} 
            disabled={!hasPrev || loading}
            className="p-2 w-10 h-10"
          >
            <Icon as={ChevronLeft} size={16} />
          </Button>

          {/* Page numbers */}
          <div className="flex items-center gap-1">
            {visiblePages.map((page, index) => (
              <motion.div
                key={page}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.03 }}
              >
                <Button
                  variant={currentPage === page ? 'primary' : 'ghost'}
                  onClick={() => onPageChange(page)}
                  className="p-2 w-10 h-10"
                  noMotion
                >
                  {page}
                </Button>
              </motion.div>
            ))}
          </div>

          {/* Next button */}
          <Button 
            variant="secondary" 
            onClick={onNext} 
            disabled={!hasNext || loading}
            className="p-2 w-10 h-10"
          >
            <Icon as={ChevronRight} size={16} />
          </Button>
        </div>
    </div>
  )
}
