# -*- coding: utf-8 -*-
"""
数据库模型定义
参考 little_writers_assistant_payed 项目的用户积分系统设计
采用虚拟模式，不影响其他项目
"""
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import secrets
import string
import uuid

db = SQLAlchemy()

class User(db.Model):
    """用户表"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    credits = db.Column(db.Integer, default=0, nullable=False)  # 积分余额
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    last_login = db.Column(db.DateTime)
    
    # 关联关系
    credit_transactions = db.relationship('CreditTransaction', backref='user', lazy=True)
    used_codes = db.relationship('RedemptionCode', backref='used_by_user', lazy=True)
    
    def set_password(self, password):
        """设置密码（加密存储）"""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    def check_password(self, password):
        """验证密码"""
        password_bytes = password.encode('utf-8')
        hash_bytes = self.password_hash.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    
    def add_credits(self, amount, description="积分充值"):
        """增加积分"""
        if amount <= 0:
            raise ValueError("积分数量必须大于0")
        
        self.credits += amount
        
        # 记录交易
        transaction = CreditTransaction(
            user_id=self.id,
            transaction_type='recharge',
            credits_amount=amount,
            description=description
        )
        db.session.add(transaction)
        return transaction
    
    def consume_credits(self, amount, description="使用服务"):
        """消费积分"""
        if amount <= 0:
            raise ValueError("积分数量必须大于0")
        
        if self.credits < amount:
            raise ValueError("积分余额不足")
        
        self.credits -= amount
        
        # 记录交易
        transaction = CreditTransaction(
            user_id=self.id,
            transaction_type='consume',
            credits_amount=-amount,
            description=description
        )
        db.session.add(transaction)
        return transaction
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'credits': self.credits,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class RedemptionCode(db.Model):
    """兑换码表"""
    __tablename__ = 'redemption_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    credits_value = db.Column(db.Integer, nullable=False)  # 兑换码价值的积分数
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    used_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)  # 过期时间，可为空表示永不过期
    description = db.Column(db.String(200), nullable=True)  # 兑换码描述
    
    @staticmethod
    def generate_code(length=16):
        """生成随机兑换码（16位UUID风格）"""
        # 使用UUID确保唯一性，然后转换为16位大写字母数字组合
        unique_id = str(uuid.uuid4()).replace('-', '').upper()[:length]
        # 排除容易混淆的字符
        unique_id = unique_id.replace('0', 'G').replace('O', 'H').replace('1', 'J').replace('I', 'K')
        return unique_id
    
    @classmethod
    def create_code(cls, credits_value, description=None, expires_days=None):
        """创建新的兑换码"""
        code = cls.generate_code()
        
        # 确保兑换码唯一
        while cls.query.filter_by(code=code).first():
            code = cls.generate_code()
        
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        redemption_code = cls(
            code=code,
            credits_value=credits_value,
            description=description,
            expires_at=expires_at
        )
        
        return redemption_code
    
    def is_valid(self):
        """检查兑换码是否有效"""
        if self.is_used:
            return False, "兑换码已被使用"
        
        if self.expires_at and datetime.now() > self.expires_at:
            return False, "兑换码已过期"
        
        return True, "兑换码有效"
    
    def redeem(self, user):
        """兑换积分"""
        is_valid, message = self.is_valid()
        if not is_valid:
            raise ValueError(message)
        
        # 标记为已使用
        self.is_used = True
        self.used_by_user_id = user.id
        self.used_at = datetime.now()
        
        # 给用户增加积分
        description = f"兑换码充值: {self.code}"
        if self.description:
            description += f" ({self.description})"
        
        transaction = user.add_credits(self.credits_value, description)
        
        return transaction
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'code': self.code,
            'credits_value': self.credits_value,
            'is_used': self.is_used,
            'used_by_user_id': self.used_by_user_id,
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'description': self.description
        }

class CreditTransaction(db.Model):
    """积分交易记录表"""
    __tablename__ = 'credit_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'recharge' 或 'consume'
    credits_amount = db.Column(db.Integer, nullable=False)  # 正数为充值，负数为消费
    description = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'transaction_type': self.transaction_type,
            'credits_amount': self.credits_amount,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class UserSession(db.Model):
    """用户会话表（可选，如果使用JWT可以不需要）"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    
    user = db.relationship('User', backref='sessions')
    
    @classmethod
    def create_session(cls, user, expires_hours=24):
        """创建新会话"""
        session_token = secrets.token_urlsafe(64)
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        session = cls(
            user_id=user.id,
            session_token=session_token,
            expires_at=expires_at
        )
        
        return session
    
    def is_valid(self):
        """检查会话是否有效"""
        return datetime.now() < self.expires_at
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_token': self.session_token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
