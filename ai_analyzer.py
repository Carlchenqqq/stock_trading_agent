#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI分析模块
==========
支持GLM和Kimi作为主力AI模型，提供智能股票分析。
"""

import os
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI分析引擎 - 支持GLM/Kimi"""

    def __init__(self):
        self.api_key = os.environ.get("AI_API_KEY", "e39dd88167644894aada6f0d39adc0af.VJ8AZYx3yOHRuYtc")
        self.api_base = os.environ.get("AI_API_BASE", "https://open.bigmodel.cn/api/paas/v4")
        self.model = os.environ.get("AI_MODEL", "glm-4.5-air")
        self._provider = self._detect_provider()

    def _detect_provider(self) -> str:
        """根据API配置自动检测提供商"""
        base = self.api_base.lower()
        if "zhipuai" in base or "bigmodel" in base:
            return "glm"
        elif "moonshot" in base or "kimi" in base:
            return "kimi"
        elif "deepseek" in base:
            return "deepseek"
        return "glm"

    def _call_api(self, messages: list) -> Optional[str]:
        """调用AI API"""
        if not self.api_key:
            return None

        try:
            import requests
            url = f"{self.api_base.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000,
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.warning(f"AI API调用失败: {resp.status_code} {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"AI API调用异常: {e}")
            return None

    def analyze_stock(self, stock_data: Dict) -> str:
        """AI分析单只股票"""
        prompt = f"""你是一位资深A股分析师。请根据以下数据，给出简洁专业的分析建议（200字以内）。

股票数据：
- 股票: {stock_data.get('name', '未知')}
- 当前价: {stock_data.get('current_price', 0)}元
- 涨跌幅: {stock_data.get('change_pct', 0):+.2f}%
- 成交额: {stock_data.get('amount', 0)/10000:.0f}万元

请从以下角度分析：
1. 短期走势判断
2. 操作建议（买入/持有/卖出）
3. 风险提示

直接给出分析结论，不要重复数据。"""

        messages = [{"role": "user", "content": prompt}]
        result = self._call_api(messages)
        if result:
            return result
        return f"[AI分析不可用] 请配置 AI_API_KEY 环境变量。\n当前提供商: {self._provider}，模型: {self.model}"

    def analyze_market(self, market_data: Dict) -> str:
        """AI分析市场整体"""
        prompt = f"""你是一位资深A股市场分析师。请根据以下市场数据，给出简洁的市场分析（200字以内）。

市场数据：
- 上证指数: {market_data.get('sh_index', 'N/A')}
- 涨跌幅: {market_data.get('sh_change', 0):+.2f}%
- 涨停家数: {market_data.get('limit_up', 0)}
- 跌停家数: {market_data.get('limit_down', 0)}
- 上涨家数: {market_data.get('up_count', 0)}
- 下跌家数: {market_data.get('down_count', 0)}

请分析：
1. 市场整体情绪
2. 短期趋势判断
3. 操作策略建议"""

        messages = [{"role": "user", "content": prompt}]
        result = self._call_api(messages)
        if result:
            return result
        return f"[AI分析不可用] 请配置 AI_API_KEY 环境变量。"

    def analyze_strategy(self, strategy_signals: Dict[str, list]) -> str:
        """AI分析策略信号"""
        signal_text = ""
        for name, signals in strategy_signals.items():
            if signals:
                top = signals[:2]
                for s in top:
                    signal_text += f"- {name}: {s.get('code','')} {s.get('action','')} (置信度{s.get('confidence',0):.0%}) {s.get('reason','')}\n"

        if not signal_text:
            signal_text = "当前无明确策略信号"

        prompt = f"""你是一位资深A股量化分析师。请根据以下策略信号，给出综合分析建议（200字以内）。

策略信号：
{signal_text}

请分析：
1. 信号一致性
2. 综合操作建议
3. 需要关注的风险"""

        messages = [{"role": "user", "content": prompt}]
        result = self._call_api(messages)
        if result:
            return result
        return f"[AI分析不可用] 请配置 AI_API_KEY 环境变量。"

    def analyze_recommendation(self, top_stocks: list) -> str:
        """AI分析推荐股票"""
        stock_text = ""
        for s in top_stocks[:5]:
            stock_text += f"- {s.get('ts_code','')} {s.get('name','')}: 评分{s.get('total_score',0):.0f}/100, 涨跌{s.get('change_pct',0):+.1f}%, 信号: {', '.join(s.get('signals',[])[:3])}\n"

        prompt = f"""你是一位资深A股投资顾问。请根据以下推荐排名，给出投资建议（200字以内）。

推荐排名：
{stock_text}

请分析：
1. 推荐股票的整体质量
2. 建议关注的标的
3. 仓位配置建议
4. 风险提示"""

        messages = [{"role": "user", "content": prompt}]
        result = self._call_api(messages)
        if result:
            return result
        return f"[AI分析不可用] 请配置 AI_API_KEY 环境变量。"

    def get_status(self) -> Dict:
        """获取AI分析器状态"""
        return {
            "provider": self._provider,
            "model": self.model,
            "configured": bool(self.api_key),
            "api_base": self.api_base if self.api_key else ""
        }
