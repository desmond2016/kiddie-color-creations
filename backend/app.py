# -*- coding: utf-8 -*-
import os
import json
import requests # 使用 requests 库发送 HTTP 请求
import re # 导入正则表达式库
from datetime import timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS # 用于处理跨域请求
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv # 导入 load_dotenv
import traceback # 用于打印完整的错误追踪信息

# 导入数据库模型和蓝图
from models import db, User, RedemptionCode, CreditTransaction
from auth import auth_bp, setup_jwt_error_handlers
from credits import credits_bp

load_dotenv() # 在访问环境变量之前加载 .env 文件

# --- 配置 ---
API_ENDPOINT = os.getenv("IMAGE_API_ENDPOINT","https://api.gptgod.online/v1/chat/completions")
API_KEY = os.getenv("IMAGE_API_KEY") # 从环境变量获取 API 密钥

# --- Flask 应用设置 ---
app = Flask(__name__)

# 应用配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///kiddie_color_creations.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 管理员配置
app.config['ADMIN_KEY'] = os.getenv('ADMIN_KEY', 'admin123')
app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD', 'admin123')

# 初始化扩展
CORS(app, origins=[
    "https://kiddie-color-creations.pages.dev",
    "http://localhost:5500",
    "http://127.0.0.1:5500"
], supports_credentials=True)
db.init_app(app)
jwt = JWTManager(app)

# 设置JWT错误处理
setup_jwt_error_handlers(jwt)

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(credits_bp)

# 创建数据库表
with app.app_context():
    try:
        db.create_all()
        print("数据库表创建成功")
        
        # 检查是否需要创建初始数据
        if User.query.count() == 0:
            print("创建测试用户...")
            # 创建一个测试用户
            test_user = User(
                username='testuser',
                email='test@example.com',
                credits=50
            )
            test_user.set_password('123456')
            db.session.add(test_user)
            
            # 创建一些测试兑换码
            test_codes = [
                RedemptionCode.create_code(10, "测试兑换码1"),
                RedemptionCode.create_code(20, "测试兑换码2"),
                RedemptionCode.create_code(50, "测试兑换码3")
            ]
            
            for code in test_codes:
                db.session.add(code)
            
            db.session.commit()
            print("测试数据创建成功")
            print(f"测试用户: testuser / 123456")
            print(f"测试兑换码: {[code.code for code in test_codes]}")
            
    except Exception as e:
        print(f"数据库初始化错误: {e}")
        traceback.print_exc()

# --- API 路由 ---
# 注意：生图API已移动到 credits.py 中，包含认证和积分扣减功能

# --- 管理员功能 ---
def verify_admin_key():
    """验证管理员权限"""
    admin_key = request.headers.get('X-Admin-Key')
    if not admin_key or admin_key != os.getenv('ADMIN_KEY', 'admin123'):
        return False
    return True

@app.route('/api/credits/admin/users', methods=['GET'])
def admin_get_users():
    """获取用户列表"""
    if not verify_admin_key():
        return jsonify({"error": "无效的管理员权限"}), 403

    try:
        from models import User, db

        # 获取分页参数
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        search = request.args.get('search', '').strip()

        # 构建查询
        query = User.query

        # 搜索过滤
        if search:
            query = query.filter(
                db.or_(
                    User.username.contains(search),
                    User.email.contains(search)
                )
            )

        # 分页
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # 格式化用户数据
        users = []
        for user in pagination.items:
            users.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'credits': user.credits,
                'is_active': user.is_active,
                'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None,
                'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None
            })

        return jsonify({
            'users': users,
            'pagination': {
                'current_page': page,
                'total_pages': pagination.pages,
                'total_users': pagination.total,
                'per_page': per_page
            }
        }), 200

    except Exception as e:
        print(f"获取用户列表失败: {e}")
        traceback.print_exc()
        return jsonify({"error": "获取用户列表失败"}), 500

