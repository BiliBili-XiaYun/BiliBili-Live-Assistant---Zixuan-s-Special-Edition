#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
import json
import time

@dataclass
class VoteConfig:
    title: str
    options: List[str]
    preset_name: Optional[str] = None
    auto_end_timestamp: Optional[int] = None  # 运行时实际结束时间戳（不写入预设时可为空）
    auto_end_seconds: Optional[int] = None    # 预设中保存的倒计时秒数（创建投票时转换为 timestamp）

    def to_dict(self):
        return {
            "title": self.title,
            "options": self.options,
            "preset_name": self.preset_name,
            "auto_end_timestamp": self.auto_end_timestamp,
            "auto_end_seconds": self.auto_end_seconds,
        }

    @staticmethod
    def from_dict(data: Dict):
        return VoteConfig(
            title=data.get("title", "未命名投票"),
            options=data.get("options", []),
            preset_name=data.get("preset_name"),
            auto_end_timestamp=data.get("auto_end_timestamp"),
            auto_end_seconds=data.get("auto_end_seconds")
        )

@dataclass
class VoteResult:
    config: VoteConfig
    start_time: int
    end_time: Optional[int] = None
    counts: Dict[int, int] = field(default_factory=dict)  # 选项序号 -> 票数
    voters: Set[int] = field(default_factory=set)         # 已投票用户ID集合

    def to_dict(self):
        return {
            "config": self.config.to_dict(),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "counts": self.counts,
            "voters": list(self.voters)
        }

    @staticmethod
    def from_dict(data: Dict):
        vr = VoteResult(
            config=VoteConfig.from_dict(data.get("config", {})),
            start_time=data.get("start_time", int(time.time())),
            end_time=data.get("end_time"),
            counts=data.get("counts", {}),
            voters=set(data.get("voters", []))
        )
        return vr
