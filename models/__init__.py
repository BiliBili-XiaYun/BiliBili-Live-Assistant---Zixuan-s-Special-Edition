#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型模块 - 定义程序中使用的数据结构
"""


class QueueItem:
    """排队项目数据模型"""
    
    def __init__(self, name, count, index, is_cutline=False):
        """
        初始化排队项目
        
        Args:
            name (str): 用户名
            count (int): 剩余次数
            index (int): 在名单中的序号
            is_cutline (bool): 是否为插队项目
        """
        self.name = name
        self.count = count
        self.index = index
        self.is_cutline = is_cutline  # 是否为插队
        self.in_queue = False         # 是否在排队队列中
        self.in_boarding = False      # 是否在上车队列中
    
    def __repr__(self):
        """字符串表示"""
        return f"QueueItem(name='{self.name}', count={self.count}, index={self.index}, cutline={self.is_cutline})"
    
    def __str__(self):
        """友好的字符串表示"""
        status = []
        if self.in_queue:
            status.append("排队中")
        if self.in_boarding:
            status.append("上车中")
        if self.is_cutline:
            status.append("插队")
        
        status_str = f" ({', '.join(status)})" if status else ""
        return f"{self.name} (序号:{self.index}, 次数:{self.count}){status_str}"


class MessageInfo:
    """消息信息数据模型"""
    
    def __init__(self, message_type, username, timestamp, **kwargs):
        """
        初始化消息信息
        
        Args:
            message_type (str): 消息类型 ('danmaku', 'gift', 'guard', 'super_chat')
            username (str): 用户名
            timestamp (str): 时间戳
            **kwargs: 其他消息特定的属性
        """
        self.type = message_type
        self.username = username
        self.timestamp = timestamp
        
        # 根据消息类型设置特定属性
        if message_type == 'danmaku':
            self.message = kwargs.get('message', '')
            self.uid = kwargs.get('uid', 0)
            self.color = kwargs.get('color', '#000000')
            
        elif message_type == 'gift':
            self.gift_name = kwargs.get('gift_name', '未知礼物')
            self.num = kwargs.get('num', 1)
            self.uid = kwargs.get('uid', 0)
            
        elif message_type == 'guard':
            self.guard_level = kwargs.get('guard_level', 0)
            self.num = kwargs.get('num', 1)
            self.uid = kwargs.get('uid', 0)
            
        elif message_type == 'super_chat':
            self.message = kwargs.get('message', '')
            self.price = kwargs.get('price', 0)
            self.uid = kwargs.get('uid', 0)
    
    def to_dict(self):
        """转换为字典格式（兼容旧版本）"""
        data = {
            'type': self.type,
            'username': self.username,
            'timestamp': self.timestamp
        }
        
        # 添加特定类型的属性
        if hasattr(self, 'message'):
            data['message'] = self.message
        if hasattr(self, 'uid'):
            data['uid'] = self.uid
        if hasattr(self, 'color'):
            data['color'] = self.color
        if hasattr(self, 'gift_name'):
            data['gift_name'] = self.gift_name
        if hasattr(self, 'num'):
            data['num'] = self.num
        if hasattr(self, 'guard_level'):
            data['guard_level'] = self.guard_level
        if hasattr(self, 'price'):
            data['price'] = self.price
            
        return data
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建消息信息对象"""
        message_type = data.get('type', 'unknown')
        username = data.get('username', '未知用户')
        timestamp = data.get('timestamp', '')
        
        # 移除这些基本属性，其余作为kwargs传递
        kwargs = {k: v for k, v in data.items() 
                 if k not in ['type', 'username', 'timestamp']}
        
        return cls(message_type, username, timestamp, **kwargs)
    
    def __repr__(self):
        """字符串表示"""
        return f"MessageInfo(type='{self.type}', username='{self.username}', time='{self.timestamp}')"


class UserInfo:
    """用户信息数据模型"""
    
    def __init__(self, uname="", uid=0, face="", level=0):
        """
        初始化用户信息
        
        Args:
            uname (str): 用户名
            uid (int): 用户ID
            face (str): 头像URL
            level (int): 用户等级
        """
        self.uname = uname
        self.uid = uid
        self.face = face
        self.level = level
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'uname': self.uname,
            'uid': self.uid,
            'face': self.face,
            'level': self.level
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建用户信息对象"""
        return cls(
            uname=data.get('uname', ''),
            uid=data.get('uid', 0),
            face=data.get('face', ''),
            level=data.get('level', 0)
        )
    
    def __repr__(self):
        """字符串表示"""
        return f"UserInfo(uname='{self.uname}', uid={self.uid}, level={self.level})"
    
    def __str__(self):
        """友好的字符串表示"""
        return f"{self.uname} (Lv.{self.level})"
