// 13.2: Added 'superadmin' to UserRole
export type UserRole = 'admin' | 'lecturer' | 'student' | 'superadmin';

export interface User {
  id: string;
  email: string;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  tenant_id: string | null;
  institution_id: string | null;
  created_at: string;
  updated_at: string;
  // Frontend-only computed fields
  name?: string;
  tenant_name?: string | null;
  logo_url?: string | null;
  avatar?: string;
}

// 13.7: Updated InvoiceStatus to match backend enum (pending/paid/overdue/cancelled)
export type InvoiceStatus = 'pending' | 'paid' | 'overdue' | 'cancelled';

// 13.7: Added payment fields to Invoice
export interface Invoice {
  id: string;
  tenant_id: string | null;
  semester_id: string | null;
  description: string | null;
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
}

export type PlanType = 'starter' | 'intermediate' | 'enterprise';

// 13.7: Aligned CurrentUsage with backend model fields
export interface CurrentUsage {
  id: string;
  tenant_id: string | null;
  student_count: number;
  exams_graded: number;
  plan: PlanType;
  plan_updated_at: string;
  created_at: string;
  updated_at: string;
}

export type PaymentMethodType = 'credit_card' | 'paypal' | 'bank_transfer' | 'other';

export interface PaymentMethod {
  id: string;
  type: PaymentMethodType;
  tenant_id: string | null;
  created_at: string;
  updated_at: string;
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
  lecturer: User | null;
  tenant_id: string | null;
  created_at: string;
  updated_at: string;
}

export type EnrollmentStatus = 'active' | 'completed' | 'dropped' | 'pending';
export type Semester = 'fall' | 'spring' | 'summer';

// 13.7: Replaced student: User / course: Course with student_id / course_id
export interface Enrollment {
  id: string;
  student_id: string;
  course_id: string;
  semester: Semester;
  year: number;
  status: EnrollmentStatus;
  created_at: string;
  updated_at: string;
}

export type QuestionType = 'multiple_choice' | 'theory';

export interface Question {
  id: string;
  number: string;
  text: string;
  rules: string | null;
  images: string[];
  parent_id: string | null;
  tenant_id: string | null;
  industry: string | null;
  qtype: string | null;
  options: any | null;
  parsed_options: {label: string;text: string;}[];
  exams: {id: string}[];
  mark: number | null;
  answer: any | null;
  created_at: string;
  updated_at: string;
  // Frontend-only fields
  answer_id?: string;
  correct_answer?: string;
}

// 13.7: Replaced course: Course | null with course_id: string | null; added end_time; removed student_id
export interface Exam {
  id: string;
  title: string;
  description: string | null;
  duration_hours: number;
  duration_minutes: number;
  total_marks: number | null;
  passing_marks: number | null;
  status: 'not_started' | 'in_progress' | 'finished';
  max_attempts: number;
  start_time: string | null;
  end_time: string | null;
  course_id: string | null;
  lecturer: User | null;
  tenant_id: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  question_count: number;
  submission_count: number;
  // Frontend-only fields
  questions?: Question[];
}

// 13.7: Removed attempt_number and scan_pages; id is the attempt identifier
export interface SubmissionAttempt {
  id: string;
  submission_id: string;
  score: string | null;
  graded_at: string | null;
  grading_started_at: string | null;
  created_at: string;
  // Frontend-specific fields
  answers?: Record<string, any>;
}

// 13.7: Renamed attempts_count → attempts; added submitted_at
export interface Submission {
  id: string;
  student_id: string;
  exam_id: string;
  latest_score: string | null;
  attempts: number;
  submitted_at: string | null;
  graded_at: string | null;
  created_at: string;
  updated_at: string;
  // Frontend-specific fields (added by enrichment in routes)
  student_name?: string;
  exam_title?: string;
  course_id?: string;
  status?: string;
  submission_attempts?: SubmissionAttempt[];
}

export interface LecturerDashboard {
  id: string;
  lecturer_id: string;
  total_courses: number;
  total_exams: number;
  total_students: number;
  pending_submissions: number;
  graded_submissions: number;
  active_courses: number;
  created_at: string;
  updated_at: string;
}

// 13.7: Renamed total_graded_submissions/total_pending_submissions → graded_submissions/pending_submissions
export interface AdminDashboard {
  id: string;
  tenant_id: string;
  total_users: number;
  total_lecturers: number;
  total_students: number;
  total_courses: number;
  total_exams: number;
  total_submissions: number;
  graded_submissions: number;
  pending_submissions: number;
  created_at: string;
  updated_at: string;
  // Frontend-only field
  admin?: User;
}

// 13.7: Renamed total_graded/pending; added active_courses and completed_courses
export interface StudentDashboard {
  id: string;
  student_id: string;
  total_courses: number;
  total_exams: number;
  total_submissions: number;
  graded_submissions: number;
  pending_submissions: number;
  active_courses: number;
  completed_courses: number;
  missed_exams: number;
  upcoming_exams: number;
  created_at: string;
  updated_at: string;
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
