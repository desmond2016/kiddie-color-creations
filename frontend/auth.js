// -*- coding: utf-8 -*-
/**
 * 用户认证和积分系统前端逻辑
 * 参考 little_writers_assistant_payed 项目的前端实现
 */

// 全局变量
let currentUser = null;
let authToken = null;

// API配置
const API_BASE_URL = 'http://127.0.0.1:5000/api';

// DOM元素
const authModal = document.getElementById('auth-modal');
const redeemModal = document.getElementById('redeem-modal');
const historyModal = document.getElementById('history-modal');

// 工具函数
function showMessage(elementId, message, type = 'info') {
    const messageEl = document.getElementById(elementId);
    messageEl.textContent = message;
    messageEl.className = `message ${type}`;
    messageEl.style.display = 'block';
    
    // 3秒后自动隐藏成功消息
    if (type === 'success') {
        setTimeout(() => {
            messageEl.style.display = 'none';
        }, 3000);
    }
}

function hideMessage(elementId) {
    const messageEl = document.getElementById(elementId);
    messageEl.style.display = 'none';
}

// API请求函数
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    // 构建headers
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };

    // 添加认证头
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    const finalOptions = {
        ...options,
        headers
    };

    console.log('API请求:', url, finalOptions); // 调试日志

    try {
        const response = await fetch(url, finalOptions);
        const data = await response.json();

        console.log('API响应:', response.status, data); // 调试日志

        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('API请求失败:', error);
        throw error;
    }
}

// 认证相关函数
function saveAuthData(token, user) {
    authToken = token;
    currentUser = user;
    localStorage.setItem('authToken', token);
    localStorage.setItem('currentUser', JSON.stringify(user));
}

function loadAuthData() {
    authToken = localStorage.getItem('authToken');
    const userData = localStorage.getItem('currentUser');
    if (userData) {
        currentUser = JSON.parse(userData);
    }
}

function clearAuthData() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
}

function updateUI() {
    const authButtons = document.getElementById('auth-buttons');
    const userPanel = document.getElementById('user-panel');
    const loginPrompt = document.getElementById('login-prompt');
    const creditsInfo = document.getElementById('credits-info');
    const generateButton = document.getElementById('generate-button');
    
    if (currentUser && authToken) {
        // 已登录状态
        authButtons.style.display = 'none';
        userPanel.style.display = 'flex';
        loginPrompt.style.display = 'none';
        creditsInfo.style.display = 'block';
        generateButton.disabled = false;
        
        // 更新用户信息
        document.getElementById('username-display').textContent = currentUser.username;
        document.getElementById('credits-count').textContent = currentUser.credits;
        
        // 检查积分余额（需要2积分：图片+配色）
        if (currentUser.credits < 2) {
            generateButton.disabled = true;
            generateButton.innerHTML = '<i class="fas fa-coins"></i> 积分不足';
        }
    } else {
        // 未登录状态
        authButtons.style.display = 'flex';
        userPanel.style.display = 'none';
        loginPrompt.style.display = 'block';
        creditsInfo.style.display = 'none';
        generateButton.disabled = true;
    }
}

// 用户注册
async function register(username, email, password) {
    try {
        const data = await apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ username, email, password })
        });
        
        saveAuthData(data.access_token, data.user);
        updateUI();
        closeModal('auth-modal');
        showMessage('auth-message', '注册成功！欢迎加入！', 'success');
        
        return true;
    } catch (error) {
        showMessage('auth-message', error.message, 'error');
        return false;
    }
}

// 用户登录
async function login(loginInput, password) {
    try {
        const data = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ login: loginInput, password })
        });

        console.log('登录响应数据:', data);
        console.log('保存token:', data.access_token);

        saveAuthData(data.access_token, data.user);

        console.log('保存后的token:', authToken);
        console.log('保存后的用户:', currentUser);

        updateUI();
        closeModal('auth-modal');
        showMessage('auth-message', '登录成功！', 'success');

        return true;
    } catch (error) {
        showMessage('auth-message', error.message, 'error');
        return false;
    }
}

// 用户登出
function logout() {
    clearAuthData();
    updateUI();
    closeUserDropdown();
}

