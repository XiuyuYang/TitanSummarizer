import os
import subprocess
import requests
import json
import time

# Ollama模型名称（用于引用本地模型）
MODEL_NAME = "qwen2-0.5b"
# 本地模型文件路径
MODEL_PATH = r"D:\Work\AI_Models\Qwen\Qwen2-0.5B-Instruct-GGUF\qwen2-0_5b-instruct-q4_k_m.gguf"

def check_ollama_running():
    """检查Ollama服务是否正在运行"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def start_ollama():
    """启动Ollama服务"""
    print("正在启动Ollama服务...")
    # 非阻塞方式启动Ollama，使用UTF-8编码
    subprocess.Popen(["ollama", "serve"], 
                    shell=True, 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    errors='replace')
    
    # 等待服务启动
    attempts = 0
    while attempts < 10:
        if check_ollama_running():
            print("Ollama服务已启动")
            return True
        print("等待Ollama服务启动...")
        time.sleep(2)
        attempts += 1
    
    print("无法启动Ollama服务")
    return False

def load_local_model():
    """加载本地GGUF模型到Ollama"""
    # 检查模型是否已加载
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            if any(model["name"] == MODEL_NAME for model in models):
                print(f"模型 {MODEL_NAME} 已加载到Ollama中")
                return True
    except Exception as e:
        print(f"检查模型时出错: {e}")
        return False
    
    # 创建Modelfile（Ollama需要这个文件来知道如何加载本地模型）
    modelfile_content = f"""
FROM {MODEL_PATH}
PARAMETER temperature 0.7
PARAMETER top_k 40
PARAMETER top_p 0.9
PARAMETER num_ctx 2048
"""
    
    print("准备加载本地模型，配置如下:")
    print(modelfile_content)
    
    with open("Modelfile", "w") as f:
        f.write(modelfile_content)
    
    # 告诉Ollama加载本地模型文件，使用UTF-8编码并替换无法解码的字符
    print(f"正在将本地模型加载到Ollama，模型名称: {MODEL_NAME}...")
    result = subprocess.run(["ollama", "create", MODEL_NAME, "-f", "Modelfile"], 
                          shell=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE,
                          encoding='utf-8',
                          errors='replace',
                          text=True)
    
    # 打印加载过程的输出
    print("加载模型输出:")
    print(result.stdout)
    
    if result.stderr:
        print("加载过程中的错误:")
        print(result.stderr)
    
    # 等待一下让模型加载完成
    time.sleep(3)
    
    # 尝试进行一个简单的测试查询来验证模型
    try:
        print(f"验证模型 {MODEL_NAME} 是否可用...")
        headers = {"Content-Type": "application/json"}
        data = {"model": MODEL_NAME, "prompt": "Hello", "stream": False}
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            headers=headers,
            data=json.dumps(data)
        )
        
        if response.status_code == 200:
            print(f"本地模型 {MODEL_NAME} 已成功加载到Ollama并可用")
            return True
        else:
            print(f"模型验证失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"验证模型时出错: {e}")
    
    # 再次检查模型是否存在
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            if any(model["name"] == MODEL_NAME for model in models):
                print(f"模型 {MODEL_NAME} 已在Ollama列表中但可能不可用")
                return True
    except Exception as e:
        print(f"再次检查模型时出错: {e}")
    
    print(f"无法加载本地模型 {MODEL_NAME}")
    return False

def test_model():
    """测试Qwen模型"""
    print("\n正在测试模型...")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    prompt = "太阳温度是多少？"
    
    data = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post("http://localhost:11434/api/generate", 
                                headers=headers, 
                                data=json.dumps(data))
        
        if response.status_code == 200:
            result = response.json()
            print("\n提问:", prompt)
            print("\n回答:", result["response"])
            return True
        else:
            print(f"请求失败: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"测试模型时出错: {e}")
        return False

def main():
    """主函数"""
    print("开始运行本地Qwen 0.5B模型测试")
    
    # 检查Ollama是否正在运行
    if not check_ollama_running():
        if not start_ollama():
            print("无法启动Ollama服务，退出程序")
            return
    else:
        print("Ollama服务已在运行")
    
    # 等待Ollama完全启动
    time.sleep(3)
    
    # 加载本地模型
    if not load_local_model():
        print("加载本地模型失败，退出程序")
        return
    
    # 测试模型
    test_model()
    
    print("\n测试完成")

if __name__ == "__main__":
    main() 