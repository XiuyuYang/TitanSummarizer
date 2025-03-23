@echo off
echo 运行Titan摘要器单元测试...
python -m tests.run_tests --skip-modules test_deepseek_api.py,test_deepseek_summarizer.py
pause 