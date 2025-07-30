/**
 * 配色推荐UI组件
 * 负责配色推荐功能的用户界面交互
 */

class ColorUI {
    constructor() {
        this.colorAnalyzer = window.colorAnalyzer;
        this.currentRecommendations = [];
        this.isVisible = false;
        
        // 绑定方法的this上下文
        this.generateColors = this.generateColors.bind(this);
        this.applyColorScheme = this.applyColorScheme.bind(this);
        this.copyColorToClipboard = this.copyColorToClipboard.bind(this);
        
        this.init();
    }

    /**
     * 初始化UI组件
     */
    init() {
        this.createRecommendationSection();
        this.bindEvents();
    }

    /**
     * 创建配色推荐区域的HTML结构
     */
    createRecommendationSection() {
        // 查找插入位置（在图片容器之后）
        const imageContainer = document.querySelector('.image-container');
        if (!imageContainer) {
            console.warn('未找到图片容器，无法插入智能配色推荐');
            return;
        }

        // 检查是否已经创建过推荐区域
        if (document.getElementById('color-recommendation')) {
            console.log('智能配色推荐区域已存在');
            return;
        }

        // 创建配色推荐区域
        const recommendationHTML = `
            <section class="color-recommendation-section" id="color-recommendation" style="display: none;">
                <div class="container">
                    <h3><i class="fas fa-palette"></i> 智能配色推荐</h3>
                    <div class="color-schemes-container" id="color-schemes-container">
                        <!-- 配色方案将在这里动态生成 -->
                    </div>
                </div>
            </section>
        `;

        // 插入到图片容器之后
        imageContainer.insertAdjacentHTML('afterend', recommendationHTML);
        console.log('智能配色推荐区域已创建并插入到图片容器之后');
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 监听图片描述输入变化
        const promptInput = document.getElementById('prompt-input');
        if (promptInput) {
            // 添加生成配色按钮
            this.addGenerateColorsButton();
        }

        // 监听图片生成完成事件（如果有的话）
        document.addEventListener('imageGenerated', (event) => {
            const description = event.detail?.description;
            if (description) {
                this.generateColors(description);
            }
        });
    }

    /**
     * 添加生成配色按钮
     */
    addGenerateColorsButton() {
        const generateButton = document.getElementById('generate-button');
        if (!generateButton) return;

        // 检查是否已经添加过按钮
        if (document.querySelector('.generate-colors-btn')) return;

        // 创建生成配色按钮
        const colorButton = document.createElement('button');
        colorButton.type = 'button';
        colorButton.className = 'generate-colors-btn';
        colorButton.innerHTML = '<i class="fas fa-palette"></i> 生成配色';
        colorButton.onclick = () => {
            const description = document.getElementById('prompt-input')?.value;
            if (description) {
                this.generateColors(description);
            } else {
                this.showMessage('请先输入图片描述', 'warning');
            }
        };

        // 创建按钮容器（如果不存在）
        let buttonContainer = generateButton.parentNode.querySelector('.button-container');
        if (!buttonContainer) {
            buttonContainer = document.createElement('div');
            buttonContainer.className = 'button-container';

            // 将生成按钮移动到容器中
            generateButton.parentNode.insertBefore(buttonContainer, generateButton);
            buttonContainer.appendChild(generateButton);
        }

        // 将配色按钮添加到容器中
        buttonContainer.appendChild(colorButton);
    }

    /**
     * 根据描述生成配色推荐
     * @param {string} description - 图片描述
     */
    generateColors(description) {
        if (!description || !this.colorAnalyzer) {
            this.showMessage('配色分析器未初始化', 'error');
            return;
        }

        // 显示加载状态
        this.showLoadingState();
        
        // 显示推荐区域
        this.showRecommendationSection();

        // 模拟异步处理（实际上是同步的，但为了更好的用户体验）
        setTimeout(() => {
            try {
                // 获取配色推荐
                const recommendations = this.colorAnalyzer.getColorRecommendations(description, 3);
                this.currentRecommendations = recommendations;
                
                // 渲染配色方案
                this.renderColorSchemes(recommendations);
                
                // 显示成功消息
                this.showMessage(`根据"${description}"生成了 ${recommendations.length} 个配色方案`, 'success');
                
            } catch (error) {
                console.error('生成配色时出错:', error);
                this.showErrorState();
                this.showMessage('生成配色时出现错误，请重试', 'error');
            }
        }, 500);
    }

