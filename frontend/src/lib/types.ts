export type UserRole = 'admin' | 'lecturer' | 'student';

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

export type InvoiceStatus = 'pending' | 'paid' | 'failed' | 'refunded';

export interface Invoice {
  id: string;
  student_count: number;
  amount_per_student: number;
  total_amount: number;
  tenant: Tenant | null;
  status: InvoiceStatus;
  created_at: string;
  updated_at: string;
}

export type PlanType = 'starter' | 'intermediate' | 'enterprise';

export interface CurrentUsage {
  id: string;
  student_count: number;
  exams_graded: number;
  plan: PlanType;
  tenant: Tenant | null;
  plan_updated_at: string;
  created_at: string;
  updated_at: string;
}

export type PaymentMethodType = 'credit_card' | 'paypal' | 'bank_transfer' | 'other';

export interface PaymentMethod {
  id: string;
  type: PaymentMethodType;
  tenant: Tenant | null;
  created_at: string;
  updated_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  description: string | null;
  logo_url: string | null;
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

export interface Enrollment {
  id: string;
  student: User;
  course: Course;
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
  course: Course | null;
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

export interface SubmissionAttempt {
  id: string;
  submission_id: string;
  attempt_number: number;
  score: string | null;
  scan_pages: string[];
  graded_at: string | null;
  created_at: string;
  // Frontend-specific fields
  answers?: Record<string, any>;
}

export interface Submission {
  id: string;
  student_id: string;
  exam_id: string;
  latest_score: string | null;
  attempts_count: number;
  graded_at: string | null;
  created_at: string;
  updated_at: string;
  // Frontend-specific fields (added by enrichment in routes)
  student_name?: string;
  exam_title?: string;
  course_id?: string;
  status?: string;
  attempts?: SubmissionAttempt[];
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

export interface AdminDashboard {
  id: string;
  admin_id: string;
  total_users: number;
  total_lecturers: number;
  total_students: number;
  total_courses: number;
  total_exams: number;
  total_submissions: number;
  total_graded_submissions: number;
  total_pending_submissions: number;
  created_at: string;
  updated_at: string;
  // Frontend-only field
  admin?: User;
}

export interface StudentDashboard {
  id: string;
  student_id: string;
  total_courses: number;
  total_exams: number;
  total_submissions: number;
  total_graded_submissions: number;
  total_pending_submissions: number;
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