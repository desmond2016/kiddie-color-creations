# -*- coding: utf-8 -*-
import os
import json
import requests # 使用 requests 库发送 HTTP 请求
import re # 导入正则表达式库
from flask import Flask, request, jsonify
from flask_cors import CORS # 用于处理跨域请求
from dotenv import load_dotenv # 导入 load_dotenv
import traceback # 用于打印完整的错误追踪信息

load_dotenv() # 在访问环境变量之前加载 .env 文件

# --- 配置 ---
API_ENDPOINT = os.getenv("IMAGE_API_ENDPOINT","https://api.gptgod.online/v1/chat/completions")
API_KEY = os.getenv("IMAGE_API_KEY") # 从环境变量获取 API 密钥

# --- Flask 应用设置 ---
app = Flask(__name__)
CORS(app) # 允许所有来源的跨域请求，生产环境中建议配置具体的来源

# --- API 路由 ---
@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    """
    接收前端的 prompt，调用外部 API 生成图片，并返回图片 URL。
    如果外部 API 返回多个图片，此函数设计为提取并返回第一个符合条件的图片 URL。
    """
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            print("错误: 请求体缺少 'prompt' 字段")
            return jsonify({"error": "请求体缺少 'prompt' 字段"}), 400

        user_prompt = data['prompt']
        if not user_prompt:
            print("错误: 'prompt' 不能为空")
            return jsonify({"error": "'prompt' 不能为空"}), 400

        print(f"收到生成请求，提示词: {user_prompt}")

        payload = {
           "stream": False,
           "model": "gpt-4o-image-vip", # 确保这个模型名称是您 API 支持的
           "messages": [
              {
                 "content": f"Create a simple black and white line drawing coloring page suitable for children, depicting: {user_prompt}",
                 "role": "user"
              }
           ]
        }
        headers = {
           'Content-Type': 'application/json'
        }

        if API_KEY:
            # 确保这是 api.gptgod.online 期望的认证方式
            headers['Authorization'] = f'Bearer {API_KEY}'
            print(f"已设置 Authorization Header (使用 Bearer Token 方式)")
        else:
            print("警告: IMAGE_API_KEY 未设置，将尝试无认证调用外部 API")


        print(f"准备调用外部 API: {API_ENDPOINT.strip()}") # 使用 .strip() 确保 URL 没有多余空格
        print(f"请求头 (Headers): {json.dumps(headers)}")
        print(f"请求体 (Payload): {json.dumps(payload)}")

        # 调用外部图像生成 API，增加超时时间
        response = requests.post(API_ENDPOINT.strip(), headers=headers, json=payload, timeout=120) 

        print(f"外部 API 调用完成，状态码: {response.status_code}")
        # 打印部分相关的响应头
        relevant_headers = {k: v for k, v in response.headers.items() if k.lower() in ['content-type', 'content-length', 'date', 'server', 'x-request-id']}
        print(f"外部 API 响应头 (部分): {json.dumps(relevant_headers)}")
        
        try:
            # 尝试打印完整的JSON响应，如果太大，可以考虑截断或只打印关键部分
            print(f"外部 API 响应内容 (尝试解析为JSON): {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError:
            # 如果不是JSON，打印文本内容，增加打印长度以便调试
            print(f"外部 API 响应内容 (非JSON，前2000字符): {response.text[:2000]}")


        response.raise_for_status() # 如果状态码是 4xx 或 5xx，会抛出 HTTPError 异常

        api_response_data = response.json() # 假设成功时返回 JSON

        image_url = None
        if 'choices' in api_response_data and len(api_response_data['choices']) > 0:
            message_content = api_response_data['choices'][0].get('message', {}).get('content')
            if message_content and isinstance(message_content, str):
                # 修改点：优先尝试更精确的正则表达式来匹配期望的 CDN 图片链接 (Markdown格式)
                # 这个正则表达式会查找第一个形如 ![gen_...](https://filesystem.site/cdn/....png) 的链接
                # re.search 会找到第一个匹配项
                # 请根据您实际看到的 filesystem.site 链接格式调整此处的域名（如果不同）
                cdn_match = re.search(r'!\[gen_[^\]]*\]\((https://filesystem\.site/cdn/[^)]+\.png)\)', message_content)
                if cdn_match:
                    image_url = cdn_match.group(1)
                    print(f"通过 CDN 图片链接正则表达式找到图片 URL: {image_url}")
                else:
                    # 如果特定 CDN 链接未找到，回退到您原有的更通用的 Markdown 图片链接正则表达式
                    # 这仍然会找到第一个匹配的通用 Markdown 图片链接
                    print("未能通过特定 CDN 正则找到图片，尝试通用 Markdown 图片正则...")
                    generic_match = re.search(r'!\[.*?\]\((https://[^)]+\.png)\)', message_content) # 确保捕获的是 .png 链接
                    if generic_match:
                        image_url = generic_match.group(1)
                        print(f"通过通用 Markdown 图片链接正则表达式找到图片 URL: {image_url}")
                        # 可选：进一步检查此通用 URL 是否是我们期望的域名
                        if not image_url.startswith("https://filesystem.site"): # 再次确认域名
                            print(f"警告: 通用 Markdown 提取的 URL '{image_url}' 可能不是期望的 'filesystem.site' CDN 链接。")
                            # 如果您只想严格使用 filesystem.site 的链接，可以在这里将其设为 None
                            # image_url = None 

                # 如果上述 Markdown 方式都未提取到 URL，可以再尝试您原有的下载链接逻辑作为进一步的回退
                if not image_url:
                    print("未能通过 Markdown 图片正则找到图片，尝试下载链接正则...")
                    # 请根据您实际看到的 filesystem.site 链接格式调整此处的域名（如果不同）
                    download_match = re.search(r'\[.*?下载.*?\]\((https://filesystem\.site/download/[^)]+\.png)\)', message_content, re.IGNORECASE)
                    if download_match:
                        image_url = download_match.group(1).replace('/download/', '/cdn/') # 转换为 cdn 链接
                        print(f"通过下载链接找到并转换图片 URL: {image_url}")
                
                # 您原有的 message_content.startswith('http') 逻辑作为最后的手段可能过于宽泛，
                # 如果前面的正则都失败了，很可能 content 不是一个直接的图片 URL。
                # 如果需要，可以添加更严格的检查或完全移除这个最后的 fallback。

        if not image_url:
             # 如果在所有尝试后都没有找到 image_url，则抛出错误
             print("错误: 未能从 API 响应的 content 字段中提取有效的图片 URL")
             raise ValueError("未能从 API 响应的 content 字段中提取有效的图片 URL")

        print(f"成功提取并返回给前端的图片 URL: {image_url}") # 确认这是我们期望的单个 URL
        return jsonify({"imageUrl": image_url}) # 前端期望的 JSON 结构

    except requests.exceptions.Timeout:
        print("错误: 调用外部 API 超时")
        traceback.print_exc()
        return jsonify({"error": "图像生成服务响应超时"}), 504
    except requests.exceptions.HTTPError as http_err:
        print(f"错误: 外部 API 返回 HTTP 错误: {http_err}")
        error_details = "未知错误详情"
        status_code = 500 # 默认状态码
        if http_err.response is not None: # 检查 response 对象是否存在
            error_details = http_err.response.text[:1000] # 限制错误详情长度
            status_code = http_err.response.status_code
            print(f"错误时的外部 API 响应体 (前1000字符): {error_details}")
        traceback.print_exc()
        return jsonify({"error": f"图像生成服务返回错误: {status_code}", "details": error_details}), status_code
    except requests.exceptions.RequestException as req_err:
        print(f"错误: 调用外部 API 时发生网络错误: {req_err}")
        traceback.print_exc()
        return jsonify({"error": f"无法连接图像生成服务: {str(req_err)}"}), 503
    except json.JSONDecodeError as json_err:
        print(f"错误: 无法解析外部 API 的 JSON 响应: {json_err}")
        response_text_for_error = ""
        if 'response' in locals() and hasattr(response, 'text'): # 确保 response 变量存在且有 text 属性
             response_text_for_error = response.text
             print(f"无法解析的外部 API 响应体 (前1000字符): {response_text_for_error[:1000]}")
        traceback.print_exc()
        return jsonify({"error": "图像生成服务返回了无效的 JSON 响应", "raw_response_preview": response_text_for_error[:200]}), 500
    except ValueError as val_err: # 捕获我们自己抛出的 ValueError
        print(f"错误: {val_err}")
        traceback.print_exc()
        return jsonify({"error": str(val_err)}), 500
    except Exception as e:
        print(f"处理请求时发生未知错误: {e}")
        traceback.print_exc()
        return jsonify({"error": "服务器内部未知错误"}), 500

if __name__ == '__main__':
    print("启动 Flask 开发服务器...")
    # 对于 Render.com 等平台，端口通常由 PORT 环境变量指定
    # debug 模式也最好通过环境变量控制
    flask_debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    port = int(os.getenv("PORT", 5000))
    app.run(debug=flask_debug, host='0.0.0.0', port=port)
