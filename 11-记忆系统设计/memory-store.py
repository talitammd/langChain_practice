import json
from datetime import datetime

class MemoryStore:
    def __init__(self):
        '''
        在内存里开辟了一个空列表 self.memories，用来存所有的记忆条目
        在真实生产中，这里会换成 Chroma、Pinecone 或 Milvus 等向量数据库。
        '''
        self.memories = []


    def add(self,content:str,memory_type:str="episodic",metadata:dict=None):
        '''
        写入一条记忆
        memory_type 把记忆分成了三类，这是模仿了人类认知心理学：
        Episodic（情景记忆）：具体的事件流。比如“用户昨天 debug 了一个 LangGraph 的报错”。
        Semantic（语义记忆）：事实、概念和偏好。比如“用户是 TypeScript 专家”。
        Procedural（程序记忆）：做事的标准流程。比如“遇到退款要先查订单、再验金额、最后退款”。
        '''

        memory={
            "id":len(self.memories)+1,
            "content":content,
            "memory_type":memory_type,
            "timestamp":datetime.now().isoformat(),
            "metadata":metadata or {},
            "confidence":0.8,
            "expires_at":None
        }
        self.memories.append(memory)

        return memory

    def search(self,query:str,top_k:int=3):
        """检索相关记忆（简化版：生产中用向量相似度搜索）"""
        # 生产中: query → embedding → cosine similarity
        # 简化版: 关键词匹配
        results = [
            # query.split()：先把用户的提问按空格切开。比如 "LangGraph 怎么用" 切成 ["LangGraph", "怎么用"]。
            m for m in self.memories if any(query in m["content"] for word in query.split())
        ]
        return results[:top_k]

    def cleanup_expired_memories(self):
        """清理过期记忆"""
        now = datetime.now()
        self.memories = [
            m for m in self.memories
            if not m["expires_at"] or datetime.fromisoformat(m["expires_at"]) > now
        ]

# 使用示例
store = MemoryStore()

# Agent 主动写入记忆
store.add("用户偏好用 TypeScript", memory_type="semantic")
store.add("用户正在做 LangGraph 项目", memory_type="episodic")
store.add("处理退款流程: 先查订单 → 验证金额 → 执行退款", memory_type="procedural")

# 新对话开始时检索
relevant = store.search("LangGraph 怎么用")