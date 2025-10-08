#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS 播报模块
- 首选 edge-tts（在线，微软语音），失败时自动回退 pyttsx3（Windows 上基于 SAPI）
- 支持自定义模板占位符: {username}, {message}, {giftname}, {time}, {guardname}
- 事件类型: danmaku, gift, guard, super_chat, queue, boarding, cutline
"""
from __future__ import annotations
import threading
import queue
import time
import os
import asyncio
import tempfile
import subprocess
import platform
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import sys
import shutil
from datetime import datetime

try:
    import pyttsx3  # type: ignore
    _TTS_AVAILABLE = True
except Exception:
    pyttsx3 = None  # type: ignore
    _TTS_AVAILABLE = False

try:
    import edge_tts  # type: ignore
    _EDGE_AVAILABLE = True
except Exception:
    edge_tts = None  # type: ignore
    _EDGE_AVAILABLE = False

try:
    import winsound  # type: ignore
    _WINSOUND = True
except Exception:
    _WINSOUND = False

try:
    from utils.kokoro_tts import (
        KokoroSynthesizer,
        KokoroUnavailableError,
        is_available as _KOKORO_AVAILABLE,
        builtin_voices as _kokoro_builtin_voices,
        DEFAULT_VOICE_ID as _KOKORO_DEFAULT_VOICE,
        DEFAULT_LANGUAGE as _KOKORO_DEFAULT_LANG,
    )
except Exception:
    KokoroSynthesizer = None  # type: ignore
    KokoroUnavailableError = RuntimeError  # type: ignore
    _KOKORO_AVAILABLE = False

    def _kokoro_builtin_voices() -> Dict[str, str]:  # type: ignore
        return {
            "af": "Adult Female",
            "am": "Adult Male",
        }

    _KOKORO_DEFAULT_VOICE = "af"
    _KOKORO_DEFAULT_LANG = "en"


class TTSManager:
    def __init__(self, settings: Dict[str, Any] | None = None):
        self._engine = None
        self._voices_cache = []  # 本地引擎 pyttsx3 的 voices 对象缓存
        # 语音列表缓存（按引擎区分）；edge-tts 使用 id->name 字典缓存
        self._voices_cache_mem: Dict[str, Dict[str, str]] = {}
        # 将语音列表缓存放到用户可写的持久目录（%APPDATA%/<ORG>/<APP_NAME>/）
        try:
            from version_info import ORGANIZATION_NAME, APP_NAME
            base_dir = os.path.join(os.environ.get('APPDATA', os.getcwd()), ORGANIZATION_NAME, APP_NAME)
        except Exception:
            base_dir = os.environ.get('APPDATA', os.getcwd())
        try:
            os.makedirs(base_dir, exist_ok=True)
        except Exception:
            pass
        self._voices_cache_file = os.path.join(base_dir, 'edge_tts_voices_cache.json')
        self._q: "queue.Queue[dict]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._enabled = False
        self._per_event_enabled: Dict[str, bool] = {}
        self._templates: Dict[str, str] = {}
        self._rate = 180
        self._volume = 1.0
        self._voice_id: Optional[str] = None
        # 引擎：kokoro | edge-tts | pyttsx3
        self._engine_name = "kokoro"
        self._kokoro_synth = None
        # 队列参数（不再做积压丢弃/赶进度，仅保证顺序）
        self._max_queue_size = 0             # 0 = 不限制长度（仅依赖内存）
        self._auto_degrade_threshold = 0     # 关闭自动降级
        self._auto_degraded = False          # 兼容占位
        self._edge_timeout_seconds = 12      # 单次 edge-tts 合成+播放超时秒数
        self._edge_retry = 3                 # 超时重试次数
        self._edge_strict_voice = True       # 严格校验所选语音可用性 & 音频质量
        self._seq_counter = 0                # 序号用于日志排查顺序
        self.update_settings(settings or {})
        self._ensure_worker()
        # 尝试加载语音列表缓存（不影响启动）
        try:
            self._load_voices_cache_file()
        except Exception:
            pass

    def _load_voices_cache_file(self):
        try:
            from utils import safe_json_load
            data = safe_json_load(self._voices_cache_file, default=None)
            if isinstance(data, dict):
                # 仅接受 edge-tts 的缓存结构
                cached = data.get('edge-tts')
                if isinstance(cached, dict):
                    # 规范化 key/val 为字符串
                    self._voices_cache_mem['edge-tts'] = {str(k): str(v) for k, v in cached.items()}
        except Exception:
            pass

    def _save_voices_cache_file(self):
        try:
            from utils import safe_json_save
            # 确保目录存在
            try:
                d = os.path.dirname(self._voices_cache_file)
                if d:
                    os.makedirs(d, exist_ok=True)
            except Exception:
                pass
            data = {}
            if 'edge-tts' in self._voices_cache_mem:
                data['edge-tts'] = self._voices_cache_mem['edge-tts']
            if data:
                safe_json_save(self._voices_cache_file, data)
        except Exception:
            pass

    def _log(self, level: str, title: str, detail: str):
        try:
            from utils import get_main_logger  # 延迟导入避免循环
            logger = get_main_logger()
            if level == 'error':
                logger.error(title, detail)
            elif level == 'warn' or level == 'warning':
                logger.warning(title, detail)
            else:
                logger.info(title, detail)
        except Exception:
            # 最低限度打印，避免静默
            try:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {level.upper()} {title}: {detail}")
            except Exception:
                pass

    def _compute_kokoro_speed(self) -> float:
        try:
            return max(0.5, min(2.0, float(self._rate) / 180.0))
        except Exception:
            return 1.0

    def _ensure_engine(self):
        if not _TTS_AVAILABLE:
            return
        if self._engine is None:
            try:
                self._engine = pyttsx3.init()
                self._voices_cache = self._engine.getProperty('voices') or []
                # 若未指定 voice_id，尽量选择中文语音，减少配置负担
                if not self._voice_id:
                    chosen = None
                    for v in self._voices_cache:
                        try:
                            name = (getattr(v, 'name', '') or '').lower()
                            lang = ''
                            # 某些 SAPI 驱动在 'languages' 属性中给出 locale 标识
                            try:
                                langs = getattr(v, 'languages', None)
                                if langs:
                                    lang = str(langs[0]).lower()
                            except Exception:
                                pass
                            if ('chinese' in name) or ('zh' in name) or ('中文' in name) or ('普通话' in name) or ('国话' in name) or ('zh' in lang):
                                chosen = v.id
                                break
                        except Exception:
                            continue
                    if chosen:
                        self._voice_id = chosen
            except Exception:
                self._engine = None
        if self._engine is not None:
            try:
                self._engine.setProperty('rate', int(self._rate))
                self._engine.setProperty('volume', float(self._volume))
                if self._voice_id:
                    self._engine.setProperty('voice', self._voice_id)
            except Exception:
                pass

    def _ensure_kokoro_synth(self):
        if KokoroSynthesizer is None or not _KOKORO_AVAILABLE:
            raise KokoroUnavailableError("KokoroTTS 模块未可用")
        if self._kokoro_synth is None:
            try:
                self._kokoro_synth = KokoroSynthesizer(
                    voice=_KOKORO_DEFAULT_VOICE,
                    language=_KOKORO_DEFAULT_LANG,
                )
            except Exception as exc:
                raise KokoroUnavailableError(str(exc)) from exc
        try:
            self._kokoro_synth.set_speed(self._compute_kokoro_speed())  # type: ignore[attr-defined]
            self._kokoro_synth.set_volume(self._volume)  # type: ignore[attr-defined]
        except Exception:
            pass
        return self._kokoro_synth

    def preload_kokoro(
        self,
        *,
        languages: Optional[list[str]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """提前初始化 Kokoro 管道，供启动阶段调用。"""

        if KokoroSynthesizer is None or not _KOKORO_AVAILABLE:
            if status_callback:
                status_callback("Kokoro 未安装，跳过预加载")
            return False

        try:
            synth = self._ensure_kokoro_synth()
        except KokoroUnavailableError as exc:
            if status_callback:
                status_callback(f"Kokoro 预加载失败：{exc}")
            return False
        except Exception as exc:  # pragma: no cover - 防御性
            if status_callback:
                status_callback(f"Kokoro 预加载出现错误：{exc}")
            return False

        try:
            preload_languages = languages if languages else ["zh", "en"]
            preload_kwargs = {"languages": preload_languages, "status_callback": status_callback}
            if hasattr(synth, "preload_pipelines"):
                synth.preload_pipelines(**preload_kwargs)  # type: ignore[attr-defined]
            else:  # pragma: no cover - 兼容旧版本
                if status_callback:
                    status_callback("加载 Kokoro 语音模型…")
                synth.list_voices()
                if status_callback:
                    status_callback("Kokoro 语音模型准备完成")
            return True
        except KokoroUnavailableError as exc:
            if status_callback:
                status_callback(f"Kokoro 预加载失败：{exc}")
            return False
        except Exception as exc:
            if status_callback:
                status_callback(f"Kokoro 预加载出现异常：{exc}")
            return False

    def _ensure_worker(self):
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = threading.Thread(target=self._run_loop, daemon=True)
        self._worker.start()

    def _play_media_file(self, file_path: str, cancel_event: Optional[threading.Event] = None):
        if cancel_event and cancel_event.is_set():
            raise TimeoutError('取消：播放前检测到超时标记')
        resolved = Path(file_path).resolve()
        if not resolved.exists():
            raise FileNotFoundError(str(resolved))
        suffix = resolved.suffix.lower()
        if suffix == '.wav' and _WINSOUND:
            try:
                # 使用同步播放，确保完整播放
                winsound.PlaySound(str(resolved), winsound.SND_FILENAME | winsound.SND_NODEFAULT)  # type: ignore[attr-defined]
                # 增强等待时间确保播放完全完成，特别是尾音
                import time
                time.sleep(0.3)
                winsound.PlaySound(None, winsound.SND_PURGE)  # type: ignore[attr-defined]
            except Exception as exc:
                raise RuntimeError(f'winsound 播放失败: {exc}')
            if cancel_event and cancel_event.is_set():
                raise TimeoutError('取消：播放完成后检测到超时标记')
            return

        if platform.system() != 'Windows':
            raise RuntimeError('当前平台不支持内置音频播放')

        ps_command = (
            "Add-Type -AssemblyName presentationCore; "
            "$p = New-Object System.Windows.Media.MediaPlayer; "
            f"$p.Open([uri]'" + resolved.as_uri() + "'); "
            # 等待媒体加载完成，避免开头截断
            "while($p.NaturalDuration.HasTimeSpan -eq $false){ Start-Sleep -Milliseconds 50 }; "
            # 增强准备时间，确保音频完全解码
            "Start-Sleep -Milliseconds 300; "
            # 设置音量确保清晰度
            "$p.Volume = 1.0; "
            "$p.Play(); "
            # 初始等待确保播放真正开始
            "Start-Sleep -Milliseconds 100; "
            # 等待播放完成，避免结尾截断
            "while($p.Position -lt $p.NaturalDuration.TimeSpan){ Start-Sleep -Milliseconds 30 }; "
            # 增强尾部等待确保完全播放完毕
            "Start-Sleep -Milliseconds 500; "
            "$p.Stop(); $p.Close();"
        )

        startupinfo = None
        creationflags = 0
        if hasattr(subprocess, 'STARTUPINFO'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 1)  # type: ignore[attr-defined]
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            creationflags |= getattr(subprocess, 'CREATE_NO_WINDOW')  # type: ignore[attr-defined]

        if cancel_event and cancel_event.is_set():
            raise TimeoutError('取消：播放前检测到超时标记')

        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=180,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"PowerShell 播放失败: {err}")
        if cancel_event and cancel_event.is_set():
            raise TimeoutError('取消：播放完成后检测到超时标记')

    def _run_loop(self):
        while not self._stop.is_set():
            try:
                item = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            if not self._enabled or not item:
                continue
            # 解析队列项
            try:
                text = item.get('text', '')
                ts = float(item.get('ts', time.time()))
                seq = int(item.get('seq', -1))
            except Exception:
                text, ts, seq = '', time.time(), -1
            if not text:
                continue
            # 不再做：过期丢弃 / 积压清理 / 自动降级。保证先进先出。
            engine = (self._engine_name or '').lower()
            spoke = False
            if engine == 'kokoro':
                if _KOKORO_AVAILABLE:
                    try:
                        self._speak_kokoro(text)
                        spoke = True
                    except TimeoutError:
                        self._log('warning', 'KokoroTTS 中断', '播放被取消或超时')
                    except KokoroUnavailableError as e:
                        self._log('warning', 'KokoroTTS 未就绪', str(e))
                    except Exception as e:
                        self._log('error', 'KokoroTTS 播放失败', repr(e))
                else:
                    self._log('warning', 'KokoroTTS 不可用', '未安装 KokoroTTS 依赖，将回退到备用引擎')

            if not spoke and engine == 'edge-tts' and _EDGE_AVAILABLE:
                # 超时重试（仅针对超时；非超时错误直接回退）
                timeouts = 0
                for attempt in range(1, self._edge_retry + 1):
                    cancel_event = threading.Event()
                    result_holder = {'ok': False, 'timeout': False, 'error': None, 'recoverable': False}

                    def run_once():
                        try:
                            # 第一次用用户选择的 voice，第二次改用备用晓晓
                            fallback_voice = 'zh-CN-XiaoxiaoNeural'
                            use_voice = None
                            if attempt == 2:
                                use_voice = fallback_voice
                                if use_voice != self._voice_id:
                                    self._log('warning', 'edge-tts 备用语音', f'第{attempt}次重试改用备用语音 {use_voice}')
                            self._speak_edge_tts(text, cancel_event=cancel_event, override_voice=use_voice)
                            result_holder['ok'] = True
                        except TimeoutError:
                            result_holder['timeout'] = True
                        except _RecoverableVoiceError as e:  # 可恢复错误 -> 触发备用语音或回退
                            result_holder['recoverable'] = True
                            result_holder['error'] = e
                        except Exception as e:  # 非超时错误
                            result_holder['error'] = e

                    th = threading.Thread(target=run_once, daemon=True)
                    th.start()
                    th.join(timeout=self._edge_timeout_seconds)
                    if th.is_alive():
                        # 主动标记取消，线程内部会在播放前检查
                        cancel_event.set()
                        timeouts += 1
                        self._log('warning', 'edge-tts 超时', f'第{attempt}次超时（>{self._edge_timeout_seconds}s）')
                        if attempt == 1:
                            self._log('info', 'edge-tts 重试', '准备使用备用语音晓晓进行第二次尝试')
                        elif attempt >= 2:
                            self._log('warning', 'edge-tts 回退本地', '备用语音仍然超时，将回退到本地 TTS 播放')
                        # 给线程一点时间退出（避免立即并行播放）
                        th.join(timeout=1.0)
                        if attempt >= 2:
                            # 不再继续 edge-tts，回退本地
                            break
                        continue
                    if result_holder['ok']:
                        spoke = True
                        break
                    if result_holder['timeout']:
                        timeouts += 1
                        if attempt == 1:
                            self._log('warning', 'edge-tts 内部超时', '首次内部超时，将尝试备用语音')
                            continue
                        else:
                            self._log('warning', 'edge-tts 内部超时', '备用语音仍然超时，回退本地')
                            break
                    if result_holder.get('recoverable'):
                        if attempt == 1:
                            self._log('warning', 'edge-tts 语音可恢复错误', f'首次可恢复错误: {result_holder["error"]}，尝试备用语音')
                            continue
                        else:
                            self._log('warning', 'edge-tts 备用语音仍错误', f'{result_holder["error"]}，回退本地')
                            break
                    if result_holder['error'] is not None:
                        # 非超时错误：直接退出重试，走回退
                        self._log('error', 'edge-tts 播放失败', f'非超时错误: {result_holder["error"]}')
                        break
                # 不再丢弃：若未成功 spoke，将走下方 pyttsx3 回退
            elif not spoke and engine == 'edge-tts' and not _EDGE_AVAILABLE:
                self._log('warning', 'edge-tts 不可用', '未检测到 edge-tts 模块，请确认已安装依赖或切换到本地引擎')

            # 回退到 pyttsx3
            if not spoke:
                self._ensure_engine()
                if self._engine is None:
                    self._log('error', 'TTS 回退失败', 'pyttsx3 引擎初始化失败，无法播报')
                    continue
                try:
                    self._engine.say(text)
                    self._engine.runAndWait()
                except Exception:
                    self._log('error', 'pyttsx3 播放失败', '本地引擎播放异常')
                finally:
                    # 有些环境下第二条之后会卡死，强制重置引擎最稳妥
                    try:
                        self._engine.stop()
                    except Exception:
                        pass
                    self._engine = None

    # ---------- Public API ----------
    def get_cached_voices(self) -> Dict[str, str]:
        """仅返回当前引擎的缓存语音列表，不进行网络请求。
        - edge-tts: 返回内存缓存（若无则空）
        - pyttsx3: 返回本地引擎 voices（若未初始化则会初始化）
        """
        engine = (self._engine_name or '').lower()
        if engine == 'kokoro':
            try:
                synth = self._ensure_kokoro_synth()
                voices = synth.list_voices()  # type: ignore[attr-defined]
                if voices:
                    return dict(voices)
            except KokoroUnavailableError as exc:
                self._log('warning', 'KokoroTTS 语音缓存', str(exc))
            except Exception as exc:
                self._log('warning', 'KokoroTTS 语音缓存', repr(exc))
            try:
                return dict(_kokoro_builtin_voices())
            except Exception:
                return {}
        if engine == 'edge-tts' and _EDGE_AVAILABLE:
            cached = self._voices_cache_mem.get('edge-tts')
            if isinstance(cached, dict) and cached:
                return dict(cached)
            return {}
        # pyttsx3 本地引擎
        self._ensure_engine()
        voices: Dict[str, str] = {}
        for v in (self._voices_cache or []):
            try:
                voices[v.id] = getattr(v, 'name', v.id)
            except Exception:
                continue
        return voices

    def list_voices(self) -> Dict[str, str]:
        """返回 voice_id -> name 映射，按当前引擎"""
        engine = (self._engine_name or '').lower()

        if engine == 'kokoro':
            try:
                synth = self._ensure_kokoro_synth()
                voices = synth.list_voices()
                if voices:
                    return dict(voices)
            except KokoroUnavailableError as exc:
                self._log('warning', 'KokoroTTS 语音列表', str(exc))
            except Exception as exc:
                self._log('warning', 'KokoroTTS 语音列表', repr(exc))
            try:
                return dict(_kokoro_builtin_voices())
            except Exception:
                return {
                    _KOKORO_DEFAULT_VOICE: 'Kokoro 默认女声',
                }

        if engine == 'edge-tts' and _EDGE_AVAILABLE:
            # 优先返回缓存，避免等待网络
            cached = self._voices_cache_mem.get('edge-tts')
            if cached and isinstance(cached, dict) and cached:
                return dict(cached)
            try:
                return asyncio.run(self._edge_list_voices())
            except RuntimeError:
                # 如果已有loop，创建新loop运行
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(self._edge_list_voices())
                finally:
                    loop.close()
            except Exception:
                # 兜底给常用中文声音
                return {
                    'zh-CN-XiaoxiaoNeural': '晓晓(女) - zh-CN',
                    'zh-CN-YunjianNeural': '云健(男) - zh-CN',
                    'zh-CN-XiaoyiNeural': '晓依(女) - zh-CN',
                    'zh-CN-YunxiNeural': '云希(男) - zh-CN',
                }
        # pyttsx3
        self._ensure_engine()
        voices: Dict[str, str] = {}
        for v in (self._voices_cache or []):
            try:
                voices[v.id] = getattr(v, 'name', v.id)
            except Exception:
                continue
        # 若本地语音列表为空，兜底默认中文集合，避免界面无选项
        if not voices:
            self._log('warning', '本地语音为空', 'pyttsx3 未返回可用语音，使用默认中文集合兜底')
            return {
                'zh-CN-XiaoxiaoNeural': '晓晓(女) - zh-CN',
                'zh-CN-YunjianNeural': '云健(男) - zh-CN',
                'zh-CN-XiaoyiNeural': '晓依(女) - zh-CN',
                'zh-CN-YunxiNeural': '云希(男) - zh-CN',
            }
        return voices

    async def _edge_list_voices(self) -> Dict[str, str]:
        if not _EDGE_AVAILABLE:
            self._log('warning', 'edge-tts 不可用', '列出语音时未检测到 edge-tts 模块')
            return {}
        proxy = (os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy') or
                 os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy') or None)
        # 加 3 秒超时，避免网络阻塞过久
        try:
            if proxy:
                voices = await asyncio.wait_for(edge_tts.list_voices(proxy=proxy), timeout=3.0)  # type: ignore
            else:
                voices = await asyncio.wait_for(edge_tts.list_voices(), timeout=3.0)  # type: ignore
        except asyncio.TimeoutError:
            self._log('warning', 'edge-tts 语音获取超时', '已返回默认中文语音列表，可稍后再试或检查网络/代理')
            raise
        result: Dict[str, str] = {}
        for v in voices:
            try:
                if str(v.get('Locale', '')).lower().startswith('zh'):
                    sid = v.get('ShortName') or v.get('Name')
                    name = v.get('LocalName') or v.get('DisplayName') or sid
                    if sid:
                        result[str(sid)] = str(name)
            except Exception:
                continue
        # 写入内存与文件缓存
        try:
            if result:
                self._voices_cache_mem['edge-tts'] = dict(result)
                self._save_voices_cache_file()
        except Exception:
            pass
        return result

    def _speak_edge_tts(self, text: str, cancel_event: Optional[threading.Event] = None, override_voice: Optional[str] = None):
        if not _EDGE_AVAILABLE:
            self._log('warning', 'edge-tts 不可用', '尝试合成语音时未检测到 edge-tts 模块')
            return
        # rate: 以 180 为基准，映射到 +/-100%
        try:
            rate_delta = int(round((float(self._rate) - 180.0) / 180.0 * 100.0))
            rate_delta = max(min(rate_delta, 100), -100)
            rate_pct = ("+" if rate_delta >= 0 else "") + f"{rate_delta}%"
        except Exception:
            rate_pct = "+0%"
        # volume: 0.0~1.0 -> -100%~0%（1.0 为 +0%）
        try:
            vol_delta = int(round((float(self._volume) - 1.0) * 100.0))
            vol_delta = max(min(vol_delta, 100), -100)
            vol_pct = ("+" if vol_delta >= 0 else "") + f"{vol_delta}%"
        except Exception:
            vol_pct = "+0%"

        voice = override_voice or self._voice_id or 'zh-CN-XiaoxiaoNeural'
        # 严格模式：若当前 voice 不在缓存列表且不是默认备用，则标记为可恢复错误
        if self._edge_strict_voice and override_voice is None:
            try:
                cached = self._voices_cache_mem.get('edge-tts', {})
                if cached and voice not in cached and voice != 'zh-CN-XiaoxiaoNeural':
                    raise _RecoverableVoiceError(f'所选语音 {voice} 不在当前缓存列表中')
            except _RecoverableVoiceError:
                raise
            except Exception:
                pass
        # 读取系统代理（如需要）
        proxy = (os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy') or
                 os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy') or None)

        async def gen_and_play():
            if cancel_event and cancel_event.is_set():
                raise TimeoutError('取消：开始前已标记超时')
            tmp_path = None
            try:
                # 生成音频文件（edge-tts 默认 MP3），使用系统播放
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                    tmp_path = f.name
                # 创建通信对象并保存
                if proxy:
                    communicate = edge_tts.Communicate(
                        text,
                        voice=voice,
                        rate=rate_pct,
                        volume=vol_pct,
                        proxy=proxy,
                    )
                else:
                    communicate = edge_tts.Communicate(
                        text,
                        voice=voice,
                        rate=rate_pct,
                        volume=vol_pct,
                    )
                await communicate.save(tmp_path)
                if cancel_event and cancel_event.is_set():
                    raise TimeoutError('取消：合成完成后检测到超时标记')
                # 严格模式下的音频体积质量粗检：过短音频判定为可恢复错误
                if self._edge_strict_voice and override_voice is None:
                    try:
                        if tmp_path and os.path.exists(tmp_path):
                            size = os.path.getsize(tmp_path)
                            # 经验阈值：若文本长度>10 且 MP3 < max(500B, len(text)*8) 视为可疑（可能基础占位语音 / 截断）
                            if len(text) > 10 and size < max(500, len(text) * 8):
                                raise _RecoverableVoiceError(f'音频过短 size={size} text_len={len(text)}')
                    except _RecoverableVoiceError:
                        raise
                    except Exception:
                        pass
                # 播放（阻塞，保证顺序）
                if tmp_path:
                    self._play_media_file(tmp_path, cancel_event=cancel_event)
            finally:
                if tmp_path:
                    try:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    except Exception:
                        pass

        try:
            asyncio.run(gen_and_play())
        except RuntimeError as e:
            self._log('warning', '事件循环冲突', f'使用新事件循环运行 edge-tts：{e}')
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(gen_and_play())
            finally:
                loop.close()
        except Exception as e:
            # 抛给上层以触发回退，但记录详细错误
            self._log('error', 'edge-tts 合成失败', repr(e))
            # 额外提示：语音可能失效或列表陈旧，建议刷新
            self._log('warning', '提示', '所选 Edge 语音合成失败，建议点击“刷新语音列表”后重试，或检查网络/代理设置')
            raise

    def _speak_kokoro(self, text: str):
        synth = self._ensure_kokoro_synth()
        voice_id = self._voice_id or _KOKORO_DEFAULT_VOICE
        tmp_path = None
        try:
            # 传递语速和音量参数
            kokoro_speed = self._compute_kokoro_speed()
            tmp_path = synth.synthesize_to_file(text, voice=voice_id, speed=kokoro_speed, volume=self._volume)
            
            # 播放音频文件
            self._play_media_file(str(tmp_path))
        finally:
            if tmp_path:
                try:
                    synth.cleanup_files([Path(tmp_path)])
                except Exception:
                    try:
                        Path(tmp_path).unlink(missing_ok=True)  # type: ignore[attr-defined]
                    except Exception:
                        pass

    # 已移除 Piper/Kokoro 相关代码

    def speak(self, text: str):
        if not text:
            return
        # 不再做积压丢弃，只顺序排队（可考虑未来加硬上限报警）
        # 入队
        try:
            self._seq_counter += 1
        except Exception:
            pass
        self._q.put({
            'text': text,
            'ts': time.time(),
            'seq': self._seq_counter,
        })

    def speak_event(self, event_type: str, context: Dict[str, Any]):
        if not self._enabled:
            return
        if not self._per_event_enabled.get(event_type, False):
            return
        tpl = self._templates.get(event_type, "")
        if not tpl:
            return
        try:
            # 允许模板缺字段不报错
            safe_ctx = _SafeDict(**context)
            text = tpl.format_map(safe_ctx)
        except Exception:
            text = ""
        if text:
            self.speak(text)

    def update_settings(self, settings: Dict[str, Any]):
        tts_cfg = settings.get('tts', {}) if isinstance(settings, dict) else {}
        self._enabled = bool(tts_cfg.get('enable', False))
        self._engine_name = tts_cfg.get('engine', 'kokoro')
        self._rate = int(tts_cfg.get('rate', 180))
        self._volume = float(tts_cfg.get('volume', 1.0))
        self._voice_id = tts_cfg.get('voice_id') or None
        if (self._engine_name or '').lower() == 'kokoro' and not self._voice_id:
            self._voice_id = _KOKORO_DEFAULT_VOICE
        if (self._engine_name or '').lower() != 'kokoro':
            self._kokoro_synth = None
        else:
            try:
                synth = self._ensure_kokoro_synth()
                synth.set_speed(self._compute_kokoro_speed())  # type: ignore[attr-defined]
                synth.set_volume(self._volume)  # type: ignore[attr-defined]
            except Exception:
                pass
        # 可选参数（旧流控字段兼容，但不再生效：max_queue_size / stale_* / enable_catchup_drop / auto_degrade_threshold）
        self._edge_timeout_seconds = int(tts_cfg.get('edge_timeout_seconds', self._edge_timeout_seconds))
        self._edge_retry = int(tts_cfg.get('edge_retry', self._edge_retry))
        self._edge_strict_voice = bool(tts_cfg.get('edge_strict_voice', self._edge_strict_voice))
        self._per_event_enabled = {
            'danmaku': bool(tts_cfg.get('enable_danmaku', False)),
            'gift': bool(tts_cfg.get('enable_gift', True)),
            'guard': bool(tts_cfg.get('enable_guard', True)),
            'super_chat': bool(tts_cfg.get('enable_super_chat', True)),
            'queue': bool(tts_cfg.get('enable_queue', False)),
            'boarding': bool(tts_cfg.get('enable_boarding', False)),
            'cutline': bool(tts_cfg.get('enable_cutline', False)),
        }
        self._templates = tts_cfg.get('templates', {}) or {}
        # 更新引擎属性
        if self._engine is not None:
            try:
                self._engine.setProperty('rate', int(self._rate))
                self._engine.setProperty('volume', float(self._volume))
                if self._voice_id:
                    self._engine.setProperty('voice', self._voice_id)
            except Exception:
                pass

    def shutdown(self):
        self._stop.set()
        try:
            if self._worker:
                self._worker.join(timeout=1.0)
        except Exception:
            pass
        try:
            if self._engine:
                self._engine.stop()
        except Exception:
            pass


class _SafeDict(dict):
    def __missing__(self, key):
        return ""

class _RecoverableVoiceError(Exception):
    """表示可以通过切换语音或回退本地引擎恢复的 edge-tts 可恢复错误"""
    pass
