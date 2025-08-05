#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Supabase数据库连接和初始化脚本
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_connection():
    """测试数据库连接"""
    try:
        import psycopg2
        
        database_url = os.getenv('DATABASE_URL')
        print(f"正在测试连接到: {database_url[:50]}...")
        
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
        return False

def create_tables():
    """创建数据库表"""
    try:
        from app import app
        from models import db, User, Setting, RedemptionCode
        
        print("🔧 正在创建数据库表...")
        
        with app.app_context():
            # 创建所有表
            db.create_all()
            print("✅ 数据库表创建成功")
            
            # 检查表是否创建成功
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 创建的表: {tables}")
            
            return True
            
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def initialize_admin():
    """初始化管理员账户"""
    try:
        from app import app
        from models import db, Setting
        from werkzeug.security import generate_password_hash
        
        print("👤 正在初始化管理员账户...")
        
        with app.app_context():
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
            
            # 检查是否已存在管理员密码设置
            existing_setting = Setting.query.get('admin_password')
            if existing_setting:
                print("ℹ️  管理员密码已存在，跳过初始化")
            else:
                # 创建管理员密码设置
                hashed_password = generate_password_hash(admin_password)
                admin_setting = Setting(key='admin_password', value=hashed_password)
                db.session.add(admin_setting)
                db.session.commit()
                print("✅ 管理员密码初始化成功")
            
            return True
            
    except Exception as e:
        print(f"❌ 初始化管理员失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 Supabase数据库连接测试")
    print("=" * 50)
    
    # 1. 测试连接
    if not test_connection():
        print("❌ 数据库连接失败，请检查配置")
        return False
    
    print("\n" + "=" * 50)
    
    # 2. 创建表
    if not create_tables():
        print("❌ 创建表失败")
        return False
    
    print("\n" + "=" * 50)
    
    # 3. 初始化管理员
    if not initialize_admin():
        print("❌ 初始化管理员失败")
        return False
    
    print("\n🎉 数据库初始化完成！")
    print("现在可以启动应用程序了")
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
