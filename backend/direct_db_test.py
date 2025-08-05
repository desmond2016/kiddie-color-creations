#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试Supabase数据库连接
"""

import psycopg2

def test_direct_connection():
    """直接测试数据库连接"""
    try:
        # 直接使用连接字符串
        database_url = "postgresql://postgres:t5O4sH9UJxXJf3sQ@db.fvbifgzxwvaffyuzaegr.supabase.co:5432/postgres"
        
        print("正在测试直接连接...")
        
        # 测试连接
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # 执行简单查询
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ 连接成功！PostgreSQL版本: {version[0][:50]}...")
        
        # 检查现有表
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        print(f"📋 现有表数量: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_direct_connection()
