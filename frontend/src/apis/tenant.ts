import client, { handleEnvelope, handlePaginatedEnvelope } from '@/apis/client'
import type { Tenant, User } from '@/lib/types'

export async function createTenant(payload: Record<string, any>) {
	const resp = await client.post('/tenants/', payload)
	return handleEnvelope<Tenant>(resp)
}

export async function listTenants(params?: { page?: number; per_page?: number }) {
	const resp = await client.get('/tenants/', { params })
	return handlePaginatedEnvelope<Tenant>(resp)
}

export async function getTenant(tenantId: string) {
	const resp = await client.get(`/tenants/${tenantId}`)
	return handleEnvelope<Tenant>(resp)
}

export async function updateTenant(tenantId: string, payload: Record<string, any>) {
	const resp = await client.put(`/tenants/${tenantId}`, payload)
	return handleEnvelope<Tenant>(resp)
}

export async function deleteTenant(tenantId: string) {
	const resp = await client.delete(`/tenants/${tenantId}`)
	return handleEnvelope<void>(resp)
}

export async function getTenantUsers(tenantId: string, params?: { page?: number; per_page?: number }) {
	const resp = await client.get(`/tenants/${tenantId}/users`, { params })
	return handlePaginatedEnvelope<User>(resp)
}

export async function getTenantStats(tenantId: string) {
	const resp = await client.get(`/tenants/${tenantId}/stats`)
	return handleEnvelope<any>(resp)
}

export default { createTenant, listTenants, getTenant, updateTenant, deleteTenant, getTenantUsers, getTenantStats }
