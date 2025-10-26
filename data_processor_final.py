import pandas as pd
import re
from pathlib import Path
import streamlit as st
from collections import Counter, defaultdict
import logging
import math
import numpy as np

# --- 0. 关键词定义 (P-Tag Engine) V9.1 ---
# (基于 V4.1 deep_dive_report.py 的词典)
DEFINITIONS = {
    # (A) 核心美学诉求 (基础)
    "WHITENING": ["显白", "黄皮", "肤色", "亲妈", "天菜", "素颜", "提亮", "去黄", "衬肤"],
    "QISE": ["显气色", "气色好", "红润", "元气", "血色感"],
    "NEG_SKIN": ["蜡黄", "暗沉", "疲惫", "没气色", "显黑", "不显白", "荧光", "芭比"],
    "NEG_DULL_SPECIFIC": ["蜡黄", "暗沉", "疲惫", "没气色"], # V9.1 新增：用于评论分析

    # (B) 四大美学路径
    "AESTHETICS_PATHS": { # V9.1: 重命名以区分
        "补光系": ["补光", "琉璃", "月光", "焦糖", "榛果", "米棕", "光泽"],
        "滤光系": ["滤光", "去黄", "修正", "宣纸", "奶茶", "灰棕", "亚麻", "青色"],
        "活血系": ["活血", "气色", "红润", "血色感", "树莓", "粉棕", "脏橘", "赤茶"],
        "衬光系": ["衬光", "对比", "釉", "瓷", "黑茶", "蓝黑", "乌木", "深棕"]
    },
    
    # (C) 品牌国别归类
    "BRAND_ORIGIN": {
        "欧美品牌": ["欧莱雅", "施华蔻", "L'Oréal", "Schwarzkopf"],
        "日韩品牌": ["爱茉莉", "美妆仙", "花王", "Liese", "莉婕", "美源", "Bigen", "Kao"],
        "国产新锐": ["三橡树", "章华", "温雅", "迪彩", "韩金靓"] 
    },

    # (D) Z世代与口碑
    "KOL_KOC": {
        "KOL": ["博主", "KOL", "达人", "测评"],
        "KOC": ["素人", "用户", "分享", "笔记", "我", "姐妹们"] 
    },

    # --- 以下为旧版定义，保留兼容性 ---
    "BRAND": {
        "欧莱雅": ["欧莱雅"], 
        "施华蔻": ["施华蔻"], 
        "花王": ["花王", "Liese"], 
        "爱茉莉": ["爱茉莉", "美妆仙"], 
        "章华": ["章华"]
    },
    "COLOR": {
        "棕色系": ["棕", "茶", "摩卡", "巧", "奶茶"], 
        "红色/橘色系": ["红", "橘", "莓", "脏橘", "酒红", "赤"], 
        "亚麻/青色系": ["亚麻", "青", "闷青", "灰绿"], 
        "灰色/蓝色/紫色系": ["灰", "蓝", "紫", "芋泥", "蓝黑", "乌木"], 
        "金色/浅色系": ["金", "白金", "米金", "浅金", "漂"]
    },
    "TECH": {
        "植物": ["植物", "植萃"], 
        "无氨": ["无氨", "温和"], 
        "泡沫": ["泡沫", "泡泡"], 
        "盖白发": ["盖白", "遮白"], 
        "免漂": ["免漂", "无需漂"]
    },
    "ARCHETYPE": { 
        "便捷型(泡沫)": ["泡沫", "泡泡"],
        "健康型(植物/无氨)": ["植物", "植萃", "无氨", "温和"],
        "功效型(盖白/免漂)": ["盖白", "遮白", "免漂"],
        "基础型(染发膏)": ["染发膏", "染发霜", "染发剂"],
        "潮色型(需漂)": ["漂染", "需漂", "漂发"]
    },
    "AESTHETICS": { # 旧版美学定义
        "东方美学": ["东方", "美学", "国风", "中式", "新中式"]
    },
    "SWATCHES": {
        "茶棕": ["茶棕"], "乌木色": ["乌木"], "赤茶色": ["赤茶"], "檀棕": ["檀棕"],
        "黑茶色": ["黑茶"], "蓝黑色": ["蓝黑"], "脏橘色": ["脏橘"], "青灰色": ["青灰"]
    },
    "CATEGORY_HEX": {
        "COLOR": {
            "棕色系": "#8C6A4F", "红色/橘色系": "#B56D5F", "亚麻/青色系": "#7A9A7A",
            "灰色/蓝色/紫色系": "#6F7C99", "金色/浅色系": "#D4B48C"
        },
        "ARCHETYPE": {
            "便捷型(泡沫)": "#E09C86", "健康型(植物/无氨)": "#7A9A7A", "功效型(盖白/免漂)": "#8C6A4F",
            "基础型(染发膏)": "#A9A9A9", "潮色型(需漂)": "#6F7C99"
        }
    },
    "SWATCH_HEX": {
        "茶棕": "#A67B5B", "乌木色": "#5B5B5B", "赤茶色": "#B85C40", "檀棕": "#8C5A4A",
        "黑茶色": "#4A4A4A", "蓝黑色": "#4A4A5B", "脏橘色": "#E08A6F", "青灰色": "#8C8C8C"
    }
}

