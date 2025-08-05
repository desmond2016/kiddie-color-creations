#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用URL编码测试Supabase数据库连接
"""

import urllib.parse
from sqlalchemy import create_engine, text
import sys

def test_url_encoded_connection():
    """使用URL编码测试数据库连接"""
    try:
        # 分别编码各个部分
        username = "postgres"
        password = urllib.parse.quote_plus("t5O4sH9UJxXJf3sQ")
        host = "db.fvbifgzxwvaffyuzaegr.supabase.co"
        port = "5432"
        database = "postgres"
        
        # 构建URL
        database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        
        print("正在使用URL编码测试连接...")
        print(f"编码后的URL: {database_url}")
        
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
    success = test_url_encoded_connection()
    sys.exit(0 if success else 1)
