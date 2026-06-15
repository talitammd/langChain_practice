import tiktoken  # pyright: ignore[reportMissingImports]
import math, random

# 示例 1：用 tiktoken 看清 token 切分与计数
# 取gpt4系列使用的编码器
enc = tiktoken.get_encoding("cl100k_base")

samples = [
    "Machine learning is a branch of artificial intelligence",
    "机器学习是人工智能的一个分支",
]
for text in samples:
    tokens = enc.encode(text)
    pieces = [enc.decode([t]) for t in tokens]
    print(f"{text!r:35} → {len(tokens)} tokens | 切分: {pieces}")

# 观察：中文 token 往往比同义英文更多，符号/数字常单独成 token
# 'Machine learning is a branch of artificial intelligence' → 8 tokens | 切分: ['Machine', ' learning', ' is', ' a',' branch', ' of', ' artificial', ' intelligence']
# '机器学习是人工智能的一个分支'                    → 15 tokens | 切分: ['机', '器', '学', '�', '�', '是', '人', '工', '�', '�', '能', '的', '一个', '分', '支']

# 模型对下一个token的原始打分
logits = {"好": 3.5, "热": 2, "冷": 1.2, "棒": 0.2}

def softmax_with_temperature(logits, temp):
    # 温度缩放后的概率分布，temp越大分布越平，越随机
    scaled = {key: logit / temp for key, logit in logits.items()}
    mx = max(scaled.values())
    exp = {key: math.exp(logit - mx) for key, logit in logits.items()}
    s = sum(exp.values())
    return {key: round(logit / s, 3) for key, logit in logits.items()}
for t in [0.2, 1.0, 2.0]:
    print(f"temperature={t}: {softmax_with_temperature(logits, t)}")
# 低温：'好' 概率接近 1（确定）；高温：各 token 概率被拉平（随机）


# Top-p截断逻辑
def top_p_filter(probs, p):
    """保留累计概率刚好达到 p 的最小候选集合"""
    ordered = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    kept, cum = {}, 0.0
    for token, prob in ordered:
        kept[token] = prob
        cum += prob
        if cum > p:
            break
    return kept


dist = {"好": 0.4, "热": 0.3, "冷": 0.2, "棒": 0.1}
print("Top-p=0.7 →", top_p_filter(dist, 0.7))  # {'好':0.4,'热':0.3}

# Top-k截断逻辑：保留前 k 个的概率 + 把其他词的概率设为 0 + 重新归一化（让 k 个词概率之和为 1）
def top_k_filter(probs, k):
    ordered = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    topk = ordered[:k]
    sum_value = sum([p for _, p in topk])
    return {
        w : p / sum_value if index < k else 0 for index, (w, p) in enumerate(ordered)
    }


print(top_k_filter(dist, 2))

print("Top-k=2 →", top_k_filter(dist, 2))  
# 调用真实 API 时的参数设置（工程片段）
# 让 Agent 做"工具决策/结构化输出"时，降低随机性以保证可解析、可复现
# resp = client.chat.completions.create(
#     model="gpt-4o-mini",
#     messages=[{"role": "user", "content": "把这句话的情感分类为 正面/负面/中性"}],
#     temperature=0,  # 决策类任务：调到最低
#     top_p=1,
#     max_tokens=10,  # 限制输出长度，省钱省延迟
# )
