#!/usr/bin/env python3
"""
Test the new features with existing courses
"""

import requests
import json
from pathlib import Path

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

def test_new_features():
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
    
    # Get existing courses
    response = session.get(f"{BASE_URL}/admin/courses", headers=headers)
    if response.status_code == 200:
        courses = response.json()
        print(f"Found {len(courses)} existing courses:")
        
        for course in courses:
            print(f"- {course['title']} (ID: {course['id']})")
            
            # Test course statistics
            print(f"\n=== Testing Course Statistics for {course['title']} ===")
            stats_response = session.get(f"{BASE_URL}/admin/courses/{course['id']}/details", headers=headers)
            
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                print("✅ Course statistics retrieved successfully")
                print(f"   Course: {stats_data['course']['title']}")
                print(f"   Statistics: {stats_data['statistics']}")
            else:
                print(f"❌ Failed to get statistics: {stats_response.status_code}")
            
            # Test course deletion (only delete one course for testing)
            if course['title'].startswith('Enhanced GST') or course['title'].startswith('GST 104'):
                print(f"\n=== Testing Course Deletion for {course['title']} ===")
                delete_response = session.delete(f"{BASE_URL}/admin/courses/{course['id']}", headers=headers)
                
                if delete_response.status_code == 200:
                    delete_data = delete_response.json()
                    print("✅ Course deleted successfully")
                    print(f"   Message: {delete_data['message']}")
                    print(f"   Attempts deleted: {delete_data.get('attempts_deleted', 0)}")
                    print(f"   Payments deleted: {delete_data.get('payments_deleted', 0)}")
                else:
                    print(f"❌ Failed to delete course: {delete_response.status_code}")
                
                break  # Only delete one course for testing
    else:
        print("Failed to get courses list")

if __name__ == "__main__":
    test_new_features()