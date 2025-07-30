/**
 * 智能配色分析器
 * 根据用户输入的图片描述，分析并推荐相应的配色方案
 */

class ColorAnalyzer {
    constructor() {
        this.colorSchemes = window.COLOR_SCHEMES || {};
        this.stopWords = ['的', '了', '在', '是', '有', '和', '与', '或', '一个', '一只', '一朵', '很', '非常', '特别'];
    }

    /**
     * 分析描述文本并返回推荐的配色方案
     * @param {string} description - 用户输入的图片描述
     * @param {number} maxResults - 最大返回结果数量，默认为3
     * @returns {Array} 推荐的配色方案数组
     */
    analyzeDescription(description, maxResults = 3) {
        if (!description || typeof description !== 'string') {
            return [];
        }

        // 1. 文本预处理
        const processedText = this.preprocessText(description);
        
        // 2. 关键词匹配和权重计算
        const matches = this.findMatches(processedText);
        
        // 3. 排序并返回最佳匹配
        const sortedMatches = this.sortMatches(matches);
        
        // 4. 返回前N个结果
        return sortedMatches.slice(0, maxResults);
    }

    /**
     * 文本预处理：去除标点符号、转换为小写、分词
     * @param {string} text - 原始文本
     * @returns {Array} 处理后的词汇数组
     */
    preprocessText(text) {
        // 去除标点符号和特殊字符
        const cleanText = text.replace(/[^\u4e00-\u9fa5\u0041-\u005a\u0061-\u007a\u0030-\u0039]/g, ' ');
        
        // 转换为小写并分词
        const words = cleanText.toLowerCase().split(/\s+/).filter(word => word.length > 0);
        
        // 去除停用词
        return words.filter(word => !this.stopWords.includes(word));
    }

    /**
     * 查找匹配的配色方案
     * @param {Array} words - 处理后的词汇数组
     * @returns {Array} 匹配结果数组
     */
    findMatches(words) {
        const matches = [];

        for (const [schemeId, scheme] of Object.entries(this.colorSchemes)) {
            let score = 0;
            let matchedKeywords = [];

            // 检查每个关键词是否匹配
            for (const keyword of scheme.keywords) {
                for (const word of words) {
                    if (this.isMatch(word, keyword)) {
                        score += this.calculateKeywordWeight(keyword, word);
                        matchedKeywords.push(keyword);
                        break; // 避免重复计分
                    }
                }
            }

            // 如果有匹配，添加到结果中
            if (score > 0) {
                matches.push({
                    id: schemeId,
                    scheme: scheme,
                    score: score,
                    matchedKeywords: matchedKeywords,
                    confidence: Math.min(score / 10, 1) // 置信度，最大为1
                });
            }
        }

        return matches;
    }

    /**
     * 判断词汇是否匹配关键词
     * @param {string} word - 用户输入的词汇
     * @param {string} keyword - 配色方案的关键词
     * @returns {boolean} 是否匹配
     */
    isMatch(word, keyword) {
        // 完全匹配
        if (word === keyword) {
            return true;
        }
        
        // 包含匹配
        if (word.includes(keyword) || keyword.includes(word)) {
            return true;
        }
        
        // 可以在这里添加更复杂的匹配逻辑，如同义词匹配
        return false;
    }

    /**
     * 计算关键词权重
     * @param {string} keyword - 关键词
     * @param {string} word - 匹配的词汇
     * @returns {number} 权重分数
     */
    calculateKeywordWeight(keyword, word) {
        // 完全匹配给更高权重
        if (word === keyword) {
            return 10;
        }
        
        // 包含匹配给较低权重
        if (word.includes(keyword) || keyword.includes(word)) {
            return 5;
        }
        
        return 1;
    }

    /**
     * 对匹配结果进行排序
     * @param {Array} matches - 匹配结果数组
     * @returns {Array} 排序后的结果数组
     */
    sortMatches(matches) {
        return matches.sort((a, b) => {
            // 首先按分数排序
            if (b.score !== a.score) {
                return b.score - a.score;
            }
            
            // 分数相同时，按匹配关键词数量排序
            return b.matchedKeywords.length - a.matchedKeywords.length;
        });
    }

    /**
     * 获取默认配色方案（当没有匹配时使用）
     * @returns {Array} 默认配色方案数组
     */
    getDefaultSchemes() {
        const defaultSchemeIds = ['rainbow', 'happy', 'cute'];
        return defaultSchemeIds.map(id => ({
            id: id,
            scheme: this.colorSchemes[id],
            score: 0,
            matchedKeywords: [],
            confidence: 0.5
        })).filter(item => item.scheme);
    }

    /**
     * 格式化配色方案用于UI显示
     * @param {Object} match - 匹配结果对象
     * @returns {Object} 格式化后的配色方案
     */
    formatSchemeForUI(match) {
        return {
            id: match.id,
            name: match.scheme.name,
            description: match.scheme.description,
            colors: match.scheme.colors,
            category: match.scheme.category,
            confidence: match.confidence,
            matchedKeywords: match.matchedKeywords
        };
    }

    /**
     * 主要的公共接口：获取配色推荐
     * @param {string} description - 图片描述
     * @param {number} maxResults - 最大结果数量
     * @returns {Array} 格式化的配色方案数组
     */
    getColorRecommendations(description, maxResults = 3) {
        let matches = this.analyzeDescription(description, maxResults);
        
        // 如果没有匹配结果，返回默认方案
        if (matches.length === 0) {
            matches = this.getDefaultSchemes().slice(0, maxResults);
        }
        
        // 格式化结果用于UI显示
        return matches.map(match => this.formatSchemeForUI(match));
    }

    /**
     * 获取所有可用的配色方案（用于展示或测试）
     * @returns {Array} 所有配色方案
     */
    getAllSchemes() {
        return Object.entries(this.colorSchemes).map(([id, scheme]) => ({
            id: id,
            name: scheme.name,
            description: scheme.description,
            colors: scheme.colors,
            category: scheme.category,
            keywords: scheme.keywords
        }));
    }

    /**
     * 根据类别获取配色方案
     * @param {string} category - 类别名称
     * @returns {Array} 该类别的配色方案
     */
    getSchemesByCategory(category) {
        return Object.entries(this.colorSchemes)
            .filter(([id, scheme]) => scheme.category === category)
            .map(([id, scheme]) => ({
                id: id,
                name: scheme.name,
                description: scheme.description,
                colors: scheme.colors,
                category: scheme.category
            }));
    }
}

// 创建全局实例
window.colorAnalyzer = new ColorAnalyzer();

// 导出类（如果在Node.js环境中）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ColorAnalyzer;
}
