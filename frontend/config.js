// 环境配置
const CONFIG = {
    // 根据当前协议和域名自动判断环境
    API_BASE_URL: (() => {
        const protocol = window.location.protocol;
        const hostname = window.location.hostname;

        // 如果是file协议或本地开发环境，使用本地API服务器
        if (protocol === 'file:' || hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'http://127.0.0.1:5000/api';  // 本地开发环境
        } else {
            return '/api';  // 生产环境（通过Cloudflare代理到Render）
        }
    })(),

    // 管理员配置
    ADMIN_KEY: 'admin123',
    ADMIN_CREDENTIALS: {
        username: 'admin',
        password: 'admin123'
    }
};

// 导出配置
window.CONFIG = CONFIG;
