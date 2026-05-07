#!/usr/bin/env python3
"""
Create test users, tenant, course, exam and questions for Wazire system
"""

import os
import requests
import json
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

def clear_database():
    """Clear all data from the database using direct SQL."""
    print("🗑️  Clearing database...")
    
    try:
        import asyncio
        import asyncpg
        import os
        from dotenv import load_dotenv
        
        # Load .env from the backend directory
        from pathlib import Path
        env_path = Path(__file__).parent / ".env"
        load_dotenv(env_path)
        db_url = "postgresql+asyncpg://wazire:wazire@postgres:5432/wazire"
        
        if not db_url:
            print("⚠️  DATABASE_URL not found in environment variables")
            return
        
        async def clear_tables():
            # Parse the DATABASE_URL
            # Format: postgresql+asyncpg://user:pass@host:port/db
            parsed_url = db_url
            if db_url.startswith("postgresql+asyncpg://"):
                parsed_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            
            conn = await asyncpg.connect(parsed_url)
            
            # Disable foreign key checks temporarily
            await conn.execute("SET session_replication_role = 'replica'")
            
            # Truncate all tables in correct order
            tables = [
                "academic.submission_attempts",
                "academic.student_answers",
                "academic.question_exams",
                "academic.submissions",
                "academic.enrollments",
                "academic.questions",
                "academic.exams",
                "academic.courses",
                "academic.answers",
                "analytics.student_dashboard",
                "analytics.lecturer_dashboard",
                "analytics.admin_dashboard",
                "account.tenant_admins",
                "account.oauth",
                "account.users",
                "account.tenants"
            ]
            
            for table in tables:
                try:
                    await conn.execute(f'TRUNCATE TABLE {table} CASCADE')
                    print(f"  ✅ Cleared {table}")
                except Exception as e:
                    print(f"  ⚠️  Could not clear {table}: {e}")
            
            # Re-enable foreign key checks
            await conn.execute("SET session_replication_role = 'origin'")
            
            await conn.close()
            print("✅ Database cleared successfully")
        
        asyncio.run(clear_tables())
    except Exception as e:
        print(f"⚠️  Could not clear database: {e}")
        print("   (This is okay if running for the first time or if database connection fails)")

def create_tenant():
    """Create Greenland University tenant"""
    tenant_data = {
        "name": "Greenland University",
        "description": "A test university for the Wazire system",
        "domain": "greenland.edu"
    }
    
    try:
        # First login as admin to get token
        login_data = {
            "email": "admin@greenland.edu",
            "password": "Adminpass123"
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            response_data = response.json()
            print(f"🔍 Login response: {response_data}")
            
            # Try different possible token locations
            token = None
            if "data" in response_data:
                data = response_data["data"]
                if "tokens" in data:
                    token = data["tokens"].get("access_token")
                elif "access_token" in data:
                    token = data["access_token"]
            elif "access_token" in response_data:
                token = response_data["access_token"]
            
            if not token:
                print("❌ Could not find token in login response")
                print(f"Response structure: {response_data}")
                return None
            
            headers = {"Authorization": f"Bearer {token}"}
            print(f"🔑 Using token: {token[:20]}...")
            
            response = requests.post(f"{BASE_URL}/api/v1/tenants/", json=tenant_data, headers=headers)
            if response.status_code == 201:
                tenant_info = response.json()
                print(f"✅ Created tenant: {tenant_data['name']}")
                return tenant_info.get("data", {}).get("id")
            elif response.status_code == 400 and "already exists" in response.text.lower():
                print(f"ℹ️  Tenant already exists: {tenant_data['name']}")
                # Try to get existing tenant
                try:
                    response = requests.get(f"{BASE_URL}/api/v1/tenants/", headers=headers)
                    if response.status_code == 200:
                        tenants = response.json().get("data", [])
                        for tenant in tenants:
                            if tenant["name"] == tenant_data["name"]:
                                return tenant["id"]
                except:
                    pass
                return None
            else:
                print(f"❌ Failed to create tenant: {response.status_code} - {response.text}")
                return None
        else:
            print(f"❌ Failed to login as admin for tenant creation: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating tenant: {str(e)}")
        return None

def create_user(email, password, first_name, last_name, role, tenant_id=None, institution_id=None):
    """Create a user with optional tenant assignment and institution_id (matric/reg number)"""
    user_data = {
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "role": role
    }
    if tenant_id:
        user_data["tenant_id"] = tenant_id
    if institution_id:
        user_data["institution_id"] = institution_id

    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=user_data)
        if response.status_code == 201:
            print(f"✅ Created {role}: {email}")
            return True
        elif response.status_code == 400 and "already exists" in response.text.lower():
            print(f"ℹ️  {role} already exists: {email}")
            return True
        else:
            print(f"❌ Failed to create {role}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating {role}: {str(e)}")
        return False

