# -*- coding: utf-8 -*-
"""
数据库初始化和配置
参考 little_writers_assistant_payed 项目的数据库设计
采用虚拟模式，不影响其他项目
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

def init_database(app):
    """初始化数据库"""
    from models import db, User, RedemptionCode, CreditTransaction
    
    # 配置数据库
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # 使用独立的数据库文件，避免与其他项目冲突
    database_path = os.path.join(basedir, 'kiddie_color_creations.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 初始化数据库
    db.init_app(app)
    
    # 初始化迁移
    migrate = Migrate(app, db)
    
    # 创建表
    with app.app_context():
        db.create_all()
        
        # 创建初始数据
        create_initial_data()
    
    return db

def create_initial_data():
    """创建初始数据"""
    from models import db, User, RedemptionCode
    
    try:
        # 检查是否已有数据
        if User.query.first() is not None:
            print("数据库已有数据，跳过初始化")
            return
        
        print("创建初始数据...")
        
        # 创建测试用户（可选）
        if os.getenv('CREATE_TEST_USER', 'false').lower() == 'true':
            test_user = User(
                username='testuser',
                email='test@example.com',
                credits=100
            )
            test_user.set_password('123456')
            db.session.add(test_user)
        
        # 创建一些测试兑换码（可选）
        if os.getenv('CREATE_TEST_CODES', 'false').lower() == 'true':
            test_codes = [
                {'credits': 50, 'desc': '测试兑换码50积分'},
                {'credits': 100, 'desc': '测试兑换码100积分'},
                {'credits': 200, 'desc': '测试兑换码200积分'},
            ]
            
            for code_data in test_codes:
                code = RedemptionCode.create_code(
                    credits_value=code_data['credits'],
                    description=code_data['desc']
                )
                db.session.add(code)
                print(f"创建测试兑换码: {code.code} ({code_data['credits']}积分)")
        
        db.session.commit()
        print("初始数据创建完成")
        
    except Exception as e:
        db.session.rollback()
        print(f"创建初始数据失败: {str(e)}")

def reset_database():
    """重置数据库（开发用）"""
    from models import db
    
    print("警告：正在重置数据库...")
    db.drop_all()
    db.create_all()
    create_initial_data()
    print("数据库重置完成")

def get_database_stats():
    """获取数据库统计信息"""
    from models import db, User, RedemptionCode, CreditTransaction
    
    try:
        stats = {
            'users': User.query.count(),
            'redemption_codes': RedemptionCode.query.count(),
            'used_codes': RedemptionCode.query.filter_by(is_used=True).count(),
            'transactions': CreditTransaction.query.count(),
            'total_credits_in_system': db.session.query(db.func.sum(User.credits)).scalar() or 0
        }
        return stats
    except Exception as e:
        print(f"获取数据库统计失败: {str(e)}")
        return None

if __name__ == '__main__':
    # 独立运行时的测试代码
    from flask import Flask
    from models import db
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    # 初始化数据库
    init_database(app)
    
    with app.app_context():
        # 显示统计信息
        stats = get_database_stats()
        if stats:
            print("\n数据库统计信息:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        # 如果需要重置数据库，取消下面的注释
        # reset_database()
