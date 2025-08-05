#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接查询数据库检查管理员设置
"""

import os
import psycopg
from dotenv import load_dotenv
from werkzeug.security import check_password_hash

# 加载环境变量
load_dotenv('backend/.env')

def check_admin_direct():
    """直接查询数据库"""
    try:
        database_url = os.getenv('DATABASE_URL')
        print(f"数据库URL: {database_url[:50]}..." if database_url else "❌ 未找到DATABASE_URL")
        
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cursor:
                # 查询所有设置
                cursor.execute("SELECT key, value FROM settings")
                settings = cursor.fetchall()
                
                print("📋 数据库中的所有设置:")
                admin_password_hash = None
                for key, value in settings:
                    if 'password' in key:
                        print(f"  - {key}: [密码哈希]")
                        if key == 'admin_password':
                            admin_password_hash = value
                    else:
                        print(f"  - {key}: {value}")
                
                if admin_password_hash:
                    print(f"\n🔑 找到管理员密码哈希")
                    
                    # 测试密码
                    test_passwords = ['admin123', 'admin', 'password', '123456']
                    for pwd in test_passwords:
                        if check_password_hash(admin_password_hash, pwd):
                            print(f"✅ 正确的管理员密码是: {pwd}")
                            return pwd
                    
                    print("❌ 测试的密码都不正确")
                    print(f"密码哈希: {admin_password_hash[:50]}...")
                else:
                    print("❌ 未找到管理员密码设置")
                
                return None
                
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    admin_password = check_admin_direct()
    if admin_password:
        print(f"\n🎉 管理员密码: {admin_password}")
    else:
        print("\n❌ 无法确定管理员密码")
