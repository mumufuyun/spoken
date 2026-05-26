"""
spoken/ai/strategies.py
AI 处理策略 — 插件化架构。

每个工作模式（A-F）对应一个策略实现：
  - DirectStrategy:     模式 A，直接返回原文
  - OpenAIStrategy:     模式 B-F，调用 OpenAI 兼容 API

使用示例::

    from spoken.ai.strategies import DirectStrategy, OpenAIStrategy
    from spoken.ai.client import AIClient

    client = AIClient(base_url="...", api_key="...")
    strategies = {
        "A": DirectStrategy(),
        "B": OpenAIStrategy(client, mode="B"),
        "C": OpenAIStrategy(client, mode="C"),
    }
"""

from __future__ import annotations

import logging
import re
import threading
from abc import ABC, abstractmethod
from typing import Callable, Optional

from .prompts import get_system_prompt

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# 处理结果
# ══════════════════════════════════════════════════════════════════════

class ProcessResult:
    """AI 处理结果封装。"""

    def __init__(
        self,
        text: str,
        mode_used: str,
        *,
        fallback: bool = False,
        interrupted: bool = False,
        timed_out: bool = False,
        error: Optional[Exception] = None,
        truncated: bool = False,
        finish_reason: Optional[str] = None,
    ) -> None:
        self.text = text
        self.mode_used = mode_used
        self.fallback = fallback
        self.interrupted = interrupted
        self.timed_out = timed_out
        self.error = error
        self.truncated = truncated
        self.finish_reason = finish_reason

    @property
    def success(self) -> bool:
        """是否成功使用了请求的 AI 模式（未发生降级）。"""
        return not self.fallback

    def __repr__(self) -> str:
        status = "OK" if self.success else "FALLBACK"
        if self.interrupted:
            status = "INTERRUPTED"
        elif self.timed_out:
            status = "TIMEOUT"
        elif self.truncated:
            status = "TRUNCATED"
        return f"ProcessResult({status}, mode={self.mode_used!r}, text={self.text[:30]!r})"


# ══════════════════════════════════════════════════════════════════════
# 策略接口
# ══════════════════════════════════════════════════════════════════════

class AIStrategy(ABC):
    """AI 处理策略接口。"""

    @abstractmethod
    def process(
        self,
        text: str,
        *,
        interrupt_event: threading.Event,
        on_chunk: Optional[Callable[[str], None]] = None,
        timeout_sec: float = 10.0,
    ) -> ProcessResult:
        """处理输入文字。

        Args:
            text: ASR 识别出的原始文字
            interrupt_event: 中断信号事件
            on_chunk: 流式回调
            timeout_sec: 超时秒数

        Returns:
            ProcessResult 对象
        """
        ...

    @property
    @abstractmethod
    def mode(self) -> str:
        """策略对应的模式标识。"""
        ...


# ══════════════════════════════════════════════════════════════════════
# 直接返回策略（模式 A）
# ══════════════════════════════════════════════════════════════════════

class DirectStrategy(AIStrategy):
    """模式 A：直接返回原文，零延迟。"""

    @property
    def mode(self) -> str:
        return "A"

    def process(
        self,
        text: str,
        *,
        interrupt_event: threading.Event,
        on_chunk: Optional[Callable[[str], None]] = None,
        timeout_sec: float = 10.0,
    ) -> ProcessResult:
        return ProcessResult(text=text, mode_used="A")


# ══════════════════════════════════════════════════════════════════════
# OpenAI API 策略（模式 B-F）
# ══════════════════════════════════════════════════════════════════════

