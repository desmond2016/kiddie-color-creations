#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查管理员密码设置
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置环境编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def check_admin_settings():
    """检查管理员设置"""
    try:
        # 导入Flask应用和模型
        sys.path.append('backend')
        from backend.app import app
        from backend.models import db, Setting
        from werkzeug.security import check_password_hash
        
        with app.app_context():
            # 查看所有设置
            settings = Setting.query.all()
            print("📋 数据库中的所有设置:")
            for setting in settings:
                if 'password' in setting.key:
                    print(f"  - {setting.key}: [密码哈希]")
                else:
                    print(f"  - {setting.key}: {setting.value}")
            
            # 检查管理员密码
            admin_password_setting = Setting.query.get('admin_password')
            if admin_password_setting:
                print(f"\n🔑 管理员密码设置存在")
                
                # 测试密码
                test_passwords = ['admin123', 'admin', 'password', '123456']
                for pwd in test_passwords:
                    if check_password_hash(admin_password_setting.value, pwd):
                        print(f"✅ 正确的管理员密码是: {pwd}")
                        return pwd
                
                print("❌ 测试的密码都不正确")
                return None
            else:
                print("❌ 未找到管理员密码设置")
                return None
                
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    admin_password = check_admin_settings()
    if admin_password:
        print(f"\n🎉 管理员密码: {admin_password}")
    else:
        print("\n❌ 无法确定管理员密码")
