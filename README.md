# Qwen 2 模型测试工具

这个Python脚本用于通过Ollama运行本地的Qwen 2 0.5B模型并进行测试。

## 前提条件

1. 安装Ollama：
   - 从[Ollama官网](https://ollama.ai/download)下载并安装Ollama

2. 安装Python依赖：
   ```
   pip install requests
   ```

3. 确保模型文件存在于指定路径：
   ```
   D:\Work\AI_Models\Qwen\Qwen2-0.5B-Instruct-GGUF\qwen2-0_5b-instruct-q4_k_m.gguf
   ```

## 使用方法

1. 运行Python脚本：
   ```
   python run_qwen_with_ollama.py
   ```

2. 脚本会自动执行以下操作：
   - 检查Ollama服务是否运行，如果没有会尝试启动
   - 创建名为"qwen2-0.5b"的模型（如果不存在）
   - 向模型发送测试提示并显示返回的结果

## 注意事项

- 脚本会自动创建一个名为"Modelfile"的临时文件
- 确保Ollama可执行文件在系统PATH中
- 如果Ollama服务无法启动，请确保已正确安装Ollama并手动启动服务后再运行脚本
- 修改脚本中的MODEL_PATH变量如果模型文件位置不同 