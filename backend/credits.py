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

# --- 辅助函数 ---
def clean_extracted_url(url):
    """清理提取到的URL"""
    if not url:
        return None

    # 移除可能的前缀和后缀
    url = url.strip()
    # 移除引号
    url = url.strip('"\'')
    # 移除可能的转义字符
    url = url.replace('\\', '')
    # 移除可能的尾部字符
    url = url.rstrip('.,;!?)"\']}')

    return url

def extract_url_from_text(text):
    """从文本中提取URL"""
    if not text:
        return None

    # 使用正则表达式查找URL
    url_pattern = r'https?://[^\s<>"\'\[\]{}\\|^`\n\r]+'
    urls = re.findall(url_pattern, text, re.IGNORECASE)

    for url in urls:
        cleaned_url = clean_extracted_url(url)
        if cleaned_url and len(cleaned_url) > 20:
            return cleaned_url

    return None

def is_valid_url_format(url):
    """检查URL格式是否有效"""
    if not url:
        return False

    return (
        url.startswith('http') and
        len(url) > 20 and
        not any(char in url for char in ['<', '>', '"', "'", '\\', ' ']) and
        '.' in url
    )

# --- 增强版URL提取 ---
def extract_image_url_from_stream(content):
    """增强版：从流式响应中提取图片URL"""
    if not content:
        current_app.logger.warning("API响应内容为空")
        return None

    try:
        current_app.logger.info(f"开始解析API响应内容，长度: {len(content)}")

        # 方法1: 尝试JSON解析（新增）
        try:
            current_app.logger.info("尝试JSON解析...")
            # 使用json模块解析，避免变量名冲突
            parsed_json = json.loads(content)
            current_app.logger.info(f"JSON解析成功，结构: {type(parsed_json)}")

            # 查找常见的图片URL字段
            url_fields = ['url', 'image_url', 'imageUrl', 'image', 'src']

            # 如果是字典，直接查找
            if isinstance(parsed_json, dict):
                for field in url_fields:
                    if field in parsed_json and parsed_json[field]:
                        url = parsed_json[field]
                        if isinstance(url, str) and url.startswith('http'):
                            current_app.logger.info(f"从JSON字段'{field}'找到URL: {url}")
                            return clean_extracted_url(url)

                # 查找data数组
                if 'data' in parsed_json and isinstance(parsed_json['data'], list):
                    for item in parsed_json['data']:
                        if isinstance(item, dict):
                            for field in url_fields:
                                if field in item and item[field]:
                                    url = item[field]
                                    if isinstance(url, str) and url.startswith('http'):
                                        current_app.logger.info(f"从JSON data[].{field}找到URL: {url}")
                                        return clean_extracted_url(url)

                # 查找choices数组（ChatGPT格式）
                if 'choices' in parsed_json and isinstance(parsed_json['choices'], list):
                    for choice in parsed_json['choices']:
                        if isinstance(choice, dict) and 'message' in choice:
                            message = choice['message']
                            if isinstance(message, dict) and 'content' in message:
                                # 在message content中查找URL
                                content_text = message['content']
                                if isinstance(content_text, str):
                                    url = extract_url_from_text(content_text)
                                    if url:
                                        current_app.logger.info(f"从choices[].message.content找到URL: {url}")
                                        return clean_extracted_url(url)

            current_app.logger.info("JSON解析成功但未找到图片URL，继续使用正则表达式")

        except ValueError:  # json.JSONDecodeError 是 ValueError 的子类
            current_app.logger.info("不是有效的JSON格式，使用正则表达式解析")
        except Exception as e:
            current_app.logger.warning(f"JSON解析出错: {e}")

        # 方法2: 直接查找图片URL - 优化版（原有逻辑）
        url_patterns = [
            # 标准图片URL
            r'https?://[^\s<>"\'\[\]{}\\|^`\n\r]+\.(?:jpg|jpeg|png|gif|webp|bmp)',
            # OpenAI相关域名
            r'https?://[^\s<>"\'\[\]{}\\|^`\n\r]*openai\.com[^\s<>"\'\[\]{}\\|^`\n\r]+',
            r'https?://[^\s<>"\'\[\]{}\\|^`\n\r]*videos\.openai\.com[^\s<>"\'\[\]{}\\|^`\n\r]+',
            # 其他可能的图片服务域名
            r'https?://[^\s<>"\'\[\]{}\\|^`\n\r]*\.amazonaws\.com[^\s<>"\'\[\]{}\\|^`\n\r]+',
            # 通用HTTPS URL（作为备选）
            r'https://[^\s<>"\'\[\]{}\\|^`\n\r]{20,}',
        ]

        for i, pattern in enumerate(url_patterns):
            current_app.logger.debug(f"尝试URL模式 {i+1}: {pattern}")
            urls = re.findall(pattern, content, re.IGNORECASE)
            if urls:
                current_app.logger.info(f"模式 {i+1} 找到 {len(urls)} 个URL")
                for url in urls:
                    try:
                        # 使用改进的URL清理函数
                        cleaned_url = clean_extracted_url(url)
                        if not cleaned_url:
                            continue

                        decoded_url = urllib.parse.unquote(cleaned_url)

                        # 使用改进的URL格式验证
                        if is_valid_url_format(decoded_url):
                            # 额外验证：确保不是文档或API端点
                            if not any(ext in decoded_url.lower() for ext in ['.html', '.json', '.xml', '.txt']):
                                current_app.logger.info(f"找到有效图片URL: {decoded_url}")
                                return decoded_url
                            else:
                                current_app.logger.debug(f"跳过文档类型URL: {decoded_url}")
                        else:
                            current_app.logger.debug(f"URL格式验证失败: {decoded_url}")
                    except Exception as e:
                        current_app.logger.warning(f"URL处理失败: {e}")
                        continue
        
        # 方法2: 解析JSON格式的响应
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('data: ') and line != 'data: [DONE]':
                try:
                    json_str = line[6:]
                    # 使用已导入的json模块
                    chunk_data = json.loads(json_str)
                    
                    if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                        choice = chunk_data['choices'][0]
                        if 'delta' in choice and 'content' in choice['delta']:
                            content_text = choice['delta']['content']
                            if content_text:
                                for pattern in url_patterns:
                                    urls = re.findall(pattern, content_text, re.IGNORECASE)
                                    if urls:
                                        decoded_url = urllib.parse.unquote(urls[0])
                                        current_app.logger.info(f"从JSON内容中找到图片URL: {decoded_url}")
                                        return decoded_url
                                            
                except (ValueError, KeyError, IndexError):  # ValueError包含JSONDecodeError
                    continue
        
        # 方法3: 查找所有URL并评分
        all_url_pattern = r'https?://[^\s<>"\'\[\]{}\\|^`\n\r]+'
        all_urls = re.findall(all_url_pattern, content)
        
        priority_keywords = ['image', 'png', 'jpg', 'jpeg', 'openai', 'cdn', 'assets']
        scored_urls = []
        
        for url in all_urls:
            try:
                decoded_url = urllib.parse.unquote(url)
                score = 0
                
                for keyword in priority_keywords:
                    if keyword in decoded_url.lower():
                        score += 10
                
                if any(ext in decoded_url.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                    score += 20
                
                scored_urls.append((score, decoded_url))
                
            except Exception:
                continue
        
        if scored_urls:
            scored_urls.sort(key=lambda x: x[0], reverse=True)
            best_url = scored_urls[0][1]
            current_app.logger.info(f"选择最高分的图片URL: {best_url}")
            return best_url
        
        current_app.logger.warning("未找到任何有效的图片URL")
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
    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    
    if not prompt:
        return jsonify({"error": "请输入图片描述"}), 400
    
    if len(prompt) > 200:
        return jsonify({"error": "图片描述太长，请限制在200字符以内"}), 400
    
    if len(prompt) < 2:
        return jsonify({"error": "图片描述太短，请至少输入2个字符"}), 400

    total_cost = CREDIT_COSTS.get('generate_image', 1) + CREDIT_COSTS.get('generate_colors', 1)
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
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
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
        
        current_app.logger.info(f"开始生成创作: {prompt}")
        
        # 重试机制 - 减少重试次数，增加超时时间
        max_retries = 1
        for attempt in range(max_retries):
            try:
                current_app.logger.info(f"开始API调用，尝试次数: {attempt + 1}/{max_retries}")
                # 避免json参数名冲突，使用data参数并手动序列化
                import json as json_module
                response = requests.post(
                    api_endpoint,
                    headers=headers,
                    data=json_module.dumps(payload),
                    timeout=90
                )
                current_app.logger.info(f"API响应状态码: {response.status_code}")
                current_app.logger.info(f"API响应内容长度: {len(response.text)}")

                # 记录完整的API响应内容（用于调试）
                current_app.logger.info("=== 完整API响应内容开始 ===")
                current_app.logger.info(response.text)
                current_app.logger.info("=== 完整API响应内容结束 ===")

                response.raise_for_status()

                current_app.logger.info("开始提取图片URL...")
                image_url = extract_image_url_from_stream(response.text)
                current_app.logger.info(f"提取到的图片URL: {image_url[:100] if image_url else 'None'}...")

                # 添加URL有效性检查
                if image_url and not is_valid_url_format(image_url):
                    current_app.logger.error(f"提取到的URL格式无效: {image_url}")
                    image_url = None
                
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
                if attempt == max_retries - 1:
                    return jsonify({
                        'error': '图片生成超时，请稍后重试',
                        'current_credits': current_user.credits,
                        'required_credits': total_cost
                    }), 504
                time.sleep(1)
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
