#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KokoroTTS integration helpers (referencing弹幕姬python版实现)."""
from __future__ import annotations

import re
import tempfile
import uuid
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Tuple

try:  # pragma: no cover - optional dependency
    from kokoro import KPipeline  # type: ignore

    _KOKORO_AVAILABLE = True
    _IMPORT_ERROR: Optional[Exception] = None
except Exception as exc:  # pragma: no cover - executed when deps missing
    KPipeline = None  # type: ignore
    _KOKORO_AVAILABLE = False
    _IMPORT_ERROR = exc

try:  # pragma: no cover - optional dependency
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover
    _np = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import soundfile as _sf  # type: ignore
except Exception:  # pragma: no cover
    _sf = None  # type: ignore

DEFAULT_SAMPLE_RATE = 24_000
DEFAULT_VOICE_ID = "zf_001"
DEFAULT_LANGUAGE = "auto"
DEFAULT_REPO_ID = "hexgrad/Kokoro-82M-v1.1-zh"

_CHINESE_REGEX = re.compile(r"[\u4e00-\u9fff]")

_CHINESE_VOICES: Dict[str, str] = {
    "zf_001": "中文女声 · 001 (专业)",
    "zf_003": "中文女声 · 003",
    "zf_005": "中文女声 · 005",
    "zf_017": "中文女声 · 017",
    "zf_021": "中文女声 · 021",
    "zf_032": "中文女声 · 032",
    "zf_047": "中文女声 · 047",
    "zf_059": "中文女声 · 059",
    "zf_070": "中文女声 · 070",
    "zf_083": "中文女声 · 083",
}

_ENGLISH_VOICES: Dict[str, str] = {
    "af_maple": "英文女声 · Maple",
    "af_sol": "英文女声 · Sol",
    "af_bella": "英文女声 · Bella",
    "af_heart": "英文女声 · Heart",
    "am_adam": "英文男声 · Adam",
    "am_liam": "英文男声 · Liam",
    "am_michael": "英文男声 · Michael",
    "bf_vale": "英文女声 · Vale",
    "bm_fable": "英文男声 · Fable",
}

_VOICE_LANG: Dict[str, str] = {**{k: "zh" for k in _CHINESE_VOICES}, **{k: "en" for k in _ENGLISH_VOICES}}

_VOICE_ALIASES: Dict[str, str] = {
    "af": "af_maple",
    "am": "am_adam",
    "bf": "bf_vale",
    "bm": "bm_fable",
    "zf": "zf_001",
    "zh": "zf_001",
}


class KokoroUnavailableError(RuntimeError):
    """Raised when KokoroTTS dependencies or models are missing."""


def is_available() -> bool:
    return _KOKORO_AVAILABLE and _sf is not None


def last_import_error() -> Optional[Exception]:
    return _IMPORT_ERROR


def builtin_voices() -> Dict[str, str]:
    result = dict(_CHINESE_VOICES)
    result.update(_ENGLISH_VOICES)
    return result


