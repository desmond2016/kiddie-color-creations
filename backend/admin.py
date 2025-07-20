# -*- coding: utf-8 -*-
"""
管理员功能相关API
"""
from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import traceback
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from models import db, User, RedemptionCode, CreditTransaction, Setting

# 创建管理员蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# --- 认证和装饰器 ---
def admin_jwt_required(f):
    """验证管理员JWT的装饰器"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        # 检查JWT身份是否为管理员
        identity = get_jwt_identity()
        if identity != 'admin':
            return jsonify({"error": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- 认证和密码管理 ---
@admin_bp.route('/login', methods=['POST'])
def admin_login():
    """管理员登录"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "无效的请求数据"}), 400
            
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "用户名和密码都不能为空"}), 400

        # 检查管理员用户名
        admin_username = current_app.config.get('ADMIN_USERNAME', 'admin')
        if username != admin_username:
            return jsonify({"error": "用户名或密码错误"}), 401
            
        # 检查密码（需要确保数据库中有admin_password设置）
        try:
            password_valid = Setting.check_password('admin_password', password)
        except Exception as e:
            current_app.logger.error(f"检查管理员密码时出错: {e}")
            # 如果没有设置密码，使用配置中的默认密码
            default_password = current_app.config.get('ADMIN_PASSWORD', 'admin123')
            if password == default_password:
                # 初始化密码到数据库
                Setting.set_password('admin_password', password)
                password_valid = True
            else:
                password_valid = False
                
        if not password_valid:
            return jsonify({"error": "用户名或密码错误"}), 401

        # 创建管理员专用的JWT
        expires = current_app.config['ADMIN_ACCESS_TOKEN_EXPIRES']
        access_token = create_access_token(identity='admin', expires_delta=expires)
        
        return jsonify({
            "success": True,
            "message": "管理员登录成功",
            "access_token": access_token
        }), 200
    except Exception as e:
        current_app.logger.error(f"管理员登录失败: {e}")
        traceback.print_exc()
        return jsonify({"error": f"登录失败: {str(e)}"}), 500

