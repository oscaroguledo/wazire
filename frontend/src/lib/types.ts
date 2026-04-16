export type UserRole = 'admin' | 'lecturer' | 'student';

export interface User {
  id: string;
  email: string;
  first_name: string;
  middle_name?: string;
  last_name: string;
  /** Computed full name for display convenience */
  name?: string;
  role: UserRole;
  is_active?: boolean;
  tenant_id?: string | null;
  institution_id?: string | null;
  tenant_name?: string | null;
  logo_url?: string | null;
  created_at?: string;
  updated_at?: string;
  avatar?: string;
}

export type InvoiceStatus = 'PENDING' | 'PAID' | 'OVERDUE' | 'CANCELLED';

export interface Invoice {
  id: string;
  student_count: number;
  amount_per_student: number;
  total_amount: number;
  tenant?: Tenant;
  status: InvoiceStatus;
  created_at?: string;
  updated_at?: string;
}

export type PlanType = 'FREE' | 'PRO' | 'ENTERPRISE';

export interface CurrentUsage {
  id: string;
  student_count: number;
  exams_graded: number;
  plan: PlanType;
  tenant?: Tenant;
  plan_updated_at?: string;
  created_at?: string;
  updated_at?: string;
}

export type PaymentMethodType = 'credit_card' | 'paypal' | 'bank_transfer' | 'other';

export interface PaymentMethod {
  id: string;
  type: PaymentMethodType;
  tenant?: Tenant;
  created_at?: string;
  updated_at?: string;
}

export interface Tenant {
  id: string;
  name: string;
  domain: string;
  logo_url?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
  admin_users?: User[];
  invoices?: Invoice[];
  usage?: CurrentUsage;
  payment_methods?: PaymentMethod[];
}

export interface Course {
  id: string;
  name: string;
  course_code: string;
  lecturer?: User;
  tenant_id?: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export type EnrollmentStatus = 'ACTIVE' | 'COMPLETED' | 'PENDING' | 'DROPPED';
export type Semester = 'FALL' | 'SPRING' | 'SUMMER';

export interface Enrollment {
  id: string;
  student: User;
  course: Course;
  semester: Semester;
  year: number;
  status: EnrollmentStatus;
  created_at?: string;
  updated_at?: string;
}

export type QuestionType = 'multiple_choice' | 'theory';

export interface Question {
  id: string;
  number: string;
  text: string;
  rules?: string;
  images?: string[];
  parent_id?: string;
  tenant_id?: string;
  qtype: QuestionType;
  industry: string;
  options?: {label: string;text: string;}[];
  answer_id?: string;
  correct_answer?: string;
  mark: number;
  exam_ids?: string[];
  created_at?: string;
  updated_at?: string;
}

export interface Exam {
  id: string;
  title: string;
  description?: string;
  duration_hours: number;
  duration_minutes: number;
  total_marks?: number;
  passing_marks?: number;
  status: 'not_started' | 'in_progress' | 'finished';
  max_attempts?: number;
  start_time?: string;
  course?: Course;
  lecturer?: User;
  tenant_id?: string;
  created_by?: string;
  updated_by?: string;
  question_count: number;
  submission_count: number;
  questions?: Question[];
  created_at?: string;
  updated_at?: string;
}

export interface SubmissionAttempt {
  id: string;
  submission_id: string;
  attempt_number: number;
  score?: string;
  scan_pages?: string[];
  graded_at?: string;
  created_at?: string;
  // Frontend-specific fields
  answers?: Record<string, any>;
}

export interface Submission {
  id: string;
  student_id: string;
  exam_id: string;
  latest_score?: string;
  attempts_count: number;
  graded_at?: string;
  created_at?: string;
  updated_at?: string;
  // Frontend-specific fields
  student_name?: string;
  exam_title?: string;
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
  created_at?: string;
  updated_at?: string;
}

export interface AdminDashboard {
  id: string;
  admin?: User;
  total_users: number;
  total_lecturers: number;
  total_students: number;
  total_courses: number;
  total_exams: number;
  total_submissions: number;
  total_graded_submissions: number;
  total_pending_submissions: number;
  created_at?: string;
  updated_at?: string;
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
  created_at?: string;
  updated_at?: string;
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