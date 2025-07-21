#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站登录模块 - 处理二维码登录功能
"""

import json
import time
from io import BytesIO
from typing import Optional, Dict, Any

import requests
import qrcode
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

from models import UserInfo
from config import Constants
from utils import safe_json_load, safe_json_save


class QRLoginThread(QThread):
    """二维码登录线程"""
    
    # 信号定义
    update_status = pyqtSignal(str)    # 状态更新信号
    login_success = pyqtSignal(dict)   # 登录成功信号
    login_failed = pyqtSignal(str)     # 登录失败信号
    
    def __init__(self, qr_key: str):
        """
        初始化登录线程
        
        Args:
            qr_key (str): 二维码密钥
        """
        super().__init__()
        self.qr_key = qr_key
        self.is_running = True
        
    def run(self):
        """轮询二维码扫码状态"""
        while self.is_running:
            try:
                resp = requests.get(
                    Constants.BILIBILI_LOGIN_POLL_URL,
                    params={"qrcode_key": self.qr_key},
                    headers=Constants.DEFAULT_HEADERS,
                    timeout=Constants.HTTP_TIMEOUT
                )
                
                if resp.status_code != 200:
                    self.login_failed.emit(f"查询扫码状态失败: HTTP状态码 {resp.status_code}")
                    break
                
                try:
                    data = resp.json()
                except json.JSONDecodeError as e:
                    self.login_failed.emit(f"响应格式错误: {str(e)}")
                    break
                
                if data["code"] != 0:
                    self.login_failed.emit(f"查询扫码状态失败: {data['message']}")
                    break
                    
                info = data["data"]
                code = info["code"]
                
                if code == Constants.QR_CODE_SUCCESS:  # 已扫码并确认
                    self.update_status.emit("登录成功！获取用户信息...")
                    cookies = self._extract_cookies(resp)
                    
                    try:
                        user_info = self._get_user_info(cookies)
                        cookies["user_info"] = user_info.to_dict()
                        self.login_success.emit(cookies)
                    except Exception as e:
                        self.login_failed.emit(f"获取用户信息失败: {str(e)}")
                    break
                    
                elif code == Constants.QR_CODE_EXPIRED:  # 二维码已失效
                    self.login_failed.emit("二维码已失效，请重新获取")
                    break
                    
                elif code == Constants.QR_CODE_SCANNED:  # 已扫码，等待确认
                    self.update_status.emit("已扫码，请在手机上确认登录")
                elif code == Constants.QR_CODE_NOT_SCANNED:  # 未扫码
                    pass
                else:  # 其他状态
                    self.update_status.emit(f"状态更新: {info.get('message', '未知状态')}")
                    
                time.sleep(Constants.LOGIN_POLL_INTERVAL)  # 每2秒检查一次
                
            except Exception as e:
                self.login_failed.emit(f"登录过程出错: {str(e)}")
                break
    
    def _extract_cookies(self, response) -> Dict[str, str]:
        """
        从响应中提取cookies
        
        Args:
            response: HTTP响应对象
            
        Returns:
            Dict[str, str]: cookies字典
        """
        cookies = {}
        for cookie in response.cookies:
            cookies[cookie.name] = cookie.value
        return cookies
    
    def _get_user_info(self, cookies: Dict[str, str]) -> UserInfo:
        """
        获取用户信息
        
        Args:
            cookies (Dict[str, str]): cookies字典
            
        Returns:
            UserInfo: 用户信息对象
            
        Raises:
            Exception: 获取用户信息失败时抛出
        """
        try:
            resp = requests.get(
                Constants.BILIBILI_NAV_URL,
                cookies=cookies,
                headers=Constants.DEFAULT_HEADERS,
                timeout=Constants.HTTP_TIMEOUT
            )
            
            if resp.status_code != 200:
                raise Exception(f"HTTP状态码错误: {resp.status_code}")
            
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                raise Exception(f"JSON解析错误: {str(e)}")
            
            if data["code"] == 0:
                user_data = data["data"]
                return UserInfo(
                    uname=user_data.get("uname", ""),
                    uid=user_data.get("mid", 0),
                    face=user_data.get("face", ""),
                    level=user_data.get("level_info", {}).get("current_level", 0)
                )
            else:
                raise Exception(data["message"])
                
        except Exception as e:
            raise Exception(f"获取用户信息失败: {str(e)}")
    
    def stop(self):
        """停止线程"""
        self.is_running = False


class LoginManager:
    """登录管理器"""
    
    def __init__(self, cookies_file: str = Constants.COOKIES_FILE):
        """
        初始化登录管理器
        
        Args:
            cookies_file (str): cookies文件路径
        """
        self.cookies_file = cookies_file
        self._cached_cookies = None
        self._cached_user_info = None
    
    def get_qr_code(self) -> tuple[QPixmap, str]:
        """
        获取登录二维码
        
        Returns:
            tuple: (二维码图片, 二维码密钥)
            
        Raises:
            Exception: 获取二维码失败时抛出
        """
        try:
            resp = requests.get(
                Constants.BILIBILI_LOGIN_QR_URL,
                headers=Constants.DEFAULT_HEADERS,
                timeout=Constants.HTTP_TIMEOUT
            )
            
            if resp.status_code != 200:
                raise Exception(f"获取二维码失败: HTTP状态码 {resp.status_code}")
            
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                raise Exception(f"响应格式错误: {str(e)}")
            
            if data["code"] != 0:
                raise Exception(f"获取二维码失败: {data['message']}")
            
            qr_info = data["data"]
            qr_code_url = qr_info["url"]
            qr_key = qr_info["qrcode_key"]
            
            # 生成二维码图片
            qr = qrcode.QRCode(version=1, box_size=8, border=4)
            qr.add_data(qr_code_url)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # 转换为QPixmap
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            
            return pixmap, qr_key
            
        except Exception as e:
            raise Exception(f"获取二维码异常: {str(e)}")
    
    def load_saved_cookies(self) -> Optional[Dict[str, Any]]:
        """
        加载保存的cookies
        
        Returns:
            Optional[Dict]: cookies字典，如果加载失败返回None
        """
        if self._cached_cookies is None:
            self._cached_cookies = safe_json_load(self.cookies_file)
        
        return self._cached_cookies
    
    def save_cookies(self, cookies: Dict[str, Any]) -> bool:
        """
        保存cookies到文件
        
        Args:
            cookies (Dict): cookies字典
            
        Returns:
            bool: 是否保存成功
        """
        if safe_json_save(self.cookies_file, cookies):
            self._cached_cookies = cookies
            # 更新缓存的用户信息
            user_info_data = cookies.get("user_info")
            if user_info_data:
                self._cached_user_info = UserInfo.from_dict(user_info_data)
            return True
        return False
    
    def get_user_info(self) -> Optional[UserInfo]:
        """
        获取当前用户信息
        
        Returns:
            Optional[UserInfo]: 用户信息对象，如果未登录返回None
        """
        if self._cached_user_info is None:
            cookies = self.load_saved_cookies()
            if cookies and "user_info" in cookies:
                self._cached_user_info = UserInfo.from_dict(cookies["user_info"])
        
        return self._cached_user_info
    
    def is_logged_in(self) -> bool:
        """
        检查是否已登录
        
        Returns:
            bool: 是否已登录
        """
        cookies = self.load_saved_cookies()
        return bool(cookies and self.get_user_info())
    
    def logout(self) -> bool:
        """
        登出（清除本地cookies）
        
        Returns:
            bool: 是否登出成功
        """
        try:
            # 清除缓存
            self._cached_cookies = None
            self._cached_user_info = None
            
            # 删除cookies文件
            import os
            if os.path.exists(self.cookies_file):
                os.remove(self.cookies_file)
            
            return True
        except Exception as e:
            print(f"登出失败: {str(e)}")
            return False
    
    def get_cookies(self) -> Optional[Dict[str, Any]]:
        """
        获取当前cookies
        
        Returns:
            Optional[Dict]: cookies字典
        """
        return self.load_saved_cookies()
    
    def validate_cookies(self, cookies: Optional[Dict[str, Any]] = None) -> bool:
        """
        验证cookies是否有效
        
        Args:
            cookies (Optional[Dict]): 要验证的cookies，如果为None则验证当前cookies
            
        Returns:
            bool: cookies是否有效
        """
        if cookies is None:
            cookies = self.load_saved_cookies()
        
        if not cookies:
            return False
        
        # 检查必要的cookie字段
        required_fields = ['SESSDATA', 'bili_jct']
        for field in required_fields:
            if field not in cookies or not cookies[field]:
                return False
        
        # 检查用户信息
        if 'user_info' not in cookies:
            return False
        
        return True
