#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块 - 提供通用的辅助函数
"""

import re
import os
import json
import time
import csv
from typing import Optional, List, Dict, Any, Tuple

# 导入新的功能模块
from .logger import QueueLogger
from .lottery_animation import RandomSelectionAnimationThread  # 现在可以直接导入了

# 延迟导入以避免循环导入
def get_constants():
    """获取常量"""
    from config import Constants
    return Constants

# 延迟导入enhanced_logger以避免循环导入
def get_main_logger():
    """获取主日志器"""
    from .enhanced_logger import main_logger
    return main_logger

def get_queue_logger():
    """获取队列日志器"""
    from .enhanced_logger import queue_logger
    return queue_logger

def get_gui_logger():
    """获取GUI日志器"""
    from .enhanced_logger import gui_logger
    return gui_logger

def get_bilibili_logger():
    """获取B站日志器"""
    from .enhanced_logger import bilibili_logger
    return bilibili_logger

def get_gui_logger():
    """获取GUI日志器"""
    from .enhanced_logger import gui_logger
    return gui_logger

# 为了向后兼容，提供直接访问方式
def __getattr__(name):
    """动态获取日志器实例"""
    if name == 'main_logger':
        return get_main_logger()
    elif name == 'queue_logger':
        return get_queue_logger()
    elif name == 'gui_logger':
        return get_gui_logger()
    elif name == 'bilibili_logger':
        return get_bilibili_logger()
    elif name == 'EnhancedLogger':
        from .enhanced_logger import EnhancedLogger
        return EnhancedLogger
    elif name == 'RandomSelectionAnimationThread':
        from .lottery_animation import RandomSelectionAnimationThread
        return RandomSelectionAnimationThread
    elif name == 'show_notification':
        from .notification import show_notification
        return show_notification
    elif name == 'show_copy_notification':
        from .notification import show_copy_notification
        return show_copy_notification
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def extract_room_id(url_or_id: str) -> int:
    """
    从URL或字符串中提取房间ID
    
    Args:
        url_or_id (str): URL或房间ID字符串
        
    Returns:
        int: 房间ID
        
    Raises:
        ValueError: 无法提取房间ID时抛出
    """
    url_or_id = url_or_id.strip()
    
    # 如果是纯数字，直接返回
    if url_or_id.isdigit():
        return int(url_or_id)
    
    # 尝试从URL中提取房间ID
    patterns = [
        r'live\.bilibili\.com/(\d+)',
        r'live\.bilibili\.com/(\d+)\?',
        r'live\.bilibili\.com/(\d+)#',
        r'/(\d+)$',
        r'/(\d+)\?',
        r'/(\d+)#'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return int(match.group(1))
    
    # 如果都匹配失败，尝试提取字符串中的数字
    numbers = re.findall(r'\d+', url_or_id)
    if numbers:
        return int(numbers[-1])  # 返回最后一个数字
    
    raise ValueError(f"无法从 '{url_or_id}' 中提取房间ID")


def parse_name_count(name_str: str) -> Tuple[str, int]:
    """
    解析名字和次数字符串
    支持格式: 
    - "名字" (默认次数1)
    - "名字(次数" (开放式英文括号)
    - "名字（次数" (开放式中文括号) 
    - "名字(次数)" (闭合式英文括号)
    - "名字（次数）" (闭合式中文括号)
    
    Args:
        name_str (str): 名字字符串
        
    Returns:
        tuple: (名字, 次数)
    """
    name_str = name_str.strip()
    
    if not name_str:
        return "", 1
    
    # 定义支持的括号对
    bracket_pairs = [
        ('(', ')'),    # 英文括号
        ('（', '）'),  # 中文括号
    ]
    
    # 尝试匹配完整的括号对格式，如 "名字(次数)" 或 "名字（次数）"
    for open_bracket, close_bracket in bracket_pairs:
        if open_bracket in name_str and close_bracket in name_str:
            # 查找最后一个开放括号的位置
            open_pos = name_str.rfind(open_bracket)
            if open_pos != -1:
                # 从开放括号位置开始查找对应的闭合括号
                close_pos = name_str.find(close_bracket, open_pos)
                if close_pos != -1:
                    # 提取名字和次数
                    name = name_str[:open_pos].strip()
                    count_str = name_str[open_pos+1:close_pos].strip()
                    
                    # 验证次数是否为有效数字
                    try:
                        count = int(count_str)
                        if count > 0:
                            return name if name else name_str, count
                    except ValueError:
                        pass
    
    # 尝试匹配开放式括号格式，如 "名字(次数" 或 "名字（次数"
    for open_bracket, _ in bracket_pairs:
        if open_bracket in name_str:
            # 查找最后一个开放括号的位置
            open_pos = name_str.rfind(open_bracket)
            if open_pos != -1:
                # 提取名字和次数部分
                name = name_str[:open_pos].strip()
                count_str = name_str[open_pos+1:].strip()
                
                # 验证次数是否为有效数字
                try:
                    count = int(count_str)
                    if count > 0:
                        return name if name else name_str, count
                except ValueError:
                    pass
    
    # 如果没有找到有效的括号格式，返回原字符串作为名字，次数为1
    return name_str, 1


def format_name_count(name: str, count: int) -> str:
    """
    格式化名字和次数为字符串
    统一使用中文括号的开放式格式
    
    Args:
        name (str): 名字
        count (int): 次数
        
    Returns:
        str: 格式化后的字符串
    """
    if count <= 1:
        return name
    else:
        return f"{name}（{count}"


def get_current_timestamp() -> str:
    """
    获取当前时间戳字符串
    
    Returns:
        str: 格式化的时间戳 (HH:MM:SS)
    """
    return time.strftime('%H:%M:%S')


def is_test_mode_input(input_str: str) -> bool:
    """
    检查输入是否为测试模式关键词
    
    Args:
        input_str (str): 输入字符串
        
    Returns:
        bool: 是否为测试模式
    """
    Constants = get_constants()
    return input_str.lower().strip() in Constants.TEST_MODE_KEYWORDS


def safe_json_load(file_path: str, default: Any = None) -> Any:
    """
    安全地加载JSON文件
    
    Args:
        file_path (str): 文件路径
        default (Any): 默认值
        
    Returns:
        Any: JSON数据或默认值
    """
    try:
        if os.path.exists(file_path):
            Constants = get_constants()
            with open(file_path, 'r', encoding=Constants.FILE_ENCODING) as f:
                return json.load(f)
    except Exception as e:
        logger = get_main_logger()
        logger.error("加载JSON文件失败", f"{file_path}: {str(e)}")
    
    return default


def safe_json_save(file_path: str, data: Any) -> bool:
    """
    安全地保存JSON文件
    
    Args:
        file_path (str): 文件路径
        data (Any): 要保存的数据
        
    Returns:
        bool: 是否保存成功
    """
    try:
        Constants = get_constants()
        with open(file_path, 'w', encoding=Constants.FILE_ENCODING) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger = get_main_logger()
        logger.error("保存JSON文件失败", f"{file_path}: {str(e)}")
        return False


def load_name_list_from_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    从CSV文件加载名单
    
    Args:
        file_path (str): CSV文件路径
        
    Returns:
        List[Dict]: 名单数据列表
    """
    name_list = []
    
    if not os.path.exists(file_path):
        logger = get_main_logger()
        logger.warning("名单文件不存在", file_path)
        return name_list
    
    try:
        Constants = get_constants()
        with open(file_path, 'r', encoding=Constants.FILE_ENCODING) as f:
            reader = csv.reader(f)
            for row_index, row in enumerate(reader):
                if row and row[0].strip():  # 非空行
                    name_str = row[0].strip()
                    name, count = parse_name_count(name_str)
                    
                    if name:  # 名字不为空
                        name_list.append({
                            'name': name,
                            'count': count,
                            'index': row_index + 1,
                            'original_str': name_str
                        })
        
        logger = get_main_logger()
        logger.operation_complete("加载名单文件", f"从 {file_path} 加载了 {len(name_list)} 个项目")
        
    except Exception as e:
        logger = get_main_logger()
        logger.error("加载名单文件失败", str(e))
    
    return name_list


