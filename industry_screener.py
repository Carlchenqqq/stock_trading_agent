# -*- coding: utf-8 -*-
"""
行业板块筛选模块

使用同花顺+新浪数据源（东方财富被服务器IP拦截）
主要功能：
1. 获取热门行业板块（同花顺，按涨跌幅排序）
2. 获取行业成分股（新浪）
3. 综合筛选：热门行业 + 领涨股信息
"""

import akshare as ak


def get_hot_industries(top_n=10):
    """
    获取热门行业板块（同花顺数据源）

    返回:
        list[dict]: 热门行业列表
    """
    try:
        df = ak.stock_board_industry_summary_ths()
        # 按涨跌幅降序排列，取前 top_n 个行业
        df = df.sort_values(by='涨跌幅', ascending=False).head(top_n)

        result = []
        for _, row in df.iterrows():
            result.append({
                'name': row.get('板块', ''),
                'code': row.get('序号', ''),
                'change_pct': round(float(row.get('涨跌幅') or 0), 2),
                'leader': row.get('领涨股', ''),
                'leader_price': round(float(row.get('领涨股-最新价') or 0), 2),
                'leader_change_pct': round(float(row.get('领涨股-涨跌幅') or 0), 2),
                'up_count': int(row.get('上涨家数') or 0),
                'down_count': int(row.get('下跌家数') or 0),
                'amount': round(float(row.get('总成交额') or 0), 2),
            })
        return result
    except Exception as e:
        print(f"[行业筛选] 获取热门行业失败(同花顺): {e}")
        return []


def get_industry_stocks(industry_name, top_n=10):
    """
    获取指定行业的成分股（新浪数据源）

    参数:
        industry_name: 行业名称（同花顺分类名）
        top_n: 返回的个股数量

    返回:
        list[dict]: 行业成分股列表
    """
    try:
        # 新浪行业板块成分股
        df = ak.stock_sector_detail(sector='行业')

        # 在新浪数据中查找匹配的行业
        # 新浪返回的 df 第一列是板块名，尝试匹配
        matched = None
        for col in df.columns[:3]:
            for val in df[col].unique():
                if industry_name in str(val) or str(val) in industry_name:
                    matched = val
                    break
            if matched:
                break

        if matched is None:
            print(f"[行业筛选] 新浪中未找到行业: {industry_name}")
            return []

        # 获取该行业的成分股详情
        detail_df = ak.stock_sector_detail(sector=str(matched))
        # 取前 top_n 只，按涨跌幅排序
        if '涨跌幅' in detail_df.columns:
            detail_df = detail_df.sort_values(by='涨跌幅', ascending=False)

        result = []
        for _, row in detail_df.head(top_n).iterrows():
            result.append({
                'ts_code': str(row.get('代码', '')),
                'name': str(row.get('名称', '')),
                'price': round(float(row.get('最新价') or 0), 2),
                'change_pct': round(float(row.get('涨跌幅') or 0), 2),
                'volume': round(float(row.get('成交量') or 0), 2),
                'amount': round(float(row.get('成交额') or 0), 2),
            })
        return result
    except Exception as e:
        print(f"[行业筛选] 获取行业成分股失败(新浪): {e}")
        return []


def screen_all(top_n=10, stocks_per_industry=10):
    """
    综合筛选：热门行业及其领涨个股

    返回:
        dict: {"industries": [...]}
    """
    try:
        hot_industries = get_hot_industries(top_n=top_n)
        if not hot_industries:
            return {'industries': []}

        industries_result = []
        for industry in hot_industries:
            stocks = get_industry_stocks(industry['name'], top_n=stocks_per_industry)
            industries_result.append({
                'name': industry['name'],
                'code': industry['code'],
                'change_pct': industry['change_pct'],
                'leader': industry['leader'],
                'leader_price': industry['leader_price'],
                'leader_change_pct': industry['leader_change_pct'],
                'up_count': industry['up_count'],
                'down_count': industry['down_count'],
                'amount': industry['amount'],
                'stocks': stocks,
            })

        return {'industries': industries_result}
    except Exception as e:
        print(f"[行业筛选] 综合筛选失败: {e}")
        return {'industries': []}
