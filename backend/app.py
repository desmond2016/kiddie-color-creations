# -*- coding: utf-8 -*-
import os
import sys
from datetime import timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from dotenv import load_dotenv
import traceback

from models import db, User, RedemptionCode, Setting
from auth import auth_bp, setup_jwt_error_handlers
from credits import credits_bp
from admin import admin_bp
from image_proxy import image_proxy_bp

load_dotenv()

# 设置系统编码为UTF-8，解决Windows编码问题
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# --- Flask 应用设置 ---
app = Flask(__name__, static_folder='../frontend', static_url_path='/')

# 配置日志级别
import logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# --- 配置 ---
# 从环境变量加载，提供默认值
def get_env_variable(name, default=None):
    value = os.getenv(name, default)
    if value is None:
        message = f"错误: 环境变量 {name} 未设置且没有默认值。"
        raise Exception(message)
    return value

app.config['SECRET_KEY'] = get_env_variable('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = get_env_variable('JWT_SECRET_KEY', 'dev-jwt-secret-change-in-production')
app.config['ADMIN_PASSWORD'] = get_env_variable('ADMIN_PASSWORD', 'admin123') # 用于首次初始化

# Supabase 配置 (可选，用于生产环境)
app.config['SUPABASE_URL'] = os.getenv('SUPABASE_URL')
app.config['SUPABASE_ANON_KEY'] = os.getenv('SUPABASE_ANON_KEY')
app.config['SUPABASE_SERVICE_KEY'] = os.getenv('SUPABASE_SERVICE_KEY')

# 为不同身份设置不同的JWT过期时间
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7) # 普通用户
app.config['ADMIN_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1) # 管理员

# 数据库配置 - 优先使用环境变量中的DATABASE_URL
database_url = os.getenv('DATABASE_URL')

if not database_url:
    # 如果没有设置DATABASE_URL环境变量，则使用Supabase连接池参数构建
    import urllib.parse
    db_user = "postgres"
    db_password = urllib.parse.quote_plus("t5O4sH9UJxXJf3sQ")
    db_host = "db.fvbifgzxwvaffyuzaegr.supabase.co"
    db_port = "6543"  # 使用连接池端口
    db_name = "postgres"
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    print("⚠️  未找到DATABASE_URL环境变量，使用默认Supabase连接池配置")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
print(f"使用数据库: {database_url[:50]}...")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 数据库连接池配置 (适用于SQLite和PostgreSQL)
database_url = app.config['SQLALCHEMY_DATABASE_URI']
if database_url.startswith('postgresql'):
    # PostgreSQL/Supabase 配置
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,          # PostgreSQL连接池大小
        'pool_recycle': 3600,    # 1小时回收连接
        'pool_pre_ping': True,   # 连接前检查
        'max_overflow': 10,      # 允许超出连接池
        'pool_timeout': 30       # 连接超时时间
    }
else:
    # SQLite 配置
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 3,          # 减少连接池大小
        'pool_recycle': 300,     # 5分钟回收连接
        'pool_pre_ping': True,   # 连接前检查
        'max_overflow': 0,       # 不允许超出连接池
        'pool_timeout': 20       # 连接超时时间
    }
app.config['ADMIN_USERNAME'] = os.getenv('ADMIN_USERNAME', 'admin')

# --- 初始化扩展 ---
# 临时使用通配符CORS配置解决跨域问题
print("正在配置CORS...")
cors = CORS(app,
     origins="*",  # 允许所有域名
     supports_credentials=False,  # 通配符模式下必须设为False
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization', 'Accept', 'X-Requested-With'],
     expose_headers=['Content-Type', 'Authorization'])
print("CORS配置完成")
db.init_app(app)
jwt = JWTManager(app)
setup_jwt_error_handlers(jwt) # 注册自定义JWT错误处理器
migrate = Migrate(app, db) # 初始化 Flask-Migrate

