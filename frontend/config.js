// 环境配置
const CONFIG = {
    // 根据当前域名自动判断环境
    API_BASE_URL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://127.0.0.1:5000/api'  // 本地开发环境
        : '/api',  // 生产环境（通过Cloudflare代理到Render）
    
    // 管理员配置
    ADMIN_KEY: 'admin123',
    ADMIN_CREDENTIALS: {
        username: 'admin',
        password: 'admin123'
    }
};

// 导出配置
window.CONFIG = CONFIG;
