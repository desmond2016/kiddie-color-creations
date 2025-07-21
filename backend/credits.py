# -*- coding: utf-8 -*-
"""
积分管理和核心服务API - 基于GPT-4O Image VIP API
"""
from flask import Blueprint, request, jsonify, current_app
import os
import requests
import traceback
import random
import base64
import re
import urllib.parse
from functools import wraps
import json

from models import db, User
from auth import auth_required

# --- 蓝图和配置 ---
credits_bp = Blueprint('credits', __name__, url_prefix='/credits')
CREDIT_COSTS = {
    'generate_image': 1,
    'generate_colors': 1,
}

# --- 核心服务逻辑 ---
def check_credits_and_consume(user, service_type):
    """检查并消费积分"""
    amount = CREDIT_COSTS.get(service_type, 1)
    if user.credits < amount:
        raise ValueError(f"积分余额不足，需要 {amount} 积分，当前为 {user.credits} 积分")
    
    description = f"使用服务: {service_type}"
    transaction = user.consume_credits(amount, description)
    return transaction, amount

def require_credits(service_type):
    """装饰器：在执行函数前检查并消费积分"""
    def decorator(f):
        @wraps(f)
        @auth_required
        def wrapper(current_user, *args, **kwargs):
            try:
                _, amount = check_credits_and_consume(current_user, service_type)
                
                result = f(current_user, *args, **kwargs) # 执行原始路由函数

                response, status_code = result
                if 200 <= status_code < 300:
                    db.session.commit()
                    current_app.logger.info(f"用户 {current_user.username} 成功消费 {amount} 积分。")
                else:
                    db.session.rollback()
                    current_app.logger.warning(f"服务执行失败，为用户 {current_user.username} 回滚积分。")
                
                return result
            except ValueError as e:
                db.session.rollback()
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"处理积分或服务时出错: {e}")
                traceback.print_exc()
                return jsonify({'error': '服务暂时不可用'}), 500
        return wrapper
    return decorator

# --- API 路由 ---
@credits_bp.route('/generate-image', methods=['POST'])
@require_credits('generate_image')
def generate_image_with_credits(current_user):
    """生成图片API（带认证和积分扣减）"""
    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({"error": "Prompt不能为空"}), 400

    try:
        # 从环境变量中获取 API 配置
        api_endpoint = os.getenv("IMAGE_API_ENDPOINT", "https://api.gptgod.online/v1/chat/completions")
        api_key = os.getenv("IMAGE_API_KEY")

        if not api_key:
            current_app.logger.error("图片生成API密钥未配置。")
            return jsonify({"error": "图片生成服务当前不可用"}), 500

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 基于GPT-4O Image VIP API的格式构建请求
        payload = {
            "stream": True,
            "model": "gpt-4o-image-vip",
            "messages": [
                {
                    "role": "user", 
                    "content": f"画一个简单的儿童涂色线条画：{prompt}。要求：黑白线条，无填充色彩，清晰轮廓，适合儿童涂色，白色背景"
                }
            ]
        }

        # 发起对外部API的请求
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        # 解析流式响应并提取图片URL
        image_url = extract_image_url_from_stream(response.text)
        
        if not image_url:
            current_app.logger.warning("API未返回有效图片URL，使用占位符")
            image_url = f"data:image/svg+xml;base64,{generate_placeholder_svg(prompt)}"

        return jsonify({"imageUrl": image_url, "prompt": prompt}), 200
    
    except requests.exceptions.Timeout:
        current_app.logger.error("API请求超时")
        return jsonify({"error": "图片生成超时，请稍后重试"}), 504
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"请求图片生成API时出错: {e}")
        return jsonify({"error": "图片生成服务暂时无法连接"}), 503
    except Exception as e:
        current_app.logger.error(f"图片生成过程中发生未知错误: {e}")
        traceback.print_exc()
        return jsonify({"error": "图片生成失败"}), 500

