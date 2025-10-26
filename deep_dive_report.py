import pandas as pd
import json
import re
from pathlib import Path
from collections import Counter, defaultdict
import logging
import os
from openai import OpenAI
import random
import math # (V4.1) 引入
import numpy as np # (V4.1) 引入

# --- 0. AI 辅助模块 (V4.1 深度版) ---
API_KEY = "sk-d2143aae7f64431fa5a718f924c109bc"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

try:
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
    )
    logging.info("AI 辅助模块 (Dashscope Qwen-max) V4.1 初始化成功。")
except Exception as e:
    logging.error(f"AI 模块初始化失败: {e}")
    client = None

def get_structured_ai_insight(system_prompt, analysis_data_str):
    """
    (V4.1) 调用 AI (Qwen-max) 生成结构化的多角度洞察。
    """
    if not client:
        return {
            "data_fact": "AI 模块未初始化",
            "zgen_insight": "AI 模块未初始化",
            "aesthetics_insight": "AI 模块未初始化",
            "brand_action": "AI 模块未初始化"
        }

    user_prompt = f"""
    请根据以下原始数据，严格按照我要求的JSON格式返回你的结构化分析。
    
    原始数据:
    {analysis_data_str}
    
    请严格返回如下JSON格式:
    {{
      "data_fact": "[数据事实] (客观描述数据，不超过2句)",
      "zgen_insight": "[Z世代洞察] (这对Z世代的'颜值经济'、'KOL口碑'、'悦己'等行为意味着什么？)",
      "aesthetics_insight": "[美学洞察] (这如何印证/挑战我们的'东方肤色美学'主题？如何关联'显白'、'显气色'、'去蜡黄'等痛点？)",
      "brand_action": "[品牌行动] (基于此，品牌应该做什么？例如：优化色卡、启动AR试色、KOL种草、强化安全成分...)"
    }}
    """

    try:
        completion = client.chat.completions.create(
            model="qwen-max",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"} 
        )
        insight_json_str = completion.choices[0].message.content
        insight_json = json.loads(insight_json_str)
        return insight_json
    except Exception as e:
        logging.error(f"AI 结构化洞察生成失败: {e}")
        return {
            "data_fact": f"AI 洞察生成失败: {e}",
            "zgen_insight": "N/A",
            "aesthetics_insight": "N/A",
            "brand_action": "N/A"
        }

def print_structured_insight(insight_json):
    """(V4.1) 打印结构化洞察"""
    print("\n  --- [AI 结构化深度洞察] ---")
    print(f"    [数据事实]: {insight_json.get('data_fact', 'N/A')}")
    print(f"    [Z世代洞察]: {insight_json.get('zgen_insight', 'N/A')}")
    print(f"    [美学洞察]: {insight_json.get('aesthetics_insight', 'N/A')}")
    print(f"    [品牌行动]: {insight_json.get('brand_action', 'N/A')}")
    print("  ---------------------------------")


# --- 1. 核心关键词定义 (V4.1 深度扩充版) ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# (A) 核心美学诉求 (基础)
WHITENING_KEYWORDS = ["显白", "黄皮", "肤色", "亲妈", "天菜", "素颜", "提亮", "去黄", "衬肤"]
QISE_KEYWORDS = ["显气色", "气色好", "红润", "元气", "血色感"]
NEG_SKIN_KEYWORDS = ["蜡黄", "暗沉", "疲惫", "没气色", "显黑", "不显白", "荧光", "芭比"]

# (B) 四大美学路径 (来自你的草案)
AESTHETICS_DICTIONARY = {
    "补光系": ["补光", "琉璃", "月光", "焦糖", "榛果", "米棕", "光泽"],
    "滤光系": ["滤光", "去黄", "修正", "宣纸", "奶茶", "灰棕", "亚麻", "青色"],
    "活血系": ["活血", "气色", "红润", "血色感", "树莓", "粉棕", "脏橘", "赤茶"],
    "衬光系": ["衬光", "对比", "釉", "瓷", "黑茶", "蓝黑", "乌木", "深棕"]
}

# (C) 品牌国别归类
BRAND_ORIGIN_DICTIONARY = {
    "欧美品牌": ["欧莱雅", "施华蔻", "L'Oréal", "Schwarzkopf"],
    "日韩品牌": ["爱茉莉", "美妆仙", "花王", "Liese", "莉婕", "美源", "Bigen", "Kao"],
    "国产新锐": ["三橡树", "章华", "温雅", "迪彩", "韩金靓"] 
}

