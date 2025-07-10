// 环境配置
// 动态判断API基础URL
const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const localApiUrl = 'http://127.0.0.1:5000'; // 本地后端的地址
const productionApiUrl = 'https://kiddie-color-creations-backend.onrender.com'; // Render生产环境地址

const CONFIG = {
    API_BASE_URL: isLocal ? localApiUrl : productionApiUrl
};

// 导出配置
window.CONFIG = CONFIG;

