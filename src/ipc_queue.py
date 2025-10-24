import multiprocessing

# 创建一个全局的、可被所有模块安全导入的进程间通信(IPC)队列。
# 这避免了将队列实例作为参数在复杂的对象间传递，从而解决了序列化(pickle)问题。
queue = multiprocessing.Queue()