# (D) Z世代与口碑
GEN_Z_KOL_DICTIONARY = {
    "KOL": ["博主", "KOL", "达人", "测评"],
    "KOC": ["素人", "用户", "分享", "笔记", "我", "姐妹们"] 
}

# (E) 评论情感分析词典
COMMENT_SENTIMENT_KEYWORDS = {
    "positive_general": ["好用", "不错", "推荐", "喜欢", "满意", "回购", "值得"],
    "positive_color_whitening": ["显白", "黄皮", "提亮", "去黄", "衬肤"],
    "positive_color_qise": ["显气色", "红润", "元气"],
    "positive_effect": ["安全", "温和", "不伤发", "植物", "无氨"],
    "negative_general": ["踩雷", "难用", "失望", "别买", "垃圾", "智商税"],
    "negative_color_black": ["显黑", "不显白", "荧光", "芭比", "村", "难看", "不适合黄皮"],
    "negative_color_dull": ["蜡黄", "暗沉", "疲惫", "没气色"],
    "negative_effect": ["伤发", "刺鼻", "过敏", "头皮疼"]
}

# AI 分析的系统提示
AI_SYSTEM_PROMPT = """
你是一位顶尖的市场洞察分析师，你的客户是一家染发品牌。
你的任务是基于我给你的原始数据，撰写结构化的商业洞察。
你必须时刻围绕两大核心主题：
1. "东方肤色美学": 消费者不再满足于"苍白"，而是追求"显白"和"显气色"（红润、鲜活）。她们的核心痛点是"蜡黄"、"暗沉"、"疲惫感"。
2. "Z世代消费观": 始于线上种草（小红书）、信赖KOL和KOC口碑、追求"颜值经济"和"悦己"、同时也关注"专业安全"和"成分"。
"""

# --- 2. 数据加载模块 (V4.1) ---

def load_data(base_dir):
    """加载所有核心数据源 (V4.1)"""
    data = {}
    
    # 1. 淘宝
    tb_files = [
        base_dir / "淘宝商品目录/淘宝网-商品列表页采集【网站反爬请查阅注意事项】.json",
        base_dir / "淘宝商品目录/淘宝网-商品列表页采集【网站反爬请查阅注意事项】-2.json",
        base_dir / "淘宝商品目录/淘宝网-商品列表页采集【网站反爬请查阅注意事项】-3.json" 
    ]
    tb_dfs = [pd.read_json(f) for f in tb_files if f.exists()]
    if not tb_dfs:
        logging.warning("未找到任何淘宝 JSON 文件。")
    data["tb"] = pd.concat(tb_dfs, ignore_index=True) if tb_dfs else pd.DataFrame()
    
    # 2. 京东
    jd_file = base_dir / "京东-商品搜索.json"
    data["jd"] = pd.read_json(jd_file) if jd_file.exists() else pd.DataFrame()
    
    # 3. 小红书
    xhs_files = [
        base_dir / "小红书-关键词笔记采集.json",
        base_dir / "小红书-关键词笔记采集2.json"
    ]
    xhs_dfs = [pd.read_json(f) for f in xhs_files if f.exists()]
    if not xhs_dfs:
        logging.warning("未找到任何小红书 JSON 文件。")
    data["xhs"] = pd.concat(xhs_dfs, ignore_index=True) if xhs_dfs else pd.DataFrame()

    # 4. 微博
    weibo_file = base_dir / "微博搜索关键词采集.json"
    data["weibo"] = pd.read_json(weibo_file) if weibo_file.exists() else pd.DataFrame()

    # 5. 淘宝评论
    comment_file = base_dir / "淘宝商品评论【网站反爬请查阅注意事项】.json"
    data["comments"] = pd.read_json(comment_file) if comment_file.exists() else pd.DataFrame()

    logging.info("所有数据加载完毕。")
    return data

# --- 3. V4.1 深度分析模块 ---

