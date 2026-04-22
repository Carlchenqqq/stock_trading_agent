# -*- coding: utf-8 -*-
"""
行业板块筛选模块

使用 AKShare 获取东方财富行业板块数据，筛选热门行业及行业领涨个股。
主要功能：
1. 获取热门行业板块（按涨跌幅排序）
2. 获取指定行业的成分股（按涨跌幅排序）
3. 综合筛选：热门行业 + 行业领涨个股
"""

import akshare as ak


def get_hot_industries(top_n=10):
    """
    获取热门行业板块

    调用东方财富行业板块接口，按涨跌幅降序排列，返回前 top_n 个热门行业。

    参数:
        top_n (int): 返回的行业数量，默认10

    返回:
        list[dict]: 热门行业列表，每项包含:
            - name (str): 行业名称
            - code (str): 行业代码
            - change_pct (float): 涨跌幅(%)
            - leader (str): 领涨股名称
            - leader_change_pct (float): 领涨股涨跌幅(%)
            失败时返回空列表
    """
    try:
        # 获取东方财富行业板块名称及涨跌幅数据
        df = ak.stock_board_industry_name_em()

        # 按涨跌幅降序排列，取前 top_n 个行业
        df = df.sort_values(by='涨跌幅', ascending=False).head(top_n)

        result = []
        for _, row in df.iterrows():
            result.append({
                'name': row.get('板块名称', ''),
                'code': row.get('板块代码', ''),
                'change_pct': round(float(row.get('涨跌幅') or 0), 2),
                'leader': row.get('领涨股票', ''),
                'leader_change_pct': round(float(row.get('领涨股票-涨跌幅') or 0), 2),
            })

        return result

    except Exception as e:
        # 异常处理：记录错误并返回空列表
        print(f"[行业筛选] 获取热门行业失败: {e}")
        return []


def get_industry_stocks(industry_code, top_n=10):
    """
    获取指定行业的成分股

    调用东方财富行业板块成分股接口，按涨跌幅降序排列，返回前 top_n 只个股。

    参数:
        industry_code (str): 行业板块代码
        top_n (int): 返回的个股数量，默认10

    返回:
        list[dict]: 行业成分股列表，每项包含:
            - ts_code (str): 股票代码
            - name (str): 股票名称
            - price (float): 最新价
            - change_pct (float): 涨跌幅(%)
            - volume (float): 成交量(手)
            - amount (float): 成交额(元)
            失败时返回空列表
    """
    try:
        # 获取指定行业板块的成分股数据
        df = ak.stock_board_industry_cons_em(symbol=industry_code)

        # 按涨跌幅降序排列，取前 top_n 只个股
        df = df.sort_values(by='涨跌幅', ascending=False).head(top_n)

        result = []
        for _, row in df.iterrows():
            result.append({
                'ts_code': row.get('代码', ''),
                'name': row.get('名称', ''),
                'price': round(float(row.get('最新价') or 0), 2),
                'change_pct': round(float(row.get('涨跌幅') or 0), 2),
                'volume': round(float(row.get('成交量') or 0), 2),
                'amount': round(float(row.get('成交额') or 0), 2),
            })

        return result

    except Exception as e:
        # 异常处理：记录错误并返回空列表
        print(f"[行业筛选] 获取行业成分股失败(industry_code={industry_code}): {e}")
        return []


def screen_all(top_n=10, stocks_per_industry=10):
    """
    综合筛选：热门行业及其领涨个股

    先获取热门行业板块，再逐一获取每个行业的领涨成分股，
    最终返回结构化的筛选结果。

    参数:
        top_n (int): 返回的热门行业数量，默认10
        stocks_per_industry (int): 每个行业返回的个股数量，默认10

    返回:
        dict: 筛选结果，格式如下:
            {
                "industries": [
                    {
                        "name": "行业名称",
                        "code": "行业代码",
                        "change_pct": 3.25,
                        "stocks": [
                            {
                                "ts_code": "000001",
                                "name": "平安银行",
                                "price": 12.50,
                                "change_pct": 5.10,
                                "volume": 100000.0,
                                "amount": 1250000.0
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }
            失败时 industries 为空列表
    """
    try:
        # 第一步：获取热门行业板块
        hot_industries = get_hot_industries(top_n=top_n)

        if not hot_industries:
            print("[行业筛选] 未获取到热门行业数据")
            return {'industries': []}

        # 第二步：逐一获取每个行业的领涨成分股
        industries_result = []
        for industry in hot_industries:
            industry_code = industry.get('code', '')
            if not industry_code:
                continue

            # 获取该行业的成分股
            stocks = get_industry_stocks(industry_code, top_n=stocks_per_industry)

            industries_result.append({
                'name': industry['name'],
                'code': industry['code'],
                'change_pct': industry['change_pct'],
                'stocks': stocks,
            })

        return {'industries': industries_result}

    except Exception as e:
        # 异常处理：记录错误并返回空结果
        print(f"[行业筛选] 综合筛选失败: {e}")
        return {'industries': []}


# 模块自测
if __name__ == '__main__':
    print("=== 测试：获取热门行业 ===")
    industries = get_hot_industries(top_n=5)
    for ind in industries:
        print(f"  {ind['name']}({ind['code']}): {ind['change_pct']}% | 领涨: {ind['leader']}({ind['leader_change_pct']}%)")

    print("\n=== 测试：综合筛选 ===")
    result = screen_all(top_n=3, stocks_per_industry=3)
    for ind in result['industries']:
        print(f"\n行业: {ind['name']}({ind['code']}) 涨跌幅: {ind['change_pct']}%")
        for stock in ind['stocks']:
            print(f"  {stock['name']}({stock['ts_code']}): {stock['price']}元 {stock['change_pct']}% 成交额:{stock['amount']}")