def create_course(tenant_id, lecturer_id):
    """Create a test course for the tenant"""
    course_data = {
        "name": "Introduction to Computer Science",
        "course_code": "CS101",
        "description": "A beginner's course in computer science",
        "lecturer_id": lecturer_id
    }
    
    try:
        # First login as lecturer to get token
        login_data = {
            "email": "lecturer@greenland.edu",
            "password": "Lecturerpass123"
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get("data", {}).get("tokens", {}).get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.post(f"{BASE_URL}/api/v1/academic/courses/", json=course_data, headers=headers)
            if response.status_code == 201:
                course_info = response.json()
                print(f"✅ Created course: {course_data['name']}")
                return course_info.get("data", {}).get("id")
            elif response.status_code == 400 and "already exists" in response.text.lower():
                print(f"ℹ️  Course may already exist: {course_data['name']}")
                # Try to get existing course
                try:
                    response = requests.get(f"{BASE_URL}/api/v1/academic/courses/", headers=headers)
                    if response.status_code == 200:
                        courses = response.json().get("data", [])
                        for course in courses:
                            if course["course_code"] == course_data["course_code"]:
                                return course["id"]
                except:
                    pass
                return None
            else:
                print(f"❌ Failed to create course: {response.status_code} - {response.text}")
                return None
        else:
            print(f"❌ Failed to login as lecturer for course creation")
            return None
    except Exception as e:
        print(f"❌ Error creating course: {str(e)}")
        return None

def create_exam(course_id, tenant_id):
    """Create a test exam for the course"""
    exam_data = {
        "title": "Computer Science Fundamentals - Final Exam",
        "description": "Comprehensive final exam covering all topics from the Introduction to Computer Science course.",
        "duration_hours": 2,
        "total_marks": 100,
        "passing_marks": 60,
        "status": "not_started",
        "start_time": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "course_id": course_id,
        "tenant_id": tenant_id
    }
    
    try:
        # Login as lecturer
        login_data = {
            "email": "lecturer@greenland.edu",
            "password": "Lecturerpass123"
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get("data", {}).get("tokens", {}).get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.post(f"{BASE_URL}/api/v1/academic/exams/", json=exam_data, headers=headers)
            if response.status_code == 201:
                exam_info = response.json()
                print(f"✅ Created exam: {exam_data['title']}")
                return exam_info.get("data", {}).get("id")
            elif response.status_code == 400 and "already exists" in response.text.lower():
                print(f"ℹ️  Exam may already exist: {exam_data['title']}")
                # Try to get existing exam
                try:
                    response = requests.get(f"{BASE_URL}/api/v1/academic/exams/", headers=headers)
                    if response.status_code == 200:
                        exams = response.json().get("data", [])
                        for exam in exams:
                            if exam["title"] == exam_data["title"]:
                                return exam["id"]
                except:
                    pass
                return None
            else:
                print(f"❌ Failed to create exam: {response.status_code} - {response.text}")
                return None
        else:
            print(f"❌ Failed to login as lecturer for exam creation")
            return None
    except Exception as e:
        print(f"❌ Error creating exam: {str(e)}")
        return None

def create_questions(exam_id, tenant_id):
    """Create test questions for the exam"""
    questions_data = [
        # Multiple Choice Questions
        {
            "number": "1",
            "text": "What is the time complexity of binary search in a sorted array of size n?",
            "qtype": "multiple_choice",
            "options": {"a": "O(n)", "b": "O(log n)", "c": "O(n log n)", "d": "O(1)"},
            "answer": "b",
            "mark": 10,
            "industry": "general",
            "exam_ids": [exam_id],
            "tenant_id": tenant_id
        },
        {
            "number": "2",
            "text": "Which of the following is NOT a fundamental principle of Object-Oriented Programming?",
            "qtype": "multiple_choice",
            "options": {"a": "Encapsulation", "b": "Inheritance", "c": "Compilation", "d": "Polymorphism"},
            "answer": "c",
            "mark": 10,
            "industry": "general",
            "exam_ids": [exam_id],
            "tenant_id": tenant_id
        },
        {
            "number": "3",
            "text": "What does the acronym 'DRY' stand for in software development?",
            "qtype": "multiple_choice",
            "options": {"a": "Don't Repeat Yourself", "b": "Data Recovery Yields", "c": "Dynamic Resource Y", "d": "Database Replication Y"},
            "answer": "a",
            "mark": 8,
            "industry": "general",
            "exam_ids": [exam_id],
            "tenant_id": tenant_id
        },
        
        {
            "number": "4",
            "text": "A ______ is a self-contained component that encapsulates data and behavior.",
            "qtype": "multiple_choice",
            "options": {"a": "Function", "b": "Variable", "c": "Class", "d": "Array"},
            "answer": "c",
            "mark": 8,
            "industry": "general",
            "exam_ids": [exam_id],
            "tenant_id": tenant_id
        },
        {
            "number": "5",
            "text": "The process of finding and fixing bugs in software is called ______.",
            "qtype": "multiple_choice",
            "options": {"a": "Refactoring", "b": "Debugging", "c": "Testing", "d": "Compiling"},
            "answer": "b",
            "mark": 8,
            "industry": "general",
            "exam_ids": [exam_id],
            "tenant_id": tenant_id
        },
        
        # Additional Multiple Choice
        {
            "number": "6",
            "text": "Which data structure follows LIFO (Last In First Out) principle?",
            "qtype": "multiple_choice",
            "options": {"a": "Queue", "b": "Stack", "c": "Array", "d": "Linked List"},
            "answer": "b",
            "mark": 15,
            "industry": "general",
            "exam_ids": [exam_id],
            "tenant_id": tenant_id
        },
        {
            "number": "7",
            "text": "Which phase of software development involves writing actual code?",
            "qtype": "multiple_choice",
            "options": {"a": "Requirements Analysis", "b": "Design", "c": "Implementation", "d": "Testing"},
            "answer": "c",
            "mark": 15,
            "industry": "general",
            "exam_ids": [exam_id],
            "tenant_id": tenant_id
        },
        {
            "number": "8",
            "text": "Which type of database is best suited for complex transactions requiring ACID compliance?",
            "qtype": "multiple_choice",
            "options": {"a": "Document Store", "b": "Key-Value Store", "c": "Graph Database", "d": "Relational (SQL) Database"},
            "answer": "d",
            "mark": 12,
            "industry": "general",
            "exam_ids": [exam_id],
            "tenant_id": tenant_id
        },
        
        # Additional Multiple Choice
        {
            "number": "9",
            "text": "Which sorting algorithm has the best average-case time complexity?",
            "qtype": "multiple_choice",
            "options": {"a": "Bubble Sort", "b": "Quick Sort", "c": "Merge Sort", "d": "Insertion Sort"},
            "answer": "c",
            "mark": 7,
            "industry": "general",
            "exam_ids": [exam_id],
            "tenant_id": tenant_id
        },
        {
            "number": "10",
            "text": "What is the primary purpose of an index in a database?",
            "qtype": "multiple_choice",
            "options": {"a": "Data encryption", "b": "Fast query performance", "c": "Data backup", "d": "User authentication"},
            "answer": "b",
            "mark": 7,
            "industry": "general",
            "exam_ids": [exam_id],
            "tenant_id": tenant_id
        }
    ]
    
    try:
        # Login as lecturer
        login_data = {
            "email": "lecturer@greenland.edu",
            "password": "Lecturerpass123"
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get("data", {}).get("tokens", {}).get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            
            created_questions = []
            for i, question_data in enumerate(questions_data, 1):
                try:
                    response = requests.post(f"{BASE_URL}/api/v1/academic/questions/", json=question_data, headers=headers)
                    if response.status_code == 201:
                        question_info = response.json()
                        created_questions.append(question_info.get("data", {}))
                        print(f"  ✅ Question {i}: {question_data['text'][:50]}...")
                    elif response.status_code == 400 and "already exists" in response.text.lower():
                        print(f"  ℹ️  Question {i} may already exist")
                    else:
                        print(f"  ❌ Failed to create question {i}: {response.status_code} - {response.text}")
                except Exception as e:
                    print(f"  ❌ Error creating question {i}: {str(e)}")
            
            print(f"✅ Created {len(created_questions)} questions")
            return created_questions
        else:
            print(f"❌ Failed to login as lecturer for questions creation")
            return []
    except Exception as e:
        print(f"❌ Error creating questions: {str(e)}")
        return []

def main():
    print("=== 🚀 CREATING TEST USERS, COURSE, EXAM AND QUESTIONS FOR GREENLAND UNIVERSITY ===\n")
    
    # Clear existing data
    clear_database()
    
    # Wait a moment for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(2)
    
    # First, create admin user (no tenant needed)
    print("👤 Creating admin user first...")
    admin_user = {
        "email": "admin@greenland.edu",
        "password": "Adminpass123",
        "first_name": "Admin",
        "last_name": "Greenland",
        "role": "admin",
        "tenant_id": None
    }
    
    admin_created = create_user(**admin_user)
    # Even if admin already exists, we can proceed with login
    if not admin_created:
        print("ℹ️  Admin user already exists, proceeding with login...")
    
    # Wait a moment for user creation to complete
    time.sleep(1)
    
    # Create tenant using admin authentication
    print("🏫 Creating Greenland University tenant...")
    tenant_id = create_tenant()
    
    # If tenant creation failed, try to get existing tenant from admin's profile
    if not tenant_id:
        try:
            login_data = {
                "email": "admin@greenland.edu",
                "password": "Adminpass123"
            }
            response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json().get("data", {})
                tenant_id = data.get("user", {}).get("tenant_id")
                if tenant_id:
                    print(f"✅ Using existing tenant: {tenant_id}")
        except Exception as e:
            print(f"❌ Could not retrieve existing tenant: {e}")
    
    if not tenant_id:
        print("❌ Could not create or find tenant. Exiting.")
        return
    
    # Create other test users with tenant assignment
    users = [
        {
            "email": "lecturer@greenland.edu", 
            "password": "Lecturerpass123",
            "first_name": "Dr. John",
            "last_name": "Smith",
            "role": "lecturer",
            "tenant_id": tenant_id
        },
        {
            "email": "student@greenland.edu",
            "password": "Studentpass123", 
            "first_name": "Jane",
            "last_name": "Doe",
            "role": "student",
            "tenant_id": tenant_id,
            "institution_id": "GUL/2024/001"  # Greenland University Matric Number
        },
        {
            "email": "student2@greenland.edu",
            "password": "Studentpass123", 
            "first_name": "Bob",
            "last_name": "Wilson",
            "role": "student",
            "tenant_id": tenant_id,
            "institution_id": "GUL/2024/002"  # Greenland University Matric Number
        }
    ]
    
    print(f"\n👥 Creating {len(users)} additional users...")
    for user in users:
        create_user(**user)
    
    # Wait a moment for user creation to complete
    time.sleep(1)
    
    # Get lecturer ID for course creation
    lecturer_id = None
    try:
        login_data = {
            "email": "lecturer@greenland.edu",
            "password": "Lecturerpass123"
        }
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            lecturer_id = response.json().get("data", {}).get("user", {}).get("id")
            print(f"✅ Found lecturer ID: {lecturer_id}")
    except Exception as e:
        print(f"❌ Could not get lecturer ID: {e}")
    
    # Create a test course
    course_id = None
    if tenant_id and lecturer_id:
        print(f"\n📚 Creating test course...")
        course_id = create_course(tenant_id, lecturer_id)
    
    # Create a test exam
    exam_id = None
    if course_id and tenant_id:
        print(f"\n📝 Creating test exam...")
        exam_id = create_exam(course_id, tenant_id)
    
    # Create test questions
    questions = []
    if exam_id and tenant_id:
        print(f"\n❓ Creating test questions...")
        questions = create_questions(exam_id, tenant_id)
    
    # Print summary
    print("\n" + "="*60)
    print("📋 CREATION SUMMARY")
    print("="*60)
    print(f"🏛️  Tenant: Greenland University (ID: {tenant_id})")
    print(f"👨‍🏫 Lecturer: Dr. John Smith (lecturer@greenland.edu)")
    if course_id:
        print(f"📚 Course: Introduction to Computer Science (CS101) (ID: {course_id})")
    if exam_id:
        print(f"📋 Exam: Computer Science Fundamentals - Final Exam (ID: {exam_id})")
    if questions:
        print(f"❓ Questions: {len(questions)} created")
        print(f"   📊 Multiple Choice: {sum(1 for q in questions if q.get('qtype') == 'multiple_choice')}")
        print(f"   📝 Fill in the Blanks: {sum(1 for q in questions if q.get('qtype') == 'fill_in_blanks')}")
        print(f"   📖 Theory: {sum(1 for q in questions if q.get('qtype') == 'theory')}")
    print("="*60)
    
    print("\n" + "="*50)
    print("📋 LOGIN CREDENTIALS FOR GREENLAND UNIVERSITY")
    print("="*50)
    
    print("\n🔐 ADMIN LOGIN:")
    print("   Email: admin@greenland.edu")
    print("   Password: Adminpass123")
    print("   Role: Can manage everything\n")
    
    print("👨‍🏫 LECTURER LOGIN:")
    print("   Email: lecturer@greenland.edu") 
    print("   Password: Lecturerpass123")
    print("   Role: Can teach courses and manage enrollments\n")
    
    print("👨‍🎓 STUDENT LOGINS:")
    print("   Email: student@greenland.edu")
    print("   Password: Studentpass123")
    print("   Email: student2@greenland.edu")
    print("   Password: Studentpass123")
    print("   Role: Can view enrolled courses and take exams\n")
    
    print("🌐 FRONTEND URL:")
    print("   http://localhost:5173 (or your frontend dev server)")
    print("\n🎯 NEXT STEPS:")
    print("   1. Login as lecturer@greenland.edu")
    print("   2. Navigate to /courses to view the created course")
    print("   3. Navigate to /exams to view the created exam")
    print("   4. Login as students to enroll and take exams!")
    print("   5. Experience the professional Take Exam interface!")
    
    print("\n" + "="*50)
    print("🚀 GREENLAND UNIVERSITY WITH EXAM SYSTEM READY!")
    print("="*50)

if __name__ == "__main__":
    main()
