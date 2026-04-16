import client, { handleEnvelope, handlePaginatedEnvelope } from '@/apis/client'
import type { Question } from '@/lib/types'

export async function createQuestion(payload: Record<string, any>) {
	const resp = await client.post('/academic/questions/', payload)
	return handleEnvelope<Question>(resp)
}

export async function uploadQuestions(payload: { pages: string[]; exam_id: string; industry?: string; mark_per_question?: number }) {
	const resp = await client.post('/academic/questions/upload', payload)
	return handleEnvelope<any>(resp)
}

export async function listQuestions(params?: { page?: number; per_page?: number; exam_id?: string; tenant_id?: string }) {
	const resp = await client.get('/academic/questions/', { params })
	return handlePaginatedEnvelope<Question>(resp)
}

export async function getQuestion(questionId: string) {
	const resp = await client.get(`/academic/questions/${questionId}`)
	return handleEnvelope<Question>(resp)
}

export async function updateQuestion(questionId: string, payload: Record<string, any>) {
	const resp = await client.put(`/academic/questions/${questionId}`, payload)
	return handleEnvelope<Question>(resp)
}

export async function getExamQuestions(examId: string) {
	const resp = await client.get(`/academic/questions/exam/${examId}`)
	return handleEnvelope<any>(resp)
}

export default { createQuestion, uploadQuestions, listQuestions, getQuestion, updateQuestion, getExamQuestions }