# --- 1. 基础清洗工具 (V9.1 确认 clean_sales) ---
def clean_sales(sales_str):
    """(V9.1 确认) 统一付款人数/评价人数，并正确处理 NaN"""
    if pd.isna(sales_str): return 0
    if isinstance(sales_str, (int, float)): return int(sales_str)
    if isinstance(sales_str, str):
        number_part = re.search(r'(\d+\.?\d*)', sales_str)
        if not number_part: return 0
        try: num = float(number_part.group(1))
        except ValueError: return 0
        if '万' in sales_str: return int(num * 10000)
        return int(num)
    return 0

def clean_price(price_str):
    if pd.isna(price_str): return 0.0
    if isinstance(price_str, (int, float)): return float(price_str)
    if isinstance(price_str, str):
        match = re.search(r'(\d+\.?\d*)', price_str)
        return float(match.group(1)) if match else 0.0
    return 0.0

def apply_tags_vectorized(series, keywords_dict):
    """向量化应用标签"""
    series_lower = series.astype(str).str.lower().fillna('') # V9.1: 强制转 str
    tags = pd.Series([[] for _ in range(len(series))], index=series.index)
    for tag, keywords in keywords_dict.items():
        pattern = '|'.join([re.escape(kw.lower()) for kw in keywords])
        mask = series_lower.str.contains(pattern, case=False, na=False, regex=True) # V9.1: regex=True
        # 使用 .loc 避免 SettingWithCopyWarning
        tags.loc[mask] = tags.loc[mask].apply(lambda x: x + [tag])
    return tags

def find_first_match(text, dictionary):
    """(V9.1) 辅助函数：查找第一个匹配的分类"""
    if not isinstance(text, str): return "未知"
    text_lower = text.lower()
    for category, keywords in dictionary.items():
        for kw in keywords:
            if kw.lower() in text_lower: return category
    return "未知"

def find_all_matches(text, dictionary):
    """(V9.1) 辅助函数：查找所有匹配的分类"""
    matches = set()
    if not isinstance(text, str): return list(matches)
    text_lower = text.lower()
    for category, keywords in dictionary.items():
        for kw in keywords:
            if kw.lower() in text_lower: matches.add(category)
    return list(matches)

