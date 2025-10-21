import pandas as pd
import re
from pathlib import Path
import streamlit as st
from collections import Counter, defaultdict
import logging
from itertools import product # 用于共现矩阵

# --- 0. 关键词定义 (P-Tag Engine) ---
DEFINITIONS = {
    "BRAND": {
        "欧莱雅": ["欧莱雅"],
        "施华蔻": ["施华蔻"],
        "花王": ["花王", "Liese", "liese", "莉婕"],
        "爱茉莉": ["爱茉莉", "amore", "美妆仙"],
        "章华": ["章华"],
        "卡尼尔": ["卡尼尔"],
        "迪彩": ["迪彩"],
        "美源": ["美源", "Bigen"],
        "利尻昆布": ["利尻昆布", "Rishiri"],
        "三橡树": ["三橡树", "3 CHÊNES"],
    },
    "COLOR": {
        "棕色系": ["棕", "茶", "摩卡", "巧", "奶茶", "蜜", "焦糖", "栗", "咖啡", "可可"],
        "红色/橘色系": ["红", "橘", "玫瑰", "酒红", "莓", "樱", "石榴", "番茄", "辣椒", "枫叶", "脏橘"],
        "亚麻/青色系": ["亚麻", "青", "闷青", "灰绿", "橄榄", "抹茶", "薄荷", "牛油果"],
        "灰色/蓝色/紫色系": ["灰", "蓝", "紫", "芋泥", "烟灰", "雾霾", "宝蓝", "葡萄", "香芋", "蓝黑"],
        "金色/浅色系": ["金", "白金", "米金", "浅金", "香槟", "砂金", "铂金", "漂", "浅色"],
        "高饱和色系": ["潮色", "霓虹", "荧光", "女团", "动漫", "海王", "湄拉", "芭比", "电光"]
    },
    "TECH": {
        "植物": ["植物", "植萃"],
        "无氨": ["无氨", "温和"],
        "泡沫": ["泡沫", "泡泡"],
        "盖白发": ["盖白", "遮白"],
        "免漂": ["免漂", "无需漂"],
        "护理": ["护理", "护发", "不伤发", "焗油"],
    },
    "WHITENING": ["显白", "黄皮", "肤色", "亲妈", "天菜", "素颜", "提亮", "去黄", "衬肤"]
}

# --- 1. 基础清洗工具 ---
def clean_sales(sales_str):
    if not isinstance(sales_str, str):
        return int(sales_str) if isinstance(sales_str, (int, float)) else 0
    number_part = re.search(r'(\d+\.?\d*)', sales_str)
    if not number_part: return 0
    num = float(number_part.group(1))
    if '万' in sales_str: return int(num * 10000)
    return int(num)

def clean_price(price_str):
    if not isinstance(price_str, str):
        return float(price_str) if isinstance(price_str, (int, float)) else 0.0
    match = re.search(r'(\d+\.?\d*)', price_str)
    return float(match.group(1)) if match else 0.0

def apply_tags_vectorized(series, keywords_dict):
    series_lower = series.str.lower().fillna('')
    tags = pd.Series([[] for _ in range(len(series))], index=series.index)
    
    for tag, keywords in keywords_dict.items():
        pattern = '|'.join([re.escape(kw.lower()) for kw in keywords])
        if not pattern: continue
        mask = series_lower.str.contains(pattern, case=False, na=False)
        tags[mask] = tags[mask].apply(lambda x: x + [tag] if tag not in x else x)
    return tags

def apply_single_tag_vectorized(series, keywords_list):
    series_lower = series.str.lower().fillna('')
    pattern = '|'.join([re.escape(kw.lower()) for kw in keywords_list])
    if not pattern:
        return pd.Series(False, index=series.index)
    return series_lower.str.contains(pattern, case=False, na=False)

