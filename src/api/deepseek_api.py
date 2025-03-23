#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DeepSeek API 客户端
用于与DeepSeek API进行交互，处理文本摘要和翻译请求
"""

import requests
import json
import time
import random
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 这里使用模拟的API密钥，生产环境应该使用环境变量或配置文件
DEEPSEEK_API_KEY = "sk-46666666666666666666666666666666"

class DeepSeekAPI:
    def __init__(self, api_key=None, use_mock=True):
        """
        初始化DeepSeekAPI客户端
        
        Args:
            api_key: API密钥，如未提供则使用默认值
            use_mock: 是否使用模拟模式（不实际调用API）
        """
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.api_base = "https://api.deepseek.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.use_mock = use_mock
        if self.use_mock:
            logger.info("使用模拟API模式，非实际API调用")
            print("注意: 使用模拟API模式，非实际API调用")
    
    def summarize_text(self, text, max_length=None, temperature=0.7):
        """
        使用DeepSeek API对文本进行缩写/摘要
        
        Args:
            text: 需要缩写的文本
            max_length: 摘要的最大长度，默认None
            temperature: 生成随机性，数值越大随机性越高，默认0.7
            
        Returns:
            缩写后的文本
        """
        # 如果使用模拟模式，则不实际调用API
        if self.use_mock:
            return self._mock_summarize(text, max_length)
            
        url = f"{self.api_base}/chat/completions"
        
        # 构建提示词来指导模型进行文本缩写
        prompt = f"请将以下文本缩写为简洁的摘要，保留关键信息：\n\n{text}"
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        }
        
        if max_length:
            payload["max_tokens"] = max_length
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()  # 抛出HTTP错误
            
            result = response.json()
            summary = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return summary
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求错误: {e}")
            # 如果API请求失败，切换到模拟模式
            logger.warning("API调用失败，切换到模拟模式")
            print("API调用失败，切换到模拟模式")
            return self._mock_summarize(text, max_length)
    
    def _mock_summarize(self, text, max_length=None):
        """
        模拟API摘要功能，用于测试
        
        Args:
            text: 需要摘要的文本
            max_length: 摘要的最大长度
            
        Returns:
            模拟生成的摘要
        """
        logger.info("执行模拟摘要")
        
        # 简单的摘要模拟算法：提取第一句话，然后随机选择其他几个关键句子
        sentences = text.split('。')
        sentences = [s + '。' for s in sentences if s.strip()]
        
        if not sentences:
            return "无法生成摘要：文本格式不正确"
            
        # 始终包含第一句
        summary_sentences = [sentences[0]]
        
        # 计算要选择的句子数量 (大约是原文的20-30%)
        select_count = max(1, min(len(sentences) // 4, 3))
        
        # 如果原文够长，随机挑选其他句子
        if len(sentences) > 2:
            selected = random.sample(sentences[1:], min(select_count, len(sentences)-1))
            summary_sentences.extend(selected)
        
        # 确保句子顺序与原文一致
        summary_sentences.sort(key=lambda s: text.index(s))
        
        summary = ''.join(summary_sentences)
        
        # 如果指定了max_length并且超出限制，截断
        if max_length and len(summary) > max_length:
            summary = summary[:max_length] + "..."
            
        # 模拟API延迟
        time.sleep(1)
        
        return summary

def test_summarize():
    """测试文本缩写功能"""
    # 使用模拟API进行测试
    api = DeepSeekAPI(use_mock=True)
    
    # 测试文本
    test_texts = [
        # 短文本
        "人工智能(AI)是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。人工智能是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的一门新的技术科学。",
        
        # 中等长度文本
        """中国是世界上最大的发展中国家，拥有超过14亿人口。自1978年改革开放以来，中国经济快速发展，现已成为世界第二大经济体。中国有着悠久的历史和灿烂的文化，是四大文明古国之一。北京是中国的首都，上海是其最大的城市和金融中心。中国地形多样，包括山脉、高原、盆地和平原等。中国是联合国安理会五个常任理事国之一，在全球事务中扮演着越来越重要的角色。"""
    ]
    
    print("===== DeepSeek API 文本缩写测试 =====")
    for i, text in enumerate(test_texts, 1):
        print(f"\n测试 {i}:")
        print(f"原文 ({len(text)}字符):\n{text}\n")
        
        # 获取缩写结果
        start_time = time.time()
        summary = api.summarize_text(text, max_length=200)
        end_time = time.time()
        
        if summary:
            print(f"缩写结果 ({len(summary)}字符):\n{summary}\n")
            print(f"处理时间: {end_time - start_time:.2f}秒")
            print(f"压缩率: {(len(summary) / len(text) * 100):.1f}%")
        else:
            print("缩写失败，请检查API密钥或网络连接")
        
        print("-" * 50)

if __name__ == "__main__":
    test_summarize() 