# --- V9.1: get_avg_likes_by_topic 保持不变 (内部逻辑已正确) ---
def get_avg_likes_by_topic(social_df, defs):
    """(V9.1 确认) 计算所有话题的平均点赞数"""
    topic_likes = defaultdict(lambda: {'total_likes': 0, 'count': 0})
    
    # Check if 'likes' column exists
    if 'likes' not in social_df.columns:
        logging.warning("get_avg_likes_by_topic: 'likes' column not found in social_df.")
        return pd.DataFrame() # Return empty DataFrame if 'likes' is missing

    # 显白
    if 'tag_whitening' in social_df.columns:
        whitening_likes = social_df.loc[social_df['tag_whitening'] == True, 'likes']
        if not whitening_likes.empty:
            topic_likes['显白'] = {'total_likes': whitening_likes.sum(), 'count': len(whitening_likes)}
    
    # 显气色
    if 'tag_qise' in social_df.columns:
        qise_likes = social_df.loc[social_df['tag_qise'] == True, 'likes']
        if not qise_likes.empty:
            topic_likes['显气色'] = {'total_likes': qise_likes.sum(), 'count': len(qise_likes)}
    
    # 功效
    if 'tag_tech' in social_df.columns:
        tech_df = social_df.explode('tag_tech')
        for tag in defs.get("TECH", {}).keys():
            if not isinstance(tag, str): continue
            likes = tech_df.loc[tech_df['tag_tech'] == tag, 'likes']
            if not likes.empty:
                topic_likes[tag]['total_likes'] += likes.sum()
                topic_likes[tag]['count'] += len(likes)
            
    # 色系
    if 'tag_color' in social_df.columns:
        color_df = social_df.explode('tag_color')
        for tag in defs.get("COLOR", {}).keys():
            if not isinstance(tag, str): continue
            likes = color_df.loc[color_df['tag_color'] == tag, 'likes']
            if not likes.empty:
                topic_likes[tag]['total_likes'] += likes.sum()
                topic_likes[tag]['count'] += len(likes)
            
    # 东方美学 (旧)
    if 'tag_aesthetics' in social_df.columns:
        aesthetics_df = social_df.explode('tag_aesthetics')
        for tag in defs.get("AESTHETICS", {}).keys():
            if not isinstance(tag, str): continue
            likes = aesthetics_df.loc[aesthetics_df['tag_aesthetics'] == tag, 'likes']
            if not likes.empty:
                topic_likes[tag]['total_likes'] += likes.sum()
                topic_likes[tag]['count'] += len(likes)

    avg_likes_data = []
    for topic, data in topic_likes.items():
        if data['count'] > 0:
            avg_likes = data['total_likes'] / data['count']
            avg_likes_data.append({'topic': topic, 'avg_likes': avg_likes, 'count': data['count']})
    
    return pd.DataFrame(avg_likes_data).sort_values('avg_likes', ascending=False)


