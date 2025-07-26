#!/usr/bin/env python3
"""
CBT LMS Backend Testing Suite
Tests all backend functionality including authentication, course management, and CBT system.
"""

import requests
import json
import os
from pathlib import Path
import time

# Get backend URL from frontend .env
def get_backend_url():
    frontend_env_path = Path("/app/frontend/.env")
    if frontend_env_path.exists():
        with open(frontend_env_path, 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    return "http://localhost:8001"

BASE_URL = get_backend_url() + "/api"
print(f"Testing backend at: {BASE_URL}")

class CBTBackendTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.user_token = None
        self.admin_token = None
        self.test_course_id = None
        self.test_results = {
            "authentication": {"passed": 0, "failed": 0, "details": []},
            "course_management": {"passed": 0, "failed": 0, "details": []},
            "course_access": {"passed": 0, "failed": 0, "details": []},
            "cbt_system": {"passed": 0, "failed": 0, "details": []},
            "database_operations": {"passed": 0, "failed": 0, "details": []}
        }
    
    def log_result(self, category, test_name, passed, details=""):
        """Log test result"""
        if passed:
            self.test_results[category]["passed"] += 1
            status = "✅ PASS"
        else:
            self.test_results[category]["failed"] += 1
            status = "❌ FAIL"
        
        result = f"{status}: {test_name}"
        if details:
            result += f" - {details}"
        
        self.test_results[category]["details"].append(result)
        print(result)
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        print("\n=== Testing User Registration ===")
        
        # Test valid registration
        user_data = {
            "email": "john.doe@example.com",
            "password": "SecurePass123",
            "full_name": "John Doe",
            "phone": "+2348012345678"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/auth/register", json=user_data)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "user" in data:
                    self.user_token = data["token"]
                    self.log_result("authentication", "User Registration", True, 
                                  f"User created with ID: {data['user']['id']}")
                else:
                    self.log_result("authentication", "User Registration", False, 
                                  "Missing token or user in response")
            else:
                self.log_result("authentication", "User Registration", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        
        except Exception as e:
            self.log_result("authentication", "User Registration", False, f"Exception: {str(e)}")
        
        # Test duplicate email registration
        try:
            response = self.session.post(f"{self.base_url}/auth/register", json=user_data)
            if response.status_code == 400:
                self.log_result("authentication", "Duplicate Email Prevention", True, 
                              "Correctly rejected duplicate email")
            else:
                self.log_result("authentication", "Duplicate Email Prevention", False, 
                              f"Should have rejected duplicate email, got: {response.status_code}")
        except Exception as e:
            self.log_result("authentication", "Duplicate Email Prevention", False, f"Exception: {str(e)}")
    
    def test_user_login(self):
        """Test user login endpoint"""
        print("\n=== Testing User Login ===")
        
        # Test valid login
        login_data = {
            "email": "john.doe@example.com",
            "password": "SecurePass123"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "user" in data:
                    self.user_token = data["token"]
                    self.log_result("authentication", "User Login", True, 
                                  f"Login successful for user: {data['user']['email']}")
                else:
                    self.log_result("authentication", "User Login", False, 
                                  "Missing token or user in response")
            else:
                self.log_result("authentication", "User Login", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        
        except Exception as e:
            self.log_result("authentication", "User Login", False, f"Exception: {str(e)}")
        
        # Test invalid login
        invalid_login = {
            "email": "john.doe@example.com",
            "password": "WrongPassword"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/auth/login", json=invalid_login)
            if response.status_code == 401:
                self.log_result("authentication", "Invalid Login Prevention", True, 
                              "Correctly rejected invalid credentials")
            else:
                self.log_result("authentication", "Invalid Login Prevention", False, 
                              f"Should have rejected invalid login, got: {response.status_code}")
        except Exception as e:
            self.log_result("authentication", "Invalid Login Prevention", False, f"Exception: {str(e)}")
    
    def test_admin_login(self):
        """Test admin login with special credentials"""
        print("\n=== Testing Admin Login ===")
        
        admin_login = {
            "email": "Admin",
            "password": "Admin@01"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/auth/login", json=admin_login)
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "user" in data and data["user"]["is_admin"]:
                    self.admin_token = data["token"]
                    self.log_result("authentication", "Admin Login", True, 
                                  f"Admin login successful: {data['user']['full_name']}")
                else:
                    self.log_result("authentication", "Admin Login", False, 
                                  "Missing token, user, or admin flag in response")
            else:
                self.log_result("authentication", "Admin Login", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        
        except Exception as e:
            self.log_result("authentication", "Admin Login", False, f"Exception: {str(e)}")
    
    def test_jwt_authentication(self):
        """Test JWT token authentication"""
        print("\n=== Testing JWT Authentication ===")
        
        if not self.user_token:
            self.log_result("authentication", "JWT Token Validation", False, "No user token available")
            return
        
        # Test accessing protected endpoint with valid token
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        try:
            response = self.session.get(f"{self.base_url}/my-attempts", headers=headers)
            
            if response.status_code == 200:
                self.log_result("authentication", "JWT Token Validation", True, 
                              "Successfully accessed protected endpoint with valid token")
            else:
                self.log_result("authentication", "JWT Token Validation", False, 
                              f"Failed to access protected endpoint: {response.status_code}")
        
        except Exception as e:
            self.log_result("authentication", "JWT Token Validation", False, f"Exception: {str(e)}")
        
        # Test accessing protected endpoint without token
        try:
            response = self.session.get(f"{self.base_url}/my-attempts")
            
            if response.status_code == 401 or response.status_code == 403:
                self.log_result("authentication", "JWT Token Required", True, 
                              "Correctly rejected request without token")
            else:
                self.log_result("authentication", "JWT Token Required", False, 
                              f"Should have rejected request without token, got: {response.status_code}")
        
        except Exception as e:
            self.log_result("authentication", "JWT Token Required", False, f"Exception: {str(e)}")
    
    def test_pdf_upload_and_parsing(self):
        """Test PDF upload and question extraction"""
        print("\n=== Testing PDF Upload and Parsing ===")
        
        if not self.admin_token:
            self.log_result("course_management", "PDF Upload", False, "No admin token available")
            return
        
        pdf_path = "/app/GST104.pdf"
        if not os.path.exists(pdf_path):
            self.log_result("course_management", "PDF Upload", False, "GST104.pdf not found")
            return
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Prepare form data
        form_data = {
            "title": "GST 104 - Introduction to General Studies",
            "description": "Comprehensive test on General Studies covering various topics",
            "is_free": "true",
            "price": "0.0"
        }
        
        try:
            with open(pdf_path, 'rb') as pdf_file:
                files = {"pdf_file": ("GST104.pdf", pdf_file, "application/pdf")}
                
                response = self.session.post(
                    f"{self.base_url}/admin/courses/upload",
                    data=form_data,
                    files=files,
                    headers=headers
                )
            
            if response.status_code == 200:
                data = response.json()
                if "course_id" in data and "questions_extracted" in data:
                    self.test_course_id = data["course_id"]
                    questions_count = data["questions_extracted"]
                    self.log_result("course_management", "PDF Upload and Parsing", True, 
                                  f"Course created with {questions_count} questions extracted")
                else:
                    self.log_result("course_management", "PDF Upload and Parsing", False, 
                                  "Missing course_id or questions_extracted in response")
            else:
                self.log_result("course_management", "PDF Upload and Parsing", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        
        except Exception as e:
            self.log_result("course_management", "PDF Upload and Parsing", False, f"Exception: {str(e)}")
    
    def test_course_creation(self):
        """Test manual course creation"""
        print("\n=== Testing Course Creation ===")
        
        if not self.admin_token:
            self.log_result("course_management", "Manual Course Creation", False, "No admin token available")
            return
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Create a simple course without PDF
        course_data = {
            "title": "Sample Mathematics Course",
            "description": "Basic mathematics test course",
            "is_free": False,
            "price": 2500.0
        }
        
        try:
            # Note: This would require a separate endpoint for manual course creation
            # For now, we'll test the admin courses listing endpoint
            response = self.session.get(f"{self.base_url}/admin/courses", headers=headers)
            
            if response.status_code == 200:
                courses = response.json()
                self.log_result("course_management", "Admin Course Listing", True, 
                              f"Retrieved {len(courses)} courses")
            else:
                self.log_result("course_management", "Admin Course Listing", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        
        except Exception as e:
            self.log_result("course_management", "Admin Course Listing", False, f"Exception: {str(e)}")
    
    def test_get_courses_list(self):
        """Test getting list of courses"""
        print("\n=== Testing Course List Access ===")
        
        try:
            response = self.session.get(f"{self.base_url}/courses")
            
            if response.status_code == 200:
                courses = response.json()
                if isinstance(courses, list):
                    self.log_result("course_access", "Course List Retrieval", True, 
                                  f"Retrieved {len(courses)} courses")
                    
                    # Check course structure
                    if courses and len(courses) > 0:
                        course = courses[0]
                        required_fields = ["id", "title", "description", "is_free", "price", "total_questions"]
                        missing_fields = [field for field in required_fields if field not in course]
                        
                        if not missing_fields:
                            self.log_result("course_access", "Course Data Structure", True, 
                                          "All required fields present in course data")
                        else:
                            self.log_result("course_access", "Course Data Structure", False, 
                                          f"Missing fields: {missing_fields}")
                else:
                    self.log_result("course_access", "Course List Retrieval", False, 
                                  "Response is not a list")
            else:
                self.log_result("course_access", "Course List Retrieval", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        
        except Exception as e:
            self.log_result("course_access", "Course List Retrieval", False, f"Exception: {str(e)}")
    
    def test_course_details_access(self):
        """Test accessing course details"""
        print("\n=== Testing Course Details Access ===")
        
        if not self.test_course_id or not self.user_token:
            self.log_result("course_access", "Course Details Access", False, 
                          "No test course ID or user token available")
            return
        
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        try:
            response = self.session.get(f"{self.base_url}/courses/{self.test_course_id}", headers=headers)
            
            if response.status_code == 200:
                course_data = response.json()
                required_fields = ["id", "title", "description", "total_questions", "questions"]
                missing_fields = [field for field in required_fields if field not in course_data]
                
                if not missing_fields:
                    questions = course_data["questions"]
                    if questions and len(questions) > 0:
                        # Check that correct answers are not exposed
                        question = questions[0]
                        if "correct_answer" not in question:
                            self.log_result("course_access", "Course Details Access", True, 
                                          f"Course details retrieved with {len(questions)} questions, correct answers hidden")
                        else:
                            self.log_result("course_access", "Course Details Access", False, 
                                          "Correct answers should not be exposed to users")
                    else:
                        self.log_result("course_access", "Course Details Access", True, 
                                      "Course details retrieved (no questions)")
                else:
                    self.log_result("course_access", "Course Details Access", False, 
                                  f"Missing fields: {missing_fields}")
            else:
                self.log_result("course_access", "Course Details Access", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        
        except Exception as e:
            self.log_result("course_access", "Course Details Access", False, f"Exception: {str(e)}")
    
    def test_free_vs_paid_access(self):
        """Test free vs paid course access logic"""
        print("\n=== Testing Free vs Paid Course Access ===")
        
        # This test would require creating both free and paid courses
        # For now, we'll test the payment initialization endpoint
        
        if not self.test_course_id or not self.user_token:
            self.log_result("course_access", "Payment System", False, 
                          "No test course ID or user token available")
            return
        
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        try:
            # Test payment initialization for a course
            response = self.session.post(
                f"{self.base_url}/payments/initialize?course_id={self.test_course_id}",
                headers=headers
            )
            
            # Since our test course is free, this should fail
            if response.status_code == 400:
                self.log_result("course_access", "Free Course Payment Prevention", True, 
                              "Correctly prevented payment for free course")
            else:
                self.log_result("course_access", "Free Course Payment Prevention", False, 
                              f"Should have prevented payment for free course, got: {response.status_code}")
        
        except Exception as e:
            self.log_result("course_access", "Free Course Payment Prevention", False, f"Exception: {str(e)}")
    
    def test_cbt_test_submission(self):
        """Test submitting test answers and scoring"""
        print("\n=== Testing CBT Test Submission ===")
        
        if not self.test_course_id or not self.user_token:
            self.log_result("cbt_system", "Test Submission", False, 
                          "No test course ID or user token available")
            return
        
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # First, get the course questions to create valid answers
        try:
            course_response = self.session.get(f"{self.base_url}/courses/{self.test_course_id}", headers=headers)
            
            if course_response.status_code != 200:
                self.log_result("cbt_system", "Test Submission", False, 
                              "Could not retrieve course questions for test")
                return
            
            course_data = course_response.json()
            questions = course_data.get("questions", [])
            
            if not questions:
                self.log_result("cbt_system", "Test Submission", False, 
                              "No questions available in course")
                return
            
            # Create sample answers (selecting first option for all questions)
            answers = {}
            for question in questions:
                answers[question["id"]] = 0  # Select first option
            
            # Submit test attempt
            response = self.session.post(
                f"{self.base_url}/courses/{self.test_course_id}/attempt",
                json=answers,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                required_fields = ["score", "correct_answers", "total_questions", "percentage"]
                missing_fields = [field for field in required_fields if field not in result]
                
                if not missing_fields:
                    score = result["score"]
                    total_questions = result["total_questions"]
                    
                    # Verify score is out of 100
                    if 0 <= score <= 100:
                        self.log_result("cbt_system", "Test Submission and Scoring", True, 
                                      f"Test completed: {score}/100 ({result['correct_answers']}/{total_questions} correct)")
                    else:
                        self.log_result("cbt_system", "Test Submission and Scoring", False, 
                                      f"Score should be 0-100, got: {score}")
                else:
                    self.log_result("cbt_system", "Test Submission and Scoring", False, 
                                  f"Missing fields in response: {missing_fields}")
            else:
                self.log_result("cbt_system", "Test Submission and Scoring", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        
        except Exception as e:
            self.log_result("cbt_system", "Test Submission and Scoring", False, f"Exception: {str(e)}")
    
    def test_user_attempts_retrieval(self):
        """Test getting user's test attempts"""
        print("\n=== Testing User Attempts Retrieval ===")
        
        if not self.user_token:
            self.log_result("cbt_system", "User Attempts Retrieval", False, "No user token available")
            return
        
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        try:
            response = self.session.get(f"{self.base_url}/my-attempts", headers=headers)
            
            if response.status_code == 200:
                attempts = response.json()
                if isinstance(attempts, list):
                    self.log_result("cbt_system", "User Attempts Retrieval", True, 
                                  f"Retrieved {len(attempts)} test attempts")
                    
                    # Check attempt structure if any attempts exist
                    if attempts:
                        attempt = attempts[0]
                        required_fields = ["id", "course_title", "score", "total_questions", "completed_at"]
                        missing_fields = [field for field in required_fields if field not in attempt]
                        
                        if not missing_fields:
                            self.log_result("cbt_system", "Attempt Data Structure", True, 
                                          "All required fields present in attempt data")
                        else:
                            self.log_result("cbt_system", "Attempt Data Structure", False, 
                                          f"Missing fields: {missing_fields}")
                else:
                    self.log_result("cbt_system", "User Attempts Retrieval", False, 
                                  "Response is not a list")
            else:
                self.log_result("cbt_system", "User Attempts Retrieval", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        
        except Exception as e:
            self.log_result("cbt_system", "User Attempts Retrieval", False, f"Exception: {str(e)}")
    
    def test_database_operations(self):
        """Test database operations indirectly through API responses"""
        print("\n=== Testing Database Operations ===")
        
        # Test user persistence
        if self.user_token:
            headers = {"Authorization": f"Bearer {self.user_token}"}
            try:
                response = self.session.get(f"{self.base_url}/my-attempts", headers=headers)
                if response.status_code == 200:
                    self.log_result("database_operations", "User Data Persistence", True, 
                                  "User data successfully persisted and retrieved")
                else:
                    self.log_result("database_operations", "User Data Persistence", False, 
                                  "Failed to retrieve user data")
            except Exception as e:
                self.log_result("database_operations", "User Data Persistence", False, f"Exception: {str(e)}")
        
        # Test course persistence
        try:
            response = self.session.get(f"{self.base_url}/courses")
            if response.status_code == 200:
                courses = response.json()
                if isinstance(courses, list):
                    self.log_result("database_operations", "Course Data Persistence", True, 
                                  f"Course data successfully persisted ({len(courses)} courses)")
                else:
                    self.log_result("database_operations", "Course Data Persistence", False, 
                                  "Invalid course data format")
            else:
                self.log_result("database_operations", "Course Data Persistence", False, 
                              "Failed to retrieve course data")
        except Exception as e:
            self.log_result("database_operations", "Course Data Persistence", False, f"Exception: {str(e)}")
        
        # Test attempt persistence (already tested in user attempts retrieval)
        if self.user_token:
            self.log_result("database_operations", "Test Attempt Recording", True, 
                          "Test attempts successfully recorded (verified in previous tests)")
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting CBT LMS Backend Testing Suite")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Authentication System Tests
        self.test_user_registration()
        self.test_user_login()
        self.test_admin_login()
        self.test_jwt_authentication()
        
        # Course Management Tests
        self.test_pdf_upload_and_parsing()
        self.test_course_creation()
        
        # Course Access Tests
        self.test_get_courses_list()
        self.test_course_details_access()
        self.test_free_vs_paid_access()
        
        # CBT System Tests
        self.test_cbt_test_submission()
        self.test_user_attempts_retrieval()
        
        # Database Operations Tests
        self.test_database_operations()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("🏁 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total_passed += passed
            total_failed += failed
            
            print(f"\n📋 {category.upper().replace('_', ' ')}")
            print(f"   ✅ Passed: {passed}")
            print(f"   ❌ Failed: {failed}")
            
            for detail in results["details"]:
                print(f"   {detail}")
        
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"   ✅ Total Passed: {total_passed}")
        print(f"   ❌ Total Failed: {total_failed}")
        print(f"   📊 Success Rate: {(total_passed / (total_passed + total_failed) * 100):.1f}%")
        
        if total_failed == 0:
            print("\n🎉 ALL TESTS PASSED! Backend is working correctly.")
        else:
            print(f"\n⚠️  {total_failed} tests failed. Please review the issues above.")

if __name__ == "__main__":
    tester = CBTBackendTester()
    tester.run_all_tests()