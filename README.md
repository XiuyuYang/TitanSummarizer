# 小说章节摘要工具

这是一个使用大型语言模型自动生成小说章节摘要的桌面应用程序，由 Allen Yang 开发。

## 功能特点

- 自动加载并解析小说章节
- 默认加载 novels 目录下的《凡人修仙传》
- 允许用户指定输入模型名称（支持 OpenRouter 上的各种模型）
- 精美的图形界面布局，符合直觉的操作
- 允许保存所有摘要到文件，以便下次自动载入

## 安装依赖

```
pip install -r requirements.txt
```

## 使用方法

```
python novel_summarizer.py
```

## 界面说明

- **顶部控制区域**：提供模型选择、摘要长度设置和文件操作按钮
- **左侧章节列表**：显示检测到的所有小说章节
- **右侧正文区域**：显示当前选中章节的内容
- **底部摘要区域**：显示/编辑当前章节的摘要，可点击"生成摘要"按钮自动生成

## 模型支持

默认使用 OpenRouter 提供的 Meta Llama 4 Maverick 模型。用户可以选择其他支持的模型，如：

- meta-llama/llama-4-maverick:free
- openai/gpt-4o-mini
- openai/gpt-4o

也可以在下拉框中输入其他 OpenRouter 支持的模型 ID。 