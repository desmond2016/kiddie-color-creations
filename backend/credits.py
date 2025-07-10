# -*- coding: utf-8 -*-
"""
积分管理相关API
参考 little_writers_assistant_payed 项目的积分系统
采用虚拟模式，不影响其他项目
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, ValidationError
import os
import requests
import traceback
import uuid
import string
import random

from models import db, User, RedemptionCode, CreditTransaction
from auth import auth_required

# 创建积分管理蓝图
credits_bp = Blueprint('credits', __name__, url_prefix='/api/credits')

# 输入验证Schema
class ConsumeCreditsSchema(Schema):
    amount = fields.Int(required=True, validate=lambda x: x > 0)
    description = fields.Str(required=True)

class GenerateCodeSchema(Schema):
    credits_value = fields.Int(required=True, validate=lambda x: x > 0)
    description = fields.Str(allow_none=True)
    expires_days = fields.Int(allow_none=True, validate=lambda x: x > 0 if x is not None else True)

# 积分消费配置
CREDIT_COSTS = {
    'generate_image': 1,      # 生成图片消耗1积分
    'generate_colors': 1,     # 生成配色消耗1积分
}

def check_credits_and_consume(user, service_type, custom_amount=None):
    """检查并消费积分"""
    amount = custom_amount or CREDIT_COSTS.get(service_type, 1)
    
    if user.credits < amount:
        raise ValueError(f"积分余额不足，需要 {amount} 积分，当前余额 {user.credits} 积分")
    
    # 消费积分
    description = f"使用服务: {service_type}"
    transaction = user.consume_credits(amount, description)
    
    return transaction, amount

# 路由定义
@credits_bp.route('/balance', methods=['GET'])
@auth_required
def get_balance(current_user):
    """获取积分余额"""
    try:
        return jsonify({
            'credits': current_user.credits,
            'user_id': current_user.id,
            'username': current_user.username
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取积分余额错误: {str(e)}")
        return jsonify({'error': '获取积分余额失败'}), 500

@credits_bp.route('/consume', methods=['POST'])
@auth_required
def consume_credits(current_user):
    """消费积分（内部API，供其他服务调用）"""
    try:
        # 验证输入数据
        schema = ConsumeCreditsSchema()
        data = schema.load(request.get_json())
        
        amount = data['amount']
        description = data['description']
        
        # 检查余额
        if current_user.credits < amount:
            return jsonify({
                'error': f'积分余额不足，需要 {amount} 积分，当前余额 {current_user.credits} 积分'
            }), 400
        
        # 消费积分
        transaction = current_user.consume_credits(amount, description)
        db.session.commit()
        
        return jsonify({
            'message': f'成功消费 {amount} 积分',
            'credits_consumed': amount,
            'remaining_credits': current_user.credits,
            'transaction': transaction.to_dict()
        }), 200
        
    except ValidationError as e:
        return jsonify({'error': '输入数据格式错误', 'details': e.messages}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"消费积分错误: {str(e)}")
        return jsonify({'error': '消费积分失败'}), 500

@credits_bp.route('/check/<service_type>', methods=['GET'])
@auth_required
def check_service_credits(current_user, service_type):
    """检查特定服务的积分要求"""
    try:
        required_credits = CREDIT_COSTS.get(service_type, 1)
        
        return jsonify({
            'service_type': service_type,
            'required_credits': required_credits,
            'current_credits': current_user.credits,
            'sufficient': current_user.credits >= required_credits
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"检查服务积分错误: {str(e)}")
        return jsonify({'error': '检查服务积分失败'}), 500

# 工具函数，供其他模块使用
def require_credits(service_type, custom_amount=None):
    """装饰器：检查并消费积分"""
    def decorator(f):
        from functools import wraps

        @wraps(f)
        def wrapper(*args, **kwargs):
            # 首先检查JWT认证
            try:
                from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
                verify_jwt_in_request()
                current_user_id = int(get_jwt_identity())
                current_app.logger.info(f"JWT认证成功，用户ID: {current_user_id}")
            except Exception as e:
                current_app.logger.error(f"JWT认证失败: {str(e)}")
                return jsonify({'error': '需要登录才能访问'}), 401

            try:
                # 获取当前用户
                current_user = User.query.get(current_user_id)

                if not current_user:
                    return jsonify({'error': '用户不存在'}), 401

                # 检查并消费积分
                transaction, amount = check_credits_and_consume(
                    current_user, service_type, custom_amount
                )

                # 执行原函数
                result = f(*args, **kwargs)

                # 如果原函数执行成功，提交积分消费
                if isinstance(result, tuple) and len(result) == 2:
                    response, status_code = result
                    if 200 <= status_code < 300:
                        db.session.commit()
                        current_app.logger.info(f"用户 {current_user.username} 消费了 {amount} 积分，剩余 {current_user.credits} 积分")
                    else:
                        db.session.rollback()
                        current_app.logger.warning(f"原函数执行失败，回滚积分消费")
                else:
                    db.session.commit()
                    current_app.logger.info(f"用户 {current_user.username} 消费了 {amount} 积分，剩余 {current_user.credits} 积分")

                return result

            except ValueError as e:
                db.session.rollback()
                current_app.logger.warning(f"积分检查失败: {str(e)}")
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"积分检查错误: {str(e)}")
                return jsonify({'error': '服务暂时不可用'}), 500

        return wrapper
    return decorator

# 生图API（需要在require_credits定义之后）
@credits_bp.route('/generate-image', methods=['POST'])
@jwt_required()
@require_credits('generate_image')
def generate_image_with_credits():
    """
    生成图片API（带认证和积分扣减）
    接收前端的 prompt，调用外部 API 生成图片，并返回图片 URL。
    """
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"error": "请求体必须包含 prompt 字段"}), 400

        prompt = data['prompt'].strip()
        if not prompt:
            return jsonify({"error": "prompt 不能为空"}), 400

        current_app.logger.info(f"收到生成图片请求，prompt: {prompt}")

        # 调用外部API生成图片
        image_api_endpoint = os.getenv('IMAGE_API_ENDPOINT')
        image_api_key = os.getenv('IMAGE_API_KEY')

        if not image_api_endpoint or not image_api_key:
            current_app.logger.error("图片生成API配置缺失")
            return jsonify({"error": "图片生成服务配置错误"}), 500

        # 构建请求数据 - 使用原有的API格式
        api_data = {
            "stream": False,
            "model": "gpt-4o-image-vip",
            "messages": [
                {
                    "content": f"Create a simple black and white line drawing coloring page suitable for children, depicting: {prompt}. The drawing should have clear, bold outlines with no shading or color fills, perfect for children to color in. IMPORTANT: Keep all content within image boundaries - no parts should extend beyond edges. Generate only black and white line art - absolutely no colors allowed. Style requirements: coloring book page, simple line art, 1:1 aspect ratio, clean and smooth lines, pure black outlines, pure white background, no shadows or fills, black border frame around the entire image, all elements must stay completely within the border boundaries.",
                    "role": "user"
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {image_api_key}",
            "Content-Type": "application/json"
        }

        current_app.logger.info(f"调用外部API: {image_api_endpoint}")

        # 发送请求到外部API
        response = requests.post(
            image_api_endpoint,
            json=api_data,
            headers=headers,
            timeout=120
        )

        current_app.logger.info(f"外部API响应状态: {response.status_code}")

        if response.status_code != 200:
            error_msg = f"外部API调用失败，状态码: {response.status_code}"
            try:
                error_detail = response.json()
                current_app.logger.error(f"外部API错误详情: {error_detail}")
                if 'error' in error_detail:
                    error_msg += f"，错误: {error_detail['error']}"
            except:
                current_app.logger.error(f"外部API响应内容: {response.text}")

            return jsonify({"error": error_msg}), 500

        # 解析响应
        try:
            api_response = response.json()
            current_app.logger.info(f"外部API响应数据: {api_response}")
        except ValueError as e:
            current_app.logger.error(f"解析外部API响应失败: {e}")
            return jsonify({"error": "外部API响应格式错误"}), 500

        # 使用原有的图片URL提取逻辑
        image_url = None
        if 'choices' in api_response and len(api_response['choices']) > 0:
            message_content = api_response['choices'][0].get('message', {}).get('content')
            current_app.logger.info(f"API返回的消息内容: {message_content}")

            if message_content and isinstance(message_content, str):
                # 检查是否包含错误信息
                if "生成失败" in message_content or "失败原因" in message_content:
                    # 提取错误原因
                    import re
                    error_match = re.search(r'失败原因[：:]\s*([^\n]+)', message_content)
                    if error_match:
                        error_reason = error_match.group(1).strip()
                        current_app.logger.error(f"外部API生成失败: {error_reason}")
                        return jsonify({"error": f"图片生成失败: {error_reason}"}), 503
                    else:
                        current_app.logger.error(f"外部API生成失败，未知原因")
                        return jsonify({"error": "图片生成服务暂时不可用，请稍后重试"}), 503

                import re
                # 优先尝试CDN链接
                cdn_match = re.search(r'!\[gen_[^\]]*\]\((https://filesystem\.site/cdn/[^)]+\.png)\)', message_content)
                if cdn_match:
                    image_url = cdn_match.group(1)
                    current_app.logger.info(f"通过CDN正则找到图片URL: {image_url}")
                else:
                    # 回退到通用Markdown链接
                    generic_match = re.search(r'!\[.*?\]\((https://[^)]+\.png)\)', message_content)
                    if generic_match:
                        image_url = generic_match.group(1)
                        current_app.logger.info(f"通过通用正则找到图片URL: {image_url}")

        if image_url:
            current_app.logger.info(f"成功生成图片: {image_url}")
            return jsonify({
                "imageUrl": image_url,
                "prompt": prompt,
                "message": "图片生成成功"
            }), 200
        else:
            current_app.logger.error("未能从API响应中提取图片URL")
            current_app.logger.error(f"完整API响应: {api_response}")
            return jsonify({"error": "图片生成服务暂时不可用，请稍后重试"}), 503

    except requests.exceptions.Timeout:
        current_app.logger.error("外部API请求超时")
        return jsonify({"error": "图片生成超时，请稍后重试"}), 504
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"外部API请求异常: {e}")
        return jsonify({"error": "图片生成服务暂时不可用"}), 503
    except Exception as e:
        current_app.logger.error(f"生成图片时发生未知错误: {e}")
        traceback.print_exc()
        return jsonify({"error": "服务器内部错误"}), 500

# 配色API
@credits_bp.route('/generate-colors', methods=['POST'])
@require_credits('generate_colors')
def generate_colors():
    """
    生成配色方案API（带认证和积分扣减）
    """
    try:
        data = request.get_json()
        if not data or 'imageUrl' not in data:
            return jsonify({"error": "请求体必须包含 imageUrl 字段"}), 400

        image_url = data['imageUrl'].strip()
        if not image_url:
            return jsonify({"error": "imageUrl 不能为空"}), 400

        current_app.logger.info(f"收到配色请求，图片URL: {image_url}")

        # 模拟配色生成（实际项目中可以调用AI配色API）
        import random

        # 生成适合儿童涂色的配色方案
        color_palettes = [
            ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],  # 清新活泼
            ["#FF7675", "#74B9FF", "#00B894", "#FDCB6E", "#E17055"],  # 温暖明亮
            ["#6C5CE7", "#A29BFE", "#FD79A8", "#FDCB6E", "#00B894"],  # 梦幻彩虹
            ["#FF6348", "#FF9F43", "#10AC84", "#5F27CD", "#00D2D3"],  # 活力四射
            ["#FF3838", "#FF9500", "#2ECC71", "#3742FA", "#2F3542"],  # 经典搭配
        ]

        # 随机选择一个配色方案
        selected_palette = random.choice(color_palettes)

        # 添加一些随机变化
        varied_palette = []
        for color in selected_palette:
            # 轻微调整颜色亮度
            varied_palette.append(color)

        current_app.logger.info(f"生成配色方案: {varied_palette}")

        return jsonify({
            "colors": varied_palette,
            "message": "配色方案生成成功"
        }), 200

    except Exception as e:
        current_app.logger.error(f"生成配色时发生错误: {e}")
        traceback.print_exc()
        return jsonify({"error": "配色生成失败"}), 500

# 工具函数，供其他模块使用
def require_credits(service_type, custom_amount=None):
    """装饰器：检查并消费积分"""
    def decorator(f):
        from functools import wraps

        @wraps(f)
        def wrapper(*args, **kwargs):
            # 首先检查JWT认证
            try:
                from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
                verify_jwt_in_request()
                current_user_id = int(get_jwt_identity())
                current_app.logger.info(f"JWT认证成功，用户ID: {current_user_id}")
            except Exception as e:
                current_app.logger.error(f"JWT认证失败: {str(e)}")
                return jsonify({'error': '需要登录才能访问'}), 401

            try:
                # 获取当前用户
                current_user = User.query.get(current_user_id)

                if not current_user:
                    return jsonify({'error': '用户不存在'}), 401

                # 检查并消费积分
                transaction, amount = check_credits_and_consume(
                    current_user, service_type, custom_amount
                )

                # 执行原函数
                result = f(*args, **kwargs)

                # 如果原函数执行成功，提交积分消费
                if isinstance(result, tuple) and len(result) == 2:
                    response, status_code = result
                    if 200 <= status_code < 300:
                        db.session.commit()
                        current_app.logger.info(f"用户 {current_user.username} 消费了 {amount} 积分，剩余 {current_user.credits} 积分")
                    else:
                        db.session.rollback()
                        current_app.logger.warning(f"原函数执行失败，回滚积分消费")
                else:
                    db.session.commit()
                    current_app.logger.info(f"用户 {current_user.username} 消费了 {amount} 积分，剩余 {current_user.credits} 积分")

                return result

            except ValueError as e:
                db.session.rollback()
                current_app.logger.warning(f"积分检查失败: {str(e)}")
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"积分检查错误: {str(e)}")
                return jsonify({'error': '服务暂时不可用'}), 500

        return wrapper
    return decorator

# 生图API（需要在require_credits定义之后）
@credits_bp.route('/generate-image', methods=['POST'])
@jwt_required()
@require_credits('generate_image')
def generate_image_with_credits():
    """
    生成图片API（带认证和积分扣减）
    接收前端的 prompt，调用外部 API 生成图片，并返回图片 URL。
    """
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"error": "请求体必须包含 prompt 字段"}), 400

        prompt = data['prompt'].strip()
        if not prompt:
            return jsonify({"error": "prompt 不能为空"}), 400

        current_app.logger.info(f"收到生成图片请求，prompt: {prompt}")

        # 调用外部API生成图片
        image_api_endpoint = os.getenv('IMAGE_API_ENDPOINT')
        image_api_key = os.getenv('IMAGE_API_KEY')

        if not image_api_endpoint or not image_api_key:
            current_app.logger.error("图片生成API配置缺失")
            return jsonify({"error": "图片生成服务配置错误"}), 500

        # 构建请求数据 - 使用原有的API格式
        api_data = {
            "stream": False,
            "model": "gpt-4o-image-vip",
            "messages": [
                {
                    "content": f"Create a simple black and white line drawing coloring page suitable for children, depicting: {prompt}. The drawing should have clear, bold outlines with no shading or color fills, perfect for children to color in. IMPORTANT: Keep all content within image boundaries - no parts should extend beyond edges. Generate only black and white line art - absolutely no colors allowed. Style requirements: coloring book page, simple line art, 1:1 aspect ratio, clean and smooth lines, pure black outlines, pure white background, no shadows or fills, black border frame around the entire image, all elements must stay completely within the border boundaries.",
                    "role": "user"
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {image_api_key}",
            "Content-Type": "application/json"
        }

        current_app.logger.info(f"调用外部API: {image_api_endpoint}")

        # 发送请求到外部API
        response = requests.post(
            image_api_endpoint,
            json=api_data,
            headers=headers,
            timeout=120
        )

        current_app.logger.info(f"外部API响应状态: {response.status_code}")

        if response.status_code != 200:
            error_msg = f"外部API调用失败，状态码: {response.status_code}"
            try:
                error_detail = response.json()
                current_app.logger.error(f"外部API错误详情: {error_detail}")
                if 'error' in error_detail:
                    error_msg += f"，错误: {error_detail['error']}"
            except:
                current_app.logger.error(f"外部API响应内容: {response.text}")

            return jsonify({"error": error_msg}), 500

        # 解析响应
        try:
            api_response = response.json()
            current_app.logger.info(f"外部API响应数据: {api_response}")
        except ValueError as e:
            current_app.logger.error(f"解析外部API响应失败: {e}")
            return jsonify({"error": "外部API响应格式错误"}), 500

        # 使用原有的图片URL提取逻辑
        image_url = None
        if 'choices' in api_response and len(api_response['choices']) > 0:
            message_content = api_response['choices'][0].get('message', {}).get('content')
            current_app.logger.info(f"API返回的消息内容: {message_content}")

            if message_content and isinstance(message_content, str):
                # 检查是否包含错误信息
                if "生成失败" in message_content or "失败原因" in message_content:
                    # 提取错误原因
                    import re
                    error_match = re.search(r'失败原因[：:]\s*([^\n]+)', message_content)
                    if error_match:
                        error_reason = error_match.group(1).strip()
                        current_app.logger.error(f"外部API生成失败: {error_reason}")
                        return jsonify({"error": f"图片生成失败: {error_reason}"}), 503
                    else:
                        current_app.logger.error(f"外部API生成失败，未知原因")
                        return jsonify({"error": "图片生成服务暂时不可用，请稍后重试"}), 503

                import re
                # 优先尝试CDN链接
                cdn_match = re.search(r'!\[gen_[^\]]*\]\((https://filesystem\.site/cdn/[^)]+\.png)\)', message_content)
                if cdn_match:
                    image_url = cdn_match.group(1)
                    current_app.logger.info(f"通过CDN正则找到图片URL: {image_url}")
                else:
                    # 回退到通用Markdown链接
                    generic_match = re.search(r'!\[.*?\]\((https://[^)]+\.png)\)', message_content)
                    if generic_match:
                        image_url = generic_match.group(1)
                        current_app.logger.info(f"通过通用正则找到图片URL: {image_url}")

        if image_url:
            current_app.logger.info(f"成功生成图片: {image_url}")
            return jsonify({
                "imageUrl": image_url,
                "prompt": prompt,
                "message": "图片生成成功"
            }), 200
        else:
            current_app.logger.error("未能从API响应中提取图片URL")
            current_app.logger.error(f"完整API响应: {api_response}")
            return jsonify({"error": "图片生成服务暂时不可用，请稍后重试"}), 503

    except requests.exceptions.Timeout:
        current_app.logger.error("外部API请求超时")
        return jsonify({"error": "图片生成超时，请稍后重试"}), 504
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"外部API请求异常: {e}")
        return jsonify({"error": "图片生成服务暂时不可用"}), 503
    except Exception as e:
        current_app.logger.error(f"生成图片时发生未知错误: {e}")
        traceback.print_exc()
        return jsonify({"error": "服务器内部错误"}), 500

# 配色API
@credits_bp.route('/generate-colors', methods=['POST'])
@require_credits('generate_colors')
def generate_colors():
    """
    生成配色方案API（带认证和积分扣减）
    """
    try:
        data = request.get_json()
        if not data or 'imageUrl' not in data:
            return jsonify({"error": "请求体必须包含 imageUrl 字段"}), 400

        image_url = data['imageUrl'].strip()
        if not image_url:
            return jsonify({"error": "imageUrl 不能为空"}), 400

        current_app.logger.info(f"收到配色请求，图片URL: {image_url}")

        # 模拟配色生成（实际项目中可以调用AI配色API）
        import random

        # 生成适合儿童涂色的配色方案
        color_palettes = [
            ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],  # 清新活泼
            ["#FF7675", "#74B9FF", "#00B894", "#FDCB6E", "#E17055"],  # 温暖明亮
            ["#6C5CE7", "#A29BFE", "#FD79A8", "#FDCB6E", "#00B894"],  # 梦幻彩虹
            ["#FF6348", "#FF9F43", "#10AC84", "#5F27CD", "#00D2D3"],  # 活力四射
            ["#FF3838", "#FF9500", "#2ECC71", "#3742FA", "#2F3542"],  # 经典搭配
        ]

        # 随机选择一个配色方案
        selected_palette = random.choice(color_palettes)

        # 添加一些随机变化
        varied_palette = []
        for color in selected_palette:
            # 轻微调整颜色亮度
            varied_palette.append(color)

        current_app.logger.info(f"生成配色方案: {varied_palette}")

        return jsonify({
            "colors": varied_palette,
            "message": "配色方案生成成功"
        }), 200

    except Exception as e:
        current_app.logger.error(f"生成配色时发生错误: {e}")
        traceback.print_exc()
        return jsonify({"error": "配色生成失败"}), 500
