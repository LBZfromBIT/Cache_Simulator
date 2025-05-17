import math
import random
from collections import OrderedDict

class Memory:
    """内存类"""
    def __init__(self, size):
        self.size = size
        self.data = [None] * size  # 初始化内存数据
        self.access_count = 0  # 访问次数
    
    def read(self, address):
        """从内存读取数据"""
        if address < 0 or address >= self.size:
            raise ValueError("Address out of range")
        self.access_count += 1
        if self.data[address] is None:
            return 0
        else:
            return self.data[address]
    
    def write(self, address, data):
        """向内存写入数据"""
        if address < 0 or address >= self.size:
            raise ValueError("Address out of range")
        self.access_count += 1
        self.data[address] = data

class CacheBlock:
    """Cache块"""
    def __init__(self,block_size):
        self.tag = None   #标签
        self.valid = False  #有效位
        self.dirty = False  #脏位
        self.block_size = block_size #块大小
        self.data = [None]* self.block_size  #数据
        self.base_address = None  #整个块的起始主存地址
        self.load_time = 0 #用于FIFO，记录进入Cache时间，每次访问Cache时+1
        self.last_time = 0 #用于LRU，记录上次访问时间，每次访问Cache时+1，被访问后清零

class CacheSet:
    """Cache组"""
    def __init__(self, associativity,policy,memory):
        self.memory = memory #内存类对象
        self.blocks = OrderedDict()  #使用有序字典来实现LRU和FIFO
        self.associativity = associativity
        self.policy = policy

    def find_block(self, tag):
        """在组内查找符合tag的Cache块"""
        if tag in self.blocks:
            return self.blocks[tag]
        return None
    
    def add_block(self,block):
        """添加Cache块,如果组满了则根据策略删除一个块"""
        if len(self.blocks) >= self.associativity:
            self.evict_block()
        self.blocks[block.tag]=block

    def evict_block(self):
        """根据策略驱逐Cache块"""
        evict_tag = None

        if not self.blocks:
            return
        
        if self.policy ==  'RANDOM':
            # 随机替换实现
            evict_tag = random.choice(list(self.blocks.keys()))
        elif self.policy == 'FIFO':
            # FIFO替换实现:寻找组内load_time最小替换
            temp = -1 
            for tag,block in self.blocks.items():
                if temp == -1 or block.load_time < temp:
                    temp = block.load_time
                    evict_tag = tag
        elif self.policy == 'LRU':
            # LRU替换实现：寻找组内last_time最小替换
            temp = -1 
            for tag,block in self.blocks.items():
                if temp == -1 or block.last_time < temp:
                    temp = block.last_time
                    evict_tag = tag

        if evict_tag is not None:
            if self.blocks[evict_tag].dirty and self.blocks[evict_tag].data:
                # 如果块是脏的，写回内存
                for i in range(self.blocks[evict_tag].block_size):
                    addr = self.blocks[evict_tag].base_address + i
                    if addr < self.memory.size:  # 确保地址在有效范围内
                        self.memory.write(addr, self.blocks[evict_tag].data[i])
            del self.blocks[evict_tag]