# --- 2. 核心数据加载与处理 (Cached) V9.1 ---
@st.cache_data(ttl=3600, show_spinner="正在加载与处理全域数据...")
def load_and_process_data(base_dir):
    """
    V9.1: 重构的数据处理核心 (匹配 V4.1 报告 & V9.1 dashboard)
    """
    logging.info("V9.1: 开始加载与处理数据...")
    data = {}
    defs = DEFINITIONS 
    
    # 1. 加载电商数据
    tb_files = list(base_dir.glob("淘宝商品目录/*.json"))
    tb_dfs = [pd.read_json(f, encoding='utf-8') for f in tb_files if f.exists()]
    tb_df = pd.concat(tb_dfs, ignore_index=True) if tb_dfs else pd.DataFrame(columns=['产品名称', '产品价格', '付款人数', '地理位置', '关键词'])
    
    jd_file = base_dir / "京东-商品搜索.json"
    jd_df = pd.read_json(jd_file, encoding='utf-8') if jd_file.exists() else pd.DataFrame(columns=['商品名称', '价格', '评价人数', '搜索关键词'])

    tb_unified = pd.DataFrame({
        'title': tb_df.get('产品名称'), # Use .get() for safety
        'price': tb_df.get('产品价格', pd.Series(dtype='object')).apply(clean_price), 
        'sales': tb_df.get('付款人数', pd.Series(dtype='object')).apply(clean_sales),
        'location': tb_df.get('地理位置', pd.Series(dtype='object')).astype(str).str.split(' ').str[0], 
        'platform': 'Taobao', 
        'keyword': tb_df.get('关键词')
    })
    jd_unified = pd.DataFrame({
        'title': jd_df.get('商品名称'),
        'price': jd_df.get('价格', pd.Series(dtype='object')).apply(clean_price), 
        'sales': jd_df.get('评价人数', pd.Series(dtype='object')).apply(clean_sales),
        'location': '未知', 
        'platform': 'JD', 
        'keyword': jd_df.get('搜索关键词')
    })
    ecom_df = pd.concat([tb_unified, jd_unified], ignore_index=True).dropna(subset=['title'])
    ecom_df = ecom_df[(ecom_df['price'] > 10) & (ecom_df['price'] < 2000) & (ecom_df['sales'] > 10)].reset_index(drop=True)
    logging.info(f"电商数据加载完成: {len(ecom_df)} 条")

    # 2. 加载社交数据
    xhs_files = list(base_dir.glob("小红书-*.json"))
    xhs_dfs = [pd.read_json(f, encoding='utf-8') for f in xhs_files if f.exists()]
    xhs_df = pd.concat(xhs_dfs, ignore_index=True) if xhs_dfs else pd.DataFrame(columns=['标题', '点赞数', '搜索词', '作者']) # V9.1: 添加'作者'
    
    weibo_file = base_dir / "微博搜索关键词采集.json"
    weibo_df = pd.read_json(weibo_file, encoding='utf-8') if weibo_file.exists() else pd.DataFrame(columns=['博文内容', '点赞数', '关键词', '作者']) # V9.1: 添加'作者'

    xhs_unified = pd.DataFrame({
        'title': xhs_df.get('标题'), 
        'likes': xhs_df.get('点赞数', pd.Series(dtype='object')).apply(clean_sales), 
        'platform': 'XHS', 
        'keyword': xhs_df.get('搜索词'),
        'author': xhs_df.get('作者') # V9.1
    })
    weibo_unified = pd.DataFrame({
        'title': weibo_df.get('博文内容'), 
        'likes': weibo_df.get('点赞数', pd.Series(dtype='object')).apply(clean_sales), 
        'platform': 'Weibo', 
        'keyword': weibo_df.get('关键词'),
        'author': weibo_df.get('作者') # V9.1
    })
    social_df = pd.concat([xhs_unified, weibo_unified], ignore_index=True).dropna(subset=['title'])
    social_df = social_df[~social_df['keyword'].astype(str).str.contains("小红书网页版", na=False)].reset_index(drop=True)
    logging.info(f"社交数据加载完成: {len(social_df)} 条")

    # 3. 加载评论数据
    comment_file = base_dir / "淘宝商品评论【网站反爬请查阅注意事项】.json"
    comments_df = pd.read_json(comment_file, encoding='utf-8') if comment_file.exists() else pd.DataFrame(columns=['评论内容'])
    logging.info(f"评论数据加载完成: {len(comments_df)} 条")

    # 4. P-Tag 引擎：统一打标签 (V9.1 确认)
    ecom_df['tag_brand'] = apply_tags_vectorized(ecom_df['title'], defs["BRAND"])
    ecom_df['tag_color'] = apply_tags_vectorized(ecom_df['title'], defs["COLOR"])
    ecom_df['tag_tech'] = apply_tags_vectorized(ecom_df['title'], defs["TECH"])
    ecom_df['tag_swatch'] = apply_tags_vectorized(ecom_df['title'], defs["SWATCHES"]) 
    ecom_df['tag_archetype'] = apply_tags_vectorized(ecom_df['title'], defs["ARCHETYPE"]) 
    ecom_df['tag_whitening'] = ecom_df['title'].astype(str).str.lower().str.contains('|'.join(defs["WHITENING"]), case=False, na=False, regex=True)
    ecom_df['tag_qise'] = ecom_df['title'].astype(str).str.lower().str.contains('|'.join(defs["QISE"]), case=False, na=False, regex=True) 
    ecom_df['tag_aesthetics'] = apply_tags_vectorized(ecom_df['title'], defs["AESTHETICS"]) 
    ecom_df['archetype'] = ecom_df['tag_archetype'].apply(lambda x: x[0] if x else '其他')

    social_df['tag_brand'] = apply_tags_vectorized(social_df['title'], defs["BRAND"])
    social_df['tag_color'] = apply_tags_vectorized(social_df['title'], defs["COLOR"])
    social_df['tag_tech'] = apply_tags_vectorized(social_df['title'], defs["TECH"])
    social_df['tag_swatch'] = apply_tags_vectorized(social_df['title'], defs["SWATCHES"]) 
    social_df['tag_aesthetics'] = apply_tags_vectorized(social_df['title'], defs["AESTHETICS"]) 
    social_df['tag_whitening'] = social_df['title'].astype(str).str.lower().str.contains('|'.join(defs["WHITENING"]), case=False, na=False, regex=True)
    social_df['tag_qise'] = social_df['title'].astype(str).str.lower().str.contains('|'.join(defs["QISE"]), case=False, na=False, regex=True) 
    
    logging.info("P-Tag 引擎打标完成")

    # 5. V9.1: 核心语义分析模块 (合并电商与社交)
    all_df_for_analysis = pd.concat([
        ecom_df[['tag_brand', 'tag_color', 'tag_tech', 'tag_whitening', 'tag_qise']],
        social_df[['tag_brand', 'tag_color', 'tag_tech', 'tag_whitening', 'tag_qise']]
    ]).reset_index(drop=True)

    # 5A. "显白" 共现分析 (V9.1: 添加 total_mentions)
    whitening_df = all_df_for_analysis[all_df_for_analysis['tag_whitening'] == True]
    co_occurrence_data = {
        'color': Counter([tag for tags in whitening_df['tag_color'] for tag in tags]),
        'brand': Counter([tag for tags in whitening_df['tag_brand'] for tag in tags]),
        'tech': Counter([tag for tags in whitening_df['tag_tech'] for tag in tags]),
        'total_mentions': len(whitening_df) # V9.1 新增
    }
    # V9.1: "显白" 色系 x 功效 共现热力图 (保持不变)
    co_matrix_data = []
    top_5_colors = [tag for tag, count in co_occurrence_data['color'].most_common(5)]
    top_5_techs = [tag for tag, count in co_occurrence_data['tech'].most_common(5)]
    for _, row in whitening_df.iterrows():
        colors = set(row['tag_color']) & set(top_5_colors)
        techs = set(row['tag_tech']) & set(top_5_techs)
        for c in colors:
            for t in techs:
                co_matrix_data.append({'color': c, 'tech': t})
    if co_matrix_data:
        co_matrix_df = pd.DataFrame(co_matrix_data).groupby(['color', 'tech'], observed=True).size().reset_index(name='count')
        co_occurrence_data['co_matrix'] = co_matrix_df.pivot_table(index='color', columns='tech', values='count', fill_value=0)
    else:
        co_occurrence_data['co_matrix'] = pd.DataFrame() 
        
    logging.info("“显白”共现分析完成")

    # 5B. V9.1: "显气色" 共现分析 (添加 total_mentions)
    qise_df = all_df_for_analysis[all_df_for_analysis['tag_qise'] == True]
    qise_co_occurrence_data = {
        'color': Counter([tag for tags in qise_df['tag_color'] for tag in tags]),
        'brand': Counter([tag for tags in qise_df['tag_brand'] for tag in tags]),
        'tech': Counter([tag for tags in qise_df['tag_tech'] for tag in tags]),
        'total_mentions': len(qise_df) # V9.1 新增
    }
    logging.info("“显气色”共现分析完成")
    
    # 5C. V9.1: "中国色彩"色卡分析 (保持不变)
    swatch_ecom_df = ecom_df.explode('tag_swatch').dropna(subset=['tag_swatch'])
    swatch_sales = swatch_ecom_df.groupby('tag_swatch')['sales'].sum().reset_index(name='total_sales')
    swatch_sales['hex'] = swatch_sales['tag_swatch'].map(defs["SWATCH_HEX"]) 
    swatch_analysis_df = swatch_sales.sort_values('total_sales', ascending=False)
    logging.info("“中国色彩”色卡分析完成")

    # 5D. V9.1: "社媒平均点赞"分析 (保持不变)
    social_avg_likes_df = get_avg_likes_by_topic(social_df, defs)
    logging.info("“社媒平均点赞”分析完成")

    # ======================================================================
    # 【【【 V9.1 新增分析模块 】】】
    # ======================================================================
    
    # 5E. (新) 品牌国别分析 (V4.1 Part 3 逻辑)
    brand_origin_data = {}
    # 电商
    ecom_df['brand_origin'] = ecom_df['title'].apply(lambda x: find_first_match(x, defs["BRAND_ORIGIN"]))
    origin_sales = ecom_df.groupby('brand_origin')['sales'].sum().sort_values(ascending=False)
    brand_origin_data['ecom_sales'] = origin_sales[origin_sales.index != '未知']
    # 社媒 (XHS Only for quality)
    xhs_only_df = social_df[social_df['platform'] == 'XHS'].copy()
    if not xhs_only_df.empty:
        xhs_only_df['brand_origin'] = xhs_only_df['title'].apply(lambda x: find_first_match(x, defs["BRAND_ORIGIN"]))
        origin_social = xhs_only_df.groupby('brand_origin').agg(
            total_likes=('likes', 'sum'),
            count=('title', 'count')
        ).reset_index()
        origin_social['avg_likes'] = origin_social['total_likes'] / origin_social['count']
        origin_social = origin_social.sort_values('avg_likes', ascending=False)
        brand_origin_data['social_buzz'] = origin_social[origin_social['brand_origin'] != '未知'].set_index('brand_origin')
    else:
        brand_origin_data['social_buzz'] = pd.DataFrame()
    logging.info("品牌国别分析完成")

    # 5F. (新) KOL/KOC 交叉分析 (V4.1 Part 4 逻辑, XHS Only)
    kol_koc_analysis_data = {}
    if not xhs_only_df.empty and 'author' in xhs_only_df.columns:
        kol_pattern = '|'.join(defs["KOL_KOC"]['KOL']).lower()
        xhs_only_df['is_kol'] = xhs_only_df['author'].astype(str).str.lower().str.contains(kol_pattern, na=False, regex=True)
        
        kol_posts = xhs_only_df[xhs_only_df['is_kol'] == True].copy()
        koc_posts = xhs_only_df[xhs_only_df['is_kol'] == False].copy()
        
        kol_count = len(kol_posts)
        koc_count = len(koc_posts)
        
        if kol_count > 0 and koc_count > 0:
            kol_avg_likes = kol_posts['likes'].mean()
            koc_avg_likes = koc_posts['likes'].mean()
            kol_koc_analysis_data['influence'] = pd.DataFrame({
                'type': ['KOL', 'KOC'],
                'count': [kol_count, koc_count],
                'avg_likes': [kol_avg_likes, koc_avg_likes]
            }).set_index('type')

            whitening_pattern = '|'.join(defs["WHITENING"])
            qise_pattern = '|'.join(defs["QISE"])
            
            kol_posts['has_whitening'] = kol_posts['title'].astype(str).str.contains(whitening_pattern, case=False, na=False, regex=True)
            kol_posts['has_qise'] = kol_posts['title'].astype(str).str.contains(qise_pattern, case=False, na=False, regex=True)
            koc_posts['has_whitening'] = koc_posts['title'].astype(str).str.contains(whitening_pattern, case=False, na=False, regex=True)
            koc_posts['has_qise'] = koc_posts['title'].astype(str).str.contains(qise_pattern, case=False, na=False, regex=True)

            kol_whitening_pct = kol_posts['has_whitening'].mean() * 100
            kol_qise_pct = kol_posts['has_qise'].mean() * 100
            koc_whitening_pct = koc_posts['has_whitening'].mean() * 100
            koc_qise_pct = koc_posts['has_qise'].mean() * 100
            
            kol_koc_analysis_data['topics'] = pd.DataFrame({
                'type': ['KOL', 'KOC', 'KOL', 'KOC'],
                'topic': ['显白', '显白', '显气色', '显气色'],
                'percentage': [kol_whitening_pct, koc_whitening_pct, kol_qise_pct, koc_qise_pct]
            })
            logging.info("KOL/KOC 交叉分析完成")
        else:
            logging.warning("KOL 或 KOC 笔记数量不足，无法进行交叉分析。")
            kol_koc_analysis_data = None # Indicate data is missing
    else:
        logging.warning("小红书数据或'作者'字段缺失，无法进行KOL/KOC分析。")
        kol_koc_analysis_data = None # Indicate data is missing

    # 5G. (新) 四大美学路径分析 (V4.1 Part 6 逻辑)
    four_paths_analysis_data = {}
    # 电商
    ecom_df['path'] = ecom_df['title'].apply(lambda x: find_first_match(x, defs["AESTHETICS_PATHS"]))
    path_sales = ecom_df.groupby('path')['sales'].sum().sort_values(ascending=False)
    four_paths_analysis_data['ecom_sales'] = path_sales[path_sales.index != '未知']
    # 社媒 (XHS Only)
    if not xhs_only_df.empty:
        xhs_only_df['path'] = xhs_only_df['title'].apply(lambda x: find_first_match(x, defs["AESTHETICS_PATHS"]))
        path_social = xhs_only_df.groupby('path').agg(
            total_likes=('likes', 'sum'),
            count=('title', 'count')
        ).reset_index()
        path_social['avg_likes'] = path_social['total_likes'] / path_social['count']
        path_social = path_social.sort_values('avg_likes', ascending=False)
        four_paths_analysis_data['social_buzz'] = path_social[path_social['path'] != '未知'].set_index('path')
    else:
        four_paths_analysis_data['social_buzz'] = pd.DataFrame()
    logging.info("四大美学路径分析完成")
    # ======================================================================
    # 【【【 END 新增分析模块 】】】
    # ======================================================================

    # 6. 评论洞察处理 (V9.1: 增加 dull_mentions 和 _raw 后缀)
    comments = comments_df['评论内容'].dropna().astype(str).str.lower()
    comments_insight = {
        'total_comments': len(comments),
        # 旧键名（可能被旧图表使用）- 使用聚合词典
        'whitening_mentions': int(comments.str.contains('|'.join(defs["WHITENING"]), regex=True).sum()),
        'blackening_mentions': int(comments.str.contains('|'.join(["显黑", "不显白"]), regex=True).sum()), # 稍微精确一点
        'qise_mentions': int(comments.str.contains('|'.join(defs["QISE"]), regex=True).sum()), 
        # 新键名（V4.1 报告 & V9.1 dashboard 使用）- 更精确
        'whitening_mentions_raw': int(comments.str.contains("显白").sum()), # 只统计"显白"
        'blackening_mentions_raw': int(comments.str.contains("显黑").sum()), # 只统计"显黑"
        'dull_mentions': int(comments.str.contains('|'.join(defs["NEG_DULL_SPECIFIC"]), regex=True).sum()) # 只统计蜡黄暗沉
    }
    logging.info("评论洞察分析完成")

    # 7. 原始数据统计 (V9.1 确认)
    raw_counts = {
        '淘宝商品': len(tb_df), '京东商品': len(jd_df),
        '小红书笔记': len(xhs_df), '微博帖子': len(weibo_df),
        '淘宝评论': len(comments_df)
    }
    raw_counts_kpi = {
        '淘宝商品': len(tb_df), '京东商品': len(jd_df),
        # V9.1 FIX: Check if 'keyword' column exists before filtering
        '小红书笔记': len(xhs_df[~xhs_df['keyword'].astype(str).str.contains("小红书网页版", na=False)]) if 'keyword' in xhs_df.columns else len(xhs_df),
        '微博帖子': len(weibo_df),
        '淘宝评论': len(comments_df),
        '电商关键词': ecom_df['keyword'].nunique(),
        '社交关键词': social_df['keyword'].nunique()
    }
    
    # 8. 关键词策略数据 (V9.1: 升级到 Top 15)
    ecom_k_series = ecom_df['keyword'].value_counts().head(15) # V9.1 升级
    ecom_k_df = pd.DataFrame({'keyword': ecom_k_series.index, 'count': ecom_k_series.values})
    
    social_k_series = social_df['keyword'].value_counts().head(15) # V9.1 升级
    social_k_df = pd.DataFrame({'keyword': social_k_series.index, 'count': social_k_series.values})

    keyword_strategy = {
        '电商关键词 (Top 15)': ecom_k_df, # V9.1 升级键名
        '社交关键词 (Top 15)': social_k_df  # V9.1 升级键名
    }
    logging.info("关键词策略分析完成 (Top 15)")

    # 9. 打包所有处理好的数据 (V9.1)
    data_pack = {
        'ecom': ecom_df,
        'social': social_df,
        'comments_insight': comments_insight, # V9.1 更新
        'raw_counts': raw_counts,
        'raw_counts_kpi': raw_counts_kpi,
        'keyword_strategy': keyword_strategy, # V9.1 更新
        'definitions': defs, 
        
        # --- V7/V5 数据 (保持不变) ---
        'co_occurrence': co_occurrence_data, # V9.1 更新 (含 total_mentions)
        'qise_co_occurrence': qise_co_occurrence_data, # V9.1 更新 (含 total_mentions)
        'swatch_analysis': swatch_analysis_df, 
        'social_avg_likes': social_avg_likes_df,
        
        # --- V9.1 新增数据 ---
        'brand_origin': brand_origin_data,
        'kol_koc_analysis': kol_koc_analysis_data,
        'four_paths_analysis': four_paths_analysis_data
    }
    
    logging.info("V9.1: 数据处理全部完成。")
    return data_pack

