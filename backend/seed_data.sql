-- Seed data for local development
-- WARNING: passwords are stored with a development plaintext prefix 'plain$' for convenience.
-- Remove or change before production.

BEGIN;

-- Tenant
INSERT INTO account.tenants (id, name, domain, logo_url, is_active, created_at, updated_at)
VALUES ('11111111-1111-1111-1111-111111111111', 'Greenland University', 'greenland.edu', NULL, true, now(), now())
ON CONFLICT (id) DO NOTHING;

-- Users (all use the same development password: Adminpass123)
INSERT INTO account.users (id, first_name, middle_name, last_name, email, password, role, is_active, tenant_id, institution_id, created_at, updated_at)
VALUES
  ('22222222-2222-2222-2222-222222222222', 'Admin', NULL, 'Greenland', 'admin@greenland.edu', 'plain$Adminpass123', 'admin', true, NULL, NULL, now(), now()),
  ('33333333-3333-3333-3333-333333333333', 'Dr. John', NULL, 'Smith', 'lecturer@greenland.edu', 'plain$Adminpass123', 'lecturer', true, '11111111-1111-1111-1111-111111111111', NULL, now(), now()),
  ('44444444-4444-4444-4444-444444444444', 'Jane', NULL, 'Doe', 'student@greenland.edu', 'plain$Adminpass123', 'student', true, '11111111-1111-1111-1111-111111111111', 'GUL/2024/001', now(), now()),
  ('55555555-5555-5555-5555-555555555555', 'Bob', NULL, 'Wilson', 'student2@greenland.edu', 'plain$Adminpass123', 'student', true, '11111111-1111-1111-1111-111111111111', 'GUL/2024/002', now(), now())
ON CONFLICT (email) DO NOTHING;

-- Tenant admins association
INSERT INTO account.tenant_admins (tenant_id, user_id)
VALUES ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222')
ON CONFLICT DO NOTHING;

-- Course
INSERT INTO academic.courses (id, name, description, course_code, lecturer_id, tenant_id, created_at, updated_at)
VALUES ('66666666-6666-6666-6666-666666666666', 'Introduction to Computer Science', 'A beginner''s course in computer science', 'CS101', '33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', now(), now())
ON CONFLICT (course_code) DO NOTHING;

-- Exam (duration in hours)
INSERT INTO academic.exams (id, title, description, duration, total_marks, passing_marks, status, start_time, max_attempts, course_id, tenant_id, created_at, updated_at, created_by, updated_by)
VALUES ('77777777-7777-7777-7777-777777777777', 'Computer Science Fundamentals - Final Exam', 'Comprehensive final exam covering all topics from the Introduction to Computer Science course.', 2.00, 100, 60, 'not_started', now() + INTERVAL '7 days', 1, '66666666-6666-6666-6666-666666666666', '11111111-1111-1111-1111-111111111111', now(), now(), '33333333-3333-3333-3333-333333333333', '33333333-3333-3333-3333-333333333333')
ON CONFLICT (id) DO NOTHING;

-- Answers (MCQ)
INSERT INTO academic.answers (id, value, text_value, acceptable_variations, answer_type, created_at, updated_at)
VALUES
  ('99999999-9999-9999-9999-999999999991', 'b', NULL, NULL, 'mcq', now(), now()),
  ('99999999-9999-9999-9999-999999999992', 'c', NULL, NULL, 'mcq', now(), now()),
  ('99999999-9999-9999-9999-999999999993', 'a', NULL, NULL, 'mcq', now(), now())
ON CONFLICT (id) DO NOTHING;

-- Questions (store options as JSON object for simplicity)
INSERT INTO academic.questions (id, number, text, images, parent_id, tenant_id, rules, mark, industry, qtype, options, created_at, updated_at, answer_id)
VALUES
  ('88888888-8888-8888-8888-888888888881', '1', 'What is the time complexity of binary search in a sorted array of size n?', NULL, NULL, '11111111-1111-1111-1111-111111111111', NULL, 10.0, 'general', 'multiple_choice', '{"a":"O(n)","b":"O(log n)","c":"O(n log n)","d":"O(1)"}', now(), now(), '99999999-9999-9999-9999-999999999991'),
  ('88888888-8888-8888-8888-888888888882', '2', 'Which of the following is NOT a fundamental principle of Object-Oriented Programming?', NULL, NULL, '11111111-1111-1111-1111-111111111111', NULL, 10.0, 'general', 'multiple_choice', '{"a":"Encapsulation","b":"Inheritance","c":"Compilation","d":"Polymorphism"}', now(), now(), '99999999-9999-9999-9999-999999999992'),
  ('88888888-8888-8888-8888-888888888883', '3', 'What does the acronym ''DRY'' stand for in software development?', NULL, NULL, '11111111-1111-1111-1111-111111111111', NULL, 8.0, 'general', 'multiple_choice', '{"a":"Don''t Repeat Yourself","b":"Data Recovery Yields","c":"Dynamic Resource Y","d":"Database Replication Y"}', now(), now(), '99999999-9999-9999-9999-999999999993')
ON CONFLICT (id) DO NOTHING;

-- Link questions to exam
INSERT INTO academic.question_exams (question_id, exam_id, created_at, updated_at)
VALUES
  ('88888888-8888-8888-8888-888888888881', '77777777-7777-7777-7777-777777777777', now(), now()),
  ('88888888-8888-8888-8888-888888888882', '77777777-7777-7777-7777-777777777777', now(), now()),
  ('88888888-8888-8888-8888-888888888883', '77777777-7777-7777-7777-777777777777', now(), now())
ON CONFLICT DO NOTHING;

COMMIT;
