// 13.2: Added 'superadmin' to UserRole
export type UserRole = 'admin' | 'lecturer' | 'student' | 'superadmin';

export interface User {
  id: string;
  email: string;
  first_name: string;
  middle_name: string | null;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  is_locked: boolean;
  tenant_id: string | null;
  institution_id: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

// 13.7: Updated InvoiceStatus to match backend enum (pending/paid/overdue/cancelled)
export type InvoiceStatus = 'pending' | 'paid' | 'overdue' | 'cancelled';

// 13.7: Added payment fields to Invoice
export interface Invoice {
  id: string;
  tenant_id: string;
  semester_id: string | null;
  description: string;
  student_count: number;
  amount_per_student: number;
  total_amount: number;
  status: InvoiceStatus;
  payment_reference: string | null;
  payment_gateway: 'paystack' | 'monnify' | null;
  paid_at: string | null;
  payment_url: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

export type PlanType = 'starter' | 'intermediate' | 'enterprise';

// 13.7: Aligned CurrentUsage with backend model fields
export interface CurrentUsage {
  id: string;
  tenant_id: string;
  semester_id: string | null;
  student_count: number;
  current_plan: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

export type PaymentMethodType = 'credit_card' | 'bank_transfer' | 'direct_debit' | 'other';

export interface PaymentMethod {
  id: string;
  type: PaymentMethodType;
  tenant_id: string;
  details: Record<string, any>;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

// 13.7: Added domain, is_active, is_deleted, deleted_at, tenant_code fields to Tenant
export interface Tenant {
  id: string;
  name: string;
  description: string | null;
  logo_url: string | null;
  domain: string | null;
  is_active: boolean;
  is_deleted: boolean;
  deleted_at: string | null;
  tenant_code: string | null;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface Course {
  id: string;
  name: string;
  description: string | null;
  course_code: string;
  tenant_id: string;
  semester_id: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

export type EnrollmentStatus = 'active' | 'completed' | 'dropped' | 'pending';
export type Semester = 'fall' | 'spring' | 'summer';

export interface Enrollment {
  id: string;
  student_id: string;
  course_id: string;
  semester_id: string | null;
  year: number;
  status: EnrollmentStatus;
  tenant_id: string;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

export type QuestionType = 'multiple_choice' | 'theory' | 'fill_in_blanks';

export interface Question {
  id: string;
  number: string;
  text: string;
  rules: string | null;
  images: string[] | null;
  parent_id: string | null;
  tenant_id: string | null;
  semester_id: string | null;
  industry: string | null;
  qtype: QuestionType | null;
  options: any | null;
  parsed_options: {label: string; text: string;}[] | null;
  exam_ids: string[] | null;
  mark: number | null;
  answer: any | null;
  answer_id: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
  // Frontend-only fields
  correct_answer?: string;
  exams?: {id: string}[];
}

// 13.7: Aligned with backend Exam model and ExamRead schema
export interface Exam {
  id: string;
  title: string;
  description: string | null;
  duration_hours: number;
  duration_minutes: number;
  total_marks: number | null;
  passing_marks: number | null;
  status: 'not_started' | 'in_progress' | 'finished' | 'draft';
  max_attempts: number;
  start_time: string | null;
  end_time: string | null;
  course_id: string | null;
  tenant_id: string | null;
  semester_id: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  // Frontend-only computed fields
  question_count?: number;
  submission_count?: number;
  questions?: Question[];
}

export interface SubmissionAttempt {
  id: string;
  submission_id: string;
  attempt_number: number;
  score: string | null;
  scan_pages: Record<string, any> | null;
  grading_started_at: string | null;
  graded_at: string | null;
  created_at: string;
}

export interface Submission {
  id: string;
  student_id: string;
  exam_id: string;
  tenant_id: string;
  semester_id: string | null;
  latest_score: string | null;
  attempts: number;
  status: 'pending' | 'submitted' | 'graded';
  submitted_at: string | null;
  graded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LecturerDashboard {
  id: string;
  lecturer_id: string;
  tenant_id: string;
  total_courses: number;
  active_courses: number;
  total_students: number;
  total_exams: number;
  pending_submissions: number;
  graded_submissions: number;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

export interface AdminDashboard {
  id: string;
  tenant_id: string;
  total_users: number;
  total_students: number;
  total_lecturers: number;
  total_courses: number;
  total_exams: number;
  total_submissions: number;
  pending_submissions: number;
  graded_submissions: number;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

export interface StudentDashboard {
  id: string;
  student_id: string;
  tenant_id: string;
  total_courses: number;
  active_courses: number;
  completed_courses: number;
  total_exams: number;
  upcoming_exams: number;
  missed_exams: number;
  total_submissions: number;
  graded_submissions: number;
  pending_submissions: number;
  average_score: number | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

export interface DashboardStats {
  totalCourses?: number;
  totalExams?: number;
  totalStudents?: number;
  avgScore?: number;
  totalUsers?: number;
  totalTenants?: number;
  enrolledCourses?: number;
  upcomingExams?: number;
}
