import os
import re
import logging
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class NovelSummarizer:
    def __init__(self):
        logging.info("初始化生成式摘要器")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logging.info(f"使用设备: {self.device}")
        
        if self.device == "cuda":
            torch.cuda.empty_cache()
        
        model_name = "ClueAI/ChatYuan-large-v2"
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True,
            legacy=False  # 避免legacy警告
        )
        
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            low_cpu_mem_usage=True,
            trust_remote_code=True
        ).to(self.device)
        
        self.pipeline = pipeline(
            "summarization",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if self.device == "cuda" else -1,
            trust_remote_code=True
        )
        logging.info("模型加载成功")

    def preprocess_text(self, text):
        text = re.sub(r'\s+', '', text)
        text = re.sub(r'([。！？])', r'\1\n', text)
        return text.strip()

    def postprocess_text(self, text):
        text = re.sub(r'\s+', '', text)
        text = re.sub(r'([。！？])', r'\1\n', text)
        text = re.sub(r'([，、：；])', r'\1 ', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r' +\n', '\n', text)
        text = re.sub(r'\n+', '\n', text)
        
        if not text.endswith(('。', '！', '？')):
            last_sentence_end = max(text.rfind('。'), text.rfind('！'), text.rfind('？'))
            text = text[:last_sentence_end + 1] if last_sentence_end > 0 else text + '。'
            
        return text.strip()

    def split_text(self, text, max_length=1024):  # 减小分块大小
        sentences = re.split('([。！？])', text)
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences)-1, 2):
            sentence = sentences[i] + sentences[i+1]
            if len(current_chunk) + len(sentence) <= max_length:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
            
        logging.info(f"文本被分割为 {len(chunks)} 个块")
        return chunks

    def generate_summary(self, text):
        text = self.preprocess_text(text)
        chunks = self.split_text(text)
        summaries = []
        
        target_length = 200  # 目标摘要长度
        
        for i, chunk in enumerate(chunks, 1):
            logging.info(f"正在处理第 {i}/{len(chunks)} 个文本块")
            try:
                # 根据目标长度动态调整每个块的摘要长度
                chunk_target_length = target_length // len(chunks)
                max_length = min(chunk_target_length + 50, len(chunk))  # 允许一定的浮动空间
                min_length = max(chunk_target_length - 50, 30)  # 确保最小长度不会太短
                
                summary = self.pipeline(
                    chunk,
                    max_length=max_length,
                    min_length=min_length,
                    do_sample=True,
                    num_beams=4,
                    temperature=0.7,  # 降低随机性
                    top_k=30,
                    top_p=0.9,
                    repetition_penalty=1.2,
                    no_repeat_ngram_size=2,
                    early_stopping=True
                )[0]['summary_text']
                
                if summary:
                    summaries.append(summary)
                
            except Exception as e:
                logging.error(f"生成摘要时出错: {str(e)}")
                continue
        
        if not summaries:
            return "《小说摘要》\n\n无法生成摘要。"
            
        final_summary = "《小说摘要》\n\n"
        combined_summary = self.postprocess_text("。".join(summaries))
        
        # 如果摘要太长，进行截断
        if len(combined_summary) > target_length:
            sentences = re.split('([。！？])', combined_summary)
            truncated_summary = ""
            for i in range(0, len(sentences)-1, 2):
                if len(truncated_summary) + len(sentences[i] + sentences[i+1]) <= target_length:
                    truncated_summary += sentences[i] + sentences[i+1]
                else:
                    break
            final_summary += truncated_summary
        else:
            final_summary += combined_summary
            
        return final_summary

def main():
    print("开始生成摘要...\n")
    
    test_texts = [
        """二愣子睁大着双眼，直直望着茅草和烂泥糊成的黑屋顶，身上盖着的旧棉被，已呈深黄色，看不出原来的本来面目，还若有若无的散发着淡淡的霉味。在他身边紧挨着的另一人，是二哥韩铸，酣睡的十分香甜，从他身上不时传来轻重不一的阵阵打呼声。离床大约半丈远的地方，是一堵黄泥糊成的土墙，因为时间过久，墙壁上裂开了几丝不起眼的细长口子，从这些裂纹中，隐隐约约的传来韩母唠唠叨叨的埋怨声，偶尔还掺杂着韩父，抽旱烟杆的"啪嗒""啪嗒"吸吮声。二愣子姓韩名立，这么像模像样的名字，他父母可取不出来，这是他父亲用两个粗粮制成的窝头，求村里老张叔给取的名字。老张叔年轻时，曾经跟城里的有钱人当过几年的伴读书童，是村里唯一认识几个字的读书人，村里小孩子的名字，倒有一多半是他给取的。韩立被村里人叫作"二愣子"，可人并不是真愣真傻，反而是村中首屈一指的聪明孩子，但就像其他村中的孩子一样，除了家里人外，他就很少听到有人正式叫他名字"韩立"，倒是"二愣子""二愣子"的称呼一直伴随至今。而之所以被人起了个"二愣子"的绰号，也只不过是因为村里已有一个叫"愣子"的孩子了。这也没啥，村里的其他孩子也是"狗娃""二蛋"之类的被人一直称呼着，这些名字也不见得比"二愣子"好听到哪里去。因此，韩立虽然并不喜欢这个称呼，但也只能这样一直的自我安慰着。""",
        """韩立出身于青牛镇的一个普通的农民家庭，父母都是老实巴交的农民。虽然他生性聪慧，但天资仅仅比普通人好上一点，算不上特别出众的人。在修仙之前，他是镇里有名的"二愣子"，这个称号源于他总是独来独往，不爱与人交际。韩立从小就对医术表现出浓厚的兴趣，经常帮助镇上的人采药。而他的梦想是成为一名医生，用自己的医术帮助更多的人。知道他的家境虽然不富裕，但父母也很支持他学医的想法。而直到有一天，他的叔叔从外地回来，告诉了他一个惊人的消息。"""
    ]
    
    summarizer = NovelSummarizer()
    
    for i, text in enumerate(test_texts, 1):
        print(f"=== 测试文本{i} ===")
        summary = summarizer.generate_summary(text)
        print(summary + "\n")

if __name__ == "__main__":
    main()