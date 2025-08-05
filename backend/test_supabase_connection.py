#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Supabase数据库连接 - 解决Windows编码问题
"""

import os
import sys
from dotenv import load_dotenv

# 设置环境编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 加载环境变量
load_dotenv()

def test_connection_with_psycopg():
    """使用psycopg测试连接"""
    try:
        import psycopg
        
        database_url = os.getenv('DATABASE_URL')
        print(f"正在测试连接到: {database_url[:50]}...")
        
        # 测试连接
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cursor:
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
        
        return True
        
    except Exception as e:
        print(f"❌ psycopg连接失败: {e}")
        return False

def test_connection_with_sqlalchemy():
    """使用SQLAlchemy测试连接"""
    try:
        from sqlalchemy import create_engine, text
        
        database_url = os.getenv('DATABASE_URL')
        print(f"正在使用SQLAlchemy测试连接...")
        
        # 创建引擎，使用psycopg驱动
        engine = create_engine(database_url.replace('postgresql://', 'postgresql+psycopg://'))
        
        # 测试连接
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()
            print(f"✅ SQLAlchemy连接成功！PostgreSQL版本: {version[0][:50]}...")
            
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
        print(f"❌ SQLAlchemy连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 Supabase数据库连接测试 (解决编码问题)")
    print("=" * 60)
    
    # 1. 测试psycopg连接
    print("\n1. 测试psycopg连接:")
    psycopg_success = test_connection_with_psycopg()
    
    print("\n" + "=" * 60)
    
    # 2. 测试SQLAlchemy连接
    print("\n2. 测试SQLAlchemy连接:")
    sqlalchemy_success = test_connection_with_sqlalchemy()
    
    print("\n" + "=" * 60)
    
    if psycopg_success or sqlalchemy_success:
        print("🎉 至少一种连接方式成功！")
        return True
    else:
        print("❌ 所有连接方式都失败了")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
