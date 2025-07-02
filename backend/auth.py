# -*- coding: utf-8 -*-
"""
用户认证相关API
参考 little_writers_assistant_payed 项目的JWT认证系统
采用虚拟模式，不影响其他项目
"""
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity, get_jwt
from marshmallow import Schema, fields, ValidationError
import re

from models import db, User, CreditTransaction

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 输入验证Schema
class UserRegistrationSchema(Schema):
    username = fields.Str(required=True, validate=lambda x: len(x) >= 3 and len(x) <= 20)
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=lambda x: len(x) >= 6)

class UserLoginSchema(Schema):
    login = fields.Str(required=True)  # 可以是用户名或邮箱
    password = fields.Str(required=True)

class RedemptionSchema(Schema):
    code = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)

# 工具函数
def validate_username(username):
    """验证用户名格式"""
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return False, "用户名只能包含字母、数字和下划线，长度3-20位"
    return True, ""

def validate_password(password):
    """验证密码强度"""
    if len(password) < 6:
        return False, "密码长度至少6位"
    return True, ""

# 认证装饰器
def auth_required(f):
    """需要登录的装饰器"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            current_user_id = int(get_jwt_identity())  # 转换为整数
            current_user = User.query.get(current_user_id)
            if not current_user or not current_user.is_active:
                return jsonify({'error': '用户不存在或已被禁用'}), 401
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': '认证失败'}), 401
    return decorated_function

# 路由定义
@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        # 验证输入数据
        schema = UserRegistrationSchema()
        data = schema.load(request.get_json())
        
        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        
        # 额外验证
        is_valid, msg = validate_username(username)
        if not is_valid:
            return jsonify({'error': msg}), 400
        
        is_valid, msg = validate_password(password)
        if not is_valid:
            return jsonify({'error': msg}), 400
        
        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({'error': '用户名已存在'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': '邮箱已被注册'}), 400
        
        # 创建新用户
        user = User(
            username=username,
            email=email,
            credits=10  # 新用户赠送10积分
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # 记录赠送积分
        if user.credits > 0:
            transaction = CreditTransaction(
                user_id=user.id,
                transaction_type='recharge',
                credits_amount=user.credits,
                description='新用户注册赠送'
            )
            db.session.add(transaction)
            db.session.commit()
        
        # 生成访问令牌
        access_token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(days=7)
        )
        
        return jsonify({
            'message': '注册成功',
            'access_token': access_token,
            'user': user.to_dict()
        }), 201
        
    except ValidationError as e:
        return jsonify({'error': '输入数据格式错误', 'details': e.messages}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"注册错误: {str(e)}")
        return jsonify({'error': '注册失败，请稍后重试'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        # 验证输入数据
        schema = UserLoginSchema()
        data = schema.load(request.get_json())
        
        login_input = data['login'].strip()
        password = data['password']
        
        # 查找用户（支持用户名或邮箱登录）
        user = None
        if '@' in login_input:
            # 邮箱登录
            user = User.query.filter_by(email=login_input.lower()).first()
        else:
            # 用户名登录
            user = User.query.filter_by(username=login_input).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': '用户名/邮箱或密码错误'}), 401
        
        if not user.is_active:
            return jsonify({'error': '账户已被禁用'}), 401
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # 生成访问令牌
        access_token = create_access_token(
            identity=str(user.id),
            expires_delta=timedelta(days=7)
        )
        
        return jsonify({
            'message': '登录成功',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
        
    except ValidationError as e:
        return jsonify({'error': '输入数据格式错误', 'details': e.messages}), 400
    except Exception as e:
        current_app.logger.error(f"登录错误: {str(e)}")
        return jsonify({'error': '登录失败，请稍后重试'}), 500

@auth_bp.route('/profile', methods=['GET'])
@auth_required
def get_profile(current_user):
    """获取用户信息"""
    try:
        return jsonify({
            'user': current_user.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取用户信息错误: {str(e)}")
        return jsonify({'error': '获取用户信息失败'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@auth_required
def change_password(current_user):
    """用户修改密码"""
    try:
        data = request.get_json()
        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()

        # 验证输入
        if not current_password:
            return jsonify({'error': '请输入当前密码'}), 400

        if not new_password:
            return jsonify({'error': '请输入新密码'}), 400

        if len(new_password) < 6:
            return jsonify({'error': '新密码长度至少6位'}), 400

        if new_password != confirm_password:
            return jsonify({'error': '两次输入的新密码不一致'}), 400

        # 验证当前密码
        if not current_user.check_password(current_password):
            return jsonify({'error': '当前密码错误'}), 400

        # 检查新密码是否与当前密码相同
        if current_user.check_password(new_password):
            return jsonify({'error': '新密码不能与当前密码相同'}), 400

        # 设置新密码
        current_user.set_password(new_password)

        # 记录操作日志
        current_app.logger.info(f"用户 {current_user.username} 修改了密码")

        db.session.commit()

        return jsonify({
            'message': '密码修改成功',
            'user': current_user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"修改密码错误: {str(e)}")
        return jsonify({'error': '修改密码失败'}), 500

@auth_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({'status': 'healthy', 'service': 'kiddie-color-creations'}), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """用户登出（JWT无状态，主要用于前端清理）"""
    try:
        # JWT是无状态的，这里主要是为了API一致性
        # 实际的登出逻辑在前端处理（删除token）
        return jsonify({'message': '登出成功'}), 200
    except Exception as e:
        current_app.logger.error(f"登出错误: {str(e)}")
        return jsonify({'error': '登出失败'}), 500

@auth_bp.route('/redeem', methods=['POST'])
@auth_required
def redeem_code(current_user):
    """兑换积分码"""
    try:
        # 验证输入数据
        schema = RedemptionSchema()
        data = schema.load(request.get_json())
        
        code = data['code'].strip().upper()  # 转换为大写
        
        # 查找兑换码
        from models import RedemptionCode
        redemption_code = RedemptionCode.query.filter_by(code=code).first()
        
        if not redemption_code:
            return jsonify({'error': '兑换码不存在'}), 404
        
        # 验证兑换码有效性
        is_valid, message = redemption_code.is_valid()
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # 执行兑换
        transaction = redemption_code.redeem(current_user)
        db.session.commit()
        
        return jsonify({
            'message': f'兑换成功！获得 {redemption_code.credits_value} 积分',
            'credits_added': redemption_code.credits_value,
            'current_credits': current_user.credits,
            'transaction': transaction.to_dict()
        }), 200
        
    except ValidationError as e:
        return jsonify({'error': '输入数据格式错误', 'details': e.messages}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"兑换码错误: {str(e)}")
        return jsonify({'error': '兑换失败，请稍后重试'}), 500

@auth_bp.route('/transactions', methods=['GET'])
@auth_required
def get_transactions(current_user):
    """获取用户积分交易记录"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        transactions = CreditTransaction.query.filter_by(user_id=current_user.id)\
            .order_by(CreditTransaction.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'transactions': [t.to_dict() for t in transactions.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': transactions.total,
                'pages': transactions.pages,
                'has_next': transactions.has_next,
                'has_prev': transactions.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取交易记录错误: {str(e)}")
        return jsonify({'error': '获取交易记录失败'}), 500

# JWT错误处理
def setup_jwt_error_handlers(jwt):
    """设置JWT错误处理器"""
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': '登录已过期，请重新登录'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': '无效的登录令牌'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': '需要登录才能访问'}), 401
