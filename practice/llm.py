import tiktoken

# 取gpt4系列使用的编码器
enc = tiktoken.get_encoding('cl100k_base')

samples = ['hello world', '人工智能']
for text in samples:
    tokens = enc.encode(text)
    pieces = [enc.decode([t]) for t in tokens]
    print(f"{text!r:35} → {len(tokens)} tokens | 切分: {pieces}")