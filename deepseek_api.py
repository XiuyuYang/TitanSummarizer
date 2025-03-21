DEEPSEEK_API_KEY = "sk-46666666666666666666666666666666"

import requests
import json
import time
import random

class DeepSeekAPI:
    def __init__(self, api_key=None, use_mock=True):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.api_base = "https://api.deepseek.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.use_mock = use_mock
        if self.use_mock:
            print("注意: 使用模拟API模式，非实际API调用")
    
    def summarize_text(self, text, max_length=None, temperature=0.7):
        """
        使用DeepSeek API对文本进行缩写/摘要
        
        参数:
            text (str): 需要缩写的文本
            max_length (int, optional): 摘要的最大长度，默认None
            temperature (float, optional): 生成随机性，数值越大随机性越高，默认0.7
            
        返回:
            str: 缩写后的文本
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
            print(f"API请求错误: {e}")
            # 如果API请求失败，切换到模拟模式
            print("API调用失败，切换到模拟模式")
            return self._mock_summarize(text, max_length)
    
    def _mock_summarize(self, text, max_length=None):
        """模拟API摘要功能，用于测试"""
        print("注意: 使用模拟API模式，非实际API调用")
        
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
        """中国是世界上最大的发展中国家，拥有超过14亿人口。自1978年改革开放以来，中国经济快速发展，现已成为世界第二大经济体。中国有着悠久的历史和灿烂的文化，是四大文明古国之一。北京是中国的首都，上海是其最大的城市和金融中心。中国地形多样，包括山脉、高原、盆地和平原等。中国是联合国安理会五个常任理事国之一，在全球事务中扮演着越来越重要的角色。""",

        """用最简单的中文语言缩写，不超过200字：

二愣子睁大着双眼，直直望着茅草和烂泥糊成的黑屋顶，身上盖着的旧棉被，已呈深黄色，看不出原来的本来面目，还若有若无的散发着淡淡的霉味。

在他身边紧挨着的另一人，是二哥韩铸，酣睡的十分香甜，从他身上不时传来轻重不一的阵阵打呼声。

离床大约半丈远的地方，是一堵黄泥糊成的土墙，因为时间过久，墙壁上裂开了几丝不起眼的细长口子，从这些裂纹中，隐隐约约的传来韩母唠唠叨叨的埋怨声，偶尔还掺杂着韩父，抽旱烟杆的"啪嗒""啪嗒"吸吮声。

二愣子缓缓的闭上已有些发涩的双目，迫使自己尽早进入深深的睡梦中。他心里非常清楚，再不老实入睡的话，明天就无法早起了，也就无法和其他约好的同伴一起进山拣干柴。

二愣子姓韩名立，这么像模像样的名字，他父母可取不出来，这是他父亲用两个粗粮制成的窝头，求村里老张叔给取的名字。

老张叔年轻时，曾经跟城里的有钱人当过几年的伴读书童，是村里唯一认识几个字的读书人，村里小孩子的名字，倒有一多半是他给取的。

韩立被村里人叫作"二愣子"，可人并不是真愣真傻，反而是村中首屈一指的聪明孩子，但就像其他村中的孩子一样，除了家里人外，他就很少听到有人正式叫他名字"韩立"，倒是"二愣子""二愣子"的称呼一直伴随至今。

而之所以被人起了个"二愣子"的绰号，也只不过是因为村里已有一个叫"愣子"的孩子了。

这也没啥，村里的其他孩子也是"狗娃""二蛋"之类的被人一直称呼着，这些名字也不见得比"二愣子"好听到哪里去。

因此，韩立虽然并不喜欢这个称呼，但也只能这样一直的自我安慰着。

韩立外表长得很不起眼，皮肤黑黑的，就是一个普通的农家小孩模样。但他的内心深处，却比同龄人早熟了许多，他从小就向往外面世界的富饶繁华，梦想有一天，他能走出这个巴掌大的村子，去看看老张叔经常所说的外面世界。

当然韩立的这个想法，一直没敢和其他人说起过。否则，一定会使村里人感到愕然，一个乳臭未干的小屁孩，竟然会有这么一个大人也不敢轻易想的念头。要知道，其他同韩立差不多大的小孩，都还只会满村的追鸡摸狗，更别说会有离开故土这么一个古怪的念头。

韩立一家七口人，有两个兄长，一个姐姐，还有一个小妹，他在家里排行老四，今年刚十岁，家里的生活很清苦，一年也吃不上几顿带荤腥的饭菜，全家人一直在温饱线上徘徊着。

此时的韩立，正处于迷迷糊糊、似睡未睡之间，脑中还一直残留着这样的念头：上山时，一定要帮他最疼爱的妹妹，多拣些她最喜欢吃的红浆果。

