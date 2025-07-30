# -*- coding: utf-8 -*-
"""
积分管理和核心服务API - 稳定版（含URL验证和重试机制）
"""
from flask import Blueprint, request, jsonify, current_app
import os
import json
import requests
import traceback
import random
import base64
import re
import urllib.parse
import time
from functools import wraps

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
                
                result = f(current_user, *args, **kwargs)
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

# --- 简化的辅助函数 ---
# 移除了复杂的辅助函数，保持代码简单

# --- 简化版URL提取 ---
def extract_image_url_from_stream(content):
    """简化版：从API响应中提取第一个图片URL"""
    if not content:
        current_app.logger.warning("API响应内容为空")
        return None

    try:
        current_app.logger.info(f"开始解析API响应内容，长度: {len(content)}")

        # 最简单的正则表达式：按文本顺序查找第一个图片URL
        # 优先查找OpenAI域名的URL（因为我们知道这是正确的）
        openai_pattern = r'https://videos\.openai\.com/[^\s<>"\'\[\]{}\\|^`\n\r]+'
        openai_urls = re.findall(openai_pattern, content, re.IGNORECASE)

        if openai_urls:
            # 直接返回第一个OpenAI URL（这是我们要的第一张图片）
            first_url = openai_urls[0].rstrip('.,;!?)"\']}')
            current_app.logger.info(f"找到OpenAI图片URL: {first_url}")
            return first_url

        # 如果没有找到OpenAI URL，尝试通用图片URL模式
        general_pattern = r'https?://[^\s<>"\'\[\]{}\\|^`\n\r]+\.(?:jpg|jpeg|png|gif|webp|bmp)'
        general_urls = re.findall(general_pattern, content, re.IGNORECASE)

        if general_urls:
            # 返回第一个找到的图片URL
            first_url = general_urls[0].rstrip('.,;!?)"\']}')
            current_app.logger.info(f"找到通用图片URL: {first_url}")
            return first_url

        # 如果都没找到，记录警告
        current_app.logger.warning("未找到任何图片URL")
        return None

    except Exception as e:
        current_app.logger.error(f"提取图片URL时发生异常: {e}")
        traceback.print_exc()
        return None

# --- URL验证和重试机制 ---
def validate_image_url(url, timeout=5):
    """验证图片URL是否可访问 - 优化版"""
    if not url:
        return False

    # 对于可信域名，跳过验证直接返回True
    trusted_domains = [
        'openai.com',
        'videos.openai.com',
        'oaidalleapiprodscus.blob.core.windows.net',  # OpenAI DALL-E存储
        'cdn.openai.com',
        'images.openai.com'
    ]

    for domain in trusted_domains:
        if domain in url:
            current_app.logger.info(f"跳过可信域名验证: {domain} - {url[:100]}...")
            return True

    # 对其他域名进行验证
    try:
        # 使用更友好的请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ImageBot/1.0)',
            'Accept': 'image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }

        # 首先尝试HEAD请求
        response = requests.head(url, timeout=timeout, allow_redirects=True, headers=headers)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if content_type.startswith('image/'):
                current_app.logger.info(f"HEAD请求验证成功: {url[:100]}...")
                return True

        # 如果HEAD失败，尝试GET请求
        current_app.logger.info(f"HEAD请求失败，尝试GET请求: {url[:100]}...")
        response = requests.get(url, timeout=timeout, stream=True, headers=headers)
        if response.status_code == 200:
            # 读取前1KB检查是否为图片
            chunk = next(response.iter_content(1024), b'')
            if len(chunk) > 100:
                current_app.logger.info(f"GET请求验证成功: {url[:100]}...")
                return True

    except Exception as e:
        current_app.logger.warning(f"URL验证失败: {url[:100]}... - {e}")

    return False

