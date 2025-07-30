/**
 * 智能配色库 - 关键词与配色方案映射
 * 用于根据用户输入的图片描述生成相应的配色推荐
 */

const COLOR_SCHEMES = {
    // ===== 自然主题配色 =====
    ocean: {
        keywords: ['海洋', '大海', '海水', '蓝色', '海浪', '海滩', '海边', '海洋生物', '鲸鱼', '海豚'],
        colors: ['#0077BE', '#87CEEB', '#E0F6FF', '#4682B4', '#B0E0E6'],
        name: '海洋蓝调',
        description: '清新的海洋色彩，带来宁静与清凉感',
        category: 'nature'
    },
    
    forest: {
        keywords: ['森林', '树木', '绿色', '叶子', '草地', '植物', '大树', '丛林', '竹子', '松树'],
        colors: ['#228B22', '#90EE90', '#F0FFF0', '#32CD32', '#98FB98'],
        name: '森林绿意',
        description: '自然的绿色系，充满生机与活力',
        category: 'nature'
    },
    
    flower: {
        keywords: ['花朵', '花园', '玫瑰', '郁金香', '樱花', '花瓣', '花束', '鲜花', '花田'],
        colors: ['#FF69B4', '#FFB6C1', '#FFF0F5', '#FF1493', '#FFCCCB'],
        name: '花园粉韵',
        description: '温柔的粉色系，如花朵般浪漫',
        category: 'nature'
    },
    
    sunshine: {
        keywords: ['太阳', '阳光', '黄色', '金色', '向日葵', '明亮', '温暖', '光芒'],
        colors: ['#FFD700', '#FFFF99', '#FFFACD', '#F0E68C', '#FFEFD5'],
        name: '阳光金辉',
        description: '温暖的黄色系，充满阳光活力',
        category: 'nature'
    },
    
    rainbow: {
        keywords: ['彩虹', '七彩', '多彩', '缤纷', '色彩', '彩色'],
        colors: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'],
        name: '彩虹缤纷',
        description: '丰富的彩虹色彩，充满童趣',
        category: 'nature'
    },
    
    snow: {
        keywords: ['雪', '雪花', '冬天', '白色', '冰雪', '雪人', '冰'],
        colors: ['#FFFFFF', '#F0F8FF', '#E6E6FA', '#B0C4DE', '#D3D3D3'],
        name: '雪花纯净',
        description: '纯净的白色系，如雪花般清新',
        category: 'nature'
    },
    
    desert: {
        keywords: ['沙漠', '沙子', '骆驼', '仙人掌', '橙色', '土黄'],
        colors: ['#CD853F', '#F4A460', '#DEB887', '#D2691E', '#FFDEAD'],
        name: '沙漠暖阳',
        description: '温暖的沙漠色调，充满异域风情',
        category: 'nature'
    },
    
    // ===== 动物主题配色 =====
    cat: {
        keywords: ['小猫', '猫咪', '猫', '喵', '波斯猫', '橘猫', '黑猫', '白猫'],
        colors: ['#D2691E', '#F4A460', '#FFF8DC', '#DEB887', '#FFEFD5'],
        name: '温暖猫咪',
        description: '温暖的棕色系，如猫咪般可爱',
        category: 'animal'
    },
    
    dog: {
        keywords: ['小狗', '狗狗', '狗', '汪', '金毛', '拉布拉多', '柯基', '哈士奇'],
        colors: ['#8B4513', '#DEB887', '#F5DEB3', '#D2B48C', '#FFEBCD'],
        name: '忠诚小狗',
        description: '温馨的棕黄色调，如小狗般忠诚',
        category: 'animal'
    },
    
    butterfly: {
        keywords: ['蝴蝶', '蛾子', '翅膀', '飞舞', '花蝴蝶'],
        colors: ['#FF6347', '#FFD700', '#9370DB', '#00CED1', '#FF69B4'],
        name: '蝴蝶翩翩',
        description: '绚烂的彩色系，如蝴蝶般美丽',
        category: 'animal'
    },
    
    bird: {
        keywords: ['小鸟', '鸟儿', '鸟', '麻雀', '燕子', '鹦鹉', '孔雀', '天鹅'],
        colors: ['#4169E1', '#87CEEB', '#98FB98', '#F0E68C', '#FFB6C1'],
        name: '自由飞鸟',
        description: '清新的蓝绿色调，如鸟儿般自由',
        category: 'animal'
    },
    
    rabbit: {
        keywords: ['兔子', '小兔', '兔兔', '白兔', '灰兔'],
        colors: ['#FFB6C1', '#FFFFFF', '#F5F5F5', '#E6E6FA', '#FFEFD5'],
        name: '可爱兔子',
        description: '柔和的粉白色系，如兔子般可爱',
        category: 'animal'
    },
    
    panda: {
        keywords: ['熊猫', '大熊猫', '国宝', '黑白'],
        colors: ['#000000', '#FFFFFF', '#696969', '#D3D3D3', '#F5F5F5'],
        name: '熊猫经典',
        description: '经典的黑白配色，如熊猫般憨态可掬',
        category: 'animal'
    },
    
    // ===== 情感主题配色 =====
    happy: {
        keywords: ['快乐', '开心', '高兴', '愉快', '欢乐', '笑容', '微笑'],
        colors: ['#FF6B6B', '#4ECDC4', '#FFE66D', '#A8E6CF', '#FFB3BA'],
        name: '快乐心情',
        description: '明亮的暖色系，传递快乐与活力',
        category: 'emotion'
    },
    
    warm: {
        keywords: ['温暖', '舒适', '温馨', '暖和', '拥抱', '家'],
        colors: ['#FF7F50', '#FFA07A', '#FFEFD5', '#F4A460', '#FFCCCB'],
        name: '温暖怀抱',
        description: '温暖的橙色系，带来舒适感',
        category: 'emotion'
    },
    
    dreamy: {
        keywords: ['梦幻', '童话', '梦想', '仙女', '魔法', '神奇'],
        colors: ['#DDA0DD', '#F0E68C', '#E6E6FA', '#B19CD9', '#FFE4E1'],
        name: '梦幻童话',
        description: '柔和的紫色系，充满梦幻色彩',
        category: 'emotion'
    },
    
    energetic: {
        keywords: ['活力', '精力', '运动', '跳跃', '奔跑', '活泼'],
        colors: ['#FF4500', '#32CD32', '#FFD700', '#FF69B4', '#00BFFF'],
        name: '活力四射',
        description: '鲜艳的色彩组合，充满活力',
        category: 'emotion'
    },
    
    peaceful: {
        keywords: ['宁静', '平静', '安静', '祥和', '冥想', '放松'],
        colors: ['#B0E0E6', '#E0FFFF', '#F0F8FF', '#E6E6FA', '#F5FFFA'],
        name: '宁静致远',
        description: '清淡的冷色系，带来宁静感',
        category: 'emotion'
    },
    
    cute: {
        keywords: ['可爱', '萌', '甜美', '小巧', '娇小', '软萌'],
        colors: ['#FFB6C1', '#FFCCCB', '#F0E68C', '#E0FFFF', '#FFEFD5'],
        name: '萌萌可爱',
        description: '粉嫩的色彩搭配，超级可爱',
        category: 'emotion'
    }
};

// 导出配色库
if (typeof module !== 'undefined' && module.exports) {
    module.exports = COLOR_SCHEMES;
} else {
    window.COLOR_SCHEMES = COLOR_SCHEMES;
}