# --- 注册蓝图 ---
app.register_blueprint(auth_bp)
app.register_blueprint(credits_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(image_proxy_bp)

# --- CORS调试和备用处理 ---
@app.before_request
def before_request():
    """请求前处理 - CORS调试"""
    if request.method == 'OPTIONS':
        print(f"OPTIONS请求: {request.url}")
        print(f"Origin: {request.headers.get('Origin')}")

@app.after_request
def after_request(response):
    """请求后处理 - 确保CORS头正确设置"""
    # 手动添加CORS头作为备用
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, X-Requested-With'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Type, Authorization'
    return response

# --- 数据库和初始数据设置 ---
@app.cli.command("init-db-seed")
def init_db_seed():
    """在数据库中植入初始数据"""
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

# --- 通用API路由 ---
@app.route('/', methods=['GET'])
def root():
    from flask import send_from_directory
    return send_from_directory('../frontend', 'index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        # 使用Supabase REST API进行健康检查
        from supabase_client import get_supabase_manager
        manager = get_supabase_manager()

        if manager.is_connected() and manager.test_connection():
            db_status = 'connected'
        else:
            db_status = 'disconnected'
    except Exception:
        db_status = 'disconnected'
    return jsonify({'status': 'healthy', 'database': db_status}), 200

@app.route('/api/config-check', methods=['GET'])
def config_check():
    """检查关键配置项（调试用）"""
    config_status = {
        'IMAGE_API_ENDPOINT': 'configured' if os.getenv('IMAGE_API_ENDPOINT') else 'missing',
        'IMAGE_API_KEY': 'configured' if os.getenv('IMAGE_API_KEY') else 'missing',
        'DATABASE_URL': 'configured' if os.getenv('DATABASE_URL') else 'missing',
        'SECRET_KEY': 'configured' if os.getenv('SECRET_KEY') else 'missing',
    }
    return jsonify(config_status), 200

# --- 错误处理 ---
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'API端点不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': '服务器内部错误'}), 500

# 重复的after_request装饰器已移除

if __name__ == '__main__':
    print("="*50)
    print("启动 Kiddie Color Creations API 开发服务器...")
    print(f"数据库: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"管理员用户名: {app.config['ADMIN_USERNAME']}")
    print("="*50)
    
    # 跳过启动时的数据库初始化，避免编码问题
    print("🔄 跳过启动时数据库初始化，数据库表已在Supabase中手动创建")
    print("📝 管理员密码和测试数据已通过SQL脚本预设")
    
    flask_debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    port = int(os.getenv("PORT", 5000))
    app.run(debug=flask_debug, host='0.0.0.0', port=port)

# 为生产环境（如Render）初始化数据库 - 优化版本
def initialize_database():
    """使用Supabase REST API进行数据库初始化检查"""
    try:
        print("=== Supabase REST API 数据库检查 ===")

        # 使用Supabase REST API进行检查
        from supabase_client import get_supabase_manager
        from models_supabase import SettingSupabase, UserSupabase

        manager = get_supabase_manager()

        if not manager.is_connected():
            print("❌ Supabase客户端未正确初始化")
            return

        if not manager.test_connection():
            print("❌ Supabase连接测试失败")
            return

        print("✅ Supabase REST API连接正常")

        # 检查管理员密码设置
        try:
            admin_password = SettingSupabase.get('admin_password')
            if not admin_password:
                print("创建管理员密码设置...")
                initial_password = app.config['ADMIN_PASSWORD']
                SettingSupabase.set_password('admin_password', initial_password)
                print(f"管理员密码已初始化: {initial_password}")
            else:
                print("管理员密码已存在")

            # 检查用户数据
            users = UserSupabase.get_all()
            if len(users) == 0:
                print("创建测试用户...")
                test_user = UserSupabase.create(
                    username='testuser',
                    email='test@example.com',
                    password='123456',
                    credits=50
                )
                if test_user:
                    print("测试用户创建成功: testuser/123456")
                else:
                    print("测试用户创建失败")
            else:
                print(f"数据库已有 {len(users)} 个用户")

        except Exception as api_error:
            print(f"Supabase API操作错误: {api_error}")
            # 不阻止应用启动

        print("Supabase数据库初始化检查完成")

    except Exception as e:
        print(f"数据库初始化时发生错误: {e}")
        # 不阻止应用启动，只记录错误
        print("应用将继续启动，使用Supabase REST API模式")

# 在应用启动时初始化数据库（适用于生产环境）
# 临时注释掉，使用SQLite测试模式
# with app.app_context():
#     initialize_database()