def extract_image_url_from_stream(content):
    """从流式响应中提取图片URL"""
    if not content:
        return None
    
    try:
        # 查找图片URL
        url_pattern = r'https?://[^\s<>"\'\[\]{}\\|^`\n\r]+'
        urls = re.findall(url_pattern, content)
        
        if urls:
            # 优先选择图片相关的URL
            for url in urls:
                # URL解码处理
                try:
                    decoded_url = urllib.parse.unquote(url)
                    
                    # 检查是否是图片URL
                    if any(keyword in decoded_url.lower() for keyword in ['.jpg', '.jpeg', '.png', '.gif', '.webp', 'image', 'openai.com', 'videos.openai.com']):
                        return decoded_url
                except Exception:
                    continue
            
            # 如果没有找到明确的图片URL，返回第一个URL
            if urls:
                try:
                    return urllib.parse.unquote(urls[0])
                except Exception:
                    return urls[0]
        
        # 尝试解析JSON数据块
        lines = content.split('\n')
        for line in lines:
            if line.startswith('data: ') and line.strip() != 'data: [DONE]':
                try:
                    json_str = line[6:]  # 移除 'data: ' 前缀
                    chunk_data = json.loads(json_str)
                    if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                        choice = chunk_data['choices'][0]
                        if 'delta' in choice and 'content' in choice['delta']:
                            chunk_content = choice['delta']['content']
                            chunk_urls = re.findall(url_pattern, chunk_content)
                            if chunk_urls:
                                try:
                                    return urllib.parse.unquote(chunk_urls[0])
                                except Exception:
                                    return chunk_urls[0]
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
        
        return None
        
    except Exception as e:
        current_app.logger.error(f"提取图片URL失败: {e}")
        return None

def generate_placeholder_svg(prompt):
    """生成占位符SVG图片"""
    # 确保prompt是安全的字符串
    safe_prompt = prompt[:20] + "..." if len(prompt) > 20 else prompt
    # 转义特殊字符以防止XSS
    safe_prompt = safe_prompt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    svg_content = f'''<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
        <rect width="400" height="400" fill="white" stroke="black" stroke-width="2"/>
        <circle cx="200" cy="120" r="40" fill="none" stroke="black" stroke-width="3"/>
        <rect x="160" y="180" width="80" height="60" fill="none" stroke="black" stroke-width="3"/>
        <text x="200" y="260" text-anchor="middle" font-family="Arial" font-size="14" fill="black">
            线条画: {safe_prompt}
        </text>
        <text x="200" y="280" text-anchor="middle" font-family="Arial" font-size="11" fill="gray">
            （示例图片 - API服务暂时不可用）
        </text>
        <text x="200" y="300" text-anchor="middle" font-family="Arial" font-size="10" fill="gray">
            您已成功提交请求，请联系管理员检查API配置
        </text>
        <text x="200" y="320" text-anchor="middle" font-family="Arial" font-size="10" fill="blue">
            如果多次出现此问题，请刷新页面后重试
        </text>
    </svg>'''
    return base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')

