import pandas as pd
import re
from pathlib import Path
import streamlit as st
from collections import Counter, defaultdict
import logging

# --- 0. 关键词定义 (P-Tag Engine) V7 ---
DEFINITIONS = {
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
    "ARCHETYPE": { # V5: 用于图 12
        "便捷型(泡沫)": ["泡沫", "泡泡"],
        "健康型(植物/无氨)": ["植物", "植萃", "无氨", "温和"],
        "功效型(盖白/免漂)": ["盖白", "遮白", "免漂"],
        "基础型(染发膏)": ["染发膏", "染发霜", "染发剂"],
        "潮色型(需漂)": ["漂染", "需漂", "漂发"]
    },
    "WHITENING": ["显白", "黄皮", "肤色", "提亮", "去黄", "衬肤"],
    "QISE": ["气色", "红润", "元气"], # V5: 新增“显气色”
    
    "AESTHETICS": {
        "东方美学": ["东方", "美学", "国风", "中式", "新中式"]
    },
    
    "SWATCHES": {
        "茶棕": ["茶棕"], "乌木色": ["乌木"], "赤茶色": ["赤茶"], "檀棕": ["檀棕"],
        "黑茶色": ["黑茶"], "蓝黑色": ["蓝黑"], "脏橘色": ["脏橘"], "青灰色": ["青灰"]
    },
    
    # 【【【 V7 美学修复：替换为更“高雅”的低饱和度色卡 】】】
    "CATEGORY_HEX": {
        "COLOR": {
            "棕色系": "#8C6A4F",       # 檀木棕
            "红色/橘色系": "#B56D5F",   # 赭红
            "亚麻/青色系": "#7A9A7A",   # 艾绿
            "灰色/蓝色/紫色系": "#6F7C99", # 黛蓝灰
            "金色/浅色系": "#D4B48C"    # 浅金
        },
        "ARCHETYPE": {
            "便捷型(泡沫)": "#E09C86",     # 浅橘
            "健康型(植物/无氨)": "#7A9A7A", # 艾绿
            "功效型(盖白/免漂)": "#8C6A4F", # 檀木棕
            "基础型(染发膏)": "#A9A9A9",     # 中灰
            "潮色型(需漂)": "#6F7C99"      # 黛蓝灰
        }
    },
    "SWATCH_HEX": {
        "茶棕": "#A67B5B", "乌木色": "#5B5B5B", "赤茶色": "#B85C40",
        "檀棕": "#8C5A4A", "黑茶色": "#4A4A4A", "蓝黑色": "#4A4A5B",
        "脏橘色": "#E08A6F", "青灰色": "#8C8C8C"
    }
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

# --- V5: 修复BUG，将此函数移至此处 (原在 dashboard 的 __main__ 中) ---
def get_avg_likes_by_topic(social_df, defs):
    """
    (V5 修复) 计算所有话题的平均点赞数
    """
    topic_likes = defaultdict(lambda: {'total_likes': 0, 'count': 0})
    
    # 显白
    whitening_likes = social_df[social_df['tag_whitening'] == True]['likes']
    if not whitening_likes.empty:
        topic_likes['显白'] = {'total_likes': whitening_likes.sum(), 'count': len(whitening_likes)}
    
    # 显气色 (V5 新增)
    qise_likes = social_df[social_df['tag_qise'] == True]['likes']
    if not qise_likes.empty:
        topic_likes['显气色'] = {'total_likes': qise_likes.sum(), 'count': len(qise_likes)}
    
    # 功效
    tech_df = social_df.explode('tag_tech')
    for tag in defs["TECH"].keys():
        if not isinstance(tag, str): continue
        likes = tech_df[tech_df['tag_tech'] == tag]['likes']
        if not likes.empty:
            topic_likes[tag]['total_likes'] += likes.sum()
            topic_likes[tag]['count'] += len(likes)
            
    # 色系
    color_df = social_df.explode('tag_color')
    for tag in defs["COLOR"].keys():
        if not isinstance(tag, str): continue
        likes = color_df[color_df['tag_color'] == tag]['likes']
        if not likes.empty:
            topic_likes[tag]['total_likes'] += likes.sum()
            topic_likes[tag]['count'] += len(likes)
            
    # 东方美学 (V5 新增)
    aesthetics_df = social_df.explode('tag_aesthetics')
    for tag in defs["AESTHETICS"].keys():
        if not isinstance(tag, str): continue
        likes = aesthetics_df[aesthetics_df['tag_aesthetics'] == tag]['likes']
        if not likes.empty:
            topic_likes[tag]['total_likes'] += likes.sum()
            topic_likes[tag]['count'] += len(likes)

    avg_likes_data = []
    for topic, data in topic_likes.items():
        if data['count'] > 0:
            avg_likes = data['total_likes'] / data['count']
            avg_likes_data.append({'topic': topic, 'avg_likes': avg_likes, 'count': data['count']})
    
    return pd.DataFrame(avg_likes_data).sort_values('avg_likes', ascending=False)


# --- 2. 核心数据加载与处理 (Cached) V7 ---
@st.cache_data(ttl=3600, show_spinner="正在加载与处理全域数据...")
def load_and_process_data(base_dir):
    """
    V7: 重构的数据处理核心
    """
    logging.info("V7: 开始加载与处理数据...")
    data = {}
    defs = DEFINITIONS # 使用 V7 定义
    
    # 1. 加载电商数据
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
    ecom_df = ecom_df[(ecom_df['price'] > 10) & (ecom_df['price'] < 2000) & (ecom_df['sales'] > 10)].reset_index(drop=True)
    logging.info(f"电商数据加载完成: {len(ecom_df)} 条")

    # 2. 加载社交数据
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
    social_df = social_df[~social_df['keyword'].str.contains("小红书网页版", na=False)].reset_index(drop=True)
    logging.info(f"社交数据加载完成: {len(social_df)} 条")

    # 3. 加载评论数据
    comment_file = base_dir / "淘宝商品评论【网站反爬请查阅注意事项】.json"
    comments_df = pd.read_json(comment_file, encoding='utf-8') if comment_file.exists() else pd.DataFrame(columns=['评论内容'])
    logging.info(f"评论数据加载完成: {len(comments_df)} 条")

    # 4. P-Tag 引擎：统一打标签 (V7)
    title_lower_ecom = ecom_df['title'].str.lower().fillna('')
    ecom_df['tag_brand'] = apply_tags_vectorized(ecom_df['title'], defs["BRAND"])
    ecom_df['tag_color'] = apply_tags_vectorized(ecom_df['title'], defs["COLOR"])
    ecom_df['tag_tech'] = apply_tags_vectorized(ecom_df['title'], defs["TECH"])
    ecom_df['tag_swatch'] = apply_tags_vectorized(ecom_df['title'], defs["SWATCHES"]) # V5 新增
    ecom_df['tag_archetype'] = apply_tags_vectorized(ecom_df['title'], defs["ARCHETYPE"]) # V5 新增
    ecom_df['tag_whitening'] = title_lower_ecom.str.contains('|'.join(defs["WHITENING"]), case=False, na=False)
    ecom_df['tag_qise'] = title_lower_ecom.str.contains('|'.join(defs["QISE"]), case=False, na=False) # V5 新增
    ecom_df['tag_aesthetics'] = apply_tags_vectorized(ecom_df['title'], defs["AESTHETICS"]) # V5 新增
    
    ecom_df['archetype'] = ecom_df['tag_archetype'].apply(lambda x: x[0] if x else '其他')

    title_lower_social = social_df['title'].str.lower().fillna('')
    social_df['tag_brand'] = apply_tags_vectorized(social_df['title'], defs["BRAND"])
    social_df['tag_color'] = apply_tags_vectorized(social_df['title'], defs["COLOR"])
    social_df['tag_tech'] = apply_tags_vectorized(social_df['title'], defs["TECH"])
    social_df['tag_swatch'] = apply_tags_vectorized(social_df['title'], defs["SWATCHES"]) # V5 新增
    social_df['tag_aesthetics'] = apply_tags_vectorized(social_df['title'], defs["AESTHETICS"]) # V5 新增
    social_df['tag_whitening'] = title_lower_social.str.contains('|'.join(defs["WHITENING"]), case=False, na=False)
    social_df['tag_qise'] = title_lower_social.str.contains('|'.join(defs["QISE"]), case=False, na=False) # V5 新增
    
    logging.info("P-Tag 引擎打标完成")

    # 5. V7: 核心语义分析模块 (合并电商与社交)
    all_df_for_analysis = pd.concat([
        ecom_df[['tag_brand', 'tag_color', 'tag_tech', 'tag_whitening', 'tag_qise']],
        social_df[['tag_brand', 'tag_color', 'tag_tech', 'tag_whitening', 'tag_qise']]
    ]).reset_index(drop=True)

    # 5A. "显白" 共现分析
    whitening_df = all_df_for_analysis[all_df_for_analysis['tag_whitening'] == True]
    co_occurrence_data = {
        'color': Counter([tag for tags in whitening_df['tag_color'] for tag in tags]),
        'brand': Counter([tag for tags in whitening_df['tag_brand'] for tag in tags]),
        'tech': Counter([tag for tags in whitening_df['tag_tech'] for tag in tags]),
    }
    # V5: "显白" 色系 x 功效 共现热力图 (图 19)
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

    # 5B. V5: "显气色" 共现分析 (图 20, 21)
    qise_df = all_df_for_analysis[all_df_for_analysis['tag_qise'] == True]
    qise_co_occurrence_data = {
        'color': Counter([tag for tags in qise_df['tag_color'] for tag in tags]),
        'brand': Counter([tag for tags in qise_df['tag_brand'] for tag in tags]),
        'tech': Counter([tag for tags in qise_df['tag_tech'] for tag in tags]),
    }
    logging.info("“显气色”共现分析完成")
    
    # 5C. V5: "中国色彩"色卡分析 (图 11)
    swatch_ecom_df = ecom_df.explode('tag_swatch').dropna(subset=['tag_swatch'])
    swatch_sales = swatch_ecom_df.groupby('tag_swatch')['sales'].sum().reset_index(name='total_sales')
    swatch_sales['hex'] = swatch_sales['tag_swatch'].map(defs["SWATCH_HEX"]) # 映射 HEX
    swatch_analysis_df = swatch_sales.sort_values('total_sales', ascending=False)
    logging.info("“中国色彩”色卡分析完成")

    # 5D. V5: "社媒平均点赞"分析 (图 16)
    social_avg_likes_df = get_avg_likes_by_topic(social_df, defs)
    logging.info("“社媒平均点赞”分析完成")


    # 6. 评论洞察处理 (V5: 增加“显气色”)
    comments = comments_df['评论内容'].dropna().astype(str).str.lower()
    comments_insight = {
        'whitening_mentions': int(comments.str.contains("显白").sum()),
        'blackening_mentions': int(comments.str.contains("显黑").sum()),
        'qise_mentions': int(comments.str.contains('|'.join(defs["QISE"])).sum()), # V5 新增
        'total_comments': len(comments)
    }
    logging.info("评论洞察分析完成")

    # 7. 原始数据统计
    raw_counts = {
        '淘宝商品': len(tb_df), '京东商品': len(jd_df),
        '小红书笔记': len(xhs_df), '微博帖子': len(weibo_df),
        '淘宝评论': len(comments_df)
    }
    raw_counts_kpi = {
        '淘宝商品': len(tb_df), '京东商品': len(jd_df),
        '小红书笔记': len(xhs_df[~xhs_df['搜索词'].str.contains("小红书网页版", na=False)]), # V5: 清理 XHS
        '微博帖子': len(weibo_df),
        '淘宝评论': len(comments_df),
        '电商关键词': ecom_df['keyword'].nunique(),
        '社交关键词': social_df['keyword'].nunique()
    }
    
    # 8. 关键词策略数据 (V5: 修复 Top 10)
    ecom_k_series = ecom_df['keyword'].value_counts().head(10)
    ecom_k_df = pd.DataFrame({'keyword': ecom_k_series.index, 'count': ecom_k_series.values})
    
    social_k_series = social_df['keyword'].value_counts().head(10)
    social_k_df = pd.DataFrame({'keyword': social_k_series.index, 'count': social_k_series.values})

    keyword_strategy = {
        '电商关键词 (Top 10)': ecom_k_df,
        '社交关键词 (Top 10)': social_k_df
    }
    logging.info("关键词策略分析完成")

    # 9. 打包所有处理好的数据
    data_pack = {
        'ecom': ecom_df,
        'social': social_df,
        'comments_insight': comments_insight,
        'raw_counts': raw_counts,
        'raw_counts_kpi': raw_counts_kpi,
        'keyword_strategy': keyword_strategy,
        'definitions': defs, # V7: 必须返回定义
        
        # --- V5 新增数据 ---
        'co_occurrence': co_occurrence_data, # “显白”
        'qise_co_occurrence': qise_co_occurrence_data, # “显气色”
        'swatch_analysis': swatch_analysis_df, # “色卡”
        'social_avg_likes': social_avg_likes_df # “平均点赞”
    }
    
    logging.info("V7: 数据处理全部完成。")
    return data_pack