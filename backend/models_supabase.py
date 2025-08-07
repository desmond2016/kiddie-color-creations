#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supabase REST API模型扩展
为现有模型添加Supabase REST API操作方法
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import bcrypt
import uuid
from supabase_client import get_supabase_manager

class UserSupabase:
    """用户模型的Supabase扩展"""
    
    @staticmethod
    def get_by_username(username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        manager = get_supabase_manager()
        return manager.get_user_by_username(username)
    
    @staticmethod
    def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        """根据邮箱获取用户"""
        manager = get_supabase_manager()
        return manager.get_user_by_email(email)
    
    @staticmethod
    def create(username: str, email: str, password: str, credits: int = 10) -> Optional[Dict[str, Any]]:
        """创建新用户"""
        # 加密密码
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        user_data = {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'credits': credits,
            'is_active': True,
            'created_at': datetime.now().isoformat()
        }
        
        manager = get_supabase_manager()
        return manager.create_user(user_data)
    
    @staticmethod
    def check_password(user_data: Dict[str, Any], password: str) -> bool:
        """验证密码"""
        if not user_data or 'password_hash' not in user_data:
            return False
        
        password_bytes = password.encode('utf-8')
        hash_bytes = user_data['password_hash'].encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    
    @staticmethod
    def update_last_login(user_id: int) -> bool:
        """更新最后登录时间"""
        manager = get_supabase_manager()
        return manager.update_user(user_id, {
            'last_login': datetime.now().isoformat()
        })
    
    @staticmethod
    def add_credits(user_id: int, amount: int, description: str = "积分充值") -> bool:
        """增加积分"""
        if amount <= 0:
            return False
        
        manager = get_supabase_manager()
        
        # 获取当前用户
        users = manager.client.table('users').select('credits').eq('id', user_id).execute()
        if not users.data:
            return False
        
        current_credits = users.data[0]['credits']
        new_credits = current_credits + amount
        
        # 更新积分
        success = manager.update_user(user_id, {'credits': new_credits})
        
        if success:
            # 记录交易
            CreditTransactionSupabase.create(
                user_id=user_id,
                transaction_type='recharge',
                credits_amount=amount,
                description=description
            )
        
        return success
    
    @staticmethod
    def consume_credits(user_id: int, amount: int, description: str = "使用服务") -> bool:
        """消费积分"""
        if amount <= 0:
            return False
        
        manager = get_supabase_manager()
        
        # 获取当前用户
        users = manager.client.table('users').select('credits').eq('id', user_id).execute()
        if not users.data:
            return False
        
        current_credits = users.data[0]['credits']
        if current_credits < amount:
            return False  # 积分不足
        
        new_credits = current_credits - amount
        
        # 更新积分
        success = manager.update_user(user_id, {'credits': new_credits})
        
        if success:
            # 记录交易
            CreditTransactionSupabase.create(
                user_id=user_id,
                transaction_type='consume',
                credits_amount=-amount,
                description=description
            )
        
        return success
    
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """获取所有用户"""
        manager = get_supabase_manager()
        return manager.get_all_users()

class SettingSupabase:
    """设置模型的Supabase扩展"""
    
    @staticmethod
    def get(key: str) -> Optional[str]:
        """获取设置值"""
        manager = get_supabase_manager()
        return manager.get_setting(key)
    
    @staticmethod
    def set(key: str, value: str) -> bool:
        """设置值"""
        manager = get_supabase_manager()
        return manager.set_setting(key, value)
    
    @staticmethod
    def set_password(password_key: str, password: str) -> bool:
        """设置密码（加密存储）"""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        manager = get_supabase_manager()
        return manager.set_setting(password_key, hashed_password)
    
    @staticmethod
    def check_password(password_key: str, password: str) -> bool:
        """验证密码"""
        manager = get_supabase_manager()
        hashed_password = manager.get_setting(password_key)
        
        if not hashed_password:
            return False
        
        password_bytes = password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)