# ======================================================================
# 【【【 V4.1 BUGFIX 】】】
# 重写 clean_sales 函数以正确处理 NaN 值
# ======================================================================
def clean_sales(sales_str):
    """(V4.1 BUGFIX) 统一付款人数/评价人数，并正确处理 NaN"""
    
    # V4.1 Fix: Handle NaN/NaT/None values FIRST.
    # pd.isna() 是最健壮的检查方式
    if pd.isna(sales_str):
        return 0
    
    # Handle if it's already a clean number (int or float, but not NaN)
    if isinstance(sales_str, (int, float)):
        # We know it's not NaN, so int() conversion is safe.
        return int(sales_str)
    
    # Handle string parsing
    if isinstance(sales_str, str):
        number_part = re.search(r'(\d+\.?\d*)', sales_str)
        if not number_part: 
            return 0
        
        try:
            num = float(number_part.group(1))
        except ValueError: # Handle empty string or bad regex match
            return 0
            
        if '万' in sales_str: 
            return int(num * 10000)
        return int(num)
    
    # Fallback for any other weird type (e.g., list, dict)
    return 0
# ======================================================================
# 【【【 END BUGFIX 】】】
# ======================================================================

def find_first_match(text, dictionary):
    if not isinstance(text, str):
        return "未知"
    text_lower = text.lower()
    for category, keywords in dictionary.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return category
    return "未知"

def find_all_matches(text, dictionary):
    matches = set()
    if not isinstance(text, str):
        return list(matches)
    text_lower = text.lower()
    for category, keywords in dictionary.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                matches.add(category)
    return list(matches)