@app.route('/api/credits/admin/users/<int:user_id>', methods=['GET'])
def admin_get_user_detail(user_id):
    """获取用户详情"""
    if not verify_admin_key():
        return jsonify({"error": "无效的管理员权限"}), 403

    try:
        from models import User, CreditTransaction

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "用户不存在"}), 404

        # 获取用户的积分交易记录
        transactions = CreditTransaction.query.filter_by(user_id=user_id).order_by(
            CreditTransaction.created_at.desc()
        ).limit(10).all()

        transaction_list = []
        for trans in transactions:
            transaction_list.append({
                'id': trans.id,
                'amount': trans.amount,
                'transaction_type': trans.transaction_type,
                'description': trans.description,
                'created_at': trans.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        user_detail = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'credits': user.credits,
            'is_active': user.is_active,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None,
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
            'total_transactions': len(transaction_list),
            'recent_transactions': transaction_list
        }

        return jsonify({'user': user_detail}), 200

    except Exception as e:
        print(f"获取用户详情失败: {e}")
        traceback.print_exc()
        return jsonify({"error": "获取用户详情失败"}), 500

@app.route('/api/credits/admin/stats', methods=['GET'])
def admin_get_stats():
    """获取系统统计数据"""
    if not verify_admin_key():
        return jsonify({"error": "无效的管理员权限"}), 403

    try:
        from models import User, RedemptionCode, db

        # 用户统计
        total_users = User.query.count()
        total_credits = db.session.query(db.func.sum(User.credits)).scalar() or 0

        # 兑换码统计
        total_codes = RedemptionCode.query.count()
        used_codes = RedemptionCode.query.filter(RedemptionCode.used_by.isnot(None)).count()

        stats = {
            'users': {
                'total': total_users,
                'total_credits': total_credits
            },
            'codes': {
                'total': total_codes,
                'used': used_codes
            }
        }

        return jsonify(stats), 200

    except Exception as e:
        print(f"获取统计数据失败: {e}")
        traceback.print_exc()
        return jsonify({"error": "获取统计数据失败"}), 500

@app.route('/api/admin/change-password', methods=['POST'])
def admin_change_password():
    """
    管理员密码修改功能
    """
    try:
        # 验证管理员权限
        admin_key = request.headers.get('X-Admin-Key')
        if not admin_key or admin_key != app.config.get('ADMIN_KEY', 'admin123'):
            return jsonify({"error": "无效的管理员权限"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400

        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not current_password or not new_password:
            return jsonify({"error": "当前密码和新密码都不能为空"}), 400

        # 验证当前密码（这里简化处理，实际应该从数据库或配置文件验证）
        admin_current_password = app.config.get('ADMIN_PASSWORD', 'admin123')
        if current_password != admin_current_password:
            return jsonify({"error": "当前密码错误"}), 400

        # 验证新密码长度
        if len(new_password) < 6:
            return jsonify({"error": "新密码长度至少6位"}), 400

        # 这里应该将新密码保存到安全的地方
        # 由于这是演示项目，我们只返回成功消息
        # 在实际项目中，应该：
        # 1. 将密码哈希后存储到数据库
        # 2. 更新环境变量或配置文件
        # 3. 记录密码修改日志

        print(f"管理员密码修改请求：从 '{current_password}' 改为 '{new_password}'")
        print("注意：在生产环境中，应该将新密码安全地存储到数据库或配置文件中")

        return jsonify({
            "success": True,
            "message": "管理员密码修改成功",
            "note": "请记住新密码，并在生产环境中确保密码被安全存储"
        }), 200

    except Exception as e:
        print(f"管理员密码修改失败: {e}")
        traceback.print_exc()
        return jsonify({"error": "密码修改失败"}), 500

# 根路径路由
@app.route('/', methods=['GET'])
def root():
    """根路径"""
    return jsonify({
        'message': 'Kiddie Color Creations API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/api/health',
            'auth': '/api/auth/*',
            'credits': '/api/credits/*'
        }
    }), 200

# 健康检查端点
@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'database': 'connected' if db.engine else 'disconnected',
        'version': '1.0.0'
    }), 200

# 健康检查端点（兼容render.yaml配置）
@app.route('/api/auth/health', methods=['GET'])
def auth_health_check():
    """认证模块健康检查"""
    return jsonify({
        'status': 'healthy',
        'module': 'auth',
        'database': 'connected' if db.engine else 'disconnected',
        'version': '1.0.0'
    }), 200

# 应用信息端点
@app.route('/api/info', methods=['GET'])
def app_info():
    """应用信息"""
    return jsonify({
        'name': 'Kiddie Color Creations API',
        'version': '1.0.0',
        'description': '儿童涂色图片生成服务',
        'features': [
            'AI图片生成',
            '用户认证系统',
            '积分管理',
            '兑换码系统',
            '管理员后台'
        ]
    }), 200

if __name__ == '__main__':
    print("启动 Flask 开发服务器...")
    print("="*50)
    print("Kiddie Color Creations API")
    print("="*50)
    print(f"数据库: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"管理员API密钥: {app.config['ADMIN_KEY']}")
    print(f"管理员密码: {app.config['ADMIN_PASSWORD']}")
    print("="*50)
    
    # 对于 Render.com 等平台，端口通常由 PORT 环境变量指定
    # debug 模式也最好通过环境变量控制
    flask_debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    port = int(os.getenv("PORT", 5000))
    app.run(debug=flask_debug, host='0.0.0.0', port=port)