class KokoroSynthesizer:
    """Light-weight wrapper around the `kokoro` pipeline with caching."""

    def __init__(
        self,
        *,
        voice: str = DEFAULT_VOICE_ID,
        language: str = DEFAULT_LANGUAGE,
        cache_dir: Optional[Path] = None,
        repo_id: str = DEFAULT_REPO_ID,
    ) -> None:
        self.voice = self._normalize_voice(voice)
        self.language = language.lower() if language else DEFAULT_LANGUAGE
        self.repo_id = repo_id
        self.cache_dir = Path(cache_dir or Path(tempfile.gettempdir()) / "kokoro_tts")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._pipelines: Dict[str, object] = {}
        self._speed = 1.0
        self._volume = 1.0
        self._voices_cache: Optional[Dict[str, str]] = None
        self._en_callable = None  # 用于中英混合处理

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def set_speed(self, speed: float) -> None:
        try:
            self._speed = max(0.5, min(2.0, float(speed)))
        except Exception:
            self._speed = 1.0

    def set_volume(self, volume: float) -> None:
        try:
            self._volume = max(0.0, min(1.0, float(volume)))
        except Exception:
            self._volume = 1.0

    def list_voices(self) -> Dict[str, str]:
        if self._voices_cache is None:
            voices = builtin_voices()
            # 如果管道可用则尝试读取实际可用声音
            try:
                zh = self._ensure_pipeline("zh")
                en = self._ensure_pipeline("en")
                voices = self._merge_voice_list(voices, zh)
                voices = self._merge_voice_list(voices, en)
            except Exception:
                pass
            self._voices_cache = voices
        return dict(self._voices_cache)

    def preload_pipelines(
        self,
        *,
        languages: Iterable[str] | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        """提前加载指定语言的 Kokoro 管道。"""

        langs = list(languages) if languages else ["zh"]
        normalized: list[str] = []
        for lang in langs:
            if not lang:
                continue
            lower = lang.lower()
            if lower.startswith("zh") or lower.startswith("z"):
                normalized.append("zh")
            else:
                normalized.append("en")

        if not normalized:
            normalized = ["zh"]

        for lang in normalized:
            if status_callback:
                status_callback(
                    "加载 Kokoro 中文语音模型…" if lang == "zh" else "加载 Kokoro 英文语音模型…"
                )
            self._ensure_pipeline(lang)

        if status_callback:
            status_callback("Kokoro 语音模型准备完成")

    def synthesize_to_file(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        language: Optional[str] = None,
        speed: Optional[float] = None,
        volume: Optional[float] = None,
    ) -> Path:
        if not text or not text.strip():
            raise ValueError("待合成文本为空")
        if not is_available():
            if _IMPORT_ERROR:
                raise KokoroUnavailableError(str(_IMPORT_ERROR))
            raise KokoroUnavailableError("KokoroTTS 模块未安装或缺少依赖 (soundfile)")
        if _sf is None:
            raise KokoroUnavailableError("缺少 soundfile 依赖，请运行 pip install soundfile")

        voice_id, lang = self._resolve_voice_and_lang(text, voice, language)
        
        # 对于中英混合文本，优先使用中文管道（它支持英文处理）
        pipeline_lang = "zh" if self._contains_mixed_or_chinese(text) else lang
        pipeline = self._ensure_pipeline(pipeline_lang)
        current_speed = self._speed if speed is None else max(0.5, min(2.0, float(speed)))
        current_volume = self._volume if volume is None else max(0.0, min(1.0, float(volume)))

        try:
            generator = pipeline(text, voice=voice_id, speed=current_speed)
        except Exception as exc:  # pragma: no cover - upstream behaviour
            raise KokoroUnavailableError(f"调用 Kokoro 管道失败: {exc}") from exc

        audio, sample_rate = self._extract_first_audio(generator)
        if audio is None:
            raise KokoroUnavailableError("Kokoro 未返回音频数据")

        if _np is not None:
            try:
                # 确保音频数据为合适的形状和类型
                data = _np.asarray(audio, dtype="float32")  # type: ignore[arg-type]
                # 如果是多维数组，展平为一维
                if data.ndim > 1:
                    data = data.flatten()
                
                # 添加静音填充和音频增强防止截断
                if data.size > 0:
                    # 计算填充长度：语速越快，需要更多填充
                    speed_factor = max(0.5, min(2.0, current_speed))
                    # 增强填充：开头200ms，结尾400ms
                    start_padding_ms = 200 + (100 if speed_factor > 1.2 else 0)  # 快速时额外100ms
                    end_padding_ms = 400 + (200 if speed_factor > 1.2 else 0)   # 快速时额外200ms
                    
                    start_samples = int(start_padding_ms * DEFAULT_SAMPLE_RATE / 1000)
                    end_samples = int(end_padding_ms * DEFAULT_SAMPLE_RATE / 1000)
                    
                    # 创建静音填充
                    start_padding = _np.zeros(start_samples, dtype="float32")
                    end_padding = _np.zeros(end_samples, dtype="float32")
                    
                    # 音频增强：对开头和结尾进行轻微渐入渐出处理
                    fade_samples = int(0.05 * DEFAULT_SAMPLE_RATE)  # 50ms渐变
                    if data.size > fade_samples * 2:
                        # 开头渐入：防止突然开始导致的咬字不清
                        fade_in = _np.linspace(0.3, 1.0, fade_samples, dtype="float32")
                        data[:fade_samples] *= fade_in
                        
                        # 结尾渐出：防止突然结束导致的尾音偏轻
                        fade_out = _np.linspace(1.0, 0.1, fade_samples, dtype="float32")
                        data[-fade_samples:] *= fade_out
                    
                    # 添加填充
                    data = _np.concatenate([start_padding, data, end_padding])
                
                # 应用音量调整
                if current_volume != 1.0:
                    data = data * current_volume
                # 确保数据在合理范围内
                if data.size > 0:
                    data = _np.clip(data, -1.0, 1.0)
            except (ValueError, TypeError) as exc:
                raise KokoroUnavailableError(f"音频数据格式转换失败: {exc}") from exc
        else:
            data = audio

        tmp_path = self.cache_dir / f"kokoro_{uuid.uuid4().hex}.wav"
        try:
            _sf.write(str(tmp_path), data, int(sample_rate or DEFAULT_SAMPLE_RATE))
        except Exception as exc:
            raise KokoroUnavailableError(f"音频文件写入失败: {exc}") from exc
        return tmp_path

    def _contains_mixed_or_chinese(self, text: str) -> bool:
        """检测文本是否包含中文或中英混合内容"""
        return bool(_CHINESE_REGEX.search(text))

    def cleanup_files(self, paths: Iterable[Path]) -> None:
        for path in paths:
            try:
                Path(path).unlink(missing_ok=True)  # type: ignore[attr-defined]
            except FileNotFoundError:  # pragma: no cover
                pass
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _normalize_voice(self, voice: Optional[str]) -> str:
        if not voice:
            return DEFAULT_VOICE_ID
        base = voice.strip()
        if base in _VOICE_ALIASES:
            return _VOICE_ALIASES[base]
        return base

    def _ensure_pipeline(self, lang: str) -> object:
        if not is_available() or KPipeline is None:
            if _IMPORT_ERROR:
                raise KokoroUnavailableError(str(_IMPORT_ERROR))
            raise KokoroUnavailableError("KokoroTTS 未安装")

        lang = "zh" if lang in ("zh", "z") else "en"
        if lang in self._pipelines:
            return self._pipelines[lang]

        lang_code = "z" if lang == "zh" else "a"
        try:
            if lang == "zh":
                # 为中文管道创建英文处理器以支持中英混合
                if self._en_callable is None:
                    self._create_en_callable()
                pipeline = KPipeline(
                    lang_code=lang_code, 
                    repo_id=self.repo_id,
                    en_callable=self._en_callable
                )
            else:
                # 纯英文管道
                pipeline = KPipeline(lang_code=lang_code, repo_id=self.repo_id)
        except Exception as exc:  # pragma: no cover - network behaviour
            raise KokoroUnavailableError(f"初始化 Kokoro 管道失败: {exc}") from exc

        self._pipelines[lang] = pipeline
        return pipeline

    def _create_en_callable(self):
        """创建英文处理器以支持中英混合文本"""
        try:
            # 创建一个临时的英文管道用于音素提取
            en_pipeline = KPipeline(lang_code='a', repo_id=self.repo_id, model=False)
            
            def en_callable(text: str) -> str:
                """将英文文本转换为音素，供中文管道使用"""
                try:
                    # 处理一些常见的专有名词
                    text_lower = text.lower()
                    if text_lower == 'kokoro':
                        return 'kˈOkəɹO'
                    elif text_lower == 'sol':
                        return 'sˈOl'
                    elif text_lower == 'maple':
                        return 'mˈeɪpəl'
                    elif text_lower == 'vale':
                        return 'vˈeɪl'
                    
                    # 使用英文管道提取音素
                    result = next(en_pipeline(text))
                    return result.phonemes if hasattr(result, 'phonemes') else text
                except Exception:
                    # 如果转换失败，返回原文本
                    return text
            
            self._en_callable = en_callable
        except Exception:
            # 如果无法创建英文处理器，设为 None（会降级为纯中文处理）
            self._en_callable = None

    def _resolve_voice_and_lang(
        self,
        text: str,
        voice: Optional[str],
        language: Optional[str],
    ) -> Tuple[str, str]:
        voice_id = self._normalize_voice(voice or self.voice)

        lang_hint = (language or self.language or DEFAULT_LANGUAGE).lower()
        if lang_hint in ("zh", "z"):
            lang = "zh"
        elif lang_hint in ("en", "a"):
            lang = "en"
        elif voice_id in _VOICE_LANG:
            lang = _VOICE_LANG[voice_id]
        else:
            lang = "zh" if _CHINESE_REGEX.search(text) else "en"

        if voice_id not in _VOICE_LANG:
            # voice 与语言不匹配时，自动切换到默认值
            voice_id = DEFAULT_VOICE_ID if lang == "zh" else "af_maple"

        return voice_id, lang

    def _extract_first_audio(self, generator) -> Tuple[Optional[object], int]:
        audio_chunks: list[object] = []
        sample_rate = DEFAULT_SAMPLE_RATE
        try:
            for result in generator:
                chunk_audio = None
                chunk_sr = None

                # Kokoro Result 对象通常有 .audio / .sample_rate
                if hasattr(result, 'audio'):
                    chunk_audio = result.audio
                    chunk_sr = getattr(result, 'sample_rate', None)
                elif hasattr(result, '__getitem__'):
                    try:
                        if len(result) >= 3:
                            chunk_audio = result[2]
                        elif len(result) == 2:
                            chunk_audio, chunk_sr = result
                        elif len(result) == 1:
                            chunk_audio = result[0]
                    except Exception:
                        chunk_audio = result
                else:
                    chunk_audio = result

                if chunk_sr:
                    try:
                        sample_rate = int(chunk_sr)
                    except Exception:
                        pass

                if chunk_audio is None:
                    continue

                if _np is not None:
                    try:
                        arr = _np.asarray(chunk_audio, dtype="float32")
                    except Exception:
                        try:
                            arr = _np.array(list(chunk_audio), dtype="float32")  # type: ignore[arg-type]
                        except Exception:
                            continue
                    if arr.ndim > 1:
                        arr = arr.flatten()
                    if arr.size == 0:
                        continue
                    audio_chunks.append(arr)
                else:
                    # 退化场景：直接追加原始数据
                    audio_chunks.append(chunk_audio)
        finally:
            try:
                generator.close()  # type: ignore[attr-defined]
            except Exception:
                pass

        if not audio_chunks:
            return None, sample_rate

        if _np is not None:
            audio = audio_chunks[0] if len(audio_chunks) == 1 else _np.concatenate(audio_chunks)
        else:
            audio = audio_chunks
        return audio, sample_rate

    def _merge_voice_list(self, existing: Dict[str, str], pipeline: object) -> Dict[str, str]:
        voices = getattr(pipeline, "voices", None)
        if isinstance(voices, dict):
            for key in voices.keys():
                if key not in existing:
                    existing[key] = key
        elif hasattr(pipeline, "voices") and isinstance(pipeline.voices, list):  # type: ignore[attr-defined]
            for key in pipeline.voices:  # type: ignore[attr-defined]
                if key not in existing:
                    existing[key] = key
        return existing


__all__ = [
    "KokoroSynthesizer",
    "KokoroUnavailableError",
    "is_available",
    "last_import_error",
    "builtin_voices",
    "DEFAULT_VOICE_ID",
    "DEFAULT_LANGUAGE",
    "DEFAULT_SAMPLE_RATE",
]
