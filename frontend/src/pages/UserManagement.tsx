import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Users, Plus, Edit, Trash2, Search, Filter, UserPlus, GraduationCap, BookOpen, AlertCircle, Pencil } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Icon from '@/components/Icon'
import { useAuth } from '@/contexts/AuthContext'
import * as authApi from '@/apis/auth'
import type { User } from '@/lib/types'
import Pagination from '@/components/Pagination'
import SearchInput from '@/components/SearchInput'
import Dropdown from '@/components/Dropdown'
import Button from '@/components/Button'
import { Modal } from '@/components/Modal'
import Input from '@/components/Input'
import { StatusBadge } from '@/components/StatusBadge'
import Table from '@/components/Table'
import Breadcrumbs from '@/components/Breadcrumbs'
import { EmptyState } from '@/components/EmptyState'
import UserManagementSkeleton from './UserManagementSkeleton'
import { config } from '@/config'

type RoleFilter = User['role'] | 'all'

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-[var(--color-premium-100)] text-[var(--color-premium-600)] border-[var(--color-premium-100)]',
  lecturer: 'bg-[var(--color-primary-50)] text-[var(--color-primary-600)] border-[var(--color-border-light)]',
  student: 'bg-[var(--color-success-100)] text-[var(--color-success-600)] border-[var(--color-success-100)]',
}

const ROLE_ICONS: Record<string, React.ElementType> = {
  admin: Users,
  lecturer: GraduationCap,
  student: BookOpen,
}

function fullName(u: User) {
  return [u.first_name, u.middle_name, u.last_name].filter(Boolean).join(' ')
}

function getInitials(u: User): string {
  const first = u.first_name?.[0] || ''
  const last = u.last_name?.[0] || ''
  return (first + last).toUpperCase() || '?'
}

function UserAvatar({ user, size = 40 }: { user: User; size?: number }) {
  const initials = getInitials(user)

  if (user.avatar) {
    return (
      <img
        src={user.avatar}
        alt={fullName(user)}
        className="rounded-lg object-cover"
        style={{ width: size, height: size }}
      />
    )
  }

  return (
    <div
      className="bg-[var(--color-primary-50)] rounded-lg flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <span className="text-sm font-semibold text-[var(--color-primary-600)]">{initials}</span>
    </div>
  )
}

