import client from './client'

/**
 * Simple health check to test backend connectivity
 */
export async function healthCheck() {
  try {
    // Use absolute URL for health check since it doesn't have /api/v1 prefix
    const response = await client.get('/health', { baseURL: 'http://localhost:8000' })
    return { success: true, data: response.data }
  } catch (error) {
    console.error('Health check failed:', error)
    return { 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error',
      status: (error as any)?.response?.status || null
    }
  }
}

/**
 * Test API connectivity and show helpful error messages
 */
export async function testApiConnection() {
  console.log('Testing API connection...')
  console.log('API Base URL:', client.defaults.baseURL)
  
  const result = await healthCheck()
  
  if (result.success) {
    console.log('✅ API connection successful')
    console.log('✅ Backend health check passed:', result.data)
    return true
  } else {
    console.error('❌ API connection failed:', result.error)
    
    if (result.status === 404) {
      console.error('💡 The backend server may not be running or the health endpoint is incorrect')
      console.error('💡 Expected health endpoint: /health')
      console.error('💡 Make sure the backend server is running on http://localhost:8000')
    } else if (result.error && result.error.includes('Network error')) {
      console.error('💡 Network error - check if backend server is running')
    } else if (result.error && result.error.includes('ERR_CONNECTION_REFUSED')) {
      console.error('💡 Connection refused - backend server may not be running')
    }
    
    return false
  }
}

export default { healthCheck, testApiConnection }
