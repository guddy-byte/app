#!/usr/bin/env python3
"""
Test enhanced PDF parsing specifically
"""

import requests
import json
from pathlib import Path
import os

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

def test_enhanced_pdf_parsing():
    session = requests.Session()
    
    # Login as admin
    admin_login = {
        "email": "Admin",
        "password": "Admin@01"
    }
    
    response = session.post(f"{BASE_URL}/auth/login", json=admin_login)
    if response.status_code != 200:
        print("Failed to login as admin")
        return
    
    admin_token = response.json()["token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test enhanced PDF parsing
    pdf_path = "/app/GST104.pdf"
    if not os.path.exists(pdf_path):
        print("GST104.pdf not found")
        return
    
    form_data = {
        "title": "Enhanced GST 104 - PDF Parsing Test",
        "description": "Testing enhanced PDF parsing capabilities with deduplication",
        "is_free": "true",
        "price": "0.0"
    }
    
    print("=== Testing Enhanced PDF Parsing ===")
    
    with open(pdf_path, 'rb') as pdf_file:
        files = {"pdf_file": ("GST104.pdf", pdf_file, "application/pdf")}
        
        response = session.post(
            f"{BASE_URL}/admin/courses/upload",
            data=form_data,
            files=files,
            headers=headers
        )
    
    if response.status_code == 200:
        data = response.json()
        questions_count = data["questions_extracted"]
        print(f"✅ Enhanced PDF parsing successful!")
        print(f"   Questions extracted: {questions_count}")
        print(f"   Course ID: {data['course_id']}")
        
        # Test course statistics for the new course
        course_id = data['course_id']
        print(f"\n=== Testing Course Statistics ===")
        stats_response = session.get(f"{BASE_URL}/admin/courses/{course_id}/details", headers=headers)
        
        if stats_response.status_code == 200:
            stats_data = stats_response.json()
            print("✅ Course statistics retrieved successfully")
            print(f"   Statistics: {stats_data['statistics']}")
        else:
            print(f"❌ Failed to get statistics: {stats_response.status_code}")
        
        # Test course deletion
        print(f"\n=== Testing Course Deletion ===")
        delete_response = session.delete(f"{BASE_URL}/admin/courses/{course_id}", headers=headers)
        
        if delete_response.status_code == 200:
            delete_data = delete_response.json()
            print("✅ Course deleted successfully")
            print(f"   Message: {delete_data['message']}")
            print(f"   Attempts deleted: {delete_data.get('attempts_deleted', 0)}")
            print(f"   Payments deleted: {delete_data.get('payments_deleted', 0)}")
        else:
            print(f"❌ Failed to delete course: {delete_response.status_code}")
            
    else:
        print(f"❌ Enhanced PDF parsing failed: {response.status_code}")
        print(f"   Response: {response.text}")

if __name__ == "__main__":
    test_enhanced_pdf_parsing()