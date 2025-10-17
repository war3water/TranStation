# src/server/websocket_server.py
import asyncio
import websockets
import logging
import json
from queue import Queue
from websockets.exceptions import ConnectionClosed

class WebSocketServer:
    """
    管理 WebSocket 连接并向上层应用推送数据。
    """
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.connected_clients = set()
        self.message_queue = Queue()

    async def _register(self, websocket):
        """
        注册新的客户端连接。
        """
        self.connected_clients.add(websocket)
        logging.info(f"新客户端连接: {websocket.remote_address}")

    async def _unregister(self, websocket):
        """
        注销断开的客户端连接。
        """
        self.connected_clients.remove(websocket)
        logging.info(f"客户端断开连接: {websocket.remote_address}")

    async def _producer(self):
        """
        从队列中获取消息。
        """
        loop = asyncio.get_event_loop()
        while True:
            message = await loop.run_in_executor(None, self.message_queue.get)
            yield message

    async def _handler(self, websocket, path):
        """
        处理单个客户端连接的主循环。
        """
        await self._register(websocket)
        try:
            await websocket.wait_closed()
        finally:
            await self._unregister(websocket)

    async def _broadcast_messages(self):
        """
        从生成器获取消息并广播给所有连接的客户端。
        """
        async for message in self._producer():
            if self.connected_clients:
                message_json = json.dumps(message)
                await asyncio.gather(
                    *[client.send(message_json) for client in self.connected_clients],
                    return_exceptions=True
                )

    def queue_message(self, message: dict):
        """
        线程安全地将消息放入队列。
        """
        self.message_queue.put(message)

    def run(self):
        """
        启动 WebSocket 服务器。
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def start_server():
            """
            一个 async 的入口点，用于正确启动服务器和任务。
            """
            server = await websockets.serve(self._handler, self.host, self.port)
            logging.info(f"WebSocket 服务器已在 ws://{self.host}:{self.port} 上启动")
            asyncio.create_task(self._broadcast_messages())
            await server.wait_closed()

        try:
            loop.run_until_complete(start_server())
        # 关键修复：捕获端口占用错误并提供清晰的提示
        except OSError as e:
            if e.winerror == 10048:
                logging.error(f"!!!!!!!!!! 端口 {self.port} 已被占用 !!!!!!!!!!")
                logging.error("请关闭其他正在使用此端口的程序，或使用 'taskkill' 命令强制释放端口。")
            else:
                logging.error(f"WebSocket 服务器启动时发生未知OSError: {e}", exc_info=True)
        except Exception as e:
            logging.error(f"WebSocket 服务器运行时出错: {e}", exc_info=True)
        finally:
            loop.close()
            logging.info("WebSocket 服务器已关闭。")