def save_name_list_to_csv(file_path: str, name_list: List[Dict[str, Any]]) -> bool:
    """
    保存名单到CSV文件
    
    Args:
        file_path (str): CSV文件路径
        name_list (List[Dict]): 名单数据列表
        
    Returns:
        bool: 是否保存成功
    """
    # 按原序号排序，只保存次数大于0的项目
    valid_items = [item for item in name_list if item.get('count', 0) > 0]
    sorted_list = sorted(valid_items, key=lambda x: x.get('index', 0))
    
    try:
        Constants = get_constants()
        with open(file_path, 'w', encoding=Constants.FILE_ENCODING, newline='') as f:
            writer = csv.writer(f)
            for item in sorted_list:
                name = item.get('name', '')
                count = item.get('count', 1)
                formatted_name = format_name_count(name, count)
                writer.writerow([formatted_name])
            # 强制刷新到磁盘
            f.flush()
            os.fsync(f.fileno())
        
        logger = get_main_logger()
        logger.operation_complete("保存名单文件", file_path)
        return True
        
    except Exception as e:
        logger = get_main_logger()
        logger.error("保存名单文件失败", str(e))
        return False


def log_deduction(username: str, deducted_count: int, reason: str = "", 
                 log_file: str = None) -> None:
    """
    记录次数扣除日志
    
    Args:
        username (str): 用户名
        deducted_count (int): 扣除次数
        reason (str): 扣除原因
        log_file (str): 日志文件路径
    """
    try:
        if log_file is None:
            Constants = get_constants()
            log_file = Constants.DEDUCTION_LOG_FILE
            
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {username} - 扣除 {deducted_count} 次"
        if reason:
            log_entry += f" - {reason}"
        log_entry += "\n"
        
        Constants = get_constants()
        with open(log_file, 'a', encoding=Constants.FILE_ENCODING) as f:
            f.write(log_entry)
            
    except Exception as e:
        logger = get_main_logger()
        logger.error("写入扣除日志失败", str(e))