    /**
     * 显示推荐区域
     */
    showRecommendationSection() {
        const section = document.getElementById('color-recommendation');
        if (section) {
            section.style.display = 'block';
            this.isVisible = true;
            
            // 平滑滚动到推荐区域
            setTimeout(() => {
                section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
        }
    }

    /**
     * 隐藏推荐区域
     */
    hideRecommendationSection() {
        const section = document.getElementById('color-recommendation');
        if (section) {
            section.style.display = 'none';
            this.isVisible = false;
        }
    }

    /**
     * 显示加载状态
     */
    showLoadingState() {
        const container = document.getElementById('color-schemes-container');
        if (container) {
            container.innerHTML = `
                <div class="color-schemes-loading">
                    <i class="fas fa-spinner"></i>
                    <p>正在分析描述并生成配色方案...</p>
                </div>
            `;
        }
    }

    /**
     * 显示错误状态
     */
    showErrorState() {
        const container = document.getElementById('color-schemes-container');
        if (container) {
            container.innerHTML = `
                <div class="color-schemes-empty">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h4>生成失败</h4>
                    <p>无法生成配色方案，请检查输入并重试</p>
                </div>
            `;
        }
    }

    /**
     * 渲染配色方案
     * @param {Array} schemes - 配色方案数组
     */
    renderColorSchemes(schemes) {
        const container = document.getElementById('color-schemes-container');
        if (!container) return;

        if (schemes.length === 0) {
            container.innerHTML = `
                <div class="color-schemes-empty">
                    <i class="fas fa-palette"></i>
                    <h4>未找到匹配的配色</h4>
                    <p>尝试使用不同的描述词，或查看默认配色方案</p>
                </div>
            `;
            return;
        }

        // 生成配色方案HTML
        const schemesHTML = schemes.map((scheme, index) => 
            this.createSchemeCardHTML(scheme, index)
        ).join('');

        container.innerHTML = schemesHTML;

        // 绑定事件
        this.bindSchemeEvents();
    }

    /**
     * 创建配色方案卡片HTML
     * @param {Object} scheme - 配色方案对象
     * @param {number} index - 索引
     * @returns {string} HTML字符串
     */
    createSchemeCardHTML(scheme, index) {
        const colorsHTML = scheme.colors.map(color => 
            `<div class="color-swatch" style="background-color: ${color}" data-color="${color}" title="${color}"></div>`
        ).join('');

        const keywordsHTML = scheme.matchedKeywords && scheme.matchedKeywords.length > 0 
            ? `<div class="matched-keywords">
                <div class="keywords-label">匹配关键词:</div>
                <div class="keyword-tags">
                    ${scheme.matchedKeywords.map(keyword => 
                        `<span class="keyword-tag">${keyword}</span>`
                    ).join('')}
                </div>
            </div>` 
            : '';

        const confidencePercent = Math.round(scheme.confidence * 100);

        return `
            <div class="color-scheme-card" data-scheme-index="${index}">
                <div class="scheme-header">
                    <h4>${scheme.name}</h4>
                    <p>${scheme.description}</p>
                </div>
                
                <div class="confidence-indicator">
                    <span>匹配度:</span>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${confidencePercent}%"></div>
                    </div>
                    <span>${confidencePercent}%</span>
                </div>
                
                ${keywordsHTML}
                
                <div class="color-palette">
                    ${colorsHTML}
                </div>
                
                <button class="apply-colors-btn" data-scheme-index="${index}">
                    <i class="fas fa-check"></i> 应用此配色
                </button>
            </div>
        `;
    }

    /**
     * 绑定配色方案相关事件
     */
    bindSchemeEvents() {
        // 应用配色按钮事件
        document.querySelectorAll('.apply-colors-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.schemeIndex);
                this.applyColorScheme(index);
            });
        });

