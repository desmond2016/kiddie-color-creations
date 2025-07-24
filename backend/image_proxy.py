# -*- coding: utf-8 -*-
"""
图片代理服务 - 简化版URL处理
"""
import os
import io
import requests
import hashlib
from datetime import datetime, timedelta
from flask import Blueprint, send_file, jsonify, current_app, request
import urllib.parse

image_proxy_bp = Blueprint('image_proxy', __name__, url_prefix='/proxy')

# 图片缓存配置
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'static', 'cached_images')
CACHE_DURATION = timedelta(days=7)
MAX_CACHE_SIZE = 50 * 1024 * 1024  # 50MB

def ensure_cache_dir():
    """确保缓存目录存在"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_filename(url):
    """根据URL生成缓存文件名"""
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    return f"{url_hash}.png"

def download_image(url, filename):
    """下载图片到本地缓存"""
    try:
        response = requests.get(url, timeout=15, stream=True)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            return False
            
        file_path = os.path.join(CACHE_DIR, filename)
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return True
    except Exception as e:
        current_app.logger.error(f"下载图片失败: {e}")
        return False

def get_cached_image_path(url):
    """获取缓存图片路径"""
    ensure_cache_dir()
    
    filename = get_cache_filename(url)
    file_path = os.path.join(CACHE_DIR, filename)
    
    if os.path.exists(file_path):
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_path))
        if file_age < CACHE_DURATION:
            return file_path
    
    if download_image(url, filename):
        return file_path
    
    return None

@image_proxy_bp.route('/image')
def proxy_image():
    """简化版代理图片请求 - 使用查询参数"""
    image_url = request.args.get('url')
    
    if not image_url:
        return jsonify({'error': '缺少图片URL参数'}), 400
    
    try:
        # URL解码
        decoded_url = urllib.parse.unquote(image_url)
        
        if not decoded_url.startswith('http'):
            return jsonify({'error': '无效的URL格式'}), 400
        
        # 临时禁用缓存，直接代理以减少内存使用
        current_app.logger.info(f"直接代理图片: {decoded_url}")

        # 直接代理，不缓存，添加适当的请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ImageProxy/1.0)',
            'Accept': 'image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }

        response = requests.get(decoded_url, timeout=30, stream=True, headers=headers)
        response.raise_for_status()

        # 流式返回，减少内存占用
        return send_file(
            io.BytesIO(response.content),
            mimetype=response.headers.get('content-type', 'image/png'),
            as_attachment=False
        )
            
    except Exception as e:
        current_app.logger.error(f"图片代理错误: {e}")
        return jsonify({'error': '图片加载失败'}), 404

@image_proxy_bp.route('/direct')
def proxy_direct():
    """直接代理模式 - 不缓存"""
    image_url = request.args.get('url')
    
    if not image_url:
        return jsonify({'error': '缺少图片URL参数'}), 400
    
    try:
        decoded_url = urllib.parse.unquote(image_url)
        response = requests.get(decoded_url, timeout=10)
        response.raise_for_status()
        
        return send_file(
            io.BytesIO(response.content),
            mimetype=response.headers.get('content-type', 'image/png')
        )
    except Exception as e:
        current_app.logger.error(f"直接代理错误: {e}")
        return jsonify({'error': '图片加载失败'}), 404

def get_proxy_url(original_url):
    """获取简化版代理URL"""
    if not original_url:
        return None
    
    # 如果是本地URL或数据URL，直接返回
    if original_url.startswith('data:') or original_url.startswith('/'):
        return original_url
    
    # 简化版代理URL - 使用查询参数
    encoded_url = urllib.parse.quote(original_url, safe='')
    return f"/proxy/image?url={encoded_url}"

# 健康检查
@image_proxy_bp.route('/health')
def health_check():
    """代理服务健康检查"""
    ensure_cache_dir()
    
    cache_info = {
        'cache_dir': CACHE_DIR,
        'cache_exists': os.path.exists(CACHE_DIR),
        'cached_files': len(os.listdir(CACHE_DIR)) if os.path.exists(CACHE_DIR) else 0
    }
    
    return jsonify(cache_info), 200