@admin_bp.route('/change-password', methods=['POST'])
@admin_jwt_required
def admin_change_password():
    """管理员密码修改功能"""
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not current_password or not new_password:
            return jsonify({"error": "当前密码和新密码都不能为空"}), 400
        if not Setting.check_password('admin_password', current_password):
            return jsonify({"error": "当前密码错误"}), 400
        if len(new_password) < 6:
            return jsonify({"error": "新密码长度至少6位"}), 400

        Setting.set_password('admin_password', new_password)
        current_app.logger.info("管理员密码已成功修改")
        return jsonify({"success": True, "message": "管理员密码修改成功"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"管理员密码修改失败: {e}")
        return jsonify({"error": "密码修改失败"}), 500

# --- 用户管理 ---
@admin_bp.route('/users', methods=['GET'])
@admin_jwt_required
def get_users():
    """获取用户列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '').strip()

        query = User.query
        if search:
            query = query.filter(db.or_(User.username.ilike(f'%{search}%'), User.email.ilike(f'%{search}%')))

        pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        users_data = []
        for user in pagination.items:
            user_dict = user.to_dict()
            user_dict['is_active_text'] = '活跃' if user.is_active else '禁用'
            users_data.append(user_dict)

        return jsonify({
            'users': users_data,
            'pagination': {
                'page': pagination.page, 'per_page': pagination.per_page,
                'total': pagination.total, 'pages': pagination.pages,
                'has_next': pagination.has_next, 'has_prev': pagination.has_prev
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取用户列表失败: {e}")
        return jsonify({"error": "获取用户列表失败"}), 500

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_jwt_required
def get_user_detail(user_id):
    """获取用户详细信息"""
    try:
        user = User.query.get_or_404(user_id)
        transactions = CreditTransaction.query.filter_by(user_id=user_id).order_by(CreditTransaction.created_at.desc()).limit(50).all()
        used_codes = RedemptionCode.query.filter_by(used_by_user_id=user_id).order_by(RedemptionCode.used_at.desc()).all()

        user_data = user.to_dict()
        user_data.update({
            'transactions': [t.to_dict() for t in transactions],
            'used_codes': [code.to_dict() for code in used_codes],
            'is_active_text': '活跃' if user.is_active else '禁用'
        })
        return jsonify({'user': user_data}), 200
    except Exception as e:
        current_app.logger.error(f"获取用户详情失败: {e}")
        return jsonify({"error": "获取用户详情失败"}), 500

@admin_bp.route('/users/<int:user_id>/credits', methods=['POST'])
@admin_jwt_required
def adjust_user_credits(user_id):
    """调整用户积分"""
    try:
        data = request.get_json()
        amount = data.get('amount', 0)
        description = data.get('description', '管理员调整')

        if amount == 0: return jsonify({'error': '调整数量不能为0'}), 400
        
        user = User.query.get_or_404(user_id)
        if amount > 0:
            transaction = user.add_credits(amount, f"管理员���加: {description}")
        else:
            if user.credits < abs(amount): return jsonify({'error': '用户积分不足，无法扣减'}), 400
            transaction = user.consume_credits(abs(amount), f"管理员扣减: {description}")
        
        db.session.commit()
        return jsonify({'message': '积分调整成功', 'user': user.to_dict(), 'transaction': transaction.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"调整用户积分失败: {e}")
        return jsonify({'error': '调整积分失败'}), 500

@admin_bp.route('/users/<int:user_id>/status', methods=['PUT'])
@admin_jwt_required
def toggle_user_status(user_id):
    """切换用户状态（启用/禁用）"""
    try:
        user = User.query.get_or_404(user_id)
        user.is_active = not user.is_active
        db.session.commit()
        status_text = '启用' if user.is_active else '禁用'
        return jsonify({'message': f'用户已{status_text}', 'user': user.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"切换用户状态失败: {e}")
        return jsonify({'error': '操作失败'}), 500

@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_jwt_required
def reset_user_password(user_id):
    """重置用户密码"""
    try:
        data = request.get_json()
        new_password = data.get('new_password', '').strip()
        if not new_password or len(new_password) < 6:
            return jsonify({'error': '新密码不能为空且长度至少6位'}), 400
        
        user = User.query.get_or_404(user_id)
        user.set_password(new_password)
        db.session.commit()
        current_app.logger.info(f"管理员重置了用户 {user.username} 的密码")
        return jsonify({'message': f'用户 {user.username} 的密码已重置', 'new_password': new_password}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"重置用户密码失败: {e}")
        return jsonify({'error': '重置密码失败'}), 500

# --- 兑换码管理 ---
@admin_bp.route('/codes/generate', methods=['POST'])
@admin_jwt_required
def generate_redemption_code():
    """生成��换码"""
    try:
        data = request.get_json()
        credits_value = data.get('credits_value')
        if not credits_value or credits_value <= 0:
            return jsonify({'error': '积分数值必须为正数'}), 400

        redemption_code = RedemptionCode.create_code(
            credits_value=credits_value,
            description=data.get('description'),
            expires_days=data.get('expires_days')
        )
        db.session.add(redemption_code)
        db.session.commit()
        return jsonify({'message': '兑换码生成成功', 'redemption_code': redemption_code.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"生成兑换码失败: {e}")
        return jsonify({'error': '生成兑换码失败'}), 500

@admin_bp.route('/codes', methods=['GET'])
@admin_jwt_required
def list_redemption_codes():
    """获取兑换码列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = RedemptionCode.query.order_by(RedemptionCode.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'codes': [code.to_dict() for code in pagination.items],
            'pagination': {
                'page': pagination.page, 'per_page': pagination.per_page,
                'total': pagination.total, 'pages': pagination.pages
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取兑换码列表失败: {e}")
        return jsonify({'error': '获取兑换码列表失败'}), 500

# --- 统计数据 ---
@admin_bp.route('/stats', methods=['GET'])
@admin_jwt_required
def get_stats():
    """获取系统统计数据"""
    try:
        total_users = User.query.count()
        total_credits = db.session.query(db.func.sum(User.credits)).scalar() or 0
        total_codes = RedemptionCode.query.count()
        used_codes = RedemptionCode.query.filter(RedemptionCode.is_used == True).count()

        return jsonify({
            'users': {'total': total_users, 'total_credits': total_credits},
            'codes': {'total': total_codes, 'used': used_codes}
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取统计数据失败: {e}")
        return jsonify({"error": "获取统计数据失败"}), 500
