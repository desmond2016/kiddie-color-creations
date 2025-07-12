#!/usr/bin/env python3
"""
测试启动脚本 - 验证所有组件是否能正常工作
"""
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """测试所有模块导入"""
    print("📦 测试模块导入...")
    
    try:
        from flask import Flask
        print("✅ Flask 导入成功")
    except ImportError as e:
        print(f"❌ Flask 导入失败: {e}")
        return False
    
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ 环境变量加载成功")
    except ImportError as e:
        print(f"❌ python-dotenv 导入失败: {e}")
        return False
    
    try:
        from models import db, User, RedemptionCode, CreditTransaction, Setting
        print("✅ 数据库模型导入成功")
    except ImportError as e:
        print(f"❌ 数据库模型导入失败: {e}")
        return False
    
    try:
        from auth import auth_bp
        print("✅ 认证模块导入成功")
    except ImportError as e:
        print(f"❌ 认证模块导入失败: {e}")
        return False
    
    try:
        from credits import credits_bp
        print("✅ 积分模块导入成功")
    except ImportError as e:
        print(f"❌ 积分模块导入失败: {e}")
        return False
    
    try:
        from admin import admin_bp
        print("✅ 管理员模块导入成功")
    except ImportError as e:
        print(f"❌ 管理员模块导入失败: {e}")
        return False
    
    return True

def test_app_creation():
    """测试应用创建"""
    print("\n🏗️  测试应用创建...")
    
    try:
        from app import app
        print("✅ Flask应用创建成功")
        
        with app.app_context():
            # 测试数据库连接
            from models import db
            try:
                db.session.execute('SELECT 1')
                print("✅ 数据库连接成功")
            except Exception as e:
                print(f"❌ 数据库连接失败: {e}")
                return False
            
            # 测试路由注册
            routes = [rule.rule for rule in app.url_map.iter_rules()]
            expected_routes = ['/api/auth/login', '/api/credits/generate-creation', '/api/admin/login']
            
            for route in expected_routes:
                if route in routes:
                    print(f"✅ 路由 {route} 注册成功")
                else:
                    print(f"❌ 路由 {route} 未找到")
                    return False
        
        return True
    except Exception as e:
        print(f"❌ 应用创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """测试配置"""
    print("\n⚙️  测试配置...")
    
    # 检查环境变量
    required_vars = ['SECRET_KEY', 'JWT_SECRET_KEY', 'ADMIN_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 缺少环境变量: {missing_vars}")
        print("提示: 请检查 backend/.env 文件")
        return False
    else:
        print("✅ 所有必需的环境变量都已设置")
        return True

def main():
    """主测试函数"""
    print("🔍 开始测试 Kiddie Color Creations 项目...")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("配置检查", test_config),
        ("应用创建", test_app_creation)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 {test_name} 时发生异常: {e}")
            results.append((test_name, False))
    
    # 输出总结
    print("\n" + "=" * 50)
    print("📊 测试总结:")
    
    all_passed = True
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有测试通过！项目可以正常启动。")
        print("\n启动说明:")
        print("1. 确保安装了所有Python依赖: pip install -r backend/requirements.txt")
        print("2. 启动后端: cd backend && python app.py")
        print("3. 打开前端: 在浏览器中打开 frontend/index.html")
    else:
        print("⚠️  存在问题，请根据上述错误信息修复后重试。")
    
    return all_passed

if __name__ == "__main__":
    sys.exit(0 if main() else 1)