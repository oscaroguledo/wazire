#!/usr/bin/env python3
"""
Comprehensive API testing script
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(method, path, data=None, headers=None, expected_status=200):
    """Test a single endpoint"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{path}", headers=headers)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{path}", json=data, headers=headers)
        elif method == "PUT":
            response = requests.put(f"{BASE_URL}{path}", json=data, headers=headers)
        elif method == "DELETE":
            response = requests.delete(f"{BASE_URL}{path}", headers=headers)
        
        status = "✅" if response.status_code == expected_status else f"❌ ({response.status_code})"
        return f"{status} {method} {path} - {response.status_code}"
    except Exception as e:
        return f"❌ {method} {path} - ERROR: {str(e)}"

def main():
    print("=== 🚀 COMPREHENSIVE API TEST ===\n")
    
    # Test endpoints that don't require auth
    print("🟢 PUBLIC ENDPOINTS:")
    print(test_endpoint("GET", "/health"))
    print(test_endpoint("GET", "/docs"))
    
    # Setup users
    print("\n🔐 AUTH SETUP:")
    
    # Create admin
    admin_data = {
        "email": "admin@test.com",
        "password": "adminpass123",
        "first_name": "Admin",
        "last_name": "User",
        "full_name": "Admin User",
        "role": "admin"
    }
    
    try:
        requests.post(f"{BASE_URL}/api/v1/auth/register", json=admin_data)
    except:
        pass
    
    # Login admin
    admin_login = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "adminpass123"
    })
    
    admin_token = None
    if admin_login.status_code == 200:
        admin_token = admin_login.json().get("access_token")
        print("✅ Admin login successful")
    else:
        print("❌ Admin login failed")
        return
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create student
    student_data = {
        "email": "student@test.com", 
        "password": "studentpass123",
        "first_name": "Student",
        "last_name": "User", 
        "full_name": "Student User",
        "role": "student"
    }
    
    try:
        requests.post(f"{BASE_URL}/api/v1/auth/register", json=student_data)
    except:
        pass
    
    student_login = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "student@test.com",
        "password": "studentpass123"
    })
    
    student_token = None
    if student_login.status_code == 200:
        student_token = student_login.json().get("access_token")
        print("✅ Student login successful")
    
    student_headers = {"Authorization": f"Bearer {student_token}"}
    
    print("\n🟡 AUTH ENDPOINTS:")
    print(test_endpoint("POST", "/api/v1/auth/register", admin_data))
    print(test_endpoint("POST", "/api/v1/auth/login", {"email": "admin@test.com", "password": "adminpass123"}))
    print(test_endpoint("GET", "/api/v1/auth/me", headers=admin_headers))
    
    print("\n🏢 TENANT ENDPOINTS:")
    print(test_endpoint("POST", "/api/v1/tenants/", {"name": "Test University", "description": "Test"}, admin_headers))
    print(test_endpoint("GET", "/api/v1/tenants/", headers=admin_headers))
    
    print("\n📚 COURSE ENDPOINTS:")
    print(test_endpoint("POST", "/api/v1/academic/courses/", {
        "title": "Math 101", 
        "description": "Basic math", 
        "course_code": "MATH101"
    }, admin_headers))
    print(test_endpoint("GET", "/api/v1/academic/courses/", headers=admin_headers))
    
    print("\n🎓 ENROLLMENT ENDPOINTS:")
    print(test_endpoint("POST", "/api/v1/academic/enrollments/", {
        "student_id": "00000000-0000-0000-0000-000000000000",
        "course_id": "00000000-0000-0000-0000-000000000000"
    }, admin_headers))
    print(test_endpoint("GET", "/api/v1/academic/enrollments/", headers=admin_headers))
    print(test_endpoint("GET", "/api/v1/academic/enrollments/check/?student_id=00000000-0000-0000-0000-000000000000&course_id=00000000-0000-0000-0000-000000000000", headers=admin_headers))
    print(test_endpoint("POST", "/api/v1/academic/enrollments/bulk/", {
        "enrollments": [
            {"student_id": "00000000-0000-0000-0000-000000000000", "course_id": "00000000-0000-0000-0000-000000000000"}
        ]
    }, admin_headers))
    
    print("\n📝 EXAM ENDPOINTS:")
    print(test_endpoint("POST", "/api/v1/academic/exams/", {
        "title": "Math Test",
        "duration": 60
    }, admin_headers))
    print(test_endpoint("GET", "/api/v1/academic/exams/", headers=admin_headers))
    
    print("\n❓ QUESTION ENDPOINTS:")
    print(test_endpoint("GET", "/api/v1/academic/questions/", headers=admin_headers))
    print(test_endpoint("POST", "/api/v1/academic/questions/", {
        "number": "1",
        "text": "What is 2+2?",
        "qtype": "multiple_choice",
        "industry": "mathematics_and_statistics",
        "options": "[a]-4 [b]-3 [c]-5 [d]-2",
        "mark": 5.0
    }, admin_headers))
    
    print("\n💡 ANSWER ENDPOINTS:")
    print(test_endpoint("GET", "/api/v1/academic/answers/", headers=admin_headers))
    print(test_endpoint("POST", "/api/v1/academic/answers/", {"value": "a"}, admin_headers))
    
    print("\n📤 SUBMISSION ENDPOINTS:")
    print(test_endpoint("GET", "/api/v1/academic/submissions/?exam_id=test", headers=admin_headers))
    
    if student_token:
        print(test_endpoint("POST", "/api/v1/academic/submissions/", {
            "exam_id": "00000000-0000-0000-0000-000000000000",
            "answers": {"test": "answer"}
        }, student_headers))
    
    print("\n🏁 TEST COMPLETE!")

if __name__ == "__main__":
    main()
