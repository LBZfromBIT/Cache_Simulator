import math
import random
from collections import OrderedDict

class CacheBlock:
    """Cache块"""
    def __init__(self):
        self.tag = None   #标签
        self.valid = False  #有效位
        self.dirty = False  #脏位
        self.data = None  #数据
        self.load_time = 0 #用于FIFO，记录进入Cache时间，每次访问Cache时+1
        self.last_time = 0 #用于LRU，记录上次访问时间，每次访问Cache时+1，被访问后清零

class CacheSet:
    """Cache组"""
    def __init__(self, associativity,policy):
        self.blocks = OrderedDict()  #使用有序字典来实现LRU和FIFO
        self.associativity = associativity
        self.policy = policy

    def find_block(self, tag):
        """在组内查找符合tag的Cache块"""
        if tag in self.blocks:
            return self.blocks[tag]
        return None
    
    def add_block(self,block,current_time):
        """添加Cache块,如果组满了则根据策略删除一个块"""
        if len(self.blocks) > self.associativity:
            self.evict_block()

        block.load_time = current_time
        block.last_time = current_time
        self.blocks[block.tag]=block

    def evict_block(self):
        """根据策略驱逐Cache块"""
        evict_tag = None

        if self.policy ==  'RANDOM':
            # 随机替换实现
            evict_tag = random.choice(list(self.blocks.keys()))
            del self.blocks[evict_tag]
        elif self.policy == 'FIFO':
            # FIFO替换实现
            for i in self.blocks:
                if self.blocks[i].load_time == max(self.blocks[i].load_time for i in self.blocks):
                    evict_tag = i
                    break
            del self.blocks[evict_tag]
        elif self.policy == 'LRU':
            # LRU替换实现
            for i in self.blocks:
                if self.blocks[i].last_time == max(self.blocks[i].last_time for i in self.blocks):
                    evict_tag = i
                    break
            del self.blocks[evict_tag]

    def update_on_hit(self,tag):
        """命中cache时更新块的时间"""
        block = self.find_block(tag)
        if block:
            if self.policy == 'LRU':
                block.last_time = 0
            block.load_time += 1
            return True
        return False
    
class Cache:
    """Cache主类"""
    def __init__(self,cache_size,asscociativity,policy,address_bit):
        if cache_size <= 0:
            raise ValueError("Size must be greater than 0")
        if math.log2(cache_size) % 1 != 0 or math.log2(asscociativity) % 1 != 0:  
            raise ValueError("Cache size and asscociativity must be a power of 2")
        if cache_size < 2**address_bit:
            raise ValueError("Size must be greater than address space")
        if policy not in ['FIFO', 'LRU', 'RANDOM']:
            raise ValueError("Policy must be one of FIFO , LRU, RANDOM")        
        
        