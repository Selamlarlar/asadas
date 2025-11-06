import requests
import sys
from datetime import datetime
import json

class TFDAPITester:
    def __init__(self, base_url="https://tfd-roblox.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.admin_token = None
        self.founder_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
        elif self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)

            success = response.status_code == expected_status
            
            if success:
                self.log_test(name, True)
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                error_msg = f"Expected {expected_status}, got {response.status_code}"
                try:
                    error_detail = response.json().get('detail', '')
                    if error_detail:
                        error_msg += f" - {error_detail}"
                except:
                    pass
                self.log_test(name, False, error_msg)
                return False, {}

        except requests.exceptions.RequestException as e:
            self.log_test(name, False, f"Request error: {str(e)}")
            return False, {}
        except Exception as e:
            self.log_test(name, False, f"Unexpected error: {str(e)}")
            return False, {}

    def test_register(self):
        """Test user registration"""
        timestamp = datetime.now().strftime('%H%M%S')
        test_user = {
            "username": f"testuser_{timestamp}",
            "nickname": f"Test User {timestamp}",
            "email": f"test_{timestamp}@example.com",
            "password": "TestPass123!"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=test_user
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   Registered user: {test_user['username']}")
            return True, test_user
        return False, {}

    def test_login(self, username, password):
        """Test user login"""
        login_data = {"username": username, "password": password}
        
        success, response = self.run_test(
            f"User Login ({username})",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            return True, response
        return False, {}

    def test_admin_login(self, username, password, role_name):
        """Test admin login"""
        admin_data = {"username": username, "password": password}
        
        success, response = self.run_test(
            f"Admin Login ({role_name})",
            "POST",
            "auth/admin-login",
            200,
            data=admin_data
        )
        
        if success and 'access_token' in response:
            if role_name == "Admin":
                self.admin_token = response['access_token']
            else:
                self.founder_token = response['access_token']
            return True, response
        return False, {}

    def test_get_current_user(self, token_type="regular"):
        """Test getting current user info"""
        token = self.token
        if token_type == "admin":
            token = self.admin_token
        elif token_type == "founder":
            token = self.founder_token
            
        success, response = self.run_test(
            f"Get Current User ({token_type})",
            "GET",
            "users/me",
            200,
            token=token
        )
        return success, response

    def test_online_count(self):
        """Test getting online user count"""
        success, response = self.run_test(
            "Get Online Count",
            "GET",
            "users/online-count",
            200
        )
        
        if success and 'online_count' in response:
            print(f"   Online users: {response['online_count']}")
        return success, response

    def test_send_message(self, message_text, token_type="regular"):
        """Test sending chat message"""
        token = self.token
        if token_type == "admin":
            token = self.admin_token
        elif token_type == "founder":
            token = self.founder_token
            
        message_data = {"message": message_text}
        
        success, response = self.run_test(
            f"Send Chat Message ({token_type})",
            "POST",
            "chat/messages",
            200,
            data=message_data,
            token=token
        )
        return success, response

    def test_get_messages(self):
        """Test getting chat messages"""
        success, response = self.run_test(
            "Get Chat Messages",
            "GET",
            "chat/messages",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} messages")
        return success, response

    def test_create_announcement(self, title, content, image_url=None, token_type="admin"):
        """Test creating announcement (admin/founder only)"""
        token = self.admin_token if token_type == "admin" else self.founder_token
        
        announcement_data = {
            "title": title,
            "content": content,
            "image_url": image_url
        }
        
        success, response = self.run_test(
            f"Create Announcement ({token_type})",
            "POST",
            "announcements",
            200,
            data=announcement_data,
            token=token
        )
        return success, response

    def test_get_announcements(self):
        """Test getting announcements"""
        success, response = self.run_test(
            "Get Announcements",
            "GET",
            "announcements",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} announcements")
        return success, response

    def test_regular_user_announcement_forbidden(self):
        """Test that regular users cannot create announcements"""
        announcement_data = {
            "title": "Test Forbidden",
            "content": "This should fail"
        }
        
        success, response = self.run_test(
            "Regular User Announcement (Should Fail)",
            "POST",
            "announcements",
            403,  # Expecting forbidden
            data=announcement_data,
            token=self.token
        )
        return success, response

    def test_logout(self, token_type="regular"):
        """Test logout"""
        token = self.token
        if token_type == "admin":
            token = self.admin_token
        elif token_type == "founder":
            token = self.founder_token
            
        success, response = self.run_test(
            f"Logout ({token_type})",
            "POST",
            "auth/logout",
            200,
            token=token
        )
        return success, response

def main():
    print("🚀 Starting TFD API Tests...")
    print("=" * 50)
    
    tester = TFDAPITester()
    
    # Test 1: User Registration
    print("\n📝 Testing User Registration & Authentication...")
    reg_success, test_user = tester.test_register()
    if not reg_success:
        print("❌ Registration failed, stopping tests")
        return 1

    # Test 2: User Login
    login_success, _ = tester.test_login(test_user['username'], test_user['password'])
    if not login_success:
        print("❌ Login failed, stopping tests")
        return 1

    # Test 3: Get Current User
    tester.test_get_current_user("regular")

    # Test 4: Admin Logins
    print("\n🔑 Testing Admin Authentication...")
    admin_success, _ = tester.test_admin_login("Admintfd", "tfdadamdır", "Admin")
    founder_success, _ = tester.test_admin_login("Efe", "Efeisholderr", "Founder")
    
    if admin_success:
        tester.test_get_current_user("admin")
    if founder_success:
        tester.test_get_current_user("founder")

    # Test 5: Online Count
    print("\n👥 Testing User Management...")
    tester.test_online_count()

    # Test 6: Chat System
    print("\n💬 Testing Chat System...")
    tester.test_send_message("Test message from regular user", "regular")
    if admin_success:
        tester.test_send_message("Test message from admin", "admin")
    if founder_success:
        tester.test_send_message("Test message from founder", "founder")
    
    tester.test_get_messages()

    # Test 7: Announcements
    print("\n📢 Testing Announcement System...")
    tester.test_get_announcements()
    
    # Test regular user cannot create announcements
    tester.test_regular_user_announcement_forbidden()
    
    # Test admin/founder can create announcements
    if admin_success:
        tester.test_create_announcement(
            "Admin Test Announcement", 
            "This is a test announcement from admin",
            "https://via.placeholder.com/300x200",
            "admin"
        )
    
    if founder_success:
        tester.test_create_announcement(
            "Founder Test Announcement", 
            "This is a test announcement from founder",
            None,
            "founder"
        )
    
    # Get announcements again to verify creation
    tester.test_get_announcements()

    # Test 8: Logout
    print("\n🚪 Testing Logout...")
    tester.test_logout("regular")
    if admin_success:
        tester.test_logout("admin")
    if founder_success:
        tester.test_logout("founder")

    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the details above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())