# -*- coding: utf-8 -*-
"""
积分管理和核心服务API
"""
from flask import Blueprint, request, jsonify, current_app
import os
import requests
import traceback
import random
from functools import wraps

from models import db, User
from auth import auth_required

# --- 蓝图和配置 ---
credits_bp = Blueprint('credits', __name__, url_prefix='/api/credits')
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
        api_endpoint = os.getenv("IMAGE_API_ENDPOINT")
        api_key = os.getenv("IMAGE_API_KEY")

        if not api_endpoint or not api_key:
            current_app.logger.error("图片生成API的端点或密钥未配置。")
            return jsonify({"error": "图片生成服务当前不可用"}), 500

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # 构建符合外部API要求的请求体 - 改进提示词用于线条画生成
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user", 
                    "content": f"Generate a simple black and white line drawing for children to color, featuring: {prompt}. The image should have clean, thick outlines, no shading or details inside, suitable for kids coloring book, white background."
                }
            ],
            "max_tokens": 1000,
        }

        # 发起对外部API的请求
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        # 解析响应并提取图片URL
        api_response = response.json()
        
        # 根据实际API响应格式调整解析逻辑
        image_url = None
        if 'choices' in api_response and len(api_response['choices']) > 0:
            choice = api_response['choices'][0]
            if 'message' in choice and 'content' in choice['message']:
                content = choice['message']['content']
                # 如果content包含图片URL，提取它
                if content.startswith('http'):
                    image_url = content.strip()
                else:
                    # 如果API返回的是描述而不是图片URL，则使用占位符
                    image_url = f"data:image/svg+xml;base64,{generate_placeholder_svg(prompt)}"
        
        if not image_url:
            current_app.logger.error(f"API响应中未找到图片URL: {api_response}")
            # 返回占位符图片
            image_url = f"data:image/svg+xml;base64,{generate_placeholder_svg(prompt)}"

        return jsonify({"imageUrl": image_url, "prompt": prompt}), 200
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"请求图片生成API时出错: {e}")
        return jsonify({"error": "图片生成服务暂时无法连接"}), 503
    except Exception as e:
        current_app.logger.error(f"图片生成过程中发生未知错误: {e}")
        traceback.print_exc()
        return jsonify({"error": "图片生成失败"}), 500

def generate_placeholder_svg(prompt):
    """生成占位符SVG图片的base64编码"""
    import base64
    # 安全地处理提示词，避免XSS
    safe_prompt = prompt.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')[:30]
    svg_content = f'''<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
        <rect width="400" height="400" fill="white" stroke="black" stroke-width="2"/>
        <circle cx="200" cy="150" r="50" fill="none" stroke="black" stroke-width="3"/>
        <text x="200" y="250" text-anchor="middle" font-family="Arial" font-size="16" fill="black">
            涂色画: {safe_prompt}
        </text>
        <text x="200" y="280" text-anchor="middle" font-family="Arial" font-size="12" fill="gray">
            (示例图片 - 请配置API密钥获取真实图片)
        </text>
        <text x="200" y="320" text-anchor="middle" font-family="Arial" font-size="10" fill="gray">
            这是一个占位符，请联系管理员配置图片生成服务
        </text>
    </svg>'''
    return base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')


# --- 新的统一生成端点 ---
@credits_bp.route('/generate-creation', methods=['POST'])
@auth_required
def generate_creation(current_user):
    """原子化地生成图片和配色方案，并扣除积分"""
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
        api_endpoint = os.getenv("IMAGE_API_ENDPOINT")
        api_key = os.getenv("IMAGE_API_KEY")
        
        if not api_endpoint:
            current_app.logger.warning("IMAGE_API_ENDPOINT 未配置，使用占位符图片")
            image_url = f"data:image/svg+xml;base64,{generate_placeholder_svg(prompt)}"
        elif not api_key:
            current_app.logger.warning("IMAGE_API_KEY 未配置，使用占位符图片")
            image_url = f"data:image/svg+xml;base64,{generate_placeholder_svg(prompt)}"
        else:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user", 
                        "content": f"Generate a simple black and white line drawing for children to color, featuring: {prompt}. The image should have clean, thick outlines, no shading or details inside, suitable for kids coloring book, white background."
                    }
                ],
                "max_tokens": 1000,
            }
            
            try:
                response = requests.post(api_endpoint, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                api_response = response.json()
                
                # 解析图片URL
                image_url = None
                if 'choices' in api_response and len(api_response['choices']) > 0:
                    choice = api_response['choices'][0]
                    if 'message' in choice and 'content' in choice['message']:
                        content = choice['message']['content']
                        if content.startswith('http'):
                            image_url = content.strip()
                
                if not image_url:
                    current_app.logger.warning("API未返回图片URL，使用占位符")
                    image_url = f"data:image/svg+xml;base64,{generate_placeholder_svg(prompt)}"
                    
            except requests.exceptions.Timeout:
                current_app.logger.error("API请求超时，使用占位符图片")
                image_url = f"data:image/svg+xml;base64,{generate_placeholder_svg(prompt)}"
            except requests.exceptions.RequestException as e:
                current_app.logger.error(f"API请求失败: {e}，使用占位符图片")
                image_url = f"data:image/svg+xml;base64,{generate_placeholder_svg(prompt)}"

        # --- 2. 配色方案生成逻辑 ---
        color_palettes = [
            ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],
            ["#FF7675", "#74B9FF", "#00B894", "#FDCB6E", "#E17055"],
        ]
        colors = random.choice(color_palettes)

        # --- 3. 积分扣除 ---
        description = f"生成创作: {prompt[:50]}"
        current_user.consume_credits(total_cost, description)
        db.session.commit()
        current_app.logger.info(f"用户 {current_user.username} 成功消费 {total_cost} 积分。")

        return jsonify({
            "imageUrl": image_url,
            "colors": colors,
            "user": current_user.to_dict() # 返回更新后的用户信息
        }), 200

    except requests.exceptions.RequestException as e:
        db.session.rollback()
        current_app.logger.error(f"请求外部API时出错: {e}")
        return jsonify({"error": "外部服务暂时无法连接"}), 503
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"创作生成过程中发生错误: {e}")
        traceback.print_exc()
        return jsonify({'error': f'服务暂时不可用: {str(e)}'}), 500


@credits_bp.route('/generate-colors', methods=['POST'])
@require_credits('generate_colors')
def generate_colors(current_user):
    """生成配色方案API（带认证和积分扣减）"""
    try:
        color_palettes = [
            ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],
            ["#FF7675", "#74B9FF", "#00B894", "#FDCB6E", "#E17055"],
        ]
        return jsonify({"colors": random.choice(color_palettes)}), 200
    except Exception as e:
        return jsonify({"error": "配色生成失败"}), 500