export function UserManagement() {
  const { user: currentUser } = useAuth()

  // Pagination
  const [page, setPage] = useState(1)
  const [perPage] = useState(10)

  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRole, setSelectedRole] = useState<RoleFilter>('all')
  const [selectedStatus, setSelectedStatus] = useState<'all' | 'active' | 'inactive'>('all')

  // Create modal
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState({ first_name: '', last_name: '', email: '', password: '', role: 'student' as User['role'] })
  const [createLoading, setCreateLoading] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  // Edit modal
  const [editUser, setEditUser] = useState<User | null>(null)
  const [editForm, setEditForm] = useState({ first_name: '', middle_name: '', last_name: '', is_active: true })
  const [editLoading, setEditLoading] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  // React Query hook for fetching users - automatically deduplicates requests
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['users', page, perPage, currentUser?.tenant_id],
    queryFn: async () => {
      const res = await authApi.listUsers({
        page,
        per_page: perPage,
        tenant_id: currentUser?.tenant_id || undefined
      })
      return res
    },
    enabled: !!currentUser,
    staleTime: config.QUERY_CACHE_USERS, // 2 minutes - users are relatively static
  })

  const users = data?.items || []
  const totalPages = data?.pagination?.pages || 1
  const hasNext = data?.pagination?.has_next || false
  const hasPrev = data?.pagination?.has_prev || false
  const total = data?.pagination?.total || 0

  const goNext = () => setPage(p => p + 1)
  const goPrev = () => setPage(p => Math.max(1, p - 1))

  // Filtered view (client-side search/role/status filter on current page)
  const filtered = users.filter(u => {
    const name = fullName(u).toLowerCase()
    const matchSearch = name.includes(searchQuery.toLowerCase()) || u.email.toLowerCase().includes(searchQuery.toLowerCase())
    const matchRole = selectedRole === 'all' || u.role === selectedRole
    const matchStatus = selectedStatus === 'all' || (selectedStatus === 'active' ? u.is_active : !u.is_active)
    return matchSearch && matchRole && matchStatus
  })

  // Create
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreateError(null)
    setCreateLoading(true)
    try {
      await authApi.register({
        first_name: createForm.first_name,
        last_name: createForm.last_name,
        email: createForm.email,
        password: createForm.password,
        role: createForm.role,
        tenant_id: currentUser?.tenant_id ?? undefined,
      })
      setCreateOpen(false)
      setCreateForm({ first_name: '', last_name: '', email: '', password: '', role: 'student' })
      // reset to first page and refetch
      setPage(1)
      refetch()
    } catch (e: unknown) {
      setCreateError(e instanceof Error ? e.message : 'Failed to create user')
    } finally {
      setCreateLoading(false)
    }
  }

  // Edit
  const openEdit = (u: User) => {
    setEditUser(u)
    setEditForm({ first_name: u.first_name, middle_name: u.middle_name ?? '', last_name: u.last_name, is_active: u.is_active })
    setEditError(null)
  }

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editUser) return
    setEditError(null)
    setEditLoading(true)
    try {
      await authApi.updateUser(editUser.id, {
        first_name: editForm.first_name,
        middle_name: editForm.middle_name || undefined,
        last_name: editForm.last_name,
        is_active: editForm.is_active,
      })
      setEditUser(null)
      refetch()
    } catch (e: unknown) {
      setEditError(e instanceof Error ? e.message : 'Failed to update user')
    } finally {
      setEditLoading(false)
    }
  }

  // Delete
  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleteLoading(true)
    try {
      await authApi.deleteUser(deleteTarget.id)
      setDeleteTarget(null)
      refetch()
    } catch (e: unknown) {
      setDeleteError(e instanceof Error ? e.message : 'Failed to delete user')
      setDeleteTarget(null)
    } finally {
      setDeleteLoading(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <Breadcrumbs />
        <Button className="flex items-center gap-2" onClick={() => setCreateOpen(true)}>
          <Icon as={UserPlus} size={16} />
          Add User
        </Button>
      </div>

      <div className="flex gap-3 mb-5">
        <SearchInput
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder="Search by name or email..."
          className="flex-1 max-w-sm"
        />
        <Dropdown
          options={[
            { value: 'all', label: 'All Roles' },
            { value: 'admin', label: 'Admins' },
            { value: 'lecturer', label: 'Lecturers' },
            { value: 'student', label: 'Students' },
          ]}
          value={selectedRole}
          onChange={(v: string) => setSelectedRole(v as RoleFilter)}
        />
        <Dropdown
          options={[
            { value: 'all', label: 'All Status' },
            { value: 'active', label: 'Active' },
            { value: 'inactive', label: 'Inactive' },
          ]}
          value={selectedStatus}
          onChange={(v: string) => setSelectedStatus(v as 'all' | 'active' | 'inactive')}
          placeholder="Filter by status"
          className="w-40"
        />
      </div>

      {error && (
        <div className="mb-4 p-4 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg flex items-center gap-2">
          <Icon as={AlertCircle} size={16} className="text-[var(--color-error-600)] shrink-0" />
          <p className="text-sm text-[var(--color-error-600)] flex-1">{error.message || 'Failed to load users'}</p>
          <Button variant="ghost" onClick={() => refetch()}>Retry</Button>
        </div>
      )}

      {isLoading ? (
        <UserManagementSkeleton />
      ) : (
        <div className="bg-[var(--color-bg-card)] rounded-xl shadow-sm overflow-hidden">
          {/* Desktop Table - hidden on small screens */}
          <div className="hidden md:block">
            <Table>
              <thead className="bg-[var(--color-bg-hover)] border-b border-[var(--color-border-light)]">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-[var(--color-text-primary)]">User</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-[var(--color-text-primary)]">Role</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-[var(--color-text-primary)]">Status</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-[var(--color-text-primary)]">Created</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-[var(--color-text-primary)]">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border-light)]">
                {filtered.map((u, idx) => {
                  const RoleIcon = ROLE_ICONS[u.role] ?? Users
                  return (
                    <motion.tr
                      key={u.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.03 }}
                      className="hover:bg-[var(--color-bg-hover)] transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <UserAvatar user={u} size={40} />
                          <div>
                            <p className="font-medium text-[var(--color-text-primary)]">{fullName(u)}</p>
                            <p className="text-xs text-[var(--color-text-muted)]">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border ${ROLE_COLORS[u.role] ?? 'bg-[var(--color-bg-subtle)] text-[var(--color-text-secondary)] border-[var(--color-border-light)]'}`}>
                          <Icon as={RoleIcon} size={11} />
                          {u.role.charAt(0).toUpperCase() + u.role.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={u.is_active ? 'active' : 'inactive'} size="sm" />
                      </td>
                      <td className="px-6 py-4 text-sm text-[var(--color-text-secondary)]">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2">
                          <Button variant="secondary" onClick={() => openEdit(u)} className="flex items-center gap-1 text-xs py-1.5 px-3">
                            <Pencil size={13} /> Edit
                          </Button>
                          {u.id !== currentUser?.id && (
                            <Button variant="danger" onClick={() => setDeleteTarget(u)} className="flex items-center gap-1 text-xs py-1.5 px-3">
                              <Trash2 size={13} /> Remove
                            </Button>
                          )}
                        </div>
                      </td>
                    </motion.tr>
                  )
                })}
              </tbody>
            </Table>
          </div>

          {/* Mobile Cards - shown only on small screens */}
          <div className="md:hidden space-y-3 p-4">
            {filtered.map((u, idx) => {
              const RoleIcon = ROLE_ICONS[u.role] ?? Users
              return (
                <motion.div
                  key={u.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.03 }}
                  className="bg-[var(--color-bg-card)] border border-[var(--color-border-light)] rounded-lg p-4 space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <UserAvatar user={u} size={40} />
                      <div>
                        <p className="font-medium text-[var(--color-text-primary)]">{fullName(u)}</p>
                        <p className="text-xs text-[var(--color-text-muted)]">{u.email}</p>
                      </div>
                    </div>
                    <StatusBadge status={u.is_active ? 'active' : 'inactive'} size="sm" />
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border ${ROLE_COLORS[u.role] ?? 'bg-[var(--color-bg-subtle)] text-[var(--color-text-secondary)] border-[var(--color-border-light)]'}`}>
                      <Icon as={RoleIcon} size={11} />
                      {u.role.charAt(0).toUpperCase() + u.role.slice(1)}
                    </span>
                    <span className="text-xs text-[var(--color-text-muted)]">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                    </span>
                  </div>
                  
                  <div className="flex gap-2 pt-2 border-t border-[var(--color-border-light)]">
                    <Button variant="secondary" onClick={() => openEdit(u)} className="flex-1 flex items-center justify-center gap-1 text-xs py-2">
                      <Pencil size={13} /> Edit
                    </Button>
                    {u.id !== currentUser?.id && (
                      <Button variant="danger" onClick={() => setDeleteTarget(u)} className="flex-1 flex items-center justify-center gap-1 text-xs py-2">
                        <Trash2 size={13} /> Remove
                      </Button>
                    )}
                  </div>
                </motion.div>
              )
            })}
          </div>

          {filtered.length === 0 && !isLoading && (
            <EmptyState
              icon={Users}
              title="No Users Found"
              description={searchQuery || selectedRole !== 'all' || selectedStatus !== 'all' ? 'No users match your filters.' : 'No users yet.'}
              action={{ label: 'Add User', onClick: () => setCreateOpen(true) }}
            />
          )}
        </div>
      )}

      <Pagination
        currentPage={page}
        totalPages={totalPages}
        hasNext={hasNext}
        hasPrev={hasPrev}
        onNext={goNext}
        onPrev={goPrev}
        onPageChange={setPage}
      />

      {/* Create User Modal */}
      <Modal isOpen={createOpen} onClose={() => { setCreateOpen(false); setCreateError(null) }} title="Add New User">
        <form onSubmit={handleCreate} className="space-y-4">
          {createError && (
            <div className="p-3 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg text-sm text-[var(--color-error-600)]">{createError}</div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">First Name</label>
              <Input value={createForm.first_name} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateForm(p => ({ ...p, first_name: e.target.value }))} placeholder="First name" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">Last Name</label>
              <Input value={createForm.last_name} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateForm(p => ({ ...p, last_name: e.target.value }))} placeholder="Last name" required />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">Email</label>
            <Input type="email" value={createForm.email} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateForm(p => ({ ...p, email: e.target.value }))} placeholder="user@example.com" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">Role</label>
            <Dropdown
              options={[{ value: 'student', label: 'Student' }, { value: 'lecturer', label: 'Lecturer' }, { value: 'admin', label: 'Admin' }]}
              value={createForm.role}
              onChange={(v: string) => setCreateForm(p => ({ ...p, role: v as User['role'] }))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">Password</label>
            <Input type="password" value={createForm.password} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateForm(p => ({ ...p, password: e.target.value }))} placeholder="Min 8 characters" required />
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="secondary" type="button" className="flex-1" onClick={() => setCreateOpen(false)} disabled={createLoading}>Cancel</Button>
            <Button type="submit" className="flex-1" loading={createLoading} disabled={!createForm.first_name || !createForm.last_name || !createForm.email || !createForm.password}>Create User</Button>
          </div>
        </form>
      </Modal>

      {/* Edit User Modal */}
      <Modal isOpen={!!editUser} onClose={() => setEditUser(null)} title="Edit User">
        <form onSubmit={handleEdit} className="space-y-4">
          {editError && (
            <div className="p-3 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg text-sm text-[var(--color-error-600)]">{editError}</div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">First Name</label>
              <Input value={editForm.first_name} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm(p => ({ ...p, first_name: e.target.value }))} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">Last Name</label>
              <Input value={editForm.last_name} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm(p => ({ ...p, last_name: e.target.value }))} required />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">Middle Name (optional)</label>
            <Input value={editForm.middle_name} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditForm(p => ({ ...p, middle_name: e.target.value }))} placeholder="Optional" />
          </div>
          <div className="flex items-center gap-3">
            <input id="edit_active" type="checkbox" checked={editForm.is_active} onChange={(e) => setEditForm(p => ({ ...p, is_active: e.target.checked }))} className="w-4 h-4 rounded border-[var(--color-border-medium)] text-[var(--color-primary-600)] focus:ring-royal-500" />
            <label htmlFor="edit_active" className="text-sm font-medium text-[var(--color-text-secondary)]">Active</label>
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="secondary" type="button" className="flex-1" onClick={() => setEditUser(null)} disabled={editLoading}>Cancel</Button>
            <Button type="submit" className="flex-1" loading={editLoading}>Save Changes</Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirm Modal */}
      <Modal isOpen={!!deleteTarget} onClose={() => { setDeleteTarget(null); setDeleteError(null) }} title="Remove User">
        {deleteError && (
          <div className="mb-4 p-3 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg text-sm text-[var(--color-error-600)]">{deleteError}</div>
        )}
        <p className="text-[var(--color-text-secondary)] mb-6">
          Are you sure you want to remove <span className="font-semibold">{deleteTarget ? fullName(deleteTarget) : ''}</span>? This action cannot be undone.
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" className="flex-1" onClick={() => { setDeleteTarget(null); setDeleteError(null) }} disabled={deleteLoading}>Cancel</Button>
          <Button variant="danger" className="flex-1" loading={deleteLoading} onClick={handleDelete}>Remove</Button>
        </div>
      </Modal>
    </div>
  )
}