class OpenAIStrategy(AIStrategy):
    """模式 B-F：通过 OpenAI 兼容 API 处理。

    不同模式通过 system prompt 区分。
    """

    def __init__(
        self,
        client: "AIClient",
        mode: str,
        *,
        custom_prompt: str = "",
        mode_timeout_sec: Optional[float] = None,
    ) -> None:
        self._client = client
        self._mode = mode
        self._custom_prompt = custom_prompt
        self._mode_timeout_sec = mode_timeout_sec

    @property
    def mode(self) -> str:
        return self._mode

    def process(
        self,
        text: str,
        *,
        interrupt_event: threading.Event,
        on_chunk: Optional[Callable[[str], None]] = None,
        timeout_sec: float = 10.0,
    ) -> ProcessResult:
        if not text.strip():
            return ProcessResult(text="", mode_used=self._mode)

        deadline = self._mode_timeout_sec or timeout_sec
        system_prompt = get_system_prompt(self._mode, custom_prompt=self._custom_prompt)

        result_holder: list = []
        done_event = threading.Event()

        def _worker() -> None:
            try:
                response = self._client.request(
                    system_prompt=system_prompt,
                    user_text=text,
                    stream=on_chunk is not None,
                    on_chunk=on_chunk,
                    interrupt_event=interrupt_event,
                )
                result_holder.append(response)
            except Exception as exc:
                result_holder.append(exc)
            finally:
                done_event.set()

        worker = threading.Thread(target=_worker, daemon=True, name=f"AIWorker-{self._mode}")
        worker.start()

        # 等待完成、超时或中断
        poll_interval = 0.1
        elapsed = 0.0
        while elapsed < deadline:
            if done_event.wait(timeout=poll_interval):
                break
            if interrupt_event.is_set():
                logger.info("AI 处理被用户中断（Esc），降级为 Mode A")
                return ProcessResult(text=text, mode_used="A", fallback=True, interrupted=True)
            elapsed += poll_interval
        else:
            logger.warning(
                "AI 请求超时（%.1fs，模式 %s），降级为 Mode A",
                deadline,
                self._mode,
            )
            return ProcessResult(text=text, mode_used="A", fallback=True, timed_out=True)

        if not result_holder:
            return ProcessResult(text=text, mode_used="A", fallback=True)

        payload = result_holder[0]
        if isinstance(payload, Exception):
            logger.error("AI API 调用失败，降级为 Mode A: %s", payload)
            return ProcessResult(text=text, mode_used="A", fallback=True, error=payload)

        # 解析结果
        finish_reason = payload.get("finish_reason")
        processed = str(payload.get("text", "")).strip()

        if finish_reason == "length" and len(processed) < len(text) * 0.3:
            logger.warning("AI 输出被截断，回退原始文字")
            return ProcessResult(
                text=text,
                mode_used="A",
                fallback=True,
                truncated=True,
                finish_reason=finish_reason,
            )

        # Mode C 特殊处理：规范化 prompt 输出
        if self._mode == "C":
            processed = self._normalize_prompt_output(processed)

        logger.info("AI 处理完成（模式: %s）: %s...", self._mode, processed[:30])
        return ProcessResult(
            text=processed,
            mode_used=self._mode,
            finish_reason=finish_reason,
        )

    @staticmethod
    def _normalize_prompt_output(text: str) -> str:
        """清理 Prompt 模式常见跑偏输出。"""
        import re

        cleaned = (text or "").strip()
        if not cleaned:
            return ""

        cleaned = re.sub(r"^```(?:[a-z0-9_+-]+)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.IGNORECASE).strip()

        prefixes = [
            "以下是优化后的prompt：", "以下是优化后的 prompt：",
            "以下是prompt：", "以下是 prompt：",
            "下面是优化后的prompt：", "下面是优化后的 prompt：",
            "下面是prompt：", "下面是 prompt：",
            "可以使用以下prompt：", "可以使用以下 prompt：",
            "这是一个可用的prompt：", "这是一个可用的 prompt：",
            "优化后的prompt：", "优化后的 prompt：",
            "prompt：", "Prompt:", "Prompt：",
        ]
        lowered = cleaned.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].lstrip()
                break

        cleaned = re.sub(
            r"^(?:你可以这样写|你可以这样输入|可以这样写|可以这样输入|请将以下内容发送给 AI)[:：]\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        lines = cleaned.splitlines()
        if lines and re.fullmatch(r"(?:prompt|提示词|模板|示例)", lines[0].strip(), flags=re.IGNORECASE):
            cleaned = "\n".join(lines[1:]).strip()

        return cleaned
