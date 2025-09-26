#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""投票核心管理模块"""
from __future__ import annotations
import os
import json
import time
from typing import Dict, Optional, List, Tuple
from dataclasses import asdict
from .vote_models import VoteConfig, VoteResult
from utils import gui_logger

PRESETS_DIR = "vote_presets"

class VoteManager:
    def __init__(self):
        self.current_result: Optional[VoteResult] = None
        self.is_running: bool = False
        # 创建预设目录
        if not os.path.exists(PRESETS_DIR):
            os.makedirs(PRESETS_DIR, exist_ok=True)

    # ---------------- 预设管理 ----------------
    def get_preset_path(self, name: str) -> str:
        if not name.lower().endswith('.json'):
            name = f"{name}.json"
        safe_name = name.replace('/', '_').replace('\\', '_')
        return os.path.join(PRESETS_DIR, safe_name)

    def save_preset(self, config: VoteConfig, file_name: Optional[str] = None, overwrite: bool = True) -> str:
        """保存预设
        使用 auto_end_seconds 字段而不是运行时 timestamp, 以便下次加载时重新计算。
        """
        if config.auto_end_timestamp and not config.auto_end_seconds:
            # 尝试推导原始秒数（大概值）
            remain = int(config.auto_end_timestamp - time.time())
            if remain > 0:
                config.auto_end_seconds = remain
        if not file_name:
            base = config.preset_name or config.title or 'vote'
            file_name = f"{base}.json"
        path = self.get_preset_path(file_name)
        if os.path.exists(path) and not overwrite:
            raise FileExistsError("预设已存在且未允许覆盖")
        # 确保不写入运行时 timestamp
        temp_ts = config.auto_end_timestamp
        config.auto_end_timestamp = None
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        # 还原（以免影响当前运行中的对象）
        config.auto_end_timestamp = temp_ts
        gui_logger.operation_complete("保存投票预设", path)
        return path

    def load_preset(self, path: str) -> Optional[VoteConfig]:
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return VoteConfig.from_dict(data)

    def delete_preset(self, name_or_path: str) -> bool:
        path = name_or_path
        if not os.path.isabs(path):
            path = os.path.join(PRESETS_DIR, name_or_path)
        if not path.lower().endswith('.json'):
            path += '.json'
        if os.path.exists(path):
            try:
                os.remove(path)
                gui_logger.operation_complete("删除投票预设", path)
                return True
            except Exception as e:
                gui_logger.error("删除投票预设失败", str(e))
        return False

    def list_presets(self) -> List[str]:
        if not os.path.exists(PRESETS_DIR):
            return []
        return [os.path.join(PRESETS_DIR, f) for f in os.listdir(PRESETS_DIR) if f.endswith('.json')]

    # ---------------- 投票控制 ----------------
    def start_vote(self, config: VoteConfig) -> bool:
        if self.is_running:
            gui_logger.warning("已有投票正在进行，忽略新的开始请求")
            return False
        if not config.options:
            gui_logger.warning("投票选项为空，无法开始")
            return False
        counts = {i+1: 0 for i in range(len(config.options))}
        self.current_result = VoteResult(config=config, start_time=int(time.time()), counts=counts)
        self.is_running = True
        gui_logger.info("投票已开始", f"标题: {config.title}, 选项数: {len(config.options)}")
        return True

    def end_vote(self) -> Optional[VoteResult]:
        if not self.is_running or not self.current_result:
            return None
        self.current_result.end_time = int(time.time())
        self.is_running = False
        gui_logger.info("投票已结束", self.current_result.config.title)
        return self.current_result

    def tick_auto_end(self) -> Optional[VoteResult]:
        if not self.is_running or not self.current_result:
            return None
        ts = self.current_result.config.auto_end_timestamp
        if ts and time.time() >= ts:
            return self.end_vote()
        return None

    # ---------------- 投票处理 ----------------
    def handle_vote_danmaku(self, uid: int, raw_text: str) -> Tuple[bool, Optional[int]]:
        """处理弹幕投票输入
        返回 (是否有效, 计入的选项号或None)"""
        if not self.is_running or not self.current_result:
            return (False, None)
        text = raw_text.strip()
        if not text.isdigit():
            return (False, None)
        opt = int(text)
        if opt < 1 or opt > len(self.current_result.config.options):
            return (False, None)
        if uid in self.current_result.voters:
            # 已投票
            return (False, None)
        self.current_result.voters.add(uid)
        self.current_result.counts[opt] = self.current_result.counts.get(opt, 0) + 1
        gui_logger.debug("投票计入", f"UID={uid} 选项={opt}")
        return (True, opt)

    # ---------------- 查询与导出 ----------------
    def get_progress(self) -> Dict:
        if not self.current_result:
            return {"running": False}
        total_votes = sum(self.current_result.counts.values())
        return {
            "running": self.is_running,
            "title": self.current_result.config.title,
            "options": self.current_result.config.options,
            "counts": self.current_result.counts,
            "total_votes": total_votes,
            "voter_count": len(self.current_result.voters),
            "auto_end": self.current_result.config.auto_end_timestamp
        }

    def export_result(self, path: str) -> bool:
        if not self.current_result:
            return False
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.current_result.to_dict(), f, ensure_ascii=False, indent=2)
            gui_logger.operation_complete("导出投票结果", path)
            return True
        except Exception as e:
            gui_logger.error("导出投票结果失败", str(e))
            return False
