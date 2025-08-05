#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重置管理员密码
"""

import os
import psycopg
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# 加载环境变量
load_dotenv('backend/.env')

def reset_admin_password():
    """重置管理员密码"""
    try:
        database_url = os.getenv('DATABASE_URL')
        new_password = "admin123"
        
        # 生成新的密码哈希
        password_hash = generate_password_hash(new_password)
        print(f"新密码哈希: {password_hash[:50]}...")
        
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cursor:
                # 更新管理员密码
                cursor.execute(
                    "UPDATE settings SET value = %s WHERE key = 'admin_password'",
                    (password_hash,)
                )
                
                # 如果不存在则插入
                if cursor.rowcount == 0:
                    cursor.execute(
                        "INSERT INTO settings (key, value) VALUES ('admin_password', %s)",
                        (password_hash,)
                    )
                
                conn.commit()
                print(f"✅ 管理员密码已重置为: {new_password}")
                return True
                
    except Exception as e:
        print(f"❌ 重置失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = reset_admin_password()
    if success:
        print("\n🎉 管理员密码重置成功！")
    else:
        print("\n❌ 管理员密码重置失败！")
