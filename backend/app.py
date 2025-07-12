# -*- coding: utf-8 -*-
import os
from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from dotenv import load_dotenv
import traceback

from models import db, User, RedemptionCode, Setting
from auth import auth_bp, setup_jwt_error_handlers
from credits import credits_bp
from admin import admin_bp

load_dotenv()

# --- Flask 应用设置 ---
app = Flask(__name__)


# --- 配置 ---
# 强制从环境变量加载，如果没有设置则抛出错误
def get_env_variable(name):
    try:
        return os.environ[name]
    except KeyError:
        message = f"错误: 环境变量 {name} 未设置。"
        raise Exception(message)

app.config['SECRET_KEY'] = get_env_variable('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = get_env_variable('JWT_SECRET_KEY')
app.config['ADMIN_PASSWORD'] = get_env_variable('ADMIN_PASSWORD') # 用于首次初始化

# 为不同身份设置不同的JWT过期时间
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7) # 普通用户
app.config['ADMIN_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1) # 管理员

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/kiddie_color_creations.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ADMIN_USERNAME'] = os.getenv('ADMIN_USERNAME', 'admin')

# --- 初始化扩展 ---
CORS(app, origins=[
    "https://kiddie-color-creations.pages.dev",
    "http://localhost:5500", "http://127.0.0.1:5500",
    "http://localhost:8000", "http://127.0.0.1:8000"
], supports_credentials=True)
db.init_app(app)
jwt = JWTManager(app)
setup_jwt_error_handlers(jwt) # 注册自定义JWT错误处理器
migrate = Migrate(app, db) # 初始化 Flask-Migrate

# --- 注册蓝图 ---
app.register_blueprint(auth_bp)
app.register_blueprint(credits_bp)
app.register_blueprint(admin_bp)

# --- 数据库和初始数据设置 ---
# 注意: 数据库表的创建现在由 Flask-Migrate 处理
# `flask db init` -> `flask db migrate` -> `flask db upgrade`
# 初始数据（如管理员）可以在首次迁移后手动或通过脚本添加
@app.cli.command("init-db-seed")
def init_db_seed():
    """在数据库��植入初始数据"""
    with app.app_context():
        try:
            # 初始化管理员密码
            if not Setting.query.get('admin_password'):
                print("初始化管理员密码...")
                initial_password = app.config['ADMIN_PASSWORD']
                Setting.set_password('admin_password', initial_password)
                print("管理员密码已初始化并存入数据库。")

            # 创建测试用户
            if User.query.count() == 0:
                print("创建测试用户...")
                test_user = User(username='testuser', email='test@example.com', credits=50)
                test_user.set_password('123456')
                db.session.add(test_user)
                db.session.commit()
                print("测试数据创建成功")
            else:
                print("数据库中已存在用户，跳过创建测试用户。")

        except Exception as e:
            print(f"数据库植入初始数据时发生错误: {e}")
            traceback.print_exc()

# setup_database(app) # 旧的数据库设置函数，已被移除

# --- 通用API路由 ---
@app.route('/', methods=['GET'])
def root():
    return jsonify({'message': 'Kiddie Color Creations API is running!', 'version': '1.0.0'}), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        db.session.execute('SELECT 1')
        db_status = 'connected'
    except Exception:
        db_status = 'disconnected'
    return jsonify({'status': 'healthy', 'database': db_status}), 200

if __name__ == '__main__':
    print("="*50)
    print("启动 Kiddie Color Creations API 开发服务器...")
    print(f"数据库: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"管理员用户名: {app.config['ADMIN_USERNAME']}")
    print("="*50)
    
    flask_debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    port = int(os.getenv("PORT", 5000))
    app.run(debug=flask_debug, host='0.0.0.0', port=port)

