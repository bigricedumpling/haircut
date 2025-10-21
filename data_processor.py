import pandas as pd
import re
from pathlib import Path
import streamlit as st
from collections import Counter, defaultdict

# --- 0. 关键词定义 (P-Tag Engine) ---
DEFINITIONS = {
    "BRAND": {"欧莱雅": ["欧莱雅"], "施华蔻": ["施华蔻"], "花王": ["花王", "Liese"], "爱茉莉": ["爱茉莉", "美妆仙"], "章华": ["章华"]},
    "COLOR": {"棕色系": ["棕", "茶", "摩卡", "巧", "奶茶"], "红色/橘色系": ["红", "橘", "莓", "脏橘", "酒红"], "亚麻/青色系": ["亚麻", "青", "闷青", "灰绿"], "灰色/蓝色/紫色系": ["灰", "蓝", "紫", "芋泥", "蓝黑"], "金色/浅色系": ["金", "白金", "米金", "浅金", "漂"]},
    "TECH": {"植物": ["植物", "植萃"], "无氨": ["无氨", "温和"], "泡沫": ["泡沫", "泡泡"], "盖白发": ["盖白", "遮白"], "免漂": ["免漂", "无需漂"]},
    "WHITENING": ["显白", "黄皮", "肤色", "提亮", "去黄", "衬肤"]
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
        mask = series_lower.str.contains(pattern, case=False, na=False)
        tags[mask] = tags[mask].apply(lambda x: x + [tag])
    return tags

# --- 2. 核心数据加载与处理 (Cached) ---
@st.cache_data(ttl=3600)
def load_and_process_data(base_dir):
    """
    加载、合并、清洗并处理所有数据。
    这是整个仪表盘的数据核心。
    """
    data = {}
    
    # 1. 加载电商数据 (淘宝 + 京东)
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
    comment_file = base_dir / "淘宝商品评论【网站反爬请查阅注意事项】.json"
    comments_df = pd.read_json(comment_file, encoding='utf-8') if comment_file.exists() else pd.DataFrame(columns=['评论内容'])

    # 4. P-Tag 引擎：统一打标签
    defs = DEFINITIONS
    ecom_df['tag_brand'] = apply_tags_vectorized(ecom_df['title'], defs["BRAND"])
    ecom_df['tag_color'] = apply_tags_vectorized(ecom_df['title'], defs["COLOR"])
    ecom_df['tag_tech'] = apply_tags_vectorized(ecom_df['title'], defs["TECH"])
    ecom_df['tag_whitening'] = ecom_df['title'].str.contains('|'.join(defs["WHITENING"]), case=False, na=False)
    
    social_df['tag_brand'] = apply_tags_vectorized(social_df['title'], defs["BRAND"])
    social_df['tag_color'] = apply_tags_vectorized(social_df['title'], defs["COLOR"])
    social_df['tag_tech'] = apply_tags_vectorized(social_df['title'], defs["TECH"])
    social_df['tag_whitening'] = social_df['title'].str.contains('|'.join(defs["WHITENING"]), case=False, na=False)

    # --- 5. 核心语义分析模块 (NEW & CRITICAL) ---
    all_titles_df = pd.concat([
        ecom_df[['title', 'tag_brand', 'tag_color', 'tag_tech', 'tag_whitening']],
        social_df[['title', 'tag_brand', 'tag_color', 'tag_tech', 'tag_whitening']]
    ]).reset_index(drop=True)
    whitening_df = all_titles_df[all_titles_df['tag_whitening'] == True]
    co_occurrence_data = {
        'color': Counter([tag for tags in whitening_df['tag_color'] for tag in tags]),
        'brand': Counter([tag for tags in whitening_df['tag_brand'] for tag in tags]),
        'tech': Counter([tag for tags in whitening_df['tag_tech'] for tag in tags]),
    }

    # --- 6. 评论洞察处理 ---
    comments = comments_df['评论内容'].dropna().astype(str)
    comments_insight = {
        'whitening_mentions': comments.str.contains("显白").sum(),
        'blackening_mentions': comments.str.contains("显黑").sum(),
        'total_comments': len(comments)
    }

    # --- 7. 原始数据统计 ---
    raw_counts = {
        '淘宝商品': len(tb_df), '京东商品': len(jd_df),
        '小红书笔记': len(xhs_df), '微博帖子': len(weibo_df),
        '淘宝评论': len(comments_df),
        '电商关键词': ecom_df['keyword'].nunique(),
        '社交关键词': social_df['keyword'].nunique()
    }
    
    # --- 8. 关键词策略数据 ---
    # 【【【 已修复 】】】
    # 错误原因: 之前依赖 reset_index() 导致列名不明确
    # 修复方案: 显式地创建 DataFrame，强制列名为 'keyword' 和 'count'
    ecom_k_series = ecom_df['keyword'].value_counts().head(5)
    ecom_k_df = pd.DataFrame({'keyword': ecom_k_series.index, 'count': ecom_k_series.values})
    
    social_k_series = social_df['keyword'].value_counts().head(5)
    social_k_df = pd.DataFrame({'keyword': social_k_series.index, 'count': social_k_series.values})

    keyword_strategy = {
        '电商关键词 (Top 5)': ecom_k_df,
        '社交关键词 (Top 5)': social_k_df
    }

    # 打包所有处理好的数据
    data_pack = {
        'ecom': ecom_df,
        'social': social_df,
        'comments_insight': comments_insight,
        'co_occurrence': co_occurrence_data,
        'raw_counts': raw_counts,
        'keyword_strategy': keyword_strategy
    }
    
    return data_pack