# --- 新的统一生成端点 ---
@credits_bp.route('/generate-creation', methods=['POST'])
@auth_required
def generate_creation(current_user):
    """原子化地生成图片和配色方案，只有成功时才扣除积分"""
    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    
    # 改进的输入验证
    if not prompt:
        return jsonify({"error": "请输入图片描述"}), 400
    
    if len(prompt) > 200:
        return jsonify({"error": "图片描述太长，请限制在200字符以内"}), 400
    
    if len(prompt) < 2:
        return jsonify({"error": "图片描述太短，请至少输入2个字符"}), 400

    # 检查总积分
    total_cost = CREDIT_COSTS.get('generate_image', 1) + CREDIT_COSTS.get('generate_colors', 1)
    if current_user.credits < total_cost:
        return jsonify({
            'error': f"积分余额不足，需要 {total_cost} 积分，当前余额 {current_user.credits} 积分",
            'current_credits': current_user.credits,
            'required_credits': total_cost
        }), 400

    try:
        # --- 1. 图片生成逻辑 ---
        api_endpoint = os.getenv("IMAGE_API_ENDPOINT", "https://api.gptgod.online/v1/chat/completions")
        api_key = os.getenv("IMAGE_API_KEY")
        
        if not api_key:
            current_app.logger.warning("IMAGE_API_KEY 未配置")
            return jsonify({
                'error': '图片生成服务未配置，请联系管理员',
                'current_credits': current_user.credits,
                'required_credits': total_cost
            }), 500
            
        # 设置headers - 使用 IMAGE_API_KEY 进行身份验证
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 基于GPT-4O Image VIP API的格式构建请求
        payload = {
            "stream": True,
            "model": "gpt-4o-image-vip",
            "messages": [
                {
                    "role": "user", 
                    "content": f"画一个简单的儿童涂色线条画：{prompt}。要求：黑白线条，无填充色彩，清晰轮廓，适合儿童涂色，白色背景"
                }
            ]
        }
        
        current_app.logger.info(f"使用payload: {payload}")
        
        try:
            response = requests.post(api_endpoint, headers=headers, json=payload, timeout=30)
            current_app.logger.info(f"API响应状态码: {response.status_code}")
            response.raise_for_status()
            
            # 处理流式响应
            image_url = extract_image_url_from_stream(response.text)
            
            if not image_url:
                current_app.logger.warning("API未返回有效图片URL")
                return jsonify({
                    'error': '图片生成失败，请稍后重试',
                    'current_credits': current_user.credits,
                    'required_credits': total_cost
                }), 500
                
        except requests.exceptions.Timeout:
            current_app.logger.error("API请求超时")
            return jsonify({
                'error': '图片生成超时，请稍后重试',
                'current_credits': current_user.credits,
                'required_credits': total_cost
            }), 504
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"API请求失败: {e}")
            return jsonify({
                'error': '图片生成服务暂时不可用，请稍后重试',
                'current_credits': current_user.credits,
                'required_credits': total_cost
            }), 503

        # --- 2. 配色方案生成逻辑 ---
        color_palettes = [
            ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],
            ["#FF7675", "#74B9FF", "#00B894", "#FDCB6E", "#E17055"],
            ["#A8E6CF", "#FFD3B6", "#FFAAA5", "#FF8B94", "#C7CEEA"],
            ["#F4A261", "#E76F51", "#2A9D8F", "#E9C46A", "#264653"],
            ["#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF"]
        ]
        colors = random.choice(color_palettes)

        # --- 3. 积分扣除 ---
        # 只有在成功获取到真实图片URL时才扣除积分
        if image_url and image_url.startswith('http'):
            # 真实图片生成成功，扣除积分
            description = f"生成创作: {prompt[:50]}"
            current_user.consume_credits(total_cost, description)
            db.session.commit()
            current_app.logger.info(f"用户 {current_user.username} 成功消费 {total_cost} 积分。")
            
            return jsonify({
                "imageUrl": image_url,
                "colors": colors,
                "user": current_user.to_dict()
            }), 200
        else:
            # 没有成功生成图片，不扣除任何积分
            current_app.logger.warning(f"图片生成失败，不扣除积分")
            return jsonify({
                'error': '图片生成失败，未扣除积分。请检查API配置或稍后重试',
                'current_credits': current_user.credits,
                'required_credits': total_cost
            }), 500

    except requests.exceptions.RequestException as e:
        db.session.rollback()
        current_app.logger.error(f"请求外部API时出错: {e}")
        return jsonify({
            "error": "外部服务暂时无法连接",
            'current_credits': current_user.credits,
            'required_credits': total_cost
        }), 503
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创作生成过程中发生错误: {e}")
        traceback.print_exc()
        return jsonify({
            'error': f'服务暂时不可用: {str(e)}',
            'current_credits': current_user.credits,
            'required_credits': total_cost
        }), 500


@credits_bp.route('/generate-colors', methods=['POST'])
@require_credits('generate_colors')
def generate_colors(current_user):
    """生成配色方案API（带认证和积分扣减）"""
    try:
        color_palettes = [
            ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],
            ["#FF7675", "#74B9FF", "#00B894", "#FDCB6E", "#E17055"],
            ["#A8E6CF", "#FFD3B6", "#FFAAA5", "#FF8B94", "#C7CEEA"],
            ["#F4A261", "#E76F51", "#2A9D8F", "#E9C46A", "#264653"],
            ["#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF"]
        ]
        colors = random.choice(color_palettes)
        return jsonify({"colors": colors}), 200
    except Exception as e:
        return jsonify({"error": "配色生成失败"}), 500
