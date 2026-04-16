import React, { useState } from 'react'
import { motion } from 'framer-motion'
import Icon from '@/components/Icon'

export interface TabItem {
  id: string
  label: string
  content: React.ReactNode
  icon?: React.ComponentType<any>
  badge?: string | number
}

interface TabsProps {
  tabs: TabItem[]
  defaultTab?: string
  activeTab?: string
  onChange?: (tabId: string) => void
  className?: string
  variant?: 'default' | 'pills' | 'underline'
}

export default function Tabs({ 
  tabs, 
  defaultTab, 
  activeTab: controlledActiveTab,
  onChange,
  className = '',
  variant = 'default'
}: TabsProps) {
  const [internalActiveTab, setInternalActiveTab] = useState(defaultTab || tabs[0]?.id || '')
  
  const isControlled = controlledActiveTab !== undefined
  const activeTab = isControlled ? controlledActiveTab : internalActiveTab

  const handleTabChange = (tabId: string) => {
    if (!isControlled) {
      setInternalActiveTab(tabId)
    }
    onChange?.(tabId)
  }

  const getTabStyles = () => {
    switch (variant) {
      case 'pills':
        return {
          container: 'bg-[var(--color-bg-card)] rounded-xl shadow-sm border border-[var(--color-border-light)] overflow-hidden',
          tabList: 'flex space-x-1 bg-[var(--color-primary-50)] p-1.5 border-b border-[var(--color-border-light)]',
          tabButton: 'px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 flex items-center gap-2',
          activeTab: 'bg-[var(--color-bg-card)] text-[var(--color-accent-coral-500)] shadow-sm border border-[var(--color-accent-coral-400)]',
          inactiveTab: 'text-[var(--color-text-secondary)] hover:text-[var(--color-accent-coral-500)] hover:bg-[var(--color-accent-coral-50)]/30',
          content: 'p-6'
        }
      case 'underline':
        return {
          container: 'bg-[var(--color-bg-card)] rounded-xl shadow-sm border border-[var(--color-border-light)] overflow-hidden',
          tabList: 'flex border-b border-[var(--color-border-light)] bg-[var(--color-bg-subtle)]/50',
          tabButton: 'px-6 py-4 text-sm font-medium border-b-2 transition-all duration-200 flex items-center gap-2',
          activeTab: 'border-[var(--color-accent-coral-500)] text-[var(--color-accent-coral-500)] bg-[var(--color-bg-card)] font-medium',
          inactiveTab: 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:border-[var(--color-border-medium)] hover:bg-[var(--color-bg-subtle)]',
          content: 'p-6'
        }
      default:
        return {
          container: 'bg-[var(--color-bg-card)] rounded-xl shadow-sm border border-[var(--color-border-light)] overflow-hidden',
          tabList: 'flex space-x-1 bg-[var(--color-bg-subtle)]/80 p-2 border-b border-[var(--color-border-light)]',
          tabButton: 'px-4 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 flex items-center gap-2',
          activeTab: 'bg-[var(--color-bg-card)] text-[var(--color-accent-coral-500)] shadow-sm border border-[var(--color-accent-coral-400)]',
          inactiveTab: 'text-[var(--color-text-secondary)] hover:text-[var(--color-accent-coral-500)] hover:bg-[var(--color-accent-coral-50)]/30',
          content: 'p-6'
        }
    }
  }

  const styles = getTabStyles()
  const activeTabData = tabs.find(tab => tab.id === activeTab)

  return (
    <div className={`${styles.container} ${className}`}>
      {/* Tab Navigation */}
      <div className={styles.tabList}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={`
              ${styles.tabButton}
              ${activeTab === tab.id ? styles.activeTab : styles.inactiveTab}
              relative
            `}
          >
            {tab.icon && (
              <Icon 
                as={tab.icon} 
                size={16} 
                className={activeTab === tab.id ? 'text-[var(--color-accent-coral-500)]' : 'text-[var(--color-text-muted)]'} 
              />
            )}
            <span>{tab.label}</span>
            {tab.badge && (
              <span className={`
                ml-1.5 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
                ${activeTab === tab.id 
                  ? 'bg-[var(--color-accent-coral-50)] text-[var(--color-accent-coral-600)]' 
                  : 'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)]'}
              `}>
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className={styles.content}
      >
        {activeTabData?.content}
      </motion.div>
    </div>
  )
}
