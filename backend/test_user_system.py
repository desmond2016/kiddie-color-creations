# -*- coding: utf-8 -*-
"""
用户系统功能测试脚本
测试用户注册、登录、管理员功能
"""
import requests
import json
import time
from datetime import datetime

# 测试配置
BASE_URL = "http://localhost:5000"
TEST_USER = {
    "username": "testuser123",
    "email": "test@example.com", 
    "password": "test123456"
}
ADMIN_CREDENTIALS = {
    "username": "admin",
    "password": "admin123"
}

class UserSystemTester:
    def __init__(self):
        self.session = requests.Session()
        self.user_token = None
        self.admin_token = None
        self.test_user_id = None
        
    def log(self, message, status="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {status}: {message}")
        
    def test_api_health(self):
        """测试API健康状态"""
        self.log("🔍 测试API健康状态...")
        try:
            response = self.session.get(f"{BASE_URL}/api/auth/health")
            if response.status_code == 200:
                self.log("✅ API健康检查通过", "SUCCESS")
                return True
            else:
                self.log(f"❌ API健康检查失败: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ API连接失败: {str(e)}", "ERROR")
            return False
    
    def test_user_registration(self):
        """测试用户注册"""
        self.log("🔍 测试用户注册...")
        try:
            # 先尝试删除可能存在的测试用户（通过登录检查）
            login_response = self.session.post(
                f"{BASE_URL}/api/auth/login",
                json={"login": TEST_USER["username"], "password": TEST_USER["password"]},
                headers={"Content-Type": "application/json"}
            )
            if login_response.status_code == 200:
                self.log("⚠️ 测试用户已存在，跳过注册测试", "WARNING")
                data = login_response.json()
                self.user_token = data.get("access_token")
                self.test_user_id = data.get("user", {}).get("id")
                return True
            
            # 进行注册
            response = self.session.post(
                f"{BASE_URL}/api/auth/register",
                json=TEST_USER,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                data = response.json()
                self.user_token = data.get("access_token")
                self.test_user_id = data.get("user", {}).get("id")
                self.log("✅ 用户注册成功", "SUCCESS")
                self.log(f"   用户ID: {self.test_user_id}")
                self.log(f"   用户名: {data.get('user', {}).get('username')}")
                self.log(f"   积分: {data.get('user', {}).get('credits')}")
                return True
            else:
                self.log(f"❌ 用户注册失败: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ 用户注册异常: {str(e)}", "ERROR")
            return False
    
    def test_user_login(self):
        """测试用户登录"""
        self.log("🔍 测试用户登录...")
        try:
            response = self.session.post(
                f"{BASE_URL}/api/auth/login",
                json={"login": TEST_USER["username"], "password": TEST_USER["password"]},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.user_token = data.get("access_token")
                self.test_user_id = data.get("user", {}).get("id")
                self.log("✅ 用户登录成功", "SUCCESS")
                self.log(f"   Token: {self.user_token[:20]}...")
                return True
            else:
                self.log(f"❌ 用户登录失败: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ 用户登录异常: {str(e)}", "ERROR")
            return False
    
    def test_user_profile(self):
        """测试获取用户信息"""
        self.log("🔍 测试获取用户信息...")
        if not self.user_token:
            self.log("❌ 没有用户Token，跳过测试", "ERROR")
            return False
            
        try:
            response = self.session.get(
                f"{BASE_URL}/api/auth/profile",
                headers={"Authorization": f"Bearer {self.user_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                user = data.get("user", {})
                self.log("✅ 获取用户信息成功", "SUCCESS")
                self.log(f"   用户名: {user.get('username')}")
                self.log(f"   邮箱: {user.get('email')}")
                self.log(f"   积分: {user.get('credits')}")
                self.log(f"   注册时间: {user.get('created_at')}")
                return True
            else:
                self.log(f"❌ 获取用户信息失败: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ 获取用户信息异常: {str(e)}", "ERROR")
            return False
    
    def test_admin_login(self):
        """测试管理员登录"""
        self.log("🔍 测试管理员登录...")
        try:
            response = self.session.post(
                f"{BASE_URL}/api/admin/login",
                json=ADMIN_CREDENTIALS,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.log("✅ 管理员登录成功", "SUCCESS")
                self.log(f"   Token: {self.admin_token[:20]}...")
                return True
            else:
                self.log(f"❌ 管理员登录失败: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ 管理员登录异常: {str(e)}", "ERROR")
            return False
    
    def test_admin_stats(self):
        """测试管理员统计数据"""
        self.log("🔍 测试管理员统计数据...")
        if not self.admin_token:
            self.log("❌ 没有管理员Token，跳过测试", "ERROR")
            return False
            
        try:
            response = self.session.get(
                f"{BASE_URL}/api/admin/stats",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log("✅ 获取统计数据成功", "SUCCESS")
                self.log(f"   总用户数: {data.get('users', {}).get('total', 0)}")
                self.log(f"   总积分: {data.get('users', {}).get('total_credits', 0)}")
                self.log(f"   总兑换码: {data.get('codes', {}).get('total', 0)}")
                self.log(f"   已使用兑换码: {data.get('codes', {}).get('used', 0)}")
                return True
            else:
                self.log(f"❌ 获取统计数据失败: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ 获取统计数据异常: {str(e)}", "ERROR")
            return False
    
    def test_admin_users_list(self):
        """测试管理员用户列表"""
        self.log("🔍 测试管理员用户列表...")
        if not self.admin_token:
            self.log("❌ 没有管理员Token，跳过测试", "ERROR")
            return False
            
        try:
            response = self.session.get(
                f"{BASE_URL}/api/admin/users?page=1&per_page=5",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                users = data.get("users", [])
                pagination = data.get("pagination", {})
                self.log("✅ 获取用户列表成功", "SUCCESS")
                self.log(f"   当前页用户数: {len(users)}")
                self.log(f"   总用户数: {pagination.get('total', 0)}")
                self.log(f"   总页数: {pagination.get('pages', 0)}")
                
                # 显示前几个用户信息
                for i, user in enumerate(users[:3]):
                    self.log(f"   用户{i+1}: {user.get('username')} ({user.get('email')}) - {user.get('credits')}积分")
                
                return True
            else:
                self.log(f"❌ 获取用户列表失败: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ 获取用户列表异常: {str(e)}", "ERROR")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        self.log("🚀 开始用户系统功能测试", "INFO")
        self.log("=" * 50)
        
        tests = [
            ("API健康检查", self.test_api_health),
            ("用户注册", self.test_user_registration),
            ("用户登录", self.test_user_login),
            ("用户信息", self.test_user_profile),
            ("管理员登录", self.test_admin_login),
            ("管理员统计", self.test_admin_stats),
            ("管理员用户列表", self.test_admin_users_list),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            self.log(f"\n--- {test_name} ---")
            if test_func():
                passed += 1
            time.sleep(0.5)  # 避免请求过快
        
        self.log("\n" + "=" * 50)
        self.log(f"🎯 测试完成: {passed}/{total} 通过", "INFO")
        
        if passed == total:
            self.log("🎉 所有测试通过！用户系统功能正常", "SUCCESS")
        else:
            self.log(f"⚠️ 有 {total - passed} 个测试失败", "WARNING")

if __name__ == "__main__":
    tester = UserSystemTester()
    tester.run_all_tests()