        // 色块点击复制事件
        document.querySelectorAll('.color-swatch').forEach(swatch => {
            swatch.addEventListener('click', (e) => {
                const color = e.target.dataset.color;
                this.copyColorToClipboard(color);
            });
        });
    }

    /**
     * 应用配色方案 - 创建配色展示区域
     * @param {number} index - 配色方案索引
     */
    applyColorScheme(index) {
        if (!this.currentRecommendations[index]) return;

        const scheme = this.currentRecommendations[index];

        // 查找或创建配色展示区域
        let colorDisplaySection = document.getElementById('applied-colors-section');

        if (!colorDisplaySection) {
            // 创建配色展示区域
            const colorDisplayHTML = `
                <section class="applied-colors-section" id="applied-colors-section">
                    <div class="container">
                        <h3><i class="fas fa-paint-brush"></i> 当前配色方案</h3>
                        <div class="color-swatches" id="applied-color-swatches">
                            <!-- 应用的配色将在这里显示 -->
                        </div>
                        <p class="palette-tip">
                            <strong>提示：</strong>点击颜色块可以复制颜色值，用于涂色创作！
                        </p>
                    </div>
                </section>
            `;

            // 插入到智能配色推荐区域之后
            const recommendationSection = document.getElementById('color-recommendation');
            if (recommendationSection) {
                recommendationSection.insertAdjacentHTML('afterend', colorDisplayHTML);
                colorDisplaySection = document.getElementById('applied-colors-section');
            }
        }

        if (colorDisplaySection) {
            const swatchesContainer = document.getElementById('applied-color-swatches');
            if (swatchesContainer) {
                // 清空现有配色
                swatchesContainer.innerHTML = '';

                // 添加新配色
                scheme.colors.forEach(color => {
                    const swatch = document.createElement('div');
                    swatch.className = 'swatch';
                    swatch.style.backgroundColor = color;
                    swatch.title = color;
                    swatch.dataset.color = color;
                    swatch.onclick = () => this.copyColorToClipboard(color);
                    swatchesContainer.appendChild(swatch);
                });

                // 显示配色展示区域
                colorDisplaySection.style.display = 'block';

                // 平滑滚动到配色展示区域
                colorDisplaySection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

                this.showMessage(`已应用"${scheme.name}"配色方案，点击颜色块可复制颜色值`, 'success');
            }
        } else {
            this.showMessage('无法创建配色展示区域', 'warning');
        }
    }

    /**
     * 复制颜色值到剪贴板
     * @param {string} color - 颜色值
     */
    copyColorToClipboard(color) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(color).then(() => {
                this.showMessage(`颜色 ${color} 已复制到剪贴板`, 'success');
            }).catch(() => {
                this.showMessage('复制失败，请手动复制', 'warning');
            });
        } else {
            // 降级方案
            const textArea = document.createElement('textarea');
            textArea.value = color;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                this.showMessage(`颜色 ${color} 已复制到剪贴板`, 'success');
            } catch (err) {
                this.showMessage('复制失败，请手动复制', 'warning');
            }
            document.body.removeChild(textArea);
        }
    }

    /**
     * 显示消息提示
     * @param {string} message - 消息内容
     * @param {string} type - 消息类型 (success, error, warning)
     */
    showMessage(message, type = 'info') {
        // 这里可以集成现有的消息提示系统
        console.log(`[${type.toUpperCase()}] ${message}`);
        
        // 简单的临时提示（可以后续改进）
        const toast = document.createElement('div');
        toast.className = `message ${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            padding: 12px 20px;
            border-radius: 5px;
            color: white;
            font-weight: 600;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        
        // 设置背景色
        const colors = {
            success: '#4CAF50',
            error: '#f44336',
            warning: '#ff9800',
            info: '#2196F3'
        };
        toast.style.backgroundColor = colors[type] || colors.info;
        
        document.body.appendChild(toast);
        
        // 显示动画
        setTimeout(() => toast.style.opacity = '1', 100);
        
        // 自动隐藏
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 3000);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 确保依赖已加载
    if (window.colorAnalyzer) {
        window.colorUI = new ColorUI();
    } else {
        console.error('ColorAnalyzer 未找到，无法初始化 ColorUI');
    }
});