# --- 2. 核心数据加载与处理 (Cached) ---
@st.cache_data(ttl=3600)
def load_and_process_data(base_dir):
    logging.info("--- 开始加载与处理数据 ---")
    data = {}
    
    # ... (数据加载部分与上一版相同，为简洁省略) ...
    # 1. 加载电商数据 (淘宝 + 京东)
    logging.info("加载电商数据...")
    tb_files = list(base_dir.glob("淘宝商品目录/*.json"))
    tb_dfs = [pd.read_json(f, encoding='utf-8') for f in tb_files if f.exists()]
    tb_df = pd.concat(tb_dfs, ignore_index=True) if tb_dfs else pd.DataFrame(columns=['产品名称', '产品价格', '付款人数', '地理位置', '关键词'])
    
    jd_file = base_dir / "京东-商品搜索.json"
    jd_df = pd.read_json(jd_file, encoding='utf-8') if jd_file.exists() else pd.DataFrame(columns=['商品名称', '价格', '评价人数', '搜索关键词'])

    tb_unified = pd.DataFrame({
        'title': tb_df['产品名称'], 'price': tb_df['产品价格'].apply(clean_price), 'sales': tb_df['付款人数'].apply(clean_sales),
        'location': tb_df['地理位置'].astype(str).str.split(' ').str[0], 'platform': 'Taobao', 
        'keyword': tb_df.get('关键词', None)
    })
    jd_unified = pd.DataFrame({
        'title': jd_df['商品名称'], 'price': jd_df['价格'].apply(clean_price), 'sales': jd_df['评价人数'].apply(clean_sales),
        'location': '未知', 'platform': 'JD', 
        'keyword': jd_df.get('搜索关键词', None)
    })
    ecom_df = pd.concat([tb_unified, jd_unified], ignore_index=True).dropna(subset=['title'])
    ecom_df = ecom_df[(ecom_df['price'] > 10) & (ecom_df['price'] < 2000) & (ecom_df['sales'] > 10)]

    # 2. 加载社交数据 (小红书 + 微博)
    logging.info("加载社交数据...")
    xhs_files = list(base_dir.glob("小红书-*.json"))
    xhs_dfs = [pd.read_json(f, encoding='utf-8') for f in xhs_files if f.exists()]
    xhs_df = pd.concat(xhs_dfs, ignore_index=True) if xhs_dfs else pd.DataFrame(columns=['标题', '点赞数', '搜索词'])
    
    weibo_file = base_dir / "微博搜索关键词采集.json"
    weibo_df = pd.read_json(weibo_file, encoding='utf-8') if weibo_file.exists() else pd.DataFrame(columns=['博文内容', '点赞数', '关键词'])

    xhs_unified = pd.DataFrame({
        'title': xhs_df['标题'], 'likes': xhs_df['点赞数'].apply(clean_sales), 
        'platform': 'XHS', 'keyword': xhs_df.get('搜索词', None)
    })
    weibo_unified = pd.DataFrame({
        'title': weibo_df['博文内容'], 'likes': weibo_df['点赞数'].apply(clean_sales), 
        'platform': 'Weibo', 'keyword': weibo_df.get('关键词', None)
    })
    social_df = pd.concat([xhs_unified, weibo_unified], ignore_index=True).dropna(subset=['title'])
    social_df = social_df[~social_df['keyword'].str.contains("小红书网页版", na=False)]

    # 3. 加载评论数据
    logging.info("加载评论数据...")
    comment_file = base_dir / "淘宝商品评论【网站反爬请查阅注意事项】.json"
    comments_df = pd.read_json(comment_file, encoding='utf-8') if comment_file.exists() else pd.DataFrame(columns=['评论内容'])


    # 4. P-Tag 引擎：统一打标签
    logging.info("开始 P-Tag 引擎打标签...")
    defs = DEFINITIONS
    ecom_df['tag_brand'] = apply_tags_vectorized(ecom_df['title'], defs["BRAND"])
    ecom_df['tag_color'] = apply_tags_vectorized(ecom_df['title'], defs["COLOR"])
    ecom_df['tag_tech'] = apply_tags_vectorized(ecom_df['title'], defs["TECH"])
    ecom_df['tag_whitening'] = apply_single_tag_vectorized(ecom_df['title'], defs["WHITENING"])
    
    social_df['tag_brand'] = apply_tags_vectorized(social_df['title'], defs["BRAND"])
    social_df['tag_color'] = apply_tags_vectorized(social_df['title'], defs["COLOR"])
    social_df['tag_tech'] = apply_tags_vectorized(social_df['title'], defs["TECH"])
    social_df['tag_whitening'] = apply_single_tag_vectorized(social_df['title'], defs["WHITENING"])

    # 为空标签设置默认值
    default_tags = {
        'tag_brand': 'Other',
        'tag_color': '未明确色系',
        'tag_tech': '基础款'
    }
    for df in [ecom_df, social_df]:
        for col, default in default_tags.items():
            df[col] = df[col].apply(lambda x: x if x else [default])

    # 5. 产品类型分析 (Product Archetype)
    logging.info("开始产品类型 (Archetype) 分析...")
    def get_archetype(row):
        tech = set(row['tag_tech'])
        color = set(row['tag_color'])
        if '盖白发' in tech: return "功能型 (盖白发)"
        if '泡沫' in tech: return "便捷型 (泡沫)"
        if '植物' in tech or '无氨' in tech: return "健康型 (植物/无氨)"
        if '亚麻/青色系' in color or '灰色/蓝色/紫色系' in color or '高饱和色系' in color: return "时尚型 (潮色)"
        if '棕色系' in color or '红色/橘色系' in color: return "主流型 (常规色)"
        return "其他"
    ecom_df['archetype'] = ecom_df.apply(get_archetype, axis=1)

    # 6. 核心语义分析模块 (WHAT IS 显白?)
    logging.info("开始'显白'语义共现分析...")
    all_titles_df = pd.concat([
        ecom_df[['title', 'platform', 'tag_brand', 'tag_color', 'tag_tech', 'tag_whitening']],
        social_df[['title', 'platform', 'tag_brand', 'tag_color', 'tag_tech', 'tag_whitening']]
    ]).reset_index(drop=True)
    
    whitening_df = all_titles_df[all_titles_df['tag_whitening'] == True]
    
    co_occurrence_data = {
        'color': Counter([tag for tags in whitening_df['tag_color'] for tag in tags if tag != '未明确色系']),
        'brand': Counter([tag for tags in whitening_df['tag_brand'] for tag in tags if tag != 'Other']),
        'tech': Counter([tag for tags in whitening_df['tag_tech'] for tag in tags if tag != '基础款']),
    }
    
    logging.info("构建'显白'共现矩阵...")
    color_tags = list(defs["COLOR"].keys())
    tech_tags = list(defs["TECH"].keys())
    co_matrix = pd.DataFrame(0, index=color_tags, columns=tech_tags)
    
    for _, row in whitening_df.iterrows():
        colors = set(row['tag_color'])
        techs = set(row['tag_tech'])
        for c, t in product(colors, techs):
            if c in color_tags and t in tech_tags:
                co_matrix.loc[c, t] += 1
    
    co_matrix = co_matrix.loc[(co_matrix.sum(axis=1) > 0), (co_matrix.sum(axis=0) > 0)]
    co_occurrence_data['co_matrix'] = co_matrix

    # 【【【 新增：为图15准备数据 】】】
    # 计算所有主要话题的平均点赞数
    logging.info("计算社媒话题平均点赞...")
    topic_likes = defaultdict(lambda: {'total_likes': 0, 'count': 0})
    
    # 显白
    whitening_likes = social_df[social_df['tag_whitening'] == True]['likes']
    topic_likes['显白'] = {'total_likes': whitening_likes.sum(), 'count': len(whitening_likes)}
    
    # 功效
    tech_df = social_df.explode('tag_tech')
    for tag in defs["TECH"].keys():
        likes = tech_df[tech_df['tag_tech'] == tag]['likes']
        topic_likes[tag]['total_likes'] += likes.sum()
        topic_likes[tag]['count'] += len(likes)
        
    # 色系
    color_df = social_df.explode('tag_color')
    for tag in defs["COLOR"].keys():
        likes = color_df[color_df['tag_color'] == tag]['likes']
        topic_likes[tag]['total_likes'] += likes.sum()
        topic_likes[tag]['count'] += len(likes)

    # 转换为DataFrame
    avg_likes_data = []
    for topic, data in topic_likes.items():
        if data['count'] > 0: # 避免除以0
            avg_likes = data['total_likes'] / data['count']
            avg_likes_data.append({'topic': topic, 'avg_likes': avg_likes, 'count': data['count']})
            
    avg_likes_df = pd.DataFrame(avg_likes_data).sort_values('avg_likes', ascending=False)
    
    # 7. 评论洞察处理
    logging.info("开始评论洞察分析...")
    comments = comments_df['评论内容'].dropna().astype(str)
    comments_insight = {
        'whitening_mentions': comments.str.contains("显白").sum(),
        'blackening_mentions': comments.str.contains("显黑").sum(),
        'total_comments': len(comments)
    }

    # 8. 原始数据统计 (用于恢复V2图表)
    raw_data_counts = {
        '淘宝商品': len(tb_df), '京东商品': len(jd_df),
        '小红书笔记': len(xhs_df), '微博帖子': len(weibo_df),
        '淘宝评论': len(comments_df)
    }
    
    # 9. 关键词策略数据 (Top 10)
    ecom_k_series = ecom_df['keyword'].value_counts().head(10)
    ecom_k_df = pd.DataFrame({'keyword': ecom_k_series.index, 'count': ecom_k_series.values})
    
    social_k_series = social_df['keyword'].value_counts().head(10)
    social_k_df = pd.DataFrame({'keyword': social_k_series.index, 'count': social_k_series.values})
    social_k_df = social_k_df[~social_k_df['keyword'].str.contains("小红书网页版", na=False)]

    keyword_strategy = {
        '电商关键词 (Top 10)': ecom_k_df,
        '社交关键词 (Top 10)': social_k_df
    }

    # 打包所有处理好的数据
    data_pack = {
        'ecom': ecom_df,
        'social': social_df,
        'social_avg_likes': avg_likes_df, # 【【【 新增数据 】】】
        'comments_insight': comments_insight,
        'co_occurrence': co_occurrence_data,
        'raw_counts': raw_data_counts, # 原始计数，用于V2图表
        'raw_counts_kpi': { # 用于V3 KPI卡
            '淘宝商品': len(tb_df), '京东商品': len(jd_df),
            '小红书笔记': len(xhs_df), '微博帖子': len(weibo_df),
            '淘宝评论': len(comments_df),
            '电商关键词': ecom_df['keyword'].nunique(),
            '社交关键词': social_df['keyword'].nunique()
        },
        'keyword_strategy': keyword_strategy
    }
    
    logging.info("--- 数据处理全部完成 ---")
    return data_pack