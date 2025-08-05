-- Kiddie Color Creations 数据库表创建脚本
-- 在Supabase SQL编辑器中运行此脚本

-- 1. 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    credits INTEGER DEFAULT 0 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login TIMESTAMP
);

-- 为用户表创建索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 2. 创建兑换码表
CREATE TABLE IF NOT EXISTS redemption_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) UNIQUE NOT NULL,
    credits_value INTEGER NOT NULL,
    is_used BOOLEAN DEFAULT FALSE NOT NULL,
    used_by_user_id INTEGER REFERENCES users(id),
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    description VARCHAR(200)
);

-- 为兑换码表创建索引
CREATE INDEX IF NOT EXISTS idx_redemption_codes_code ON redemption_codes(code);

-- 3. 创建积分交易记录表
CREATE TABLE IF NOT EXISTS credit_transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    transaction_type VARCHAR(20) NOT NULL,
    credits_amount INTEGER NOT NULL,
    description VARCHAR(200) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 为积分交易记录表创建索引
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id);

-- 4. 创建系统设置表
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(50) PRIMARY KEY,
    value VARCHAR(200) NOT NULL
);

-- 5. 插入初始管理员密码设置
-- 注意：这里使用的是bcrypt加密的 'admin123' 密码
-- 实际部署时应该更改为更安全的密码
INSERT INTO settings (key, value) VALUES 
('admin_password', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBdXfs2Sk4u2EK')
ON CONFLICT (key) DO NOTHING;

-- 6. 创建一些示例兑换码（可选）
INSERT INTO redemption_codes (code, credits_value, description) VALUES 
('WELCOME2024', 100, '新用户欢迎积分'),
('TESTCODE123', 50, '测试兑换码')
ON CONFLICT (code) DO NOTHING;

-- 验证表创建
SELECT 'users' as table_name, COUNT(*) as record_count FROM users
UNION ALL
SELECT 'redemption_codes', COUNT(*) FROM redemption_codes
UNION ALL
SELECT 'credit_transactions', COUNT(*) FROM credit_transactions
UNION ALL
SELECT 'settings', COUNT(*) FROM settings;
