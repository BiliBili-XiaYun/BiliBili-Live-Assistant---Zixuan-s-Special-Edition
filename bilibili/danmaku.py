#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站API相关模块 - 处理弹幕监控和登录
"""

import asyncio
import time
import traceback
from typing import Optional, Dict, Any, Callable

from PyQt6.QtCore import QThread, pyqtSignal

import bilibili_api
from bilibili_api import live, Credential

from models import MessageInfo
from utils import filter_cookie_data, get_current_timestamp
from config import Constants
from utils import bilibili_logger


class DanmakuMonitorThread(QThread):
    """弹幕监控线程 - 使用bilibili-api库"""
    
    # 信号定义
    message_received = pyqtSignal(dict)  # 消息接收信号
    status_changed = pyqtSignal(str)     # 状态变化信号
    error_occurred = pyqtSignal(str)     # 错误发生信号
    
    def __init__(self, room_id: int, cookies: Optional[Dict[str, Any]] = None):
        """
        初始化弹幕监控线程
        
        Args:
            room_id (int): 直播间ID
            cookies (Optional[Dict]): 登录cookies
        """        
        super().__init__()
        self.room_id = room_id
        self.cookies = cookies or {}
        self.live_danmaku = None
        self.loop = None
        self.running = False
        self._reconnect_count = 0
        self._max_reconnect_attempts = Constants.HTTP_TIMEOUT
    
    def run(self):
        """在新线程中运行异步事件循环"""
        try:
            bilibili_logger.operation_start("启动弹幕监控", f"房间ID: {self.room_id}")
            self.running = True  # 设置运行状态
            
            # 创建新的事件循环
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # 运行主协程
            self.loop.run_until_complete(self._main())
            
        except Exception as e:
            error_msg = f"弹幕监控线程异常: {str(e)}"
            bilibili_logger.error("弹幕监控错误", error_msg)
            bilibili_logger.error("详细错误堆栈", traceback.format_exc())
            self.error_occurred.emit(error_msg)
        finally:
            self._cleanup_loop()
    
    async def _main(self):
        """主协程"""
        while self.running:
            try:
                await self._connect_and_monitor()
                
                # 如果connect正常返回，说明连接被断开了
                if self.running:  # 如果还在运行状态，说明不是用户主动停止
                    bilibili_logger.warning("连接意外断开，准备重连")
                    self._reconnect_count += 1
                    
                    if self._reconnect_count < self._max_reconnect_attempts:
                        self.status_changed.emit(f"连接断开，{Constants.LOGIN_POLL_INTERVAL}秒后重连 (尝试 {self._reconnect_count}/{self._max_reconnect_attempts})...")
                        await asyncio.sleep(Constants.LOGIN_POLL_INTERVAL)
                    else:
                        self.error_occurred.emit("超过最大重连次数，停止重连")
                        break
                else:
                    # 用户主动停止
                    bilibili_logger.info("用户主动停止监控")
                    break
                    
            except Exception as e:
                self._reconnect_count += 1
                error_msg = f"连接异常 (尝试 {self._reconnect_count}/{self._max_reconnect_attempts}): {str(e)}"
                bilibili_logger.error("弹幕监控错误", error_msg)
                
                if self._reconnect_count < self._max_reconnect_attempts:
                    self.status_changed.emit(f"连接异常，{Constants.LOGIN_POLL_INTERVAL}秒后重试...")
                    await asyncio.sleep(Constants.LOGIN_POLL_INTERVAL)
                else:
                    self.error_occurred.emit("超过最大重连次数，连接失败")
                    break
    
    async def _connect_and_monitor(self):
        """连接并监控弹幕"""
        self.status_changed.emit(f"正在连接到直播间 {self.room_id}...")
        bilibili_logger.operation_start("连接直播间", str(self.room_id))
        try:
            # 创建Credential对象（如果有cookies的话）
            credential = None
            if self.cookies:
                # 过滤掉用户信息，只保留cookie数据
                cookie_data = {k: v for k, v in self.cookies.items() if k != 'user_info' and isinstance(v, str)}
                if cookie_data:
                    bilibili_logger.debug("设置凭据", str(list(cookie_data.keys())))
                    credential = Credential(
                        sessdata=cookie_data.get('SESSDATA', ''),
                        bili_jct=cookie_data.get('bili_jct', ''),
                        buvid3=cookie_data.get('buvid3', ''),
                        dedeuserid=cookie_data.get('DedeUserID', ''),
                        ac_time_value=cookie_data.get('ac_time_value', '')
                    )
            
            bilibili_logger.debug("凭据创建完成", str(credential is not None))
            
            # 简单测试：先获取直播间信息
            bilibili_logger.operation_start("测试获取直播间信息")
            room = live.LiveRoom(room_display_id=self.room_id, credential=credential)
            room_info = await room.get_room_info()
            bilibili_logger.operation_complete("获取直播间信息", room_info.get("title", "Unknown"))
            
            # 创建LiveDanmaku对象
            self.live_danmaku = live.LiveDanmaku(
                room_display_id=self.room_id,
                debug=True,  # 开启调试模式以获取更多信息
                credential=credential
            )
            bilibili_logger.debug("LiveDanmaku对象创建完成")
            
            # 注册事件处理器
            self._register_event_handlers()
            bilibili_logger.debug("事件处理器注册完成")
              # 连接到弹幕服务器
            bilibili_logger.operation_start("连接弹幕服务器")
            self.status_changed.emit("正在连接弹幕服务器...")
            
            # 使用事件处理来确认连接状态
            connection_confirmed = False
              # 添加连接确认事件处理
            @self.live_danmaku.on('VERIFICATION_SUCCESSFUL')
            async def on_verification_success(event):
                nonlocal connection_confirmed
                connection_confirmed = True
                bilibili_logger.operation_complete("弹幕服务器认证", "成功")
                
                # 检查是否以登录用户身份连接
                if credential and credential.sessdata:
                    bilibili_logger.info("已以登录用户身份连接到弹幕服务器")
                    self.status_changed.emit(f"✅ 已以登录用户身份连接到直播间 {self.room_id}")
                else:
                    bilibili_logger.info("已以访客身份连接到弹幕服务器")
                    self.status_changed.emit(f"✅ 已以访客身份连接到直播间 {self.room_id}")
            
            # 添加用户进入直播间事件处理
            @self.live_danmaku.on('INTERACT_WORD')
            async def on_interact_word(event):
                """用户进入直播间事件"""
                try:
                    data = event['data']['data']
                    username = data.get('uname', '未知用户')
                    msg_type = data.get('msg_type', 1)
                    
                    if msg_type == 1:  # 进入直播间
                        bilibili_logger.debug("用户进入直播间", username)
                except Exception as e:
                    bilibili_logger.error("处理用户进入事件异常", str(e))
            
            # 直接连接，不设置超时（让bilibili-api自己处理）
            await self.live_danmaku.connect()
            
            # 如果连接方法返回，说明连接断开了
            bilibili_logger.info("弹幕连接已断开")
            
        except asyncio.TimeoutError:
            error_msg = f"连接超时：无法在30秒内连接到直播间 {self.room_id}"
            bilibili_logger.error("弹幕监控错误", error_msg)
            self.error_occurred.emit(error_msg)
            raise
        except Exception as e:
            error_msg = f"连接失败: {str(e)}"
            bilibili_logger.error("弹幕监控错误", error_msg)
            print(f"错误详情: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(error_msg)
            raise
    
    def _create_credential(self) -> Optional[Credential]:
        """创建认证凭据"""
        credential = None
        if self.cookies:
            # 按照成功脚本的逻辑过滤cookie数据
            cookie_data = {k: v for k, v in self.cookies.items() 
                          if k != 'user_info' and isinstance(v, str)}
            
            if cookie_data:
                bilibili_logger.info("使用已登录用户凭据连接弹幕服务器")
                bilibili_logger.debug("可用cookie字段", str(list(cookie_data.keys())))
                
                # 创建Credential对象，使用与成功脚本相同的参数
                credential = Credential(
                    sessdata=cookie_data.get('SESSDATA', ''),
                    bili_jct=cookie_data.get('bili_jct', ''),
                    buvid3=cookie_data.get('buvid3', ''),
                    dedeuserid=cookie_data.get('DedeUserID', ''),
                    ac_time_value=cookie_data.get('ac_time_value', '')
                )
                
                # 验证凭据有效性
                bilibili_logger.debug("凭据创建结果:")
                bilibili_logger.debug("SESSDATA", "✅ 已设置" if credential.sessdata else "❌ 未设置")
                bilibili_logger.debug("bili_jct", "✅ 已设置" if credential.bili_jct else "❌ 未设置")
                bilibili_logger.debug("buvid3", "✅ 已设置" if credential.buvid3 else "❌ 未设置")
                bilibili_logger.debug("DedeUserID", "✅ 已设置" if credential.dedeuserid else "❌ 未设置")
                
                # 如果缺少关键字段，警告但仍然尝试连接
                if not credential.sessdata or not credential.bili_jct:
                    bilibili_logger.warning("缺少关键cookie字段，可能无法以登录用户身份连接")
                else:
                    bilibili_logger.info("所有关键cookie字段都存在，将以登录用户身份连接")
            else:
                bilibili_logger.warning("未找到有效的cookie数据")
        else:
            bilibili_logger.info("未提供cookies，将以访客身份连接弹幕服务器")
            
        return credential
    
    def _register_event_handlers(self):
        """注册事件处理器"""
        bilibili_logger.operation_start("注册事件处理器")
        
        @self.live_danmaku.on('DANMU_MSG')
        async def on_danmaku(event):
            """弹幕消息处理"""
            try:
                info = event['data']['info']
                username = info[2][1]  # 用户名
                message = info[1]      # 弹幕内容
                uid = info[2][0]       # 用户ID
                
                bilibili_logger.debug("弹幕消息", f"{username}: {message}")
                
                message_info = MessageInfo(
                    Constants.MESSAGE_TYPE_DANMAKU,
                    username,
                    get_current_timestamp(),
                    message=message,
                    uid=uid,
                    color=Constants.COLOR_DANMAKU
                )
                self._on_message(message_info)
            except Exception as e:
                bilibili_logger.error("处理弹幕消息异常", str(e))
        
        @self.live_danmaku.on('SEND_GIFT')
        async def on_gift(event):
            """礼物消息处理"""
            try:
                data = event['data']['data']
                username = data['uname']
                gift_name = data['giftName']
                num = data['num']
                uid = data['uid']
                
                bilibili_logger.debug("礼物消息", f"{username} 送出 {gift_name} x{num}")
                
                message_info = MessageInfo(
                    Constants.MESSAGE_TYPE_GIFT,
                    username,
                    get_current_timestamp(),
                    gift_name=gift_name,
                    num=num,
                    uid=uid
                )
                self._on_message(message_info)
            except Exception as e:
                bilibili_logger.error("处理礼物消息异常", str(e))
        
        # 添加连接状态监听
        @self.live_danmaku.on('LIVE')
        async def on_live_status(event):
            """直播状态事件"""
            try:
                # 只记录关键状态信息
                status = event.get('data', {}).get('live_status', 'unknown')
                bilibili_logger.debug("直播状态变更", f"状态: {status}")
            except Exception as e:
                bilibili_logger.error("处理直播状态异常", str(e))
        
        # 添加心跳监听来确认连接正常
        @self.live_danmaku.on('HEARTBEAT')
        async def on_heartbeat(event):
            """心跳事件"""
            bilibili_logger.debug("收到心跳包，连接正常")
        
        bilibili_logger.debug("事件处理器注册完成")
        
        @self.live_danmaku.on('GUARD_BUY')
        async def on_guard(event):
            """舰长购买消息处理"""
            try:
                data = event['data']['data']
                username = data['username']
                guard_level = data['guard_level']
                num = data['num']
                uid = data['uid']
                
                # 获取舰长等级名称
                guard_name = {1: "舰长", 2: "提督", 3: "总督"}.get(guard_level, f"等级{guard_level}")
                bilibili_logger.info("舰长购买", f"{username} 购买了 {num}个月{guard_name}")
                
                message_info = MessageInfo(
                    Constants.MESSAGE_TYPE_GUARD,
                    username,
                    get_current_timestamp(),
                    guard_level=guard_level,
                    num=num,
                    uid=uid
                )
                self._on_message(message_info)
            except Exception as e:
                bilibili_logger.error("处理舰长消息异常", str(e))
        
        @self.live_danmaku.on('SUPER_CHAT_MESSAGE')
        async def on_super_chat(event):
            """醒目留言处理"""
            try:
                data = event['data']['data']
                username = data['user_info']['uname']
                message = data['message']
                price = data['price']
                uid = data['uid']
                
                bilibili_logger.info("醒目留言", f"{username} (¥{price}): {message}")
                
                message_info = MessageInfo(
                    Constants.MESSAGE_TYPE_SUPER_CHAT,
                    username,
                    get_current_timestamp(),
                    message=message,
                    price=price,
                    uid=uid
                )
                self._on_message(message_info)
            except Exception as e:
                bilibili_logger.error("处理醒目留言异常", str(e))
        
        @self.live_danmaku.on('DISCONNECT')
        async def on_disconnect(event):
            """断开连接处理"""
            bilibili_logger.info("连接断开", str(event))
            if self.running:  # 只有在运行状态下才触发重连                self.status_changed.emit("连接已断开，尝试重连...")
                self._reconnect_count += 1
    
    def _on_message(self, message_info: MessageInfo):
        """处理接收到的消息"""
        try:
            # 根据消息类型记录不同级别的日志
            msg_type = message_info.type
            username = message_info.username
            
            if msg_type == Constants.MESSAGE_TYPE_DANMAKU:
                # 弹幕消息使用DEBUG级别，避免日志过多
                message_content = message_info.to_dict().get('message', '')
                bilibili_logger.debug("处理弹幕消息", f"{username}: {message_content}")
            elif msg_type == Constants.MESSAGE_TYPE_GUARD:
                # 舰长消息使用INFO级别，这是重要事件
                guard_level = message_info.to_dict().get('guard_level', 0)
                guard_name = {1: "舰长", 2: "提督", 3: "总督"}.get(guard_level, f"等级{guard_level}")
                bilibili_logger.info("处理舰长消息", f"{username} 购买{guard_name}")
            elif msg_type == Constants.MESSAGE_TYPE_GIFT:
                # 礼物消息使用DEBUG级别
                gift_info = message_info.to_dict()
                gift_name = gift_info.get('gift_name', '未知礼物')
                num = gift_info.get('num', 1)
                bilibili_logger.debug("处理礼物消息", f"{username} 送出 {gift_name} x{num}")
            elif msg_type == Constants.MESSAGE_TYPE_SUPER_CHAT:
                # 醒目留言使用INFO级别
                sc_info = message_info.to_dict()
                price = sc_info.get('price', 0)
                bilibili_logger.info("处理醒目留言", f"{username} (¥{price})")
            
            # 通过信号发送消息到主线程（保持兼容性，使用字典格式）
            self.message_received.emit(message_info.to_dict())
        except Exception as e:
            bilibili_logger.error("消息处理异常", str(e))
    
    def stop_monitoring(self):
        """停止监控"""
        try:
            bilibili_logger.operation_start("停止弹幕监控")
            self.running = False
            if self.loop and self.loop.is_running() and self.live_danmaku:
                # 在事件循环中停止客户端
                future = asyncio.run_coroutine_threadsafe(self._stop_client(), self.loop)
                future.result(timeout=Constants.MONITOR_STOP_TIMEOUT)  # 等待最多5秒
        except Exception as e:
            bilibili_logger.error("停止监控异常", str(e))
    
    async def _stop_client(self):
        """异步停止客户端"""
        try:
            if self.live_danmaku:
                bilibili_logger.operation_start("停止弹幕客户端")
                await self.live_danmaku.disconnect()
                self.live_danmaku = None
            self.status_changed.emit("已断开连接")
            bilibili_logger.operation_complete("弹幕客户端停止", "成功")
        except Exception as e:
            bilibili_logger.error("停止客户端异常", str(e))
    
    def _cleanup_loop(self):
        """清理事件循环"""
        try:
            if self.loop and not self.loop.is_closed():
                self.loop.close()
                bilibili_logger.debug("事件循环已清理")
        except Exception as e:
            bilibili_logger.error("关闭事件循环异常", str(e))
    
    def set_max_reconnect_attempts(self, attempts: int):
        """设置最大重连次数"""
        self._max_reconnect_attempts = max(1, attempts)
    
    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态信息"""
        return {
            'running': self.running,
            'room_id': self.room_id,
            'reconnect_count': self._reconnect_count,
            'max_reconnect_attempts': self._max_reconnect_attempts,
            'has_credential': bool(self.cookies)
        }
