#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API功能脚本
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_user_registration():
    """测试用户注册"""
    print("🧪 测试用户注册...")

    url = f"{BASE_URL}/api/auth/register"
    data = {
        "username": "testuser456",
        "email": "test456@example.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        return response.status_code == 201
    except Exception as e:
        print(f"❌ 注册测试失败: {e}")
        return False

def test_user_login():
    """测试用户登录"""
    print("\n🧪 测试用户登录...")

    url = f"{BASE_URL}/api/auth/login"
    data = {
        "login": "testuser456",
        "password": "password123"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            token = response.json().get('access_token')
            print(f"获取到token: {token[:50]}...")
            return token
        return None
    except Exception as e:
        print(f"❌ 登录测试失败: {e}")
        return None

def test_admin_login():
    """测试管理员登录"""
    print("\n🧪 测试管理员登录...")

    url = f"{BASE_URL}/api/admin/login"
    data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            token = response.json().get('access_token')
            print(f"获取到管理员token: {token[:50]}...")
            return token
        return None
    except Exception as e:
        print(f"❌ 管理员登录测试失败: {e}")
        return None

def test_user_info(token):
    """测试获取用户信息"""
    print("\n🧪 测试获取用户信息...")

    url = f"{BASE_URL}/api/auth/profile"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 用户信息测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试Supabase环境下的核心功能")
    print("=" * 60)
    
    # 1. 测试用户注册
    registration_success = test_user_registration()
    
    # 2. 测试用户登录
    user_token = test_user_login()
    
    # 3. 测试管理员登录
    admin_token = test_admin_login()
    
    # 4. 测试用户信息获取
    if user_token:
        user_info_success = test_user_info(user_token)
    else:
        user_info_success = False
    
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    print(f"✅ 用户注册: {'成功' if registration_success else '失败'}")
    print(f"✅ 用户登录: {'成功' if user_token else '失败'}")
    print(f"✅ 管理员登录: {'成功' if admin_token else '失败'}")
    print(f"✅ 用户信息: {'成功' if user_info_success else '失败'}")
    
    all_success = all([registration_success, user_token, admin_token, user_info_success])
    print(f"\n🎉 总体结果: {'所有测试通过' if all_success else '部分测试失败'}")
    
    return all_success

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
