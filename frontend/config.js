// 环境配置
const CONFIG = {
    // 生产环境直接使用相对路径，由Cloudflare代理
    API_BASE_URL: '/api',

    // 管理员配置
    ADMIN_KEY: 'admin123',
    ADMIN_CREDENTIALS: {
        username: 'admin',
        password: 'admin123'
    }
};

// 导出配置
window.CONFIG = CONFIG;