def ensure_directory_exists(file_path: str) -> None:
    """
    确保文件所在目录存在
    
    Args:
        file_path (str): 文件路径
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            logger = get_main_logger()
            logger.error("创建目录失败", f"{directory}: {str(e)}")


def validate_cookies(cookies: Dict[str, Any]) -> bool:
    """
    验证cookies是否有效
    
    Args:
        cookies (dict): cookies字典
        
    Returns:
        bool: cookies是否有效
    """
    if not isinstance(cookies, dict):
        return False
    
    # 检查必要的cookie字段
    required_fields = ['SESSDATA', 'bili_jct']
    for field in required_fields:
        if field not in cookies or not cookies[field]:
            return False
    
    return True


def filter_cookie_data(cookies: Dict[str, Any]) -> Dict[str, str]:
    """
    过滤cookies数据，只保留字符串类型的cookie值
    
    Args:
        cookies (dict): 原始cookies字典
        
    Returns:
        dict: 过滤后的cookies字典
    """
    return {k: v for k, v in cookies.items() 
            if k != 'user_info' and isinstance(v, str)}


def create_backup_filename(original_file: str) -> str:
    """
    创建备份文件名
    
    Args:
        original_file (str): 原始文件路径
        
    Returns:
        str: 备份文件路径
    """
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(original_file)
    return f"{name}_backup_{timestamp}{ext}"


def __getattr__(name):
    """动态导入模块属性以避免循环导入"""
    if name == 'show_notification':
        from .notification import show_notification
        return show_notification
    elif name == 'show_copy_notification':
        from .notification import show_copy_notification
        return show_copy_notification
    elif name == 'main_logger':
        # 为了向后兼容，提供main_logger的访问
        return get_main_logger()
    elif name == 'queue_logger':
        # 为了向后兼容，提供queue_logger的访问
        return get_queue_logger()
    elif name == 'gui_logger':
        # 为了向后兼容，提供gui_logger的访问
        return get_gui_logger()
    elif name == 'bilibili_logger':
        # 为了向后兼容，提供bilibili_logger的访问
        return get_bilibili_logger()
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
