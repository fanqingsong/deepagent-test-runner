"""
LLM summarizer.

Turns the structured causal + graph results into a concise, human-readable root
cause explanation. Reuses the existing GLM client; if the LLM call fails it
falls back to a deterministic templated summary so the feature degrades
gracefully.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


_VERDICT_LABELS = {
    "regression": "Regression (likely caused by a script/test change)",
    "env_issue": "Environment-specific issue",
    "flaky": "Flaky test (non-deterministic)",
    "healthy": "Healthy",
    "inconclusive": "Inconclusive",
}


def _fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.0f}%"


def _fmt_effect(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.2f}"


class Summarizer:
    """Generates natural language root cause summaries via GLM."""

    def __init__(self, llm_client: Any = None):
        # llm_client is expected to expose async generate_response(prompt) -> obj.content
        self._llm = llm_client

    async def _call_llm(self, prompt: str) -> Optional[str]:
        if self._llm is None:
            return None
        try:
            response = await self._llm.generate_response(
                prompt=prompt,
                temperature=0.2,
                max_tokens=800,
            )
            content = getattr(response, "content", None)
            return content or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM summary generation failed: %s", exc)
            return None

    async def summarize_run(self, context: Dict[str, Any]) -> str:
        """Summarize a single run's root cause."""
        prompt = (
            "You are a senior test reliability engineer. Based on the following "
            "graph + causal-inference analysis of a failed test run, write a "
            "concise root cause summary in Chinese (3-5 sentences). Clearly state "
            "whether the failure is a regression, an environment issue, or flaky, "
            "and cite the causal effect size and p-value as evidence. Be specific.\n\n"
            f"Analysis JSON:\n{json.dumps(context, ensure_ascii=False, default=str, indent=2)}\n\n"
            "Return only the summary text (markdown allowed)."
        )
        summary = await self._call_llm(prompt)
        if summary:
            return summary.strip()
        return self._fallback_run_summary(context)

    async def summarize_global(self, communities: List[Dict[str, Any]], days: int) -> str:
        """Summarize the overall failure landscape across communities."""
        prompt = (
            "You are a senior test reliability engineer. Based on the following "
            "failure communities detected over the last "
            f"{days} days via graph community detection, write a concise Chinese "
            "summary (4-6 sentences) of the dominant failure themes, which "
            "communities matter most, and recommended next actions.\n\n"
            f"Communities JSON:\n{json.dumps(communities, ensure_ascii=False, default=str, indent=2)}\n\n"
            "Return only the summary text (markdown allowed)."
        )
        summary = await self._call_llm(prompt)
        if summary:
            return summary.strip()
        return self._fallback_global_summary(communities, days)

    # ------------------------------------------------------------------
    # Deterministic fallbacks
    # ------------------------------------------------------------------

    def _fallback_run_summary(self, ctx: Dict[str, Any]) -> str:
        verdict = ctx.get("verdict", "inconclusive")
        label = _VERDICT_LABELS.get(verdict, verdict)
        causal = ctx.get("causal") or {}
        primary = (causal.get("primary") or {}) if causal else {}
        community = ctx.get("community") or {}
        selectors = ctx.get("top_selectors") or []

        parts = [f"**结论: {label}**。"]

        if verdict == "regression" and primary:
            parts.append(
                f"时间维度分析显示，变更后通过率从 {_fmt_pct(primary.get('before_pass_rate'))} "
                f"下降到 {_fmt_pct(primary.get('after_pass_rate'))}"
                f"（因果效应 {_fmt_effect(primary.get('effect'))}, p={primary.get('p_value')}），"
                "判定为脚本/用例变更引入的回归。"
            )
        elif verdict == "env_issue" and primary:
            parts.append(
                f"在 {primary.get('treatment')} 下通过率显著更低"
                f"（因果效应 {_fmt_effect(primary.get('effect'))}, p={primary.get('p_value')}），"
                "判定为环境相关问题。"
            )
        elif verdict == "flaky":
            parts.append(
                f"在相同环境与版本下结果仍然波动（总体通过率 "
                f"{_fmt_pct(ctx.get('overall_pass_rate'))}），未发现显著确定性原因，判定为 flaky。"
            )
        else:
            parts.append("未发现具有统计显著性的单一因果原因，建议补充更多执行数据。")

        if community:
            parts.append(
                f"该失败属于故障社区「{community.get('label', community.get('id'))}」"
                f"（共 {community.get('failure_count', 0)} 次失败）。"
            )
        if selectors:
            parts.append(f"相关元素选择器: {', '.join(selectors[:3])}。")

        return " ".join(parts)

    def _fallback_global_summary(self, communities: List[Dict[str, Any]], days: int) -> str:
        if not communities:
            return f"过去 {days} 天内未检测到失败社区。"
        top = communities[0]
        lines = [
            f"过去 {days} 天共检测到 {len(communities)} 个故障社区。",
            f"最主要的社区以「{', '.join(top.get('categories', [])[:3])}」类错误为主，"
            f"累计 {top.get('failure_count', 0)} 次失败。",
            "建议优先排查失败次数最多的社区，并结合因果分析区分回归与 flaky。",
        ]
        return " ".join(lines)