class RedemptionCodeSupabase:
    """兑换码模型的Supabase扩展"""
    
    @staticmethod
    def generate_code(length: int = 16) -> str:
        """生成随机兑换码"""
        unique_id = str(uuid.uuid4()).replace('-', '').upper()[:length]
        # 排除容易混淆的字符
        unique_id = unique_id.replace('0', 'G').replace('O', 'H').replace('1', 'J').replace('I', 'K')
        return unique_id
    
    @staticmethod
    def create(credits_value: int, description: str = None, expires_days: int = None) -> Optional[Dict[str, Any]]:
        """创建新的兑换码"""
        manager = get_supabase_manager()
        
        # 生成唯一兑换码
        code = RedemptionCodeSupabase.generate_code()
        while manager.get_redemption_code(code):
            code = RedemptionCodeSupabase.generate_code()
        
        expires_at = None
        if expires_days:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        code_data = {
            'code': code,
            'credits_value': credits_value,
            'description': description,
            'expires_at': expires_at,
            'is_used': False,
            'created_at': datetime.now().isoformat()
        }
        
        return manager.create_redemption_code(code_data)
    
    @staticmethod
    def get_by_code(code: str) -> Optional[Dict[str, Any]]:
        """根据兑换码获取信息"""
        manager = get_supabase_manager()
        return manager.get_redemption_code(code)
    
    @staticmethod
    def is_valid(code_data: Dict[str, Any]) -> tuple[bool, str]:
        """检查兑换码是否有效"""
        if code_data.get('is_used'):
            return False, "兑换码已被使用"
        
        expires_at = code_data.get('expires_at')
        if expires_at:
            expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if datetime.now() > expires_datetime:
                return False, "兑换码已过期"
        
        return True, "兑换码有效"
    
    @staticmethod
    def redeem(code: str, user_id: int) -> tuple[bool, str]:
        """兑换积分"""
        manager = get_supabase_manager()
        
        # 获取兑换码
        code_data = manager.get_redemption_code(code)
        if not code_data:
            return False, "兑换码不存在"
        
        # 检查有效性
        is_valid, message = RedemptionCodeSupabase.is_valid(code_data)
        if not is_valid:
            return False, message
        
        # 标记为已使用
        update_data = {
            'is_used': True,
            'used_by_user_id': user_id,
            'used_at': datetime.now().isoformat()
        }
        
        success = manager.update_redemption_code(code, update_data)
        if not success:
            return False, "兑换失败"
        
        # 给用户增加积分
        description = f"兑换码充值: {code}"
        if code_data.get('description'):
            description += f" ({code_data['description']})"
        
        credits_added = UserSupabase.add_credits(
            user_id, 
            code_data['credits_value'], 
            description
        )
        
        if credits_added:
            return True, f"成功兑换{code_data['credits_value']}积分"
        else:
            return False, "积分充值失败"
    
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """获取所有兑换码"""
        manager = get_supabase_manager()
        return manager.get_all_redemption_codes()

class CreditTransactionSupabase:
    """积分交易记录的Supabase扩展"""
    
    @staticmethod
    def create(user_id: int, transaction_type: str, credits_amount: int, description: str) -> Optional[Dict[str, Any]]:
        """创建交易记录"""
        manager = get_supabase_manager()
        
        transaction_data = {
            'user_id': user_id,
            'transaction_type': transaction_type,
            'credits_amount': credits_amount,
            'description': description,
            'created_at': datetime.now().isoformat()
        }
        
        try:
            result = manager.client.table('credit_transactions').insert(transaction_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"创建交易记录失败: {e}")
            return None
    
    @staticmethod
    def get_by_user(user_id: int) -> List[Dict[str, Any]]:
        """获取用户的交易记录"""
        manager = get_supabase_manager()
        
        try:
            result = manager.client.table('credit_transactions').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
            return result.data
        except Exception as e:
            print(f"获取交易记录失败: {e}")
            return []
