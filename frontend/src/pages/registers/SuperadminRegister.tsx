import React from 'react'
import { Register } from '@/pages/Register'

// Superadmin may be treated same as admin at frontend but kept separate for clarity
export default function SuperadminRegister() {
  return <Register defaultRole="admin" hideRoleSelector />
}
