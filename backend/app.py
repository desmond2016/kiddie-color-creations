# -*- coding: utf-8 -*-
import os
import json
import requests # 使用 requests 库发送 HTTP 请求，通常比 http.client 更方便
import re # 导入正则表达式库
from flask import Flask, request, jsonify
from flask_cors import CORS # 用于处理跨域请求
from dotenv import load_dotenv # 导入 load_dotenv

load_dotenv() # 在访问环境变量之前加载 .env 文件

# --- 配置 ---
# 现在 os.getenv 会优先读取 .env 文件中设置的值
API_ENDPOINT = os.getenv("IMAGE_API_ENDPOINT", "https://api.gptgod.online/v1/chat/completions")
API_KEY = os.getenv("IMAGE_API_KEY") # 如果 .env 中没有设置，这里会是 None

# --- Flask 应用设置 ---
app = Flask(__name__)
CORS(app) # 允许所有来源的跨域请求，在生产环境中可能需要更严格的配置

# --- API 路由 ---
@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    """
    接收前端的 prompt，调用外部 API 生成图片，并返回图片 URL。
    """
    try:
        # 1. 从请求中获取 JSON 数据
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"error": "请求体缺少 'prompt' 字段"}), 400 # Bad Request

        user_prompt = data['prompt']
        if not user_prompt:
             return jsonify({"error": "'prompt' 不能为空"}), 400 # Bad Request

        print(f"收到生成请求，提示词: {user_prompt}") # 在后端日志中打印提示词

        # 2. 准备调用外部 API 的数据 (payload) 和请求头 (headers)
        payload = {
           "stream": False, # !! 保持 False 以获取完整响应
           "model": "gpt-4o-image-vip", # 使用你指定的模型
           "messages": [
              {
                 # 优化提示词，明确要求线条画 (可以根据需要调整)
                 "content": f"Create a simple black and white line drawing coloring page suitable for children, depicting: {user_prompt}",
                 "role": "user"
              }
           ]
        }
        headers = {
           'Content-Type': 'application/json'
        }
        # 如果需要 API 密钥，添加到请求头
        if API_KEY:
            # !! 根据你的 API 提供商要求调整认证方式，可能是 Bearer Token，也可能是其他 Header
            headers['Authorization'] = f'Bearer {API_KEY}'
            # 或者 headers['X-Api-Key'] = API_KEY 等

        # 3. 调用外部图像生成 API
        print(f"正在调用外部 API: {API_ENDPOINT}")
        response = requests.post(API_ENDPOINT, headers=headers, json=payload, timeout=90) # 增加超时时间到 90 秒，图像生成可能较慢
        response.raise_for_status() # 如果请求失败 (状态码 4xx 或 5xx)，会抛出 HTTPError 异常

        # 4. 解析外部 API 的响应
        api_response_data = response.json()
        print(f"收到外部 API 响应: {json.dumps(api_response_data, indent=2, ensure_ascii=False)}") # 打印完整的 API 响应，方便调试

        # --- !!! 关键：提取图片 URL (更新逻辑) !!! ---
        image_url = None
        try:
            if 'choices' in api_response_data and len(api_response_data['choices']) > 0:
                message_content = api_response_data['choices'][0].get('message', {}).get('content')
                if message_content and isinstance(message_content, str):
                    # 使用正则表达式查找 Markdown 图片链接 ![...](...)
                    # 匹配括号内的 URL 部分
                    match = re.search(r'!\[.*?\]\((.*?)\)', message_content)
                    if match:
                        # 提取匹配到的第一个括号里的内容，即 URL
                        image_url = match.group(1)
                        print(f"通过正则表达式找到图片 URL: {image_url}")
                    else:
                        # 如果正则没匹配到，可以尝试查找下载链接作为备选
                         match_download = re.search(r'\[.*?下载.*?\]\((.*?)\)', message_content, re.IGNORECASE)
                         if match_download:
                              image_url = match_download.group(1).replace('/download/', '/cdn/') # 尝试将下载链接转为可能的 cdn 链接
                              print(f"通过下载链接找到备选 URL: {image_url}")
                         else:
                              # 作为最后的尝试，检查 content 本身是否就是一个 URL
                              if message_content.startswith('http'):
                                   image_url = message_content
                                   print(f"将 content 作为 URL: {image_url}")


            # 如果仍然没有找到 URL
            if not image_url:
                 raise ValueError("未能从 API 响应的 content 字段中提取有效的图片 URL (Markdown 格式或其他)")

        except (KeyError, IndexError, TypeError, ValueError) as e:
            print(f"解析 API 响应失败: {e}")
            # 注意：这里不再打印完整响应，因为上面已经打印过了
            return jsonify({"error": f"无法解析图像生成服务的响应格式: {e}"}), 500 # Internal Server Error

        print(f"成功提取图片 URL: {image_url}")

        # 5. 将图片 URL 返回给前端
        return jsonify({"imageUrl": image_url})

    except requests.exceptions.Timeout:
        print("调用外部 API 超时")
        return jsonify({"error": "图像生成服务响应超时"}), 504 # Gateway Timeout
    except requests.exceptions.RequestException as e:
        # 处理网络请求错误 (例如连接超时、DNS错误)
        print(f"调用外部 API 时发生网络错误: {e}")
        return jsonify({"error": f"无法连接图像生成服务: {e}"}), 503 # Service Unavailable
    except json.JSONDecodeError:
        # 处理无法解析 JSON 的情况
        print(f"无法解析外部 API 的响应 (非 JSON): {response.text}")
        return jsonify({"error": "图像生成服务返回了无效的响应"}), 500
    except Exception as e:
        # 处理其他意外错误
        print(f"处理请求时发生未知错误: {e}")
        import traceback
        traceback.print_exc() # 打印详细的错误堆栈
        return jsonify({"error": "服务器内部错误"}), 500 # Internal Server Error

# --- 启动服务器 ---
if __name__ == '__main__':
    # 使用 Waitress 作为生产环境的 WSGI 服务器，比 Flask 自带的开发服务器更稳定
    # 或者使用 Gunicorn: gunicorn -w 4 app:app
    # 这里为了简单，仍然使用 Flask 开发服务器，但建议生产环境更换
    print("启动 Flask 开发服务器...")
    # 注意：在 VS Code 中直接运行 Python 文件时，它可能不会自动重新加载 .env 文件，
    # 如果修改了 .env，最好停止服务器 (Ctrl+C) 再重新运行。
    app.run(debug=True, host='0.0.0.0', port=5000) # debug=True 方便开发调试，生产环境应设为 False
    # host='0.0.0.0' 允许从外部访问，port=5000 是常用的开发端口

