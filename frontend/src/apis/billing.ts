/**
 * Billing API functions
 * All routes under /api/v1/billing/
 */
import client, { handleEnvelope, handlePaginatedEnvelope, ApiError } from '@/apis/client'
import type { Invoice, CurrentUsage, PaymentMethod } from '@/lib/types'

export type { Invoice, CurrentUsage, PaymentMethod }

export interface BillingPlan {
  id: string
  name: string
  plan_type: string
  price_per_student: number
  max_students: number | null
  max_exams: number | null
  features: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface BillingListParams {
  page?: number
  per_page?: number
  tenant_id?: string
}

export interface BillingListResponse<T> {
  items: T[]
  pagination: {
    page: number
    per_page: number
    total: number
    pages: number
    has_next: boolean
    has_prev: boolean
  }
}

/** Extract error message from API error */
function extractMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message
  const e = error as any
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string') return detail
  const apiError = e?.response?.data?.error
  if (typeof apiError === 'string') return apiError
  if (e?.message) return e.message
  return fallback
}

// ─── Invoices ────────────────────────────────────────────────────────────────

export async function listInvoices(params?: BillingListParams): Promise<BillingListResponse<Invoice>> {
  try {
    const response = await client.get('/billing/invoices', { params })
    return handlePaginatedEnvelope<Invoice>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch invoices'))
  }
}

export async function getInvoice(invoiceId: string): Promise<Invoice> {
  if (!invoiceId) throw new ApiError('Invoice ID is required', 400)
  try {
    const response = await client.get(`/billing/invoices/${invoiceId}`)
    return handleEnvelope<Invoice>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch invoice'))
  }
}

// ─── Billing Plans ────────────────────────────────────────────────────────────

export async function listBillingPlans(params?: BillingListParams): Promise<BillingListResponse<BillingPlan>> {
  try {
    const response = await client.get('/billing/plans', { params })
    return handlePaginatedEnvelope<BillingPlan>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch billing plans'))
  }
}

export async function getBillingPlan(planId: string): Promise<BillingPlan> {
  if (!planId) throw new ApiError('Plan ID is required', 400)
  try {
    const response = await client.get(`/billing/plans/${planId}`)
    return handleEnvelope<BillingPlan>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch billing plan'))
  }
}

// ─── Payment Methods ──────────────────────────────────────────────────────────

export async function listPaymentMethods(params?: BillingListParams): Promise<BillingListResponse<PaymentMethod>> {
  try {
    const response = await client.get('/billing/payment-methods', { params })
    return handlePaginatedEnvelope<PaymentMethod>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch payment methods'))
  }
}

// ─── Usage ────────────────────────────────────────────────────────────────────

export async function getUsage(tenantId?: string): Promise<CurrentUsage> {
  try {
    const params = tenantId ? { tenant_id: tenantId } : undefined
    const response = await client.get('/billing/usage', { params })
    return handleEnvelope<CurrentUsage>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch usage'))
  }
}

export default {
  listInvoices,
  getInvoice,
  listBillingPlans,
  getBillingPlan,
  listPaymentMethods,
  getUsage,
}
