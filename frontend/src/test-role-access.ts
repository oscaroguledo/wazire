// Role-Based Access Control Test Script
// This script helps verify that the frontend properly implements role-based access control

import { UserRole } from '@/lib/types';

export interface RoleAccessTest {
  role: UserRole;
  allowedRoutes: string[];
  deniedRoutes: string[];
  description: string;
}

export const roleAccessTests: RoleAccessTest[] = [
  {
    role: 'student',
    allowedRoutes: [
      '/dashboard',
      '/courses', // Can view enrolled courses
      '/courses/:id', // Can view course details
      '/exams', // Can view available exams
      '/exams/:id', // Can view exam details
      '/exams/:id/take', // Can take exams
      '/submissions'
    ],
    deniedRoutes: [
      '/tenants',
      '/tenants/create'
    ],
    description: 'Students can view enrolled courses, available exams, take exams, and view submissions'
  },
  {
    role: 'lecturer',
    allowedRoutes: [
      '/dashboard',
      '/courses',
      '/courses/:id',
      '/exams',
      '/exams/:id',
      '/submissions'
    ],
    deniedRoutes: [
      '/exams/:id/take', // Cannot take exams, only create/manage
      '/tenants',
      '/tenants/create'
    ],
    description: 'Lecturers can manage courses, exams, and view submissions'
  },
  {
    role: 'admin',
    allowedRoutes: [
      '/dashboard',
      '/courses',
      '/courses/:id',
      '/exams',
      '/exams/:id',
      '/submissions',
      '/tenants',
      '/tenants/create'
    ],
    deniedRoutes: [
      '/exams/:id/take' // Admin typically doesn't take exams
    ],
    description: 'Admins have full access to all management features'
  }
];

export function testRoleBasedAccess() {
  console.log('🔍 Testing Role-Based Access Control...\n');
  
  roleAccessTests.forEach(test => {
    console.log(`📋 ${test.description}`);
    console.log(`   Role: ${test.role}`);
    console.log(`   ✅ Allowed Routes: ${test.allowedRoutes.join(', ')}`);
    console.log(`   ❌ Denied Routes: ${test.deniedRoutes.join(', ')}\n`);
  });
  
  console.log('🎯 Manual Testing Instructions:');
  console.log('1. Login as a student and verify you can only access allowed routes');
  console.log('2. Login as a lecturer and verify you can manage courses/exams but not tenants');
  console.log('3. Login as an admin and verify you have full access');
  console.log('4. Try accessing denied routes and verify you see the Access Denied page');
  console.log('5. Verify navigation menu only shows relevant options for each role');
}

export function validateNavigationMenu() {
  console.log('\n🧭 Navigation Menu Validation:');
  console.log('Student should see: Dashboard, Courses, Exams, Submissions');
  console.log('Lecturer should see: Dashboard, Courses, Exams, Submissions');
  console.log('Admin should see: Dashboard, Courses, Exams, Submissions, Tenants');
}

// Test API endpoint permissions
export const apiEndpointTests = {
  student: {
    canAccess: [
      'GET /api/v1/academic/submissions',
      'GET /api/v1/academic/exams/:id/take'
    ],
    cannotAccess: [
      'POST /api/v1/academic/courses',
      'PUT /api/v1/academic/courses/:id',
      'DELETE /api/v1/academic/courses/:id',
      'POST /api/v1/academic/exams',
      'PUT /api/v1/academic/exams/:id',
      'DELETE /api/v1/academic/exams/:id',
      'GET /api/v1/tenants',
      'POST /api/v1/tenants'
    ]
  },
  lecturer: {
    canAccess: [
      'GET /api/v1/academic/courses',
      'POST /api/v1/academic/courses',
      'PUT /api/v1/academic/courses/:id',
      'GET /api/v1/academic/exams',
      'POST /api/v1/academic/exams',
      'PUT /api/v1/academic/exams/:id',
      'GET /api/v1/academic/submissions'
    ],
    cannotAccess: [
      'DELETE /api/v1/academic/courses/:id', // May need admin approval
      'DELETE /api/v1/academic/exams/:id', // May need admin approval
      'GET /api/v1/tenants',
      'POST /api/v1/tenants',
      'PUT /api/v1/tenants/:id',
      'DELETE /api/v1/tenants/:id'
    ]
  },
  admin: {
    canAccess: [
      'ALL ENDPOINTS' // Full access
    ],
    cannotAccess: []
  }
};
