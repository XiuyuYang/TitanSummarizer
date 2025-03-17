import time
from transformers import AutoTokenizer, AutoModelForCausalLM

# GPU
import torch
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"使用设备: {device}")

# 加载预训练的模型和分词器
model_name = 'deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B'
# model_name = 'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B'
tokenizer = AutoTokenizer.from_pretrained(model_name)

model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True, device_map="auto", torch_dtype=torch.bfloat16, attn_implementation='eager', offload_folder="save_folder")

# 示例中文文本
text = """二愣子睁大着双眼，直直望着茅草和烂泥糊成的黑屋顶，身上盖着的旧棉被，已呈深黄色，看不出原来的本来面目，还若有若无的散发着淡淡的霉味。

在他身边紧挨着的另一人，是二哥韩铸，酣睡的十分香甜，从他身上不时传来轻重不一的阵阵打呼声。

离床大约半丈远的地方，是一堵黄泥糊成的土墙，因为时间过久，墙壁上裂开了几丝不起眼的细长口子，从这些裂纹中，隐隐约约的传来韩母唠唠叨叨的埋怨声，偶尔还掺杂着韩父，抽旱烟杆的"啪嗒""啪嗒"吸吮声。

"""

# 添加任务前缀
input_text = "Human: 请将以下文本总结到100字：\n" + text

# input_text = "你好，你叫什么？回答尽量简短"

# 使用分词器将文本编码为模型输入
input_ids = tokenizer(input_text, return_tensors="pt", max_length=2048, truncation=True).input_ids.to(device)

time_start = time.time()
# 生成摘要
with torch.no_grad():
    outputs = model.generate(
        input_ids,
        max_length=2048,
        num_beams=4,
        length_penalty=2.0,
        early_stopping=True,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=False,
        temperature=0.5,
        top_p=0.9,
    )

# 解码生成的摘要
summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(summary)
time_end = time.time()
print(f"生成时间: {time_end - time_start} 秒")