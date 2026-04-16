import React, { useState, KeyboardEvent } from 'react'
import { Search } from 'lucide-react'
import Icon from './Icon'
import Input from './Input'
import Button from './Button'

type Props = {
  value?: string
  onChange?: (value: string) => void
  onSearch?: (value: string) => void
  placeholder?: string
  disabled?: boolean
  className?: string
  inputClassName?: string
  'aria-label'?: string
}

export default function SearchInput({
  value = '',
  onChange,
  onSearch,
  placeholder = 'Search...',
  disabled = false,
  className = '',
  inputClassName = '',
  'aria-label': ariaLabel = 'Search',
}: Props) {
  const [internalValue, setInternalValue] = useState(value)

  // Use controlled or uncontrolled value
  const currentValue = onChange !== undefined ? value : internalValue

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    if (onChange) {
      onChange(newValue)
    } else {
      setInternalValue(newValue)
    }
  }

  const handleSearch = () => {
    onSearch?.(currentValue)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div className={`flex items-center gap-2 ${className}`} role="search">
      <div className="relative flex-1">
        <Icon 
          as={Search} 
          size={16} 
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] pointer-events-none"
        />
        <Input
          type="text"
          value={currentValue}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={`pl-10 ${inputClassName}`}
          disabled={disabled}
          aria-label={ariaLabel}
        />
      </div>
      <Button
        onClick={handleSearch}
        disabled={disabled}
        aria-label={`${ariaLabel} button`}
        variant="primary"
        size="md"
      >
        <Icon as={Search} size={16} className="mr-2" />
        Search
      </Button>
    </div>
  )
}
