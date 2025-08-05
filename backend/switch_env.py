#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境配置切换脚本
用于在本地开发环境和生产环境之间切换配置
"""

import os
import shutil
import sys

def switch_to_development():
    """切换到开发环境配置"""
    print("🔄 切换到开发环境配置...")
    
    # 备份当前.env文件
    if os.path.exists('.env'):
        shutil.copy('.env', '.env.backup')
        print("✅ 已备份当前.env文件为.env.backup")
    
    # 创建开发环境配置
    dev_config = """# 开发环境配置
SECRET_KEY='dev-secret-key-change-in-production'
JWT_SECRET_KEY='dev-jwt-secret-change-in-production'

# 本地SQLite数据库
DATABASE_URL='sqlite:///instance/kiddie_color_creations.db'

# 管理员配置
ADMIN_USERNAME='admin'
ADMIN_PASSWORD='admin123'

# 外部 API 配置
IMAGE_API_ENDPOINT="https://api.gptgod.online/v1/chat/completions"
IMAGE_API_KEY=your-api-key-here

# 开发环境配置
FLASK_DEBUG=True
FLASK_ENV=development
PORT=5000
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(dev_config)
    
    print("✅ 已切换到开发环境配置")
    print("📝 使用SQLite数据库，调试模式开启")

def switch_to_production():
    """切换到生产环境配置"""
    print("🔄 切换到生产环境配置...")
    
    if not os.path.exists('.env.production'):
        print("❌ 错误：找不到.env.production文件")
        print("请先创建.env.production文件并填入Supabase配置")
        return False
    
    # 备份当前.env文件
    if os.path.exists('.env'):
        shutil.copy('.env', '.env.backup')
        print("✅ 已备份当前.env文件为.env.backup")
    
    # 复制生产环境配置
    shutil.copy('.env.production', '.env')
    print("✅ 已切换到生产环境配置")
    print("📝 请确保.env文件中的Supabase配置已正确填写")
    return True

def show_current_config():
    """显示当前配置信息"""
    print("📋 当前环境配置:")
    
    if not os.path.exists('.env'):
        print("❌ 未找到.env文件")
        return
    
    with open('.env', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'sqlite' in content.lower():
        print("🔧 环境: 开发环境 (SQLite)")
    elif 'postgresql' in content.lower():
        print("🚀 环境: 生产环境 (PostgreSQL/Supabase)")
    else:
        print("❓ 环境: 未知")
    
    # 显示数据库配置
    for line in content.split('\n'):
        if line.startswith('DATABASE_URL='):
            db_url = line.split('=', 1)[1].strip().strip("'\"")
            if 'sqlite' in db_url:
                print(f"💾 数据库: SQLite")
            elif 'postgresql' in db_url:
                print(f"💾 数据库: PostgreSQL (Supabase)")
            break

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("🔧 环境配置切换工具")
        print("\n使用方法:")
        print("  python switch_env.py dev        # 切换到开发环境")
        print("  python switch_env.py prod       # 切换到生产环境")
        print("  python switch_env.py status     # 显示当前配置")
        print("\n当前状态:")
        show_current_config()
        return
    
    command = sys.argv[1].lower()
    
    if command in ['dev', 'development']:
        switch_to_development()
    elif command in ['prod', 'production']:
        switch_to_production()
    elif command in ['status', 'show']:
        show_current_config()
    else:
        print(f"❌ 未知命令: {command}")
        print("可用命令: dev, prod, status")

if __name__ == '__main__':
    main()
