#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用SQLAlchemy测试Supabase数据库连接
"""

from sqlalchemy import create_engine, text
import sys

def test_sqlalchemy_connection():
    """使用SQLAlchemy测试数据库连接"""
    try:
        # 直接使用连接字符串
        database_url = "postgresql://postgres:t5O4sH9UJxXJf3sQ@db.fvbifgzxwvaffyuzaegr.supabase.co:5432/postgres"
        
        print("正在使用SQLAlchemy测试连接...")
        
        # 创建引擎
        engine = create_engine(database_url)
        
        # 测试连接
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()
            print(f"✅ 连接成功！PostgreSQL版本: {version[0][:50]}...")
            
            # 检查现有表
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = result.fetchall()
            print(f"📋 现有表数量: {len(tables)}")
            for table in tables:
                print(f"  - {table[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_sqlalchemy_connection()
    sys.exit(0 if success else 1)