第二天中午时分，当韩立顶着火辣辣的太阳，背着半人高的木柴堆，怀里还揣着满满一布袋浆果，从山里往家里赶的时侯，并不知道家中已经来了一位，会改变他一生命运的客人。

这位贵客，是跟他血缘很近的一位至亲-他的亲三叔。

听说，在附近一个小城的酒楼，给人当大掌柜，是他父母口中的大能人。韩家近百年来，可能就出了三叔这么一位有点身份的亲戚。

韩立只在很小的时侯，见过这位三叔几次。他大哥在城里给一位老铁匠当学徒的工作，就是这位三叔给介绍的，这位三叔还经常托人给他父母捎带一些吃的、用的东西，很是照顾他们一家，因此韩立对这位三叔的印像也很好，知道父母虽然嘴里不说，心里也是很感激的。

大哥可是一家人的骄傲，听说当铁匠的学徒，不但管吃管住，一个月还有三十个铜板拿，等到正式出师被人雇用时，挣的钱可就更多了。

每当父母一提起大哥，就神采飞扬，像换了一个人一样。韩立年龄虽小，也羡慕不已，心目中最好的工作也早早就有了，就是被小城里的哪位手艺师傅看上，收做学徒，从此变成靠手艺吃饭的体面人。

所以当韩立见到穿着一身崭新的缎子衣服，胖胖的圆脸，留着一撮小胡子的三叔时，心里兴奋极了。

把木柴在屋后放好后，便到前屋腼腆的给三叔见了个礼，乖乖的叫了声："三叔好"，就老老实实的站在一边，听父母同三叔聊天。

三叔笑眯眯的望着韩立，打量着他一番，嘴里夸了他几句"听话""懂事"之类的话，然后就转过头，和他父母说起这次的来意。

韩立虽然年龄尚小，不能完全听懂三叔的话，但也听明白了大概的意思。

原来三叔工作的酒楼，属于一个叫"七玄门"的江湖门派所有，这个门派有外门和内门之分，而前不久，三叔才正式成为了这个门派的外门弟子，能够举荐7岁到12岁的孩童去参加七玄门招收内门弟子的考验。

五年一次的"七玄门"招收内门弟子测试，下个月就要开始了。这位有着几分精明且自己尚无子女的三叔，自然想到了适龄的韩立。

一向老实巴交的韩父，听到"江湖""门派"之类从未听闻过的话，心里有些犹豫不决拿不定主意，便一把拿起旱烟杆，"吧嗒""吧嗒"的狠狠抽了几口，就坐在那里，一声不吭。

在三叔嘴里，"七玄门"自然是这方圆数百里内，了不起的、数一数二的大门派。

只要成为内门弟子，不但以后可以免费习武吃喝不愁，每月还能有一两多散银的零花钱。而且参加考验的人，即使未能入选也有机会成为像三叔一样的外门人员，专门替"七玄门"打理门外的生意。

当听到有可能每月有一两银子可拿，还有机会成为和三叔一样的体面人，韩父终于拿定了主意，答应了下来。

三叔见到韩父应承了下来，心里很是高兴。又留下几两银子，说一个月后就来带韩立走，在这期间给韩立多做点好吃的，给他补补身子，好应付考验。随后三叔和韩父打声招呼，摸了摸韩立的头，出门回城了。

韩立虽然不全明白三叔所说的话，但可以进城挣大钱还是明白的。

一直以来的愿望，眼看就有可能实现，他一连好几个晚上兴奋得睡不着觉。

三叔在一个多月后，准时的来到村中，要带韩立走了。临走前韩父反复嘱咐韩立，做人要老实，遇事要忍让，别和其他人起争执，而韩母则要他多注意身体，要吃好睡好。

在马车上，看着父母渐渐远去的身影，韩立咬紧了嘴唇，强忍着不让自己眼眶中的泪珠流出来。

他虽然从小就比其他孩子成熟得多，但毕竟还是个十岁的小孩，第一次出远门让他的心里有点伤感和彷徨。他年幼的心里暗暗下定了决心，等挣到了大钱就马上赶回来，和父母再也不分开。

韩立从未想到，此次出去后钱财的多少对他已失去了意义，他竟然走上了一条与凡人不同的仙业大道，走出了自己的修仙之路。"""
    ]
    
    print("===== DeepSeek API 文本缩写测试 =====")
    for i, text in enumerate(test_texts, 1):
        print(f"\n测试 {i}:")
        print(f"原文 ({len(text)}字符):\n{text}\n")
        
        # 获取缩写结果
        start_time = time.time()
        summary = api.summarize_text(text,max_length=200)
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
   

