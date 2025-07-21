# -*- coding: utf-8 -*-
"""
Flask应用 - 添加CORS跨域支持
"""
from flask import Flask, jsonify
from flask_cors import CORS
import os

# 创建Flask应用
app = Flask(__name__)

# 配置CORS
# 允许所有域名访问（生产环境建议限制特定域名）
CORS(app, resources={
    r"/credits/*": {
        "origins": [
            "https://kiddie-color-creations.pages.dev",
            "http://localhost:3000",
            "http://localhost:5173",
            "https://kiddie-color-creations.vercel.app"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "supports_credentials": True
    },
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# 或者使用更简单的配置（允许所有来源）
# CORS(app, resources={r"/*": {"origins": "*"}})

# 手动CORS配置（备选方案）
@app.after_request
def after_request(response):
    """手动添加CORS头"""
    allowed_origins = [
        "https://kiddie-color-creations.pages.dev",
        "http://localhost:3000",
        "http://localhost:5173"
    ]
    
    origin = request.headers.get('Origin')
    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
    
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    return response

# 健康检查端点
@app.route('/health')
def health_check():
    """服务健康检查"""
    return jsonify({
        "status": "healthy",
        "service": "kiddie-color-creations-backend",
        "cors_enabled": True
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