def generate_placeholder_svg(prompt):
    """生成占位符SVG图片"""
    safe_prompt = prompt[:20] + "..." if len(prompt) > 20 else prompt
    safe_prompt = safe_prompt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    svg_content = f'''<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
        <rect width="400" height="400" fill="white" stroke="black" stroke-width="2"/>
        <circle cx="200" cy="120" r="40" fill="none" stroke="black" stroke-width="3"/>
        <rect x="160" y="180" width="80" height="60" fill="none" stroke="black" stroke-width="3"/>
        <text x="200" y="260" text-anchor="middle" font-family="Arial" font-size="14" fill="black">
            线条画: {safe_prompt}
        </text>
        <text x="200" y="280" text-anchor="middle" font-family="Arial" font-size="11" fill="gray">
            （示例图片）
        </text>
        <text x="200" y="300" text-anchor="middle" font-family="Arial" font-size="10" fill="blue">
            请重试或联系管理员
        </text>
    </svg>'''
    return base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')

# --- 稳定版图片生成 ---
@credits_bp.route('/generate-creation', methods=['POST'])
@auth_required
def generate_creation(current_user):
    """稳定版：原子化地生成图片和配色方案"""
    print("=== 开始处理图片生成请求 ===")  # 使用print确保输出
    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    print(f"收到请求，prompt: {prompt}")
    
    if not prompt:
        return jsonify({"error": "请输入图片描述"}), 400
    
    if len(prompt) > 200:
        return jsonify({"error": "图片描述太长，请限制在200字符以内"}), 400
    
    if len(prompt) < 2:
        return jsonify({"error": "图片描述太短，请至少输入2个字符"}), 400

    total_cost = CREDIT_COSTS.get('generate_image', 1)  # 只扣除图片生成费用，配色推荐免费
    if current_user.credits < total_cost:
        return jsonify({
            'error': f"积分余额不足，需要 {total_cost} 积分，当前余额 {current_user.credits} 积分",
            'current_credits': current_user.credits,
            'required_credits': total_cost
        }), 400

    try:
        api_endpoint = os.getenv("IMAGE_API_ENDPOINT", "https://api.gptgod.online/v1/chat/completions")
        api_key = os.getenv("IMAGE_API_KEY")

        if not api_key:
            current_app.logger.error("IMAGE_API_KEY未配置")
            return jsonify({
                'error': '图片生成服务未配置，请联系管理员。您的积分未被扣除。',
                'current_credits': current_user.credits,
                'required_credits': total_cost
            }), 500

        # 记录API密钥的前几位（用于调试，不泄露完整密钥）
        print(f"使用API密钥: {api_key[:10]}...{api_key[-4:]}")
        current_app.logger.info(f"使用API密钥: {api_key[:10]}...{api_key[-4:]}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "stream": False,  # 禁用流式响应，简化处理
            "model": "gpt-4o-image-vip",
            "messages": [
                {
                    "role": "user",
                    "content": f"画一个简单的儿童涂色线条画：{prompt}。要求：黑白线条，无填充色彩，清晰轮廓，适合儿童涂色，白色背景"
                }
            ]
        }
        
        current_app.logger.info(f"开始生成创作: {prompt}")
        
        # 重试机制 - 增加重试次数应对API不稳定
        max_retries = 2  # 增加到2次重试
        for attempt in range(max_retries):
            try:
                print(f"开始API调用，尝试次数: {attempt + 1}/{max_retries}")
                current_app.logger.info(f"开始API调用，尝试次数: {attempt + 1}/{max_retries}")

                # 添加开始时间记录
                import time
                start_time = time.time()

                # 使用简单的requests调用，增加超时时间到120秒
                print("正在调用OpenAI API...")
                response = requests.post(api_endpoint, headers=headers, json=payload, timeout=120)
                print("API调用完成")

                # 记录API调用耗时
                end_time = time.time()
                duration = end_time - start_time
                current_app.logger.info(f"API调用完成，耗时: {duration:.2f}秒")
                current_app.logger.info(f"API响应状态码: {response.status_code}")
                current_app.logger.info(f"API响应内容长度: {len(response.text)}")

                # 记录API响应长度（避免日志过长）
                current_app.logger.info(f"API响应内容预览: {response.text[:200]}...")

                response.raise_for_status()

                current_app.logger.info("开始提取图片URL...")
                image_url = extract_image_url_from_stream(response.text)
                current_app.logger.info(f"提取到的图片URL: {image_url[:100] if image_url else 'None'}...")

                # 简化：直接使用提取到的URL（已经过基本清理）
                
                if image_url:
                    current_app.logger.info("开始验证图片URL可访问性...")
                    # 验证URL是否可访问
                    url_is_valid = validate_image_url(image_url)

                    if url_is_valid:
                        current_app.logger.info("图片URL验证成功，开始扣除积分")
                    else:
                        current_app.logger.warning(f"图片URL验证失败，但仍然尝试使用: {image_url}")
                        # 降级策略：即使验证失败，仍然尝试使用URL
                        # 让前端决定是否能够加载图片

                    # 无论验证结果如何，都尝试返回图片（降级策略）
                    current_app.logger.info("开始扣除积分")
                    description = f"生成创作: {prompt[:50]}"
                    current_user.consume_credits(total_cost, description)
                    db.session.commit()
                    current_app.logger.info(f"积分扣除成功，剩余积分: {current_user.credits}")

                    colors = random.choice([
                        ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],
                        ["#FF7675", "#74B9FF", "#00B894", "#FDCB6E", "#E17055"],
                        ["#A8E6CF", "#FFD3B6", "#FFAAA5", "#FF8B94", "#C7CEEA"],
                        ["#F4A261", "#E76F51", "#2A9D8F", "#E9C46A", "#264653"],
                        ["#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF"]
                    ])

                    response_data = {
                        "imageUrl": image_url,
                        "colors": colors,
                        "user": current_user.to_dict()
                    }

                    # 如果URL验证失败，添加警告信息
                    if not url_is_valid:
                        response_data["warning"] = "图片URL验证失败，但仍然尝试加载"

                    return jsonify(response_data), 200
                else:
                    current_app.logger.warning("未找到有效图片URL")
                    if attempt == max_retries - 1:
                        # 最后一次尝试失败，返回详细错误信息
                        error_msg = '图片生成失败：无法从API响应中提取有效的图片URL。'
                        if len(response.text) > 0:
                            error_msg += f' API响应长度: {len(response.text)} 字符。'
                        error_msg += ' 您的积分未被扣除。'

                        return jsonify({
                            'error': error_msg,
                            'current_credits': current_user.credits,
                            'required_credits': total_cost,
                            'debug_info': {
                                'response_length': len(response.text),
                                'response_preview': response.text[:200] if response.text else 'Empty'
                            }
                        }), 503
                    time.sleep(1)
                    continue
                    
            except requests.exceptions.Timeout:
                print(f"API超时，尝试 {attempt + 1}/{max_retries}")
                current_app.logger.error(f"API请求超时 (尝试 {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    return jsonify({
                        'error': f'图片生成超时（已重试{max_retries}次），OpenAI服务响应较慢，请稍后重试。您的积分未被扣除。',
                        'current_credits': current_user.credits,
                        'required_credits': total_cost
                    }), 504
                # 指数退避：第一次重试等待5秒，第二次等待10秒
                wait_time = 5 * (attempt + 1)
                print(f"等待{wait_time}秒后重试...")
                current_app.logger.info(f"等待{wait_time}秒后重试...")
                time.sleep(wait_time)
                continue
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    return jsonify({
                        'error': '图片生成服务暂时不可用，请稍后重试',
                        'current_credits': current_user.credits,
                        'required_credits': total_cost
                    }), 503
                time.sleep(1)
                continue
        
        # 所有重试都失败，返回错误信息而不是占位符
        return jsonify({
            'error': '图片生成服务暂时不可用，请稍后重试。您的积分未被扣除。',
            'current_credits': current_user.credits,
            'required_credits': total_cost
        }), 503

    except Exception as e:
        current_app.logger.error(f"创作生成异常: {e}")
        traceback.print_exc()
        return jsonify({
            'error': f'服务暂时不可用: {str(e)}',
            'current_credits': current_user.credits,
            'required_credits': total_cost
        }), 500


@credits_bp.route('/generate-colors', methods=['POST'])
@require_credits('generate_colors')
def generate_colors(current_user):
    """生成配色方案API"""
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
