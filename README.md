# 🎨 Kiddie Color Creations

儿童涂色创作平台 - 完整版

## ✨ 功能特性

- 🔐 **用户系统**: 注册、登录、JWT认证
- 💰 **积分系统**: 积分充值、消费、兑换码
- 🎨 **AI图片生成**: 基于描述生成线条画（1积分）
- 🌈 **智能配色**: 深度分析生成精确配色（1积分）
- 👨‍💼 **管理员后台**: 用户管理、兑换码生成、系统统计
- 📱 **响应式设计**: 适配各种设备



## 📋 使用流程

1. **管理员操作**
   - 登录管理员后台
   - 生成兑换码（设置积分数量）
   - 查看用户管理和系统统计

2. **用户操作**
   - 注册用户账号
   - 兑换积分码获取积分
   - 输入描述生成涂色图片
   - 获取智能配色推荐

## 🏗️ 技术架构

### 后端 (Flask)
- **app.py**: 主应用和API路由
- **auth.py**: JWT认证和用户管理
- **credits.py**: 积分系统和兑换码
- **models.py**: SQLAlchemy数据模型
- **database.py**: 数据库初始化

### 前端 (HTML/JS)
- **index.html**: 主页面（用户功能）
- **admin.html**: 管理员后台
- **auth.js**: 认证和用户交互
- **config.js**: 配置文件
- **style.css**: 样式文件

### 数据库 (SQLite)
- 用户表 (User)
- 兑换码表 (RedemptionCode)
- 积分交易表 (CreditTransaction)

## 🎨 智能配色算法

### 核心特性
- **深度语义分析**: 识别主体、颜色、环境、情绪
- **权重优先级**: 明确颜色 > 主体颜色 > 环境颜色
- **个性化生成**: 每个描述都有独特配色
- **儿童友好**: 所有颜色适合儿童涂色

### 分析维度
- 🎯 **主要对象**: 动物、人物、建筑等
- 🌈 **明确颜色**: 用户提到的具体颜色
- 🏞️ **环境场景**: 自然、室内、水边、天空
- 😊 **情绪动作**: 开心、安静、玩耍等
- ⏰ **时间背景**: 白天、夜晚、日落

## 📁 项目结构

```
kiddie-color-creations/
├── backend/                 # 后端服务
│   ├── app.py              # 主应用
│   ├── auth.py             # 认证模块
│   ├── credits.py          # 积分系统
│   ├── models.py           # 数据模型
│   ├── database.py         # 数据库
│   ├── requirements.txt    # Python依赖
│   ├── venv/               # 虚拟环境
│   └── instance/           # 实例文件
│       └── kiddie_color_creations.db  # 数据库文件
├── frontend/               # 前端页面
│   ├── index.html          # 主页面
│   ├── admin.html          # 管理员后台
│   ├── auth.js             # 认证脚本
│   ├── config.js           # 配置文件
│   └── style.css           # 样式文件
├── start_simple.bat        # Windows启动脚本
├── start_frontend.py       # 前端服务器
├── render.yaml             # Render部署配置
├── _redirects              # Cloudflare重定向配置
└── README.md               # 项目说明
```

## 🔧 开发说明

### 环境要求
- Python 3.7+
- Flask 2.0+
- SQLAlchemy
- Flask-JWT-Extended
- bcrypt

### 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 数据库初始化
首次运行会自动创建数据库和管理员账号

## 🎯 核心API

### 用户认证
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/profile` - 获取用户信息

### 积分系统
- `POST /api/credits/redeem` - 兑换积分码
- `GET /api/credits/transactions` - 交易记录

### 图片生成
- `POST /api/generate-image` - 生成线条画
- `POST /api/generate-colors` - 智能配色

### 管理员功能
- `GET /api/credits/admin/stats` - 系统统计
- `POST /api/credits/admin/generate-code` - 生成兑换码
- `GET /api/credits/admin/users` - 用户列表
- `GET /api/credits/admin/users/{id}` - 用户详情

## 📝 更新日志

### v1.0.0 (2025-06-30)
- ✅ 完整的用户注册登录系统
- ✅ 积分充值和消费机制
- ✅ 兑换码生成和使用
- ✅ AI图片生成功能
- ✅ 智能配色推荐算法
- ✅ 管理员后台完整功能
- ✅ 响应式前端设计

## 📄 许可证

MIT License

## 👥 贡献

欢迎提交 Issue 和 Pull Request！
