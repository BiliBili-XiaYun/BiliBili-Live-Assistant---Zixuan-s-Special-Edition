#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
排队管理核心模块 - 处理排队逻辑和数据管理
"""

import os
import json  # 修复json模块的导入
from datetime import datetime
from typing import List, Optional, Dict, Any, Set, Tuple, Deque  # 添加Tuple和Deque导入
from PyQt6.QtCore import QTimer
import random  # 用于随机选择
from collections import deque  # 用于Deque类型

from models import QueueItem
from utils import get_queue_logger
from utils import (load_name_list_from_csv, save_name_list_to_csv, 
                  safe_json_load, safe_json_save, log_deduction)
from config import Constants, app_config
from typing import List, Optional, Dict, Any, Set, Tuple, Deque, TYPE_CHECKING


class QueueManager:
    """排队管理器核心类"""
    
    def __init__(self, name_list_file: str = None,
                 state_file: str = Constants.QUEUE_STATE_FILE):
        """初始化排队管理器"""
        # 获取队列日志器
        self.queue_logger = get_queue_logger()
        
        # 从配置中读取名单文件路径，如果参数为None的话
        if name_list_file is None:
            config_path = app_config.get("queue.name_list_file", "")
            if config_path:
                self.name_list_file = os.path.abspath(config_path)
                self.queue_logger.debug("从配置中读取名单文件路径", self.name_list_file)
            else:
                # 如果配置中也没有路径，使用默认路径但不自动加载
                default_path = os.path.abspath(Constants.get_name_list_file())
                self.name_list_file = default_path
                self.queue_logger.warning("配置中未设置名单文件路径，使用默认路径但不自动加载", default_path)
        else:
            self.name_list_file = os.path.abspath(name_list_file)
            self.queue_logger.debug("使用指定的名单文件路径", self.name_list_file)

        self.state_file = state_file
        self.count_log_file = "count_changes.txt"  # 次数变化记录文件        
        # 数据列表
        self.name_list: List[QueueItem] = []        # 名单列表
        self.queue_list: List[QueueItem] = []       # 排队队列
        self.cutline_list: List[QueueItem] = []     # 插队队列
        self.user_queued: Set[str] = set()          # 已排队的用户名
        self.user_boarded: Set[str] = set()         # 已上车的用户名
        self.user_cutline: Set[str] = set()         # 已插队的用户名
        
        # 最近中奖用户队列（长度为10的循环队列）
        self.recent_winners: Deque[str] = deque(maxlen=10)  # 存储用户名
        
        # 状态
        self.queue_started = False                  # 排队是否开始
        self.boarding_started = False               # 上车是否开始
        self.cutline_started = False                # 插队是否开始
          # 配置文件监听
        self._config_mtime = app_config.get_file_modification_time()
        self._config_timer = QTimer()
        self._config_timer.timeout.connect(self._check_config_changes)
        self._config_timer.start(1000)  # 每秒检查一次配置文件变更
        
        # 自动加载名单文件
        if self.name_list_file and os.path.exists(self.name_list_file):
            self.load_name_list()
            self.queue_logger.operation_complete("QueueManager初始化", f"已自动加载名单文件，共 {len(self.name_list)} 个项目")
        
    def add_recent_winner(self, username: str) -> bool:
        """
        添加中奖用户到最近中奖队列
        
        Args:
            username (str): 中奖用户名
            
        Returns:
            bool: 添加是否成功
        """
        # 添加用户名到最近中奖队列
        self.recent_winners.append(username)
        return True
            


    def load_name_list(self) -> bool:
        """
        加载名单文件
        
        Returns:
            bool: 是否加载成功
        """
        try:
            # 如果名单文件路径为空，跳过加载
            if not self.name_list_file or not self.name_list_file.strip():
                self.queue_logger.warning("名单文件路径为空，跳过加载")
                return True
            
            # 确保使用绝对路径
            abs_file_path = os.path.abspath(self.name_list_file)
            self.queue_logger.operation_start("加载名单文件", abs_file_path)
            
            if not os.path.exists(abs_file_path):
                self.queue_logger.error("名单文件不存在", abs_file_path)
                return False
            
            # 加载CSV数据
            name_data = load_name_list_from_csv(abs_file_path)
              # 转换为QueueItem对象
            self.name_list.clear()
            for item_data in name_data:
                queue_item = QueueItem(
                    name=item_data['name'],
                    count=item_data['count'],
                    index=item_data['index']
                )
                self.name_list.append(queue_item)
            
            self.queue_logger.operation_complete("加载名单文件", f"从 {abs_file_path} 加载 {len(self.name_list)} 个项目")

            return True
            
        except Exception as e:
            self.queue_logger.error("加载名单失败", str(e))
            self.queue_logger.debug("名单文件路径", str(self.name_list_file))
            self.queue_logger.debug("绝对路径", os.path.abspath(self.name_list_file) if self.name_list_file else "None")
            return False
    
    def save_name_list(self) -> bool:
        """
        保存名单文件
        
        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保使用绝对路径
            abs_file_path = os.path.abspath(self.name_list_file)
            self.queue_logger.operation_start("保存名单文件", abs_file_path)
            
            # 转换为字典格式
            name_data = []
            for item in self.name_list:
                if item.count > 0:  # 只保存次数大于0的项目
                    name_data.append({
                        'name': item.name,
                        'count': item.count,
                        'index': item.index
                    })
            
            success = save_name_list_to_csv(abs_file_path, name_data)
            if success:
                self.queue_logger.operation_complete("保存名单文件", abs_file_path)
            return success
            
        except Exception as e:
            self.queue_logger.error("保存名单失败", str(e))
            self.queue_logger.debug("名单文件路径", str(self.name_list_file))
            self.queue_logger.debug("绝对路径", os.path.abspath(self.name_list_file) if self.name_list_file else "None")
            return False
    
    def _load_recent_winners_from_persistent(self):
        """
        初始化最近中奖用户队列（重置为空）
        """
        self.recent_winners.clear()

    def _should_exclude_from_lottery(self, username: str) -> bool:
        """
        判断用户是否应该从抽奖中排除
        
        Args:
            username (str): 用户名
        
        Returns:
            bool: True 如果用户应该被排除，False 否则
        """
        # 检查用户是否在最近中奖队列中
        if username in self.recent_winners:
            return True
        
        # 检查用户是否已经上车
        if username in self.user_boarded:
            return True
        
        return False

    def random_select(self, count: int = 2) -> Tuple[List[int], List[str]]:
        """
        随机选择指定数量的用户，排除最近中奖和已上车的用户
        
        Args:
            count (int): 要选择的用户数量，默认为2
        
        Returns:
            Tuple[List[int], List[str]]: 选中用户的索引列表和用户名列表
        """
        available_users = []
        
        # 获取所有可用用户及其索引
        for i, item in enumerate(self.queue_list):
            username = item.name  # QueueItem对象使用name属性
            
            # 排除最近中奖和已上车的用户
            if not self._should_exclude_from_lottery(username):
                available_users.append((i, username))
        
        # 如果可用用户不足，就使用所有非最近中奖用户
        if len(available_users) < count:
            self.queue_logger.warning("可选用户数量不足", f"当前可用: {len(available_users)}，请求: {count}")
            return ([], [])
        
        # 使用当前时间戳作为随机种子
        random.seed(datetime.now().timestamp())
        
        # 随机选择用户
        selected = random.sample(available_users, count)
        indices = [i for i, _ in selected]
        usernames = [username for _, username in selected]
        
        # 将选中的用户添加到最近中奖队列
        for username in usernames:
            self.add_recent_winner(username)
        
        self.queue_logger.info("随机选择结果", str(usernames))
        self.queue_logger.debug("最近中奖队列", str(list(self.recent_winners)))
        return (indices, usernames)

    def start_queue(self) -> None:
        """开始排队"""
        self.queue_started = True
        self.user_queued.clear()
        self.queue_logger.info("排队服务已开始", "等待用户发送排队弹幕")
    
    def stop_queue(self) -> None:
        """停止排队"""
        self.queue_started = False
        self.queue_logger.info("排队服务已停止")
    
    def start_boarding(self) -> None:
        """开始上车"""
        self.boarding_started = True
        self.queue_logger.info("上车服务已开始")
    
    def stop_boarding(self) -> None:
        """停止上车"""
        self.boarding_started = False
        self.queue_logger.info("上车服务已停止")
    
    def start_cutline(self) -> None:
        """开始插队"""
        self.cutline_started = True
        self.queue_logger.info("插队服务已开始")
    
    def stop_cutline(self) -> None:
        """停止插队"""
        self.cutline_started = False
        self.queue_logger.info("插队服务已停止")
    
    def start_cutline(self) -> None:
        """开始自动插队"""
        self.cutline_started = True
        self.user_cutline.clear()
        self.queue_logger.info("自动插队服务已开始", "等待用户发送插队弹幕")
    
    def stop_cutline(self) -> None:
        """停止自动插队"""
        self.cutline_started = False
        self.queue_logger.info("自动插队服务已停止")
    

    
    def process_cutline_request(self, username: str) -> bool:
        """
        处理自动插队请求
        
        Args:
            username (str): 用户名
            
        Returns:
            bool: 是否成功加入插队队列
        """
        if not self.cutline_started:
            return False
        
        if username in self.user_cutline:
            self.queue_logger.debug("用户已在插队队列", f"用户 {username} 已插队，忽略")
            return False
        
        # 检查用户是否有足够的合并次数进行插队
        cutline_item = self._find_available_item_for_cutline(username)
        
        if cutline_item:
            # 将创建的插队项目添加到插队队列
            cutline_item.in_queue = True
            self.cutline_list.append(cutline_item)
            self.user_cutline.add(username)
            
            # 按序号排序
            self.cutline_list.sort(key=lambda x: x.index)
            self.queue_logger.operation_complete("自动插队成功", f"{username} 已加入插队队列")
            return True
        else:
            self.queue_logger.debug("用户不满足插队条件或无可用次数", f"用户 {username} 忽略插队")
            return False

    def process_queue_request(self, username: str) -> bool:
        """
        处理排队请求
        
        Args:
            username (str): 用户名
            
        Returns:
            bool: 是否成功加入队列
        """
        if not self.queue_started:
            return False
        
        if username in self.user_queued:
            self.queue_logger.debug("用户已在排队", f"用户 {username} 已排队，忽略")
            return False
        
        # 在名单中查找最小序号的匹配项
        matched_item = self._find_available_item(username)
        
        if matched_item:
            # 添加到排队队列            matched_item.in_queue = True
            self.queue_list.append(matched_item)
            self.user_queued.add(username)
              # 按序号排序
            self.queue_list.sort(key=lambda x: x.index)
            
            self.queue_logger.info("用户加入排队", f"用户 {username} (序号: {matched_item.index})")
            return True
        else:
            self.queue_logger.debug("用户不在名单中或无可用次数", f"用户 {username} 忽略排队")
            return False

    def insert_queue(self, selected_item: QueueItem) -> bool:
        """
        手动插队到插队队列
        
        Args:
            selected_item (QueueItem): 选中的项目
            
        Returns:
            bool: 是否插队成功
        """
        try:
            self.queue_logger.operation_start("尝试手动插队", f"{selected_item.name}, 当前次数: {selected_item.count}, 需要次数: {Constants.CUTLINE_COST}")
              # 检查是否有足够次数（需要2次）
            if selected_item.count >= Constants.CUTLINE_COST:
                # 次数足够，直接插队
                queue_item = QueueItem(
                    selected_item.name, 
                    Constants.CUTLINE_COST, 
                    selected_item.index, 
                    is_cutline=True
                )
                queue_item.in_queue = True
                self.cutline_list.append(queue_item)
                self.user_cutline.add(selected_item.name)
                
                # 按序号排序
                self.cutline_list.sort(key=lambda x: x.index)
                
                self.queue_logger.operation_complete("手动插队成功", f"{selected_item.name} (序号: {selected_item.index}), 剩余次数: {selected_item.count}")
                return True

            else:
                # 次数不足，查找相同名字的其他项目进行次数转移
                self.queue_logger.operation_start("次数不足", "尝试查找相同名字的其他项目进行次数转移")
                found_item = self._find_same_name_item(selected_item)
                
                if found_item:
                    needed_count = Constants.CUTLINE_COST - selected_item.count
                    self.queue_logger.debug("找到相同名字项目", f"{found_item.name}, 次数: {found_item.count}, 需要转移: {needed_count}")
                      # 检查找到的项目是否有足够次数用于转移
                    if found_item.count >= needed_count:
                        # 记录次数变化
                        old_found_count = found_item.count
                        old_selected_count = selected_item.count
                        
                        # 进行次数转移
                        found_item.count -= needed_count
                        selected_item.count += needed_count
                        
                        # 记录次数变化
                        self.log_count_change(found_item.name, old_found_count, found_item.count, f"为{selected_item.name}插队转移次数")
                        self.log_count_change(selected_item.name, old_selected_count, selected_item.count, f"从{found_item.name}接收插队次数")
                        
                        # 立即保存名单
                        self.save_name_list_immediately()
                        self.queue_logger.operation_complete("次数转移", f"{found_item.name} -> {selected_item.name}, 转移次数: {needed_count}")

                        queue_item = QueueItem(
                            selected_item.name, 
                            Constants.CUTLINE_COST, 
                            selected_item.index, 
                            is_cutline=True
                        )
                        queue_item.in_queue = True
                        self.cutline_list.append(queue_item)
                        self.user_cutline.add(selected_item.name)
                        self.queue_logger.operation_complete("手动插队成功", f"{selected_item.name} (序号: {selected_item.index}), 剩余次数: {selected_item.count}")
                        
                        # 按序号排序
                        self.cutline_list.sort(key=lambda x: x.index)
                        return True  # 次数转移成功，插队成功                    
                    else:
                        self.queue_logger.warning("次数转移失败", f"需要: {needed_count}, 可用: {found_item.count}")
                        return False
                else:
                    self.queue_logger.warning("手动插队失败", f"{selected_item.name} 次数不足({selected_item.count}/{Constants.CUTLINE_COST})且无其他相同名字项目可用于次数转移")
                    return False
            
        except Exception as e:
            self.queue_logger.error("手动插队失败", str(e))
            import traceback
            traceback.print_exc()
            return False

    def complete_queue_item(self, index: int) -> bool:
        """
        完成排队项目
        
        Args:
            index (int): 队列索引
            
        Returns:
            bool: 是否操作成功
        """
        if 0 <= index < len(self.queue_list):
            item = self.queue_list[index]
            
            # 计算扣除次数
            deduct_count = Constants.CUTLINE_COST if item.is_cutline else Constants.NORMAL_COST
              # 在原名单中找到对应项目并减少次数
            original_item = self._find_original_item(item.index)
            if original_item:
                old_count = original_item.count
                original_item.count -= deduct_count
                
                # 记录次数变化
                self.log_count_change(original_item.name, old_count, original_item.count, f"完成排队（{'插队' if item.is_cutline else '正常排队'}）")
                
                # 立即保存名单
                self.save_name_list_immediately()
                  # 记录扣除日志
                log_deduction(item.name, deduct_count, "完成排队")
            
            # 从排队队列中移除
            item.in_queue = False
            removed_item = self.queue_list.pop(index)
            self.queue_logger.info("完成排队", f"{removed_item.name} (序号: {removed_item.index})")
            return True
        
        return False
    
    def absent_queue_item(self, index: int) -> bool:
        """
        排队项目不在（直接删除）
        
        Args:
            index (int): 队列索引
            
        Returns:
            bool: 是否操作成功
        """
        if 0 <= index < len(self.queue_list):
            item = self.queue_list.pop(index)
            item.in_queue = False            # 从已排队用户集合中移除
            if item.name in self.user_queued:
                self.user_queued.remove(item.name)
            
            self.queue_logger.info("删除排队", item.name)
            return True
        return False
    
    def clear_queues(self) -> None:
        """清空所有队列"""
        # 重置排队状态
        for item in self.queue_list:
            item.in_queue = False
        
        # 重置上车状态
        for item in self.name_list:
            if item.in_boarding:
                item.in_boarding = False
          # 清空队列
        self.queue_list.clear()
        self.user_queued.clear()
        self.user_boarded.clear()
        
        self.queue_logger.info("队列已清空")
    
    def get_available_items(self) -> List[QueueItem]:
        """
        获取可用的名单项目（次数大于0，不论是否已在队列中）
        
        Returns:
            List[QueueItem]: 可用项目列表
        """
        return [item for item in self.name_list 
                if item.count > 0]
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态信息
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            'queue_started': self.queue_started,
            'total_names': len(self.name_list),
            'queue_count': len(self.queue_list),
            'boarding_count': len(self.user_boarded),
            'available_count': len(self.get_available_items()),
            'queued_users': len(self.user_queued)
        }
    
    def save_state(self) -> bool:
        """
        保存队列状态
        
        Returns:
            bool: 是否保存成功
        """
        try:
            state_data = {
                'queue_started': self.queue_started,
                'boarding_started': self.boarding_started,
                'user_queued': list(self.user_queued),
                'user_boarded': list(self.user_boarded),
                'queue_list': [self._item_to_dict(item) for item in self.queue_list],
                'name_list': [self._item_to_dict(item) for item in self.name_list]
            }
            
            return safe_json_save(self.state_file, state_data)
            
        except Exception as e:
            self.queue_logger.error("保存状态失败", str(e))
            return False
    
    def load_state(self) -> bool:
        """
        加载队列状态
        
        Returns:
            bool: 是否加载成功
        """
        try:
            state_data = safe_json_load(self.state_file)
            if not state_data:
                return False            # 恢复状态
            self.queue_started = state_data.get('queue_started', False)
            self.boarding_started = state_data.get('boarding_started', False)
            self.user_queued = set(state_data.get('user_queued', []))
            self.user_boarded = set(state_data.get('user_boarded', []))
            
            # 恢复队列
            self.queue_list = [self._dict_to_item(item_dict) 
                              for item_dict in state_data.get('queue_list', [])]
            
            # 恢复名单（如果有的话）
            if 'name_list' in state_data:
                self.name_list = [self._dict_to_item(item_dict) 
                                for item_dict in state_data['name_list']]
            
            self.queue_logger.operation_complete("队列状态加载", "成功")
            return True
            
        except Exception as e:
            self.queue_logger.error("加载状态失败", str(e))
            return False
    
    def reload_name_list_preserve_queues(self) -> bool:
        """
        重新加载名单文件，但保留现有队列
        
        Returns:
            bool: 是否加载成功
        """
        try:
            # 确保使用绝对路径
            abs_file_path = os.path.abspath(self.name_list_file)
            self.queue_logger.operation_start("重新加载名单文件", abs_file_path)
            
            if not os.path.exists(abs_file_path):
                self.queue_logger.error("名单文件不存在", abs_file_path)
                return False
              # 保存当前队列中的名单项目状态
            queue_states = {}  # name -> QueueItem (保存队列中的项目)
            
            # 记录队列中的项目            
            for item in self.queue_list:
                queue_states[item.name] = item
            
            # 加载CSV数据
            name_data = load_name_list_from_csv(abs_file_path)
            
            # 清空并重新构建名单
            self.name_list.clear()
            for item_data in name_data:
                queue_item = QueueItem(
                    name=item_data['name'],
                    count=item_data['count'],
                    index=item_data['index']
                )
                
                # 如果这个名字在队列中，保持其队列状态
                if queue_item.name in queue_states:
                    old_item = queue_states[queue_item.name]
                    queue_item.in_queue = old_item.in_queue
                    queue_item.is_cutline = old_item.is_cutline
                
                self.name_list.append(queue_item)
            
            # 更新队列中的项目引用，确保它们指向新的名单项目
            self._update_queue_references()
            
            self.queue_logger.operation_complete("重新加载名单", f"加载 {len(self.name_list)} 个项目，保留现有队列")
            return True
            
        except Exception as e:
            self.queue_logger.error("重新加载名单失败", str(e))
            return False
    
    def _update_queue_references(self):
        """更新队列中项目的引用，确保它们指向最新的名单项目"""
        # 创建名字到名单项目的映射
        name_to_item = {item.name: item for item in self.name_list}
          # 更新排队队列
        for i, queue_item in enumerate(self.queue_list):
            if queue_item.name in name_to_item:
                new_item = name_to_item[queue_item.name]
                # 保留队列状态，但更新引用
                new_item.in_queue = True
                new_item.is_cutline = queue_item.is_cutline
                self.queue_list[i] = new_item

    def log_count_change(self, name: str, old_count: int, new_count: int, reason: str):
        """
        记录次数变化到txt文件
        
        Args:
            name (str): 用户名
            old_count (int): 变化前次数
            new_count (int): 变化后次数
            reason (str): 变化原因
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            change = new_count - old_count
            change_str = f"+{change}" if change > 0 else str(change)
            
            log_entry = f"[{timestamp}] {name}: {old_count} -> {new_count} ({change_str}) | 原因: {reason}\n"
            
            with open(self.count_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            self.queue_logger.debug("次数变化记录", f"{name} {old_count}->{new_count} ({reason})")
            
        except Exception as e:            
            self.queue_logger.error("记录次数变化失败", str(e))
    
    def save_name_list_immediately(self):
        """
        立即保存名单到CSV文件
        """
        try:
            # 确保使用绝对路径
            abs_file_path = os.path.abspath(self.name_list_file)
            
            # 准备保存数据
            save_data = []
            for item in self.name_list:
                save_data.append({
                    'name': item.name,
                    'count': item.count,
                    'index': item.index
                })
            
            # 保存到CSV
            save_name_list_to_csv(abs_file_path, save_data)
            self.queue_logger.operation_complete("立即保存名单", abs_file_path)
            
        except Exception as e:
            self.queue_logger.error("保存名单失败", str(e))
    
    def _find_original_item(self, index: int) -> Optional[QueueItem]:
        """
        根据索引在名单中查找原始项目
        
        Args:
            index (int): 项目索引
            
        Returns:
            Optional[QueueItem]: 找到的项目，未找到返回None
        """
        for item in self.name_list:
            if item.index == index:
                return item
        return None
    
    def _find_same_name_item(self, target_item: QueueItem) -> Optional[QueueItem]:
        """
        查找与目标项目同名但不同索引的项目（用于次数转移）
        
        Args:
            target_item (QueueItem): 目标项目
            
        Returns:
            Optional[QueueItem]: 找到的同名项目，未找到返回None
        """
        for item in self.name_list:
            if (item.name == target_item.name and 
                item.index != target_item.index and 
                item.count > 0 and 
                not item.in_queue):
                return item
        return None
    
    def _item_to_dict(self, item: QueueItem) -> Dict[str, Any]:
        """
        将QueueItem转换为字典（用于状态保存）
        
        Args:
            item (QueueItem): 队列项目
            
        Returns:
            Dict[str, Any]: 项目字典
        """       
        return {
            'name': item.name,
            'count': item.count,
            'index': item.index,
            'is_cutline': item.is_cutline,
            'in_queue': item.in_queue,
            'in_boarding': item.in_boarding
        }
    
    def _dict_to_item(self, item_dict: Dict[str, Any]) -> QueueItem:
        """
        将字典转换为QueueItem（用于状态加载）
        
        Args:
            item_dict (Dict[str, Any]): 项目字典
            
        Returns:
            QueueItem: 队列项目
        """
        item = QueueItem(
            name=item_dict['name'],
            count=item_dict['count'],
            index=item_dict['index'],
            is_cutline=item_dict.get('is_cutline', False)
        )
        item.in_queue = item_dict.get('in_queue', False)
        item.in_boarding = item_dict.get('in_boarding', False)
        return item

    def cancel_queue_item(self, index: int) -> bool:
        """
        取消排队项目（不扣除次数）
        
        Args:
            index (int): 队列索引
            
        Returns:
            bool: 是否操作成功
        """
        if 0 <= index < len(self.queue_list):
            item = self.queue_list[index]
            
            # 从排队队列中移除，但不扣除次数
            item.in_queue = False
            removed_item = self.queue_list.pop(index)
            
            # 从已排队用户集合中移除
            if removed_item.name in self.user_queued:
                self.user_queued.remove(removed_item.name)
            
            self.queue_logger.info("取消排队", f"{removed_item.name} (序号: {removed_item.index}) - 未扣除次数")
            return True
        
        return False

    def add_queue(self, username: str) -> bool:
        """
        手动添加用户到排队队列（不受queue_started状态限制）
        
        Args:
            username (str): 用户名
            
        Returns:
            bool: 是否成功加入队列
        """
        if username in self.user_queued:
            self.queue_logger.debug("用户已在排队", f"用户 {username} 已排队，忽略")
            return False
        
        # 在名单中查找最小序号的匹配项
        matched_item = self._find_available_item(username)
        
        if matched_item:
            # 添加到排队队列
            matched_item.in_queue = True
            self.queue_list.append(matched_item)
            self.user_queued.add(username)
            
            # 按序号排序
            self.queue_list.sort(key=lambda x: x.index)
            
            self.queue_logger.info("手动添加用户到排队队列", f"{username} (序号: {matched_item.index})")
            return True
        else:
            self.queue_logger.warning("用户无法添加到排队", f"{username} 不在名单中或无可用次数")
            return False

    def _find_available_item(self, username: str) -> Optional[QueueItem]:
        """
        根据用户名在名单中查找可用的匹配项目（序号最小的）
        
        Args:
            username (str): 用户名
            
        Returns:
            Optional[QueueItem]: 找到的可用项目，未找到返回None
        """
        matched_items = []
          # 查找所有匹配的项目
        for item in self.name_list:
            if (item.name == username and 
                item.count > 0 and 
                not item.in_queue):
                matched_items.append(item)
        
        # 如果找到匹配项目，返回序号最小的
        if matched_items:
            matched_items.sort(key=lambda x: x.index)
            return matched_items[0]
        
        return None
    
    def _find_available_item_for_cutline(self, username: str) -> Optional[QueueItem]:
        """
        为插队功能查找可用的用户项目，采用合并次数检查方式
        从倒数第一个开始检查，合并所有同名用户的次数
        
        Args:
            username (str): 用户名
            
        Returns:
            Optional[QueueItem]: 如果总次数足够插队，返回最晚上舰的可用项目；否则返回None
        """
        # 找到所有匹配用户名且未在队列中的项目
        matched_items = []
        for item in self.name_list:
            if (item.name == username and 
                item.count > 0 and 
                not item.in_queue):
                matched_items.append(item)
        
        if not matched_items:
            return None
        
        # 按序号倒序排列（从最晚上舰的开始）
        matched_items.sort(key=lambda x: x.index, reverse=True)
        
        # 计算总可用次数
        total_count = sum(item.count for item in matched_items)
        
        # 检查总次数是否足够插队
        if total_count < Constants.CUTLINE_COST:
            return None
        
        # 从最晚上舰的项目开始，累计次数直到满足插队需求
        accumulated_count = 0
        selected_items = []
        
        for item in matched_items:
            selected_items.append(item)
            accumulated_count += item.count
            
            if accumulated_count >= Constants.CUTLINE_COST:
                break
        
        # 使用最晚上舰的项目作为代表（序号最大的）
        primary_item = selected_items[0]
        
        # 创建插队项目，使用最晚上舰项目的序号
        cutline_item = QueueItem(
            username,
            Constants.CUTLINE_COST,
            primary_item.index,
            is_cutline=True
        )
        
        self.queue_logger.debug("插队次数合并检查", 
                               f"用户 {username} 总可用次数: {total_count}, "
                               f"需要次数: {Constants.CUTLINE_COST}, "
                               f"使用序号: {primary_item.index}")
        
        return cutline_item
    
    def set_name_list_file(self, file_path: str):
        """
        设置名单文件路径，并保存到配置中
        
        Args:
            file_path (str): 新的名单文件路径
        """
        # 确保使用绝对路径
        if file_path and file_path.strip():
            abs_path = os.path.abspath(file_path.strip())
            self.name_list_file = abs_path
            
            # 保存到配置中
            app_config.set("queue.name_list_file", abs_path)
            app_config.save_config()
            self.queue_logger.operation_complete("更新名单文件路径", f"保存到配置: {abs_path}")
        else:
            # 清空路径
            self.name_list_file = ""
            app_config.set("queue.name_list_file", "")
            app_config.save_config()
            self.queue_logger.info("清空名单文件路径并保存到配置")
    
    def get_name_list_file(self) -> str:
        """
        获取当前名单文件路径
        
        Returns:
            str: 当前名单文件路径
        """
        return self.name_list_file
    
    def reload_name_list_file_from_config(self):
        """
        从配置文件重新加载名单文件路径
        当配置文件被外部修改时调用此方法同步路径
        """
        config_path = app_config.get("queue.name_list_file", "")
        if config_path:
            old_path = self.name_list_file
            self.name_list_file = os.path.abspath(config_path)
            self.queue_logger.info("从配置重新加载名单文件路径", f"{old_path} -> {self.name_list_file}")
        else:
            self.queue_logger.debug("配置中未设置名单文件路径，保持当前路径")
    
    def _check_config_changes(self):
        """检查配置文件变更并重新加载名单文件"""
        try:
            new_mtime = app_config.reload_if_modified(self._config_mtime)
            if new_mtime != self._config_mtime:
                self._config_mtime = new_mtime
                # 配置文件已更新，检查名单文件路径是否改变
                new_path = app_config.get("queue.name_list_file", "")
                if new_path and new_path.strip():
                    new_abs_path = os.path.abspath(new_path.strip())
                    if new_abs_path != self.name_list_file:
                        self.queue_logger.info("检测到名单文件路径变更", f"{self.name_list_file} -> {new_abs_path}")
                        self.name_list_file = new_abs_path
                        # 重新加载名单文件
                        self.load_name_list()
                        self.queue_logger.operation_complete("名单文件重新加载", "成功")
        except Exception as e:
            self.queue_logger.error("检查配置变更时出错", str(e))
    
    def refresh_name_list_from_config(self):
        """手动刷新名单文件路径和数据（供外部调用）"""
        try:
            # 强制重新加载配置
            app_config.reload_config_from_file()
            self._config_mtime = app_config.get_file_modification_time()
            
            # 获取新的名单文件路径
            new_path = app_config.get("queue.name_list_file", "")
            if new_path and new_path.strip():
                new_abs_path = os.path.abspath(new_path.strip())
                if new_abs_path != self.name_list_file:
                    self.queue_logger.info("手动更新名单文件路径", f"{self.name_list_file} -> {new_abs_path}")
                    self.name_list_file = new_abs_path
                  # 重新加载名单文件
                success = self.load_name_list()
                if success:
                    self.queue_logger.operation_complete("名单文件手动刷新", "成功")
                    return True
                else:
                    self.queue_logger.error("名单文件手动刷新失败")
                    return False
            else:
                self.queue_logger.warning("配置中未设置名单文件路径")
                return False
        except Exception as e:
            self.queue_logger.error("手动刷新名单文件时出错", str(e))
            return False
    
    def process_guard_gift(self, username: str, guard_level: int, guard_months: int = 1) -> bool:
        """
        处理舰长礼物事件，自动添加用户到名单（始终启用）
        
        Args:
            username (str): 用户名
            guard_level (int): 舰长等级 (1=总督, 2=提督, 3=舰长)
            guard_months (int): 购买的月份数量，默认为1
            
        Returns:
            bool: 是否成功处理
        """
        try:
            # 获取舰长等级对应的奖励次数
            guard_rewards = app_config.get("gift_monitor.guard_rewards", {})
            guard_name = Constants.GUARD_LEVEL_NAMES.get(guard_level, f"等级{guard_level}")
            base_reward_count = guard_rewards.get(guard_name, 0)
            
            if base_reward_count <= 0:
                self.queue_logger.warning("舰长等级配置缺失", f"{guard_name} 没有配置奖励次数，跳过处理")
                return False
            
            # 计算总奖励次数：基础奖励 × 购买月份数
            total_reward_count = base_reward_count * guard_months
            
            self.queue_logger.info("检测到舰长事件", f"{username} 开通了 {guard_months}个月{guard_name}，准备添加 {total_reward_count} 次机会（{base_reward_count} × {guard_months}）")
            
            # 将用户添加到名单最后
            new_index = len(self.name_list) + 1
            new_item = QueueItem(
                name=username,
                count=total_reward_count,
                index=new_index
            )
            self.name_list.append(new_item)
            self.queue_logger.operation_complete("舰长用户添加到名单", f"{username} 开通{guard_months}个月{guard_name}，获得 {total_reward_count} 次机会")
            
            # 记录新舰长到CSV文件
            self._record_new_guard_to_csv(username, total_reward_count)
            
            # 记录日志
            if app_config.get("gift_monitor.log_gift_events", True):
                log_deduction(username, total_reward_count, f"开通{guard_months}个月{guard_name}获得奖励")            # 自动保存名单
            if app_config.get("gift_monitor.auto_save_after_add", True):
                self.save_name_list_immediately()
                self.queue_logger.operation_complete("自动保存名单到文件", "成功")
            
            return True
            
        except Exception as e:
            self.queue_logger.error("处理舰长礼物事件失败", str(e))
            return False
    
    def _find_user_in_name_list(self, username: str) -> Optional[QueueItem]:
        """
        在名单中查找用户
        
        Args:
            username (str): 用户名
              Returns:
            Optional[QueueItem]: 找到的用户项，如果没找到返回None
        """
        for item in self.name_list:
            if item.name == username:
                return item
        return None
    
    def _record_new_guard_to_csv(self, username: str, count: int):
        """
        记录新舰长到CSV文件
        
        Args:
            username (str): 用户名
            count (int): 次数 - 如果次数为1，只记录用户名，不记录次数
        """
        try:
            # 获取当前日期
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # 创建CSV文件名：../日期-新舰长.csv
            csv_filename = f"../{current_date}-新舰长.csv"
            csv_filepath = os.path.abspath(csv_filename)
            
            # 准备记录内容：如果次数为1只记录用户名，否则记录用户名（次数）
            if count == 1:
                record_content = f"{username}\n"
                self.queue_logger.info("记录新舰长", f"{username}（次数为1，只记录名字）")
            else:
                record_content = f"{username}（{count}\n"
                self.queue_logger.info("记录新舰长", f"{username}（{count}）")
            
            # 检查文件是否存在，如果不存在则创建并写入标题头
            file_exists = os.path.exists(csv_filepath)
            with open(csv_filepath, 'a', encoding='utf-8', newline='') as f:
                if not file_exists:
                    # 写入CSV标题头
                    f.write("用户名\n")
                
                # 写入新舰长记录
                f.write(record_content)
            
            self.queue_logger.operation_complete("记录新舰长到文件", csv_filepath)
            if count == 1:
                self.queue_logger.debug("记录内容", username)
            else:
                self.queue_logger.debug("记录内容", f"{username}（{count}")
        
        except Exception as e:
            self.queue_logger.error("记录新舰长到CSV文件失败", str(e))
            import traceback
            traceback.print_exc()
    
    def process_boarding_request(self, username: str, is_manual: bool = False) -> bool:
        """
        处理上车请求（默认关闭，需要手动启用）
        
        Args:
            username (str): 用户名
            is_manual (bool): 是否为手动添加，如果是则不受功能开关限制
            
        Returns:
            bool: 是否成功上车
        """
        # 检查上车功能是否启用，手动添加时跳过检查
        if not self.boarding_started and not is_manual:
            self.queue_logger.debug("上车功能已关闭", f"忽略用户 {username} 的上车请求")
            return False
        
        if username in self.user_boarded:
            self.queue_logger.debug("用户已上车", f"{username} 已上车，忽略")
            return False
        
        # 在名单中查找最小序号的匹配项（专门用于上车功能）
        matched_item = self._find_available_item_for_boarding(username)
        
        if matched_item:
            # 设置上车状态并添加到已上车用户集合
            matched_item.in_boarding = True
            self.user_boarded.add(username)
            
            self.queue_logger.info("用户已上车", f"{username} (序号: {matched_item.index})")
            return True
        else:
            self.queue_logger.warning("用户无法上车", f"{username} 不在名单中或无可用次数")
            return False
    
    def complete_boarding_item(self, username: str) -> bool:
        """
        完成上车项目
        
        Args:
            username (str): 用户名
            
        Returns:
            bool: 是否操作成功
        """
        if username not in self.user_boarded:
            return False
          # 在名单中查找用户并扣除次数
        matched_item = self._find_user_in_name_list(username)
        if matched_item:
            old_count = matched_item.count
            matched_item.count -= Constants.NORMAL_COST  # 上车默认扣除1次
            matched_item.in_boarding = False  # 重置上车状态
            
            # 记录次数变化
            self.log_count_change(matched_item.name, old_count, matched_item.count, "完成上车")
            
            # 立即保存名单
            self.save_name_list_immediately()
            
            # 记录扣除日志
            log_deduction(username, Constants.NORMAL_COST, "完成上车")
        
        # 从已上车用户集合中移除
        self.user_boarded.remove(username)
        self.queue_logger.info("完成上车", username)
        return True
    
    def complete_cutline_item(self, username: str) -> bool:
        """
        完成插队项目 - 从倒数第一个开始扣除多个同名用户的次数
        
        Args:
            username (str): 用户名
            
        Returns:
            bool: 是否操作成功
        """
        if username not in self.user_cutline:
            return False
        
        # 找到所有匹配用户名且有可用次数的项目
        matched_items = []
        for item in self.name_list:
            if item.name == username and item.count > 0:
                matched_items.append(item)
        
        if not matched_items:
            return False
        
        # 按序号倒序排列（从最晚上舰的开始扣除）
        matched_items.sort(key=lambda x: x.index, reverse=True)
        
        # 计算需要扣除的总次数
        remaining_cost = Constants.CUTLINE_COST
        deducted_items = []  # 记录被扣除次数的项目
        
        # 从最晚上舰的项目开始扣除次数
        for item in matched_items:
            if remaining_cost <= 0:
                break
                
            old_count = item.count
            deduct_amount = min(item.count, remaining_cost)
            item.count -= deduct_amount
            item.in_queue = False  # 重置队列状态
            remaining_cost -= deduct_amount
            
            # 记录被扣除的项目信息
            deducted_items.append({
                'item': item,
                'old_count': old_count,
                'deducted': deduct_amount
            })
            
            self.queue_logger.debug("扣除插队次数", 
                                   f"用户 {username} (序号: {item.index}) "
                                   f"从 {old_count} 扣除 {deduct_amount} 次")
        
        # 记录所有次数变化
        for record in deducted_items:
            item = record['item']
            old_count = record['old_count']
            self.log_count_change(item.name, old_count, item.count, "完成插队")
        
        # 立即保存名单
        self.save_name_list_immediately()
        
        # 记录扣除日志
        log_deduction(username, Constants.CUTLINE_COST, "完成插队")
        
        # 从插队列表中移除
        self.cutline_list = [item for item in self.cutline_list if item.name != username]
        # 从已插队用户集合中移除
        self.user_cutline.remove(username)
        self.queue_logger.info("完成插队", f"{username} (共扣除 {Constants.CUTLINE_COST} 次)")
        return True
    
    def delete_cutline_item(self, username: str) -> bool:
        """
        取消插队项目
        
        Args:
            username (str): 用户名
            
        Returns:
            bool: 是否操作成功
        """
        if username not in self.user_cutline:
            return False
        
        # 从插队列表中移除
        self.cutline_list = [item for item in self.cutline_list if item.name != username]
        # 从已插队用户集合中移除
        self.user_cutline.remove(username)
        self.queue_logger.info("取消插队", username)
        return True
    
    def delete_boarding_item(self, username: str) -> bool:
        """
        删除上车项目（不扣除次数）
        
        Args:
            username (str): 用户名
            
        Returns:
            bool: 是否操作成功
        """        
        if username not in self.user_boarded:
            return False
        
        # 在名单中查找用户并重置上车状态
        matched_item = self._find_user_in_name_list(username)
        if matched_item:
            matched_item.in_boarding = False
        
        # 从已上车用户集合中移除
        self.user_boarded.remove(username)
        self.queue_logger.info("删除上车", username)
        return True

    def _find_available_item_for_boarding(self, username: str) -> Optional[QueueItem]:
        """
        专门用于上车功能的可用项目查找方法（不检查in_queue状态）
        
        Args:
            username (str): 用户名
            
        Returns:
            Optional[QueueItem]: 找到的可用项目，未找到返回None
        """
        matched_items = []
        for item in self.name_list:
            if (item.name == username and item.count > 0 and not item.in_boarding):
                matched_items.append(item)
        if matched_items:
            matched_items.sort(key=lambda x: x.index)
            return matched_items[0]
        return None