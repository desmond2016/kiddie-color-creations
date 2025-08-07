#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supabase客户端配置模块
用于通过REST API操作数据库，绕过IPv6连接问题
"""

import os
from supabase import create_client, Client
from typing import Optional, Dict, Any, List
import logging
from dotenv import load_dotenv

# 确保加载环境变量
load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)

class SupabaseManager:
    """Supabase客户端管理器"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化Supabase客户端"""
        try:
            # 从环境变量获取配置
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
            
            if not supabase_url or not supabase_key:
                logger.error("缺少Supabase配置：SUPABASE_URL或SUPABASE_SERVICE_KEY")
                return
            
            # 创建客户端
            self.client = create_client(supabase_url, supabase_key)
            logger.info("Supabase客户端初始化成功")
            
        except Exception as e:
            logger.error(f"Supabase客户端初始化失败: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.client is not None
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self.client:
                return False
            
            # 尝试查询一个简单的表
            result = self.client.table('users').select('id').limit(1).execute()
            return True
            
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    # 用户相关操作
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        try:
            result = self.client.table('users').select('*').eq('username', username).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """根据邮箱获取用户"""
        try:
            result = self.client.table('users').select('*').eq('email', email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            return None
    
    def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建用户"""
        try:
            result = self.client.table('users').insert(user_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            return None
    
    def update_user(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """更新用户"""
        try:
            result = self.client.table('users').update(user_data).eq('id', user_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"更新用户失败: {e}")
            return False
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """获取所有用户"""
        try:
            result = self.client.table('users').select('*').execute()
            return result.data
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return []
    
    # 设置相关操作
    def get_setting(self, key: str) -> Optional[str]:
        """获取设置值"""
        try:
            result = self.client.table('settings').select('value').eq('key', key).execute()
            return result.data[0]['value'] if result.data else None
        except Exception as e:
            logger.error(f"获取设置失败: {e}")
            return None
    
    def set_setting(self, key: str, value: str) -> bool:
        """设置值"""
        try:
            # 先尝试更新
            result = self.client.table('settings').update({'value': value}).eq('key', key).execute()
            
            # 如果没有更新任何行，则插入新记录
            if not result.data:
                result = self.client.table('settings').insert({'key': key, 'value': value}).execute()
            
            return True
        except Exception as e:
            logger.error(f"设置值失败: {e}")
            return False
    
    # 兑换码相关操作
    def get_redemption_code(self, code: str) -> Optional[Dict[str, Any]]:
        """获取兑换码"""
        try:
            result = self.client.table('redemption_codes').select('*').eq('code', code).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"获取兑换码失败: {e}")
            return None
    
    def create_redemption_code(self, code_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建兑换码"""
        try:
            result = self.client.table('redemption_codes').insert(code_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"创建兑换码失败: {e}")
            return None
    
    def update_redemption_code(self, code: str, code_data: Dict[str, Any]) -> bool:
        """更新兑换码"""
        try:
            result = self.client.table('redemption_codes').update(code_data).eq('code', code).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"更新兑换码失败: {e}")
            return False
    
    def get_all_redemption_codes(self) -> List[Dict[str, Any]]:
        """获取所有兑换码"""
        try:
            result = self.client.table('redemption_codes').select('*').execute()
            return result.data
        except Exception as e:
            logger.error(f"获取兑换码列表失败: {e}")
            return []

# 全局实例
supabase_manager = SupabaseManager()

def get_supabase_manager() -> SupabaseManager:
    """获取Supabase管理器实例"""
    return supabase_manager