# --- V9.1: 可选 - 添加一个简单的测试运行 ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    print("Running data_processor_final.py as main script for testing...")
    test_base_dir = Path('.') # Assume script is run from the data_analizy directory
    try:
        processed_pack = load_and_process_data(test_base_dir)
        print("\n--- Data Pack Keys ---")
        for key in processed_pack.keys():
            print(f"- {key}")
        
        print("\n--- Sample: Keyword Strategy (Ecom Top 15) ---")
        print(processed_pack['keyword_strategy']['电商关键词 (Top 15)'].head())

        print("\n--- Sample: Comments Insight ---")
        print(processed_pack['comments_insight'])

        print("\n--- Sample: Brand Origin (Ecom Sales) ---")
        if 'brand_origin' in processed_pack and 'ecom_sales' in processed_pack['brand_origin']:
            print(processed_pack['brand_origin']['ecom_sales'].head())
        else:
            print("Brand Origin data not fully generated.")

        print("\n--- Sample: KOL/KOC Analysis (Influence) ---")
        if processed_pack.get('kol_koc_analysis') and 'influence' in processed_pack['kol_koc_analysis']:
             print(processed_pack['kol_koc_analysis']['influence'])
        else:
            print("KOL/KOC data not fully generated.")
            
        print("\n--- Sample: Four Paths (Social Buzz) ---")
        if 'four_paths_analysis' in processed_pack and 'social_buzz' in processed_pack['four_paths_analysis']:
             print(processed_pack['four_paths_analysis']['social_buzz'].head())
        else:
            print("Four Paths data not fully generated.")
            
        print("\nTest run completed successfully!")
        
    except Exception as e:
        logging.error(f"Error during test run: {e}")
        import traceback
        traceback.print_exc()