# 根目录的app.py - 用于Render部署
# 这个文件导入backend目录中的真正应用

import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# 导入真正的Flask应用
from app import app

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
