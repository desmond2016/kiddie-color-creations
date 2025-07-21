# -*- coding: utf-8 -*-
"""
图片代理服务 - 解决CORS和URL有效期问题
"""
import os
import requests
import hashlib
import time
from datetime import datetime, timedelta
from flask import Blueprint, send_file, jsonify, current_app
from werkzeug.utils import secure_filename
import traceback

image_proxy_bp = Blueprint('image_proxy', __name__, url_prefix='/proxy')

# 图片缓存配置
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'static', 'cached_images')
CACHE_DURATION = timedelta(days=7)  # 缓存7天
MAX_CACHE_SIZE = 100 * 1024 * 1024  # 100MB

def ensure_cache_dir():
    """确保缓存目录存在"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_filename(url):
    """根据URL生成缓存文件名"""
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    extension = '.png'  # 默认使用png格式
    return f"{url_hash}{extension}"

def is_url_accessible(url, timeout=5):
    """检查URL是否可访问"""
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code == 200
    except Exception:
        return False

def download_image(url, filename):
    """下载图片到本地缓存"""
    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        # 检查内容类型
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            return False
            
        file_path = os.path.join(CACHE_DIR, filename)
        
        # 保存图片
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return True
    except Exception as e:
        current_app.logger.error(f"下载图片失败: {e}")
        return False

def get_cached_image_path(url):
    """获取缓存图片路径，如果不存在则下载"""
    ensure_cache_dir()
    
    filename = get_cache_filename(url)
    file_path = os.path.join(CACHE_DIR, filename)
    
    # 如果文件已存在且未过期
    if os.path.exists(file_path):
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_path))
        if file_age < CACHE_DURATION:
            return file_path
    
    # 下载新图片
    if download_image(url, filename):
        return file_path
    
    return None

def cleanup_old_cache():
    """清理过期缓存"""
    ensure_cache_dir()
    
    try:
        current_time = datetime.now()
        total_size = 0
        
        for filename in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, filename)
            if os.path.isfile(file_path):
                file_age = current_time - datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # 删除过期文件
                if file_age > CACHE_DURATION:
                    os.remove(file_path)
                else:
                    total_size += os.path.getsize(file_path)
        
        # 如果总大小超过限制，删除最旧的文件
        if total_size > MAX_CACHE_SIZE:
            files = [(f, os.path.getmtime(os.path.join(CACHE_DIR, f))) 
                    for f in os.listdir(CACHE_DIR) 
                    if os.path.isfile(os.path.join(CACHE_DIR, f))]
            files.sort(key=lambda x: x[1])
            
            # 删除最旧的文件直到总大小在限制内
            for filename, _ in files:
                file_path = os.path.join(CACHE_DIR, filename)
                total_size -= os.path.getsize(file_path)
                os.remove(file_path)
                if total_size <= MAX_CACHE_SIZE:
                    break
                    
    except Exception as e:
        current_app.logger.error(f"清理缓存失败: {e}")

@image_proxy_bp.route('/image/<path:image_url>')
def proxy_image(image_url):
    """代理图片请求"""
    try:
        # URL解码
        import urllib.parse
        decoded_url = urllib.parse.unquote(image_url)
        
        # 验证URL格式
        if not decoded_url.startswith('http'):
            return jsonify({'error': '无效的URL格式'}), 400
        
        # 获取缓存图片
        cached_path = get_cached_image_path(decoded_url)
        
        if cached_path and os.path.exists(cached_path):
            # 返回缓存图片
            return send_file(cached_path, mimetype='image/png')
        
        # 如果缓存不存在，尝试直接代理
        try:
            response = requests.get(decoded_url, timeout=10)
            response.raise_for_status()
            
            # 保存到缓存
            filename = get_cache_filename(decoded_url)
            file_path = os.path.join(CACHE_DIR, filename)
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            return send_file(file_path, mimetype='image/png')
            
        except Exception as e:
            current_app.logger.error(f"代理图片失败: {e}")
            return jsonify({'error': '图片加载失败'}), 404
            
    except Exception as e:
        current_app.logger.error(f"图片代理错误: {e}")
        return jsonify({'error': '服务器错误'}), 500

@image_proxy_bp.route('/health')
def health_check():
    """代理服务健康检查"""
    ensure_cache_dir()
    
    cache_info = {
        'cache_dir': CACHE_DIR,
        'cache_exists': os.path.exists(CACHE_DIR),
        'cached_files': len(os.listdir(CACHE_DIR)) if os.path.exists(CACHE_DIR) else 0,
        'cache_size_mb': 0
    }
    
    if os.path.exists(CACHE_DIR):
        total_size = 0
        for filename in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, filename)
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
        cache_info['cache_size_mb'] = round(total_size / (1024 * 1024), 2)
    
    return jsonify(cache_info), 200

@image_proxy_bp.route('/cleanup', methods=['POST'])
def cleanup_cache():
    """手动清理缓存（管理员功能）"""
    try:
        cleanup_old_cache()
        return jsonify({'message': '缓存清理完成'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_proxy_url(original_url):
    """获取代理后的URL"""
    if not original_url:
        return None
    
    # 如果是本地URL或数据URL，直接返回
    if original_url.startswith('data:') or original_url.startswith('/'):
        return original_url
    
    # 生成代理URL
    import urllib.parse
    encoded_url = urllib.parse.quote(original_url, safe='')
    return f"/proxy/image/{encoded_url}"

# 定期清理任务
def schedule_cleanup():
    """设置定期清理任务"""
    cleanup_old_cache()