def print_header(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

# --- 
# V4.1 分析模块 1: 元数据分析 (Top 15)
# ---
def analyze_meta_data(data):
    print_header("Part 1: 元数据分析 (数据源与关键词)")
    
    # 1. 数据量总览
    total_ecom = len(data.get('tb', [])) + len(data.get('jd', []))
    total_social = len(data.get('xhs', [])) + len(data.get('weibo', []))
    total_comments = len(data.get('comments', []))
    print(f"  - 电商商品 (SKU) 总计: {total_ecom} 条 (淘宝: {len(data.get('tb', []))}, 京东: {len(data.get('jd', []))})")
    print(f"  - 社媒帖子 (Posts) 总计: {total_social} 条 (小红书: {len(data.get('xhs', []))}, 微博: {len(data.get('weibo', []))})")
    print(f"  - 用户评论 (UGC) 总计: {total_comments} 条")
    print("-" * 30)
    
    # 2. 爬取关键词分析 (V4.1: 升级到 Top 15)
    ai_prompt_data = f"电商商品: {total_ecom}\n社媒帖文: {total_social}\n用户评论: {total_comments}\n\n"
    ai_prompt_data += "电商爬取关键词 (Top 15):\n"
    
    ecom_keywords = []
    if "关键词" in data.get('tb', pd.DataFrame()).columns:
        ecom_keywords.append(data['tb']['关键词'])
    if "搜索关键词" in data.get('jd', pd.DataFrame()).columns:
        ecom_keywords.append(data['jd']['搜索关键词'])
    
    if ecom_keywords:
        all_ecom_keywords = pd.concat(ecom_keywords).value_counts().head(15) # V4.1 升级
        print("  - 电商 (TB/JD) 爬取关键词词频 Top 15:")
        for k, v in all_ecom_keywords.items():
            print(f"    - {k}: {v} 条")
            ai_prompt_data += f"    - {k}: {v}\n"

    ai_prompt_data += "\n社媒爬取关键词 (Top 15):\n"
    social_keywords = []
    if "搜索词" in data.get('xhs', pd.DataFrame()).columns:
        social_keywords.append(data['xhs']['搜索词'])
    if "搜索词" in data.get('weibo', pd.DataFrame()).columns: 
        social_keywords.append(data['weibo']['搜索词'])

    if social_keywords:
        all_social_keywords = pd.concat(social_keywords).value_counts().head(15) # V4.1 升级
        print("\n  - 社媒 (XHS/Weibo) 爬取关键词词频 Top 15:")
        for k, v in all_social_keywords.items():
            print(f"    - {k}: {v} 条")
            ai_prompt_data += f"    - {k}: {v}\n"
            
    insight = get_structured_ai_insight(AI_SYSTEM_PROMPT, ai_prompt_data)
    print_structured_insight(insight)

# --- 
# V4.1 分析模块 2: 区域分析 (Top 10)
# ---
def analyze_regional_data(tb_df):
    print_header("Part 2: 区域竞争格局分析 (来自淘宝数据)")
    
    if tb_df.empty or '地理位置' not in tb_df.columns:
        print("  - 淘宝数据中未找到 '地理位置' 字段，跳过区域分析。")
        return

    tb_df['province'] = tb_df['地理位置'].apply(lambda x: str(x).split(' ')[0] if isinstance(x, str) else '未知')
    tb_df['sales'] = tb_df['付款人数'].apply(clean_sales) # 使用 V4.1 bugfix 函数
    
    ai_prompt_data = "销量Top 10省份:\n"
    
    # 1. 按省份统计总销量 (V4.1: 升级到 Top 10)
    prov_sales = tb_df.groupby('province')['sales'].sum().sort_values(ascending=False)
    print("  - 按[省份]估算总销量 Top 10:")
    for p, s in prov_sales.head(10).items(): # V4.1 升级
        if p == '未知': continue
        print(f"    - {p}: {s:,.0f} 人付款")
        ai_prompt_data += f"{p}: {s:,.0f} 销量\n"
        
    ai_prompt_data += "\nSKU数Top 10省份:\n"
    
    # 2. 按省份统计商品数量 (SKU数) (V4.1: 升级到 Top 10)
    prov_sku = tb_df['province'].value_counts()
    print("\n  - 按[省份]商品链接数 (SKU数) Top 10:")
    for p, s in prov_sku.head(10).items(): # V4.1 升级
        if p == '未知': continue
        print(f"    - {p}: {s} 个商品")
        ai_prompt_data += f"{p}: {s} SKU\n"
        
    insight = get_structured_ai_insight(AI_SYSTEM_PROMPT, ai_prompt_data)
    print_structured_insight(insight)

# --- 
# V4.1 分析模块 3: 品牌国别
# ---
def analyze_brand_origin(data):
    print_header("Part 3: 品牌国别分析 (欧美 vs 日韩 vs 国产)")
    
    # 1. 电商销量分析 (淘宝 + 京东)
    ecom_df = pd.concat([data.get('tb', pd.DataFrame()), data.get('jd', pd.DataFrame())], ignore_index=True)
    if ecom_df.empty or ('产品名称' not in ecom_df.columns and '商品名称' not in ecom_df.columns):
        print("  - 电商数据不足，跳过品牌国别分析。")
        return

    # 兼容 '产品名称' (淘宝) 和 '商品名称' (京东)
    ecom_df['title'] = ecom_df['产品名称'] if '产品名称' in ecom_df.columns else ecom_df.get('商品名称') # 使用 .get() 避免KeyError
    
    # 兼容 '付款人数' (淘宝) 和 '评价人数' (京东)
    ecom_df['sales_col'] = ecom_df['付款人数'] if '付款人数' in ecom_df.columns else ecom_df.get('评价人数') # 使用 .get() 避免KeyError
    
    # 【【 V4.1 Bugfix 在此生效 】】
    ecom_df['sales'] = ecom_df['sales_col'].apply(clean_sales)
    
    ecom_df['brand_origin'] = ecom_df['title'].apply(lambda x: find_first_match(x, BRAND_ORIGIN_DICTIONARY))
    
    origin_sales = ecom_df.groupby('brand_origin')['sales'].sum().sort_values(ascending=False)
    
    print("  - [电商销量] 按品牌国别分析:")
    ai_prompt_data = "电商销量 (总和):\n"
    for origin, sales in origin_sales.items():
        if origin == '未知': continue
        print(f"    - {origin}: {sales:,.0f} 销量")
        ai_prompt_data += f"    - {origin}: {sales:,.0f} 销量\n"

    # 2. 社媒声量分析 (小红书)
    xhs_df = data.get('xhs', pd.DataFrame()).copy()
    if xhs_df.empty or '标题' not in xhs_df.columns:
        print("  - 小红书数据不足，跳过品牌国别声量分析。")
    else:
        xhs_df['likes'] = xhs_df['点赞数'].apply(clean_sales) # 使用 V4.1 bugfix 函数
        xhs_df['brand_origin'] = xhs_df['标题'].apply(lambda x: find_first_match(x, BRAND_ORIGIN_DICTIONARY))
        
        origin_likes = xhs_df.groupby('brand_origin')['likes'].sum().sort_values(ascending=False)
        origin_posts = xhs_df['brand_origin'].value_counts()

        print("\n  - [社媒声量 (XHS)] 按品牌国别分析:")
        ai_prompt_data += "\n社媒声量 (总点赞):\n"
        for origin, likes in origin_likes.items():
            if origin == '未知': continue
            posts = origin_posts.get(origin, 0)
            avg_likes = likes / posts if posts > 0 else 0
            print(f"    - {origin}: {likes:,.0f} 总点赞 (来自 {posts} 篇笔记, 均赞 {avg_likes:.0f})")
            ai_prompt_data += f"    - {origin}: {likes:,.0f} 总点赞, {posts} 篇笔记, 均赞 {avg_likes:.0f}\n"

    insight = get_structured_ai_insight(AI_SYSTEM_PROMPT, ai_prompt_data)
    print_structured_insight(insight)

# --- 
# V4.1 分析模块 4: Z世代与KOL (深度交叉版)
# ---
def analyze_gen_z_kol_influence(xhs_df):
    print_header("Part 4: Z世代口碑影响力分析 (V4.1: KOL/KOC 交叉分析)")
    
    if xhs_df.empty or '作者' not in xhs_df.columns or '标题' not in xhs_df.columns:
        print("  - 小红书数据不足或缺少'作者'/'标题'字段，跳过KOL分析。")
        return

    kol_pattern = '|'.join(GEN_Z_KOL_DICTIONARY['KOL']).lower()
    
    xhs_df['is_kol'] = xhs_df['作者'].astype(str).str.lower().str.contains(kol_pattern, na=False)
    xhs_df['likes'] = xhs_df['点赞数'].apply(clean_sales) # 使用 V4.1 bugfix 函数
    
    kol_posts = xhs_df[xhs_df['is_kol'] == True].copy()
    koc_posts = xhs_df[xhs_df['is_kol'] == False].copy()
    
    kol_count = len(kol_posts)
    koc_count = len(koc_posts)
    
    if kol_count == 0 or koc_count == 0:
        print("  - KOL 或 KOC 笔记数量为0，无法进行交叉分析。")
        return

    # 1. 均赞对比
    kol_total_likes = kol_posts['likes'].sum()
    kol_avg_likes = kol_total_likes / kol_count
    
    koc_total_likes = koc_posts['likes'].sum()
    koc_avg_likes = koc_total_likes / koc_count
    
    print("  - [V4.1] 影响力对比 (均赞):")
    print(f"    - KOL 笔记: {kol_count} 篇, 平均点赞: {kol_avg_likes:,.0f}")
    print(f"    - KOC 笔记: {koc_count} 篇, 平均点赞: {koc_avg_likes:,.0f}")
    
    ai_prompt_data = f"KOL 笔记: {kol_count} 篇, 平均点赞: {kol_avg_likes:,.0f}\n"
    ai_prompt_data += f"KOC (素人) 笔记: {koc_count} 篇, 平均点赞: {koc_avg_likes:,.0f}\n"
    ai_prompt_data += f"KOL 均赞是 KOC 的 {kol_avg_likes / max(1, koc_avg_likes):.1f} 倍\n"
    
    # 2. (V4.1 新增) 内容交叉分析
    print("\n  - [V4.1] 议题引领力 (内容提及率):")
    
    whitening_pattern = '|'.join(WHITENING_KEYWORDS)
    qise_pattern = '|'.join(QISE_KEYWORDS)
    
    kol_posts['has_whitening'] = kol_posts['标题'].astype(str).str.contains(whitening_pattern, case=False)
    kol_posts['has_qise'] = kol_posts['标题'].astype(str).str.contains(qise_pattern, case=False)
    
    koc_posts['has_whitening'] = koc_posts['标题'].astype(str).str.contains(whitening_pattern, case=False)
    koc_posts['has_qise'] = koc_posts['标题'].astype(str).str.contains(qise_pattern, case=False)

    kol_whitening_pct = kol_posts['has_whitening'].mean() * 100
    kol_qise_pct = kol_posts['has_qise'].mean() * 100
    koc_whitening_pct = koc_posts['has_whitening'].mean() * 100
    koc_qise_pct = koc_posts['has_qise'].mean() * 100
    
    print(f"    - '显白' 提及率: KOL {kol_whitening_pct:.1f}% vs KOC {koc_whitening_pct:.1f}%")
    print(f"    - '显气色' 提及率: KOL {kol_qise_pct:.1f}% vs KOC {koc_qise_pct:.1f}%")

    ai_prompt_data += f"\n'显白' 提及率: KOL {kol_whitening_pct:.1f}% vs KOC {koc_whitening_pct:.1f}%\n"
    ai_prompt_data += f"'显气色' 提及率: KOL {kol_qise_pct:.1f}% vs KOC {koc_qise_pct:.1f}%\n"

    insight = get_structured_ai_insight(AI_SYSTEM_PROMPT, ai_prompt_data)
    print_structured_insight(insight)

# --- 
# V4.1 分析模块 5: 核心美学诉求 (Top 10)
# ---
def analyze_skin_aesthetics_insight(data):
    print_header("Part 5: 核心美学诉求分析 (痛点 vs 刚需 vs 机会)")
    
    ai_prompt_data = ""
    
    # 1. 电商 (淘宝) 平台
    tb_df = data.get('tb', pd.DataFrame()).copy()
    if not tb_df.empty:
        # 兼容 '产品名称' (淘宝)
        tb_df['title'] = tb_df['产品名称'] if '产品名称' in tb_df.columns else ""
        tb_df['sales'] = tb_df['付款人数'].apply(clean_sales) # 使用 V4.1 bugfix 函数
        
        tb_df['aesthetics'] = tb_df['title'].apply(lambda x: find_all_matches(x, {
            "显白": WHITENING_KEYWORDS,
            "显气色": QISE_KEYWORDS,
            "负面/痛点": NEG_SKIN_KEYWORDS
        }))
        
        tb_exploded = tb_df.explode('aesthetics')
        
        print("  - [电商] 诉求分析 (按商品数 Top 10):")
        ecom_counts = tb_exploded['aesthetics'].value_counts()
        print(ecom_counts.head(10)) # V4.1 升级
        
        print("\n  - [电商] 诉求分析 (按平均销量 Top 10):")
        ecom_avg_sales = tb_exploded.groupby('aesthetics')['sales'].mean().sort_values(ascending=False)
        print(ecom_avg_sales.head(10)) # V4.1 升级

        ai_prompt_data += "电商平台 (平均销量 Top 10):\n"
        for k, v in ecom_avg_sales.head(10).items(): # V4.1 升级
            ai_prompt_data += f"  - {k}: {v:.0f}\n"

    # 2. 社交 (小红书) 平台
    xhs_df = data.get('xhs', pd.DataFrame()).copy()
    if not xhs_df.empty:
        xhs_df['likes'] = xhs_df['点赞数'].apply(clean_sales) # 使用 V4.1 bugfix 函数
        
        xhs_df['aesthetics'] = xhs_df['标题'].apply(lambda x: find_all_matches(x, {
            "显白": WHITENING_KEYWORDS,
            "显气色": QISE_KEYWORDS,
            "负面/痛点": NEG_SKIN_KEYWORDS
        }))
        
        xhs_exploded = xhs_df.explode('aesthetics')

        print("\n  - [社媒 (XHS)] 诉求分析 (按笔记数 Top 10):")
        social_counts = xhs_exploded['aesthetics'].value_counts()
        print(social_counts.head(10)) # V4.1 升级

        print("\n  - [社媒 (XHS)] 诉求分析 (按平均点赞 Top 10):")
        social_avg_likes = xhs_exploded.groupby('aesthetics')['likes'].mean().sort_values(ascending=False)
        print(social_avg_likes.head(10)) # V4.1 升级

        ai_prompt_data += "\n社媒平台 (平均点赞 Top 10):\n"
        for k, v in social_avg_likes.head(10).items(): # V4.1 升级
            ai_prompt_data += f"  - {k}: {v:.0f}\n"

    insight = get_structured_ai_insight(AI_SYSTEM_PROMPT, ai_prompt_data)
    print_structured_insight(insight)

# --- 
# V4.1 分析模块 6: 四大美学路径
# ---
def analyze_four_paths_aesthetics(data):
    print_header("Part 6: [核心] 四大美学路径量化分析 (补光/滤光/活血/衬光)")
    
    ai_prompt_data = ""
    
    # 1. 电商 (淘宝 + 京东) 平台
    ecom_df = pd.concat([data.get('tb', pd.DataFrame()), data.get('jd', pd.DataFrame())], ignore_index=True)
    if not ecom_df.empty:
        ecom_df['title'] = ecom_df['产品名称'] if '产品名称' in ecom_df.columns else ecom_df.get('商品名称', "")
        ecom_df['sales_col'] = ecom_df['付款人数'] if '付款人数' in ecom_df.columns else ecom_df.get('评价人数', "")
        ecom_df['sales'] = ecom_df['sales_col'].apply(clean_sales) # 使用 V4.1 bugfix 函数
        
        ecom_df['path'] = ecom_df['title'].apply(lambda x: find_first_match(x, AESTHETICS_DICTIONARY))
        
        print("  - [电商] 四大路径 (按商品数):")
        ecom_counts = ecom_df['path'].value_counts()
        print(ecom_counts)
        
        print("\n  - [电商] 四大路径 (按总销量):")
        ecom_total_sales = ecom_df.groupby('path')['sales'].sum().sort_values(ascending=False)
        print(ecom_total_sales)

        ai_prompt_data += "电商平台 (总销量):\n"
        for k, v in ecom_total_sales.items():
            if k == '未知': continue
            ai_prompt_data += f"  - {k}: {v:,.0f}\n"

    # 2. 社交 (小红书) 平台
    xhs_df = data.get('xhs', pd.DataFrame()).copy()
    if not xhs_df.empty:
        xhs_df['likes'] = xhs_df['点赞数'].apply(clean_sales) # 使用 V4.1 bugfix 函数
        xhs_df['path'] = xhs_df['标题'].apply(lambda x: find_first_match(x, AESTHETICS_DICTIONARY))
        
        print("\n  - [社媒 (XHS)] 四大路径 (按笔记数):")
        social_counts = xhs_df['path'].value_counts()
        print(social_counts)

        print("\n  - [社媒 (XHS)] 四大路径 (按平均点赞):")
        social_avg_likes = xhs_df.groupby('path')['likes'].mean().sort_values(ascending=False)
        print(social_avg_likes)

        ai_prompt_data += "\n社媒平台 (平均点赞):\n"
        for k, v in social_avg_likes.items():
            if k == '未知': continue
            ai_prompt_data += f"  - {k}: {v:.0f}\n"

    insight = get_structured_ai_insight(AI_SYSTEM_PROMPT, ai_prompt_data)
    print_structured_insight(insight)

# --- 
# V4.1 分析模块 7: 评论口碑 (AI 样本 200)
# ---
def analyze_comments_ai_qualitative(comments_df):
    print_header(f"Part 7: 评论口碑分析 (V4.1: 统计 + AI定性 200条)")
    
    if comments_df.empty or '评论内容' not in comments_df.columns:
        print("  - 未找到 '评论内容' 或评论数据为空，跳过分析。")
        return

    comments = comments_df['评论内容'].dropna().astype(str)
    
    # --- 7A. 关键词统计 (保留关键洞察) ---
    print("  --- 7A: 关键词定量统计 ---")
    sentiment_counts = defaultdict(int)
    for comment in comments:
        comment_lower = comment.lower()
        for sentiment, keywords in COMMENT_SENTIMENT_KEYWORDS.items():
            for kw in keywords:
                if kw in comment_lower:
                    sentiment_counts[sentiment] += 1
    
    pos_whitening = sentiment_counts['positive_color_whitening']
    pos_qise = sentiment_counts['positive_color_qise']
    neg_black = sentiment_counts['negative_color_black']
    neg_dull = sentiment_counts['negative_color_dull']
    
    print(f"    - 正面-显白 (如 '显白'): {pos_whitening} 次")
    print(f"    - 正面-显气色 (如 '红润'): {pos_qise} 次")
    print(f"    - 负面-显黑 (如 '显黑'): {neg_black} 次")
    print(f"    - 负面-暗沉 (如 '蜡黄'): {neg_dull} 次")
    
    whitening_count = comments.str.contains("显白").sum()
    blackening_count = comments.str.contains("显黑").sum()
    ratio = whitening_count / max(1, blackening_count)
    print(f"    - [关键比]: “显白”提及 {whitening_count} 次 vs “显黑”提及 {blackening_count} 次 (比例 {ratio:.0f} : 1)")

    ai_prompt_data = f"“显白”提及: {whitening_count} 次\n“显黑”提及: {blackening_count} 次\n"
    ai_prompt_data += f"“显气色”提及: {pos_qise} 次\n“暗沉/蜡黄”提及: {neg_dull} 次\n"

    # --- 7B. (V4.1 升级) AI 深度定性分析 (样本 200) ---
    print("\n  --- 7B: AI 深度定性抽样 (抽样 200 条) ---") # V4.1 升级
    if not client:
        print("    - AI 模块未初始化，跳过深度定性分析。")
        insight = get_structured_ai_insight(AI_SYSTEM_PROMPT, ai_prompt_data)
        print_structured_insight(insight)
        return

    try:
        sample_size = min(200, len(comments)) # V4.1 升级
        comment_sample = random.sample(list(comments), sample_size)
        comment_sample_str = "\n".join([f"- {c}" for c in comment_sample])

        ai_system_prompt_comments = f"""
        {AI_SYSTEM_PROMPT}
        我将给你 {sample_size} 条真实的染发产品用户评论。
        请你扮演分析师，通读它们，然后归纳总结用户在“东方肤色美学”方面（显白、显气色、蜡黄、暗沉）的核心满意点和核心抱怨点。
        
        请严格返回如下JSON格式:
        {{
          "positive_summary": "[核心满意点] (例如: 很多用户提到'显白'效果明显，尤其对黄皮友好。少数提到了'显气色'。)",
          "negative_summary": "[核心抱怨点] (例如: 最大的雷区是'显黑'。也有用户抱怨颜色导致'显蜡黄'或'没精神'。)",
          "unmet_needs": "[未被满足的需求] (从抱怨中推测，用户的真实痛点是什么？例如：他们需要能精准'去黄'、'提亮'的产品，而不仅是'好看'的颜色。)"
        }}
        """
        
        ai_user_prompt_comments = f"以下是 {sample_size} 条评论：\n{comment_sample_str}"
        
        completion = client.chat.completions.create(
            model="qwen-max",
            messages=[
                {"role": "system", "content": ai_system_prompt_comments},
                {"role": "user", "content": ai_user_prompt_comments},
            ],
            response_format={"type": "json_object"}
        )
        
        qualitative_insight = json.loads(completion.choices[0].message.content)
        
        print(f"    [AI 核心满意点]: {qualitative_insight.get('positive_summary', 'N/A')}")
        print(f"    [AI 核心抱怨点]: {qualitative_insight.get('negative_summary', 'N/A')}")
        print(f"    [AI 未满足的需求]: {qualitative_insight.get('unmet_needs', 'N/A')}")

        ai_prompt_data += "\nAI 定性总结 (200条样本):\n"
        ai_prompt_data += f"满意点: {qualitative_insight.get('positive_summary', 'N/A')}\n"
        ai_prompt_data += f"抱怨点: {qualitative_insight.get('negative_summary', 'N/A')}\n"
        ai_prompt_data += f"未满足的需求: {qualitative_insight.get('unmet_needs', 'N/A')}\n"

    except Exception as e:
        print(f"    - AI 定性分析失败: {e}")
        
    # (V4.1) 最终的 AI 结构化洞察 (结合了 7A 和 7B)
    insight = get_structured_ai_insight(AI_SYSTEM_PROMPT, ai_prompt_data)
    print_structured_insight(insight)


# --- 4. 主执行函数 (V4.1) ---
def main():
    base_dir = Path('.') # 假设脚本在 data_analizy 根目录
    
    print("正在启动 [V4.1 深度挖掘版] 数据可行性分析 (已集成结构化AI)...")
    
    # 加载
    try:
        data = load_data(base_dir)
    except Exception as e:
        logging.error(f"数据加载失败，请检查文件路径和格式: {e}")
        return

    # --- V4.1 分析流程 ---
    
    # Part 1: 元数据 (Top 15)
    analyze_meta_data(data)
    
    # Part 2: 区域格局 (Top 10)
    analyze_regional_data(data.get('tb', pd.DataFrame()))
    
    # Part 3: (新) 品牌国别
    analyze_brand_origin(data)
    
    # Part 4: (新) Z世代KOL (交叉分析)
    analyze_gen_z_kol_influence(data.get('xhs', pd.DataFrame()))
        
    # Part 5: (升级) 核心美学诉求 (Top 10)
    analyze_skin_aesthetics_insight(data)
    
    # Part 6: (新) 四大美学路径 (核心)
    analyze_four_paths_aesthetics(data)
        
    # Part 7: (升级) 评论口碑 (AI 样本 200)
    analyze_comments_ai_qualitative(data.get('comments', pd.DataFrame()))
        
    print_header("V4.1 深度分析完成")
    print("请将以上所有输出内容 (从 '正在启动 [V4.1 深度挖掘版]...' 开始) 完整复制并发送给我。")
    print("这份报告将包含7个部分的深度、多角度洞察，为仪表盘提供充足的弹药。")

if __name__ == "__main__":
    main()