class Cache:
    """Cache主类"""
    def __init__(self,cache_size,block_size,associativity,policy,address_bit,memory):

        if cache_size <= 0 or block_size <= 0 or associativity <= 0:
            raise ValueError("Parameter 'Size' must be greater than 0")
        if math.log2(cache_size) % 1 != 0  or math.log2(block_size) % 1 != 0 or math.log2(associativity) % 1 != 0:  
            raise ValueError("Parameter 'Size' must be a power of 2")
        if policy not in ['FIFO', 'LRU', 'RANDOM']:
            raise ValueError("Policy must be one of FIFO , LRU, RANDOM")    

        self.cache_size = cache_size
        self.associativity = associativity
        self.policy = policy
        self.address_bit = address_bit    
        self.block_size = block_size
        self.set_count = int(cache_size / (block_size * associativity))  # 计算组数，确保为整数
        self.memory = memory
        
        # 初始化统计数据
        self.access_count = 0
        self.hit_count = 0
        self.read_count = 0
        self.write_count = 0
        self.read_hit_count = 0
        self.write_hit_count = 0

        # 时间戳
        self.time = 0
        
        # 初始化Cache组
        self.sets = {}
        for i in range(self.set_count):
            self.sets[i] = CacheSet(self.associativity, self.policy,self.memory)
        

    def address_split(self,address):
        """地址分割成tag, index, offset"""
        if address >= 2**self.address_bit:
            raise ValueError("Address out of range")
        offset = address % self.block_size
        index = (address // self.block_size) % self.set_count
        tag = address // (self.block_size * self.set_count)
        return tag, index, offset
    
    
    def read(self, address, memory):
        """从Cache读取数据,如果不命中则从内存读取"""
        self.access_count += 1
        self.read_count += 1
        
        tag, index, offset = self.address_split(address)
        cache_set = self.sets[index]
        
        # 检查是否命中
        block = cache_set.find_block(tag)
        if block and block.valid:
            # 命中
            self.hit_count += 1
            self.read_hit_count += 1
            # 更新时间戳
            if self.policy == 'LRU':
                block.last_time = self.time
            
            self.time += 1
            return block.data[offset] if block.data else None
        else:
            # 未命中，从内存读取
            block_address = (address // self.block_size) * self.block_size
            data = []
            for i in range(self.block_size):
                if block_address + i < 2**self.address_bit:
                    data.append(memory.read(block_address + i))
            
            # 创建新的Cache块
            new_block = CacheBlock(self.block_size)            
            new_block.tag = tag
            new_block.valid = True
            new_block.dirty = False
            new_block.data = data
            new_block.base_address = block_address
            new_block.load_time = self.time
            new_block.last_time = self.time            
            
            # 将块添加到Cache
            cache_set.add_block(new_block)

            self.time += 1
            return data[offset] if data else None
    
    def write(self, address, data, memory):
        """写入数据到Cache"""
        self.access_count += 1
        self.write_count += 1
        
        tag, index, offset = self.address_split(address)
        cache_set = self.sets[index]
        
        # 检查是否命中
        block = cache_set.find_block(tag)
        if block and block.valid:
            # 命中
            self.hit_count += 1
            self.write_hit_count += 1
            
            # 更新数据
            if not block.data:
                block.data = [None] * self.block_size
            block.data[offset] = data
            
            # 写回：标记为脏
            block.dirty = True
            # 更新时间戳
            if self.policy == 'LRU':
                block.last_time = self.time
            
            self.time += 1
        else:
            self.time += 1
            # 未命中直接写入内存
            memory.write(address, data)
    
    def get_hit_rate(self):
        """获取命中率"""
        if self.access_count == 0:
            return 0
        return self.hit_count / self.access_count
    
    def get_read_hit_rate(self):
        """获取读命中率"""
        if self.read_count == 0:
            return 0
        return self.read_hit_count / self.read_count
    
    def get_write_hit_rate(self):
        """获取写命中率"""
        if self.write_count == 0:
            return 0
        return self.write_hit_count / self.write_count
    
    def print_stats(self):
        """打印统计信息"""
        print(f"总访问次数: {self.access_count}")
        print(f"命中次数: {self.hit_count}")
        print(f"命中率: {self.get_hit_rate():.4f}")
        print(f"读访问次数: {self.read_count}")
        print(f"读命中次数: {self.read_hit_count}")
        print(f"读命中率: {self.get_read_hit_rate():.4f}")
        print(f"写访问次数: {self.write_count}")
        print(f"写命中次数: {self.write_hit_count}")
        print(f"写命中率: {self.get_write_hit_rate():.4f}")  


def trace_file(cache, memory, filename):
    """从跟踪文件执行指令"""
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if len(parts) < 2:
                    continue
                
                op = parts[0].lower() # 每行第一部分：操作类型
                address = int(parts[1], 16)  # 每行第二部分：操作地址 假设地址是十六进制
                
                if op == 'r' or op == 'read':
                    cache.read(address, memory)
                elif op == 'w' or op == 'write':
                    data = int(parts[2]) if len(parts) > 2 else 1  #对写入行的第三部分：操作数 默认写入1
                    cache.write(address, data, memory)
        
        print(f"跟踪文件 {filename} 执行完成")
        cache.print_stats()
    except Exception as e:
        print(f"执行跟踪文件时出错: {e}")

def random_access(cache, memory, count, read_ratio=0.7, address_range=None):
    """随机访问测试"""
    if address_range is None:
        address_range = 2**cache.address_bit
    else:
        address_range = min(address_range, 2**cache.address_bit)
    
    for _ in range(count):
        address = random.randint(0, address_range - 1)
        if random.random() < read_ratio:
            # 执行读操作
            cache.read(address, memory)
        else:
            # 执行写操作
            data = random.randint(0, 255)
            cache.write(address, data, memory)
    
    print(f"随机访问测试执行完成 ({count} 次操作)")
    cache.print_stats()

def main():
    """主函数"""
    print("欢迎使用Cache模拟器")
    
    # 默认参数
    cache_size = 1024  # 1KB
    block_size = 64    # 64字节
    associativity = 2  # 2路组相联
    policy = 'LRU'     # LRU替换策略
    address_bit = 10  # 10位地址空间 (1KB)
    
    while True:
        print("\n===== Cache模拟器菜单 =====")
        print("1. 设置Cache参数")
        print("2. 执行跟踪文件")
        print("3. 随机访问测试")
        print("4. 打印Cache统计信息")
        print("5. 退出")
        
        choice = input("请选择操作 (1-5): ")
        
        if choice == '1':
            try:
                cache_size = int(input("请输入Cache大小 (字节): "))
                block_size = int(input("请输入块大小 (字节): "))
                associativity = int(input("请输入相联度: "))
                policy = input("请输入替换策略 (FIFO/LRU/RANDOM): ").upper()
                address_bit = int(input("请输入地址位数: "))
                
                # 创建Cache和内存
                memory = Memory(2**address_bit)
                cache = Cache(cache_size, block_size, associativity, policy, address_bit, memory)
                
                print("Cache参数设置成功")
            except ValueError as e:
                print(f"参数错误: {e}")
        
        elif choice == '2':
            if 'cache' not in locals() or 'memory' not in locals():
                print("请先设置Cache参数")
                continue
            
            filename = input("请输入跟踪文件路径: ")
            trace_file(cache, memory, filename)
        
        elif choice == '3':
            if 'cache' not in locals() or 'memory' not in locals():
                print("请先设置Cache参数")
                continue
            
            try:
                count = int(input("请输入访问次数: "))
                read_ratio = float(input("请输入读操作比例 (0-1): "))
                random_access(cache, memory, count, read_ratio)
            except ValueError as e:
                print(f"参数错误: {e}")
        
        elif choice == '4':
            if 'cache' not in locals():
                print("请先设置Cache参数")
                continue
            
            cache.print_stats()
        
        elif choice == '5':
            print("谢谢使用，再见！")
            break
        
        else:
            print("无效的选择，请重新输入")

if __name__ == "__main__":
    main()