// 兑换积分码
async function redeemCode(code) {
    try {
        console.log('开始兑换积分码:', code);
        console.log('当前用户:', currentUser);
        console.log('当前token:', authToken);

        const data = await apiRequest('/auth/redeem', {
            method: 'POST',
            body: JSON.stringify({ code })
        });

        // 更新用户积分
        currentUser.credits = data.current_credits;
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        updateUI();

        closeModal('redeem-modal');
        showMessage('redeem-message', data.message, 'success');

        return true;
    } catch (error) {
        console.error('兑换失败:', error);
        showMessage('redeem-message', error.message, 'error');
        return false;
    }
}

// 修改密码
async function changePassword(currentPassword, newPassword, confirmPassword) {
    try {
        console.log('开始修改密码');
        console.log('当前用户:', currentUser);
        console.log('当前token:', authToken);

        const data = await apiRequest('/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
                confirm_password: confirmPassword
            })
        });

        // 清空表单
        document.getElementById('change-password-form').reset();

        // 关闭模态框
        closeModal('change-password-modal');

        // 显示成功消息
        showMessage('change-password-message', data.message, 'success');

        // 可选：显示全局成功提示
        alert('密码修改成功！');

        return true;
    } catch (error) {
        console.error('修改密码失败:', error);
        showMessage('change-password-message', error.message, 'error');
        return false;
    }
}

// 获取交易记录
async function loadTransactionHistory() {
    try {
        const data = await apiRequest('/auth/transactions');
        displayTransactionHistory(data.transactions);
    } catch (error) {
        document.getElementById('transaction-list').innerHTML = 
            `<div class="error">加载失败: ${error.message}</div>`;
    }
}

function displayTransactionHistory(transactions) {
    const listEl = document.getElementById('transaction-list');
    
    if (transactions.length === 0) {
        listEl.innerHTML = '<div class="empty">暂无交易记录</div>';
        return;
    }
    
    const html = transactions.map(t => `
        <div class="transaction-item ${t.transaction_type}">
            <div class="transaction-info">
                <div class="transaction-desc">${t.description}</div>
                <div class="transaction-time">${new Date(t.created_at).toLocaleString()}</div>
            </div>
            <div class="transaction-amount ${t.credits_amount > 0 ? 'positive' : 'negative'}">
                ${t.credits_amount > 0 ? '+' : ''}${t.credits_amount}
            </div>
        </div>
    `).join('');
    
    listEl.innerHTML = html;
}

// 模态框控制
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    document.body.style.overflow = 'auto';
    
    // 清除消息
    const messageIds = ['auth-message', 'redeem-message'];
    messageIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) hideMessage(id);
    });
}

function closeUserDropdown() {
    document.getElementById('user-dropdown').style.display = 'none';
}

// 初始化
function initAuth() {
    loadAuthData();
    updateUI();

    // 如果有token，验证其有效性
    if (authToken) {
        apiRequest('/auth/profile')
            .then(data => {
                currentUser = data.user;
                localStorage.setItem('currentUser', JSON.stringify(currentUser));
                updateUI();
            })
            .catch(() => {
                // Token无效，清除认证数据
                clearAuthData();
                updateUI();
            });
    }
}

// 全局函数，供HTML中的script使用
window.initAuth = initAuth;
window.showMessage = showMessage;
window.hideMessage = hideMessage;

// 刷新用户信息
async function refreshUserInfo() {
    if (!authToken) {
        console.log('没有认证token，无法刷新用户信息');
        return;
    }

    try {
        console.log('正在刷新用户信息...');
        const data = await apiRequest('/auth/profile');
        currentUser = data.user;
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        updateUI();
        console.log('用户信息刷新成功:', currentUser);
    } catch (error) {
        console.error('刷新用户信息失败:', error);
        // 如果token无效，清除认证数据
        if (error.message.includes('无效') || error.message.includes('过期')) {
            clearAuthData();
            updateUI();
        }
    }
}

// 导出函数供全局使用
window.authSystem = {
    register,
    login,
    logout,
    redeemCode,
    changePassword,
    loadTransactionHistory,
    openModal,
    closeModal,
    closeUserDropdown,
    updateUI,
    refreshUserInfo,
    getCurrentUser: () => currentUser,
    getAuthToken: () => authToken
};
