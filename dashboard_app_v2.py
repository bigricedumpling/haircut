import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import re
import logging
from collections import defaultdict
from streamlit_mermaid import st_mermaid

# --- 0. 页面配置与样式 ---
st.set_page_config(
    page_title="染发消费品数据故事",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 统一样式
DEFAULT_TEMPLATE = "plotly_white"
# 使用更高级的、简约的单色系 (蓝色系)
DEFAULT_COLOR_SEQUENCE = px.colors.sequential.Blues_r[1::2] # 反向蓝色系，跳色
GRAY_COLOR = 'rgb(200, 200, 200)' # 用于非重点数据

# --- 1. 数据加载与处理模块 (带缓存) ---

# --- 1A. 清洗工具 ---
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

# --- 1B. 核心关键词与标签定义 ---
# (这是我们分析引擎的核心，用于回答你的"关键词系统"问题)
@st.cache_data
def get_keyword_definitions():
    """集中管理所有关键词定义"""
    definitions = {
        "BRAND": {"欧莱雅": ["欧莱雅"], "施华蔻": ["施华蔻"], "花王": ["花王", "Liese"], "爱茉莉": ["爱茉莉", "美妆仙"], "章华": ["章华"]},
        "COLOR": {"棕色系": ["棕", "茶", "摩卡", "巧", "奶茶"], "红色/橘色系": ["红", "橘", "莓", "脏橘", "酒红"], "亚麻/青色系": ["亚麻", "青", "闷青", "灰绿"], "灰色/蓝色/紫色系": ["灰", "蓝", "紫", "芋泥", "蓝黑"], "金色/浅色系": ["金", "白金", "米金", "浅金", "漂"]},
        "TECH": {"植物": ["植物", "植萃"], "无氨": ["无氨", "温和"], "泡沫": ["泡沫", "泡泡"], "盖白发": ["盖白", "遮白"], "免漂": ["免漂", "无需漂"]},
        "WHITENING": ["显白", "黄皮", "肤色", "提亮", "去黄", "衬肤"]
    }
    return definitions

def apply_tags_vectorized(series, keywords_dict):
    """(更高效) 向量化标签应用函数"""
    series_lower = series.str.lower().fillna('')
    tags = pd.Series([[] for _ in range(len(series))], index=series.index)
    
    for tag, keywords in keywords_dict.items():
        pattern = '|'.join(keywords)
        mask = series_lower.str.contains(pattern, case=False, na=False)
        tags[mask] = tags[mask].apply(lambda x: x + [tag])
    return tags

# --- 1C. 数据加载函数 ---
@st.cache_data
def load_and_process_data(base_dir):
    """
    加载、合并、清洗并处理所有数据。
    这是整个仪表盘的数据核心。
    """
    data = {}
    
    # 1. 加载电商数据 (淘宝 + 京东)
    tb_files = list(base_dir.glob("淘宝商品目录/*.json"))
    tb_dfs = [pd.read_json(f) for f in tb_files if f.exists()]
    tb_df = pd.concat(tb_dfs, ignore_index=True) if tb_dfs else pd.DataFrame(columns=['产品名称', '产品价格', '付款人数', '地理位置'])
    
    jd_file = base_dir / "京东-商品搜索.json"
    jd_df = pd.read_json(jd_file) if jd_file.exists() else pd.DataFrame(columns=['商品名称', '价格', '评价人数', '搜索关键词'])

    # 统一化电商DF
    tb_unified = pd.DataFrame({
        'title': tb_df['产品名称'], 'price': tb_df['产品价格'].apply(clean_price), 'sales': tb_df['付款人数'].apply(clean_sales),
        'location': tb_df['地理位置'].astype(str).str.split(' ').str[0], 'platform': 'Taobao', 'keyword': tb_df.get('关键词', None)
    })
    jd_unified = pd.DataFrame({
        'title': jd_df['商品名称'], 'price': jd_df['价格'].apply(clean_price), 'sales': jd_df['评价人数'].apply(clean_sales),
        'location': '未知', 'platform': 'JD', 'keyword': jd_df.get('搜索关键词', None)
    })
    ecom_df = pd.concat([tb_unified, jd_unified], ignore_index=True).dropna(subset=['title'])
    ecom_df = ecom_df[(ecom_df['price'] > 10) & (ecom_df['price'] < 2000) & (ecom_df['sales'] > 10)]

    # 2. 加载社交数据 (小红书 + 微博) - 解决了你提出的"微博缺失"问题
    xhs_files = list(base_dir.glob("小红书-*.json"))
    xhs_dfs = [pd.read_json(f) for f in xhs_files if f.exists()]
    xhs_df = pd.concat(xhs_dfs, ignore_index=True) if xhs_dfs else pd.DataFrame(columns=['标题', '点赞数', '搜索词'])
    
    weibo_file = base_dir / "微博搜索关键词采集.json"
    weibo_df = pd.read_json(weibo_file) if weibo_file.exists() else pd.DataFrame(columns=['博文内容', '点赞数', '关键词'])

    # 统一化社交DF
    xhs_unified = pd.DataFrame({
        'title': xhs_df['标题'], 'likes': xhs_df['点赞数'].apply(clean_sales), 
        'platform': 'XHS', 'keyword': xhs_df.get('搜索词', None)
    })
    weibo_unified = pd.DataFrame({
        'title': weibo_df['博文内容'], 'likes': weibo_df['点赞数'].apply(clean_sales), 
        'platform': 'Weibo', 'keyword': weibo_df.get('关键词', None)
    })
    social_df = pd.concat([xhs_unified, weibo_unified], ignore_index=True).dropna(subset=['title'])
    # 清洗噪声
    social_df = social_df[~social_df['keyword'].str.contains("小红书网页版", na=False)]

    # 3. 加载评论数据
    comment_file = base_dir / "淘宝商品评论【网站反爬请查阅注意事项】.json"
    comments_df = pd.read_json(comment_file) if comment_file.exists() else pd.DataFrame(columns=['评论内容'])

    # 4. P-Tag 引擎：统一打标签
    defs = get_keyword_definitions()
    ecom_df['tag_brand'] = apply_tags_vectorized(ecom_df['title'], defs["BRAND"])
    ecom_df['tag_color'] = apply_tags_vectorized(ecom_df['title'], defs["COLOR"])
    ecom_df['tag_tech'] = apply_tags_vectorized(ecom_df['title'], defs["TECH"])
    ecom_df['tag_whitening'] = ecom_df['title'].str.contains('|'.join(defs["WHITENING"]), case=False, na=False)
    
    social_df['tag_brand'] = apply_tags_vectorized(social_df['title'], defs["BRAND"])
    social_df['tag_color'] = apply_tags_vectorized(social_df['title'], defs["COLOR"])
    social_df['tag_whitening'] = social_df['title'].str.contains('|'.join(defs["WHITENING"]), case=False, na=False)

    # 5. [新] 产品类型分析 (Product Archetype) - 解决你"更深产品分析"的需求
    def get_archetype(row):
        tech = set(row['tag_tech'])
        color = set(row['tag_color'])
        if '盖白发' in tech: return "功能型 (盖白发)"
        if '泡沫' in tech: return "便捷型 (泡沫)"
        if '植物' in tech or '无氨' in tech: return "健康型 (植物/无氨)"
        if '亚麻/青色系' in color or '灰色/蓝色/紫色系' in color: return "时尚型 (潮色)"
        if '棕色系' in color or '红色/橘色系' in color: return "主流型 (常规色)"
        return "其他"
    ecom_df['archetype'] = ecom_df.apply(get_archetype, axis=1)

    # 6. [新] 评论洞察处理
    comments = comments_df['评论内容'].dropna().astype(str)
    data['comments_insight'] = pd.DataFrame({
        'sentiment': ['正面口碑 ("显白")', '负面口碑 ("显黑")'],
        'count': [comments.str.contains("显白").sum(), comments.str.contains("显黑").sum()]
    })

    data['ecom'] = ecom_df
    data['social'] = social_df
    data['raw_counts'] = {
        '淘宝商品': len(tb_df), '京东商品': len(jd_df),
        '小红书笔记': len(xhs_df), '微博帖子': len(weibo_df),
        '淘宝评论': len(comments_df)
    }
    
    return data

# --- 2. 图表绘制模块 (Plotters) ---
# 每个图表都是一个独立的、低耦合的函数

# --- 2A. 方法论图表 ---
def plot_methodology_flow():
    """图 1: 分析方法论 (逻辑流程图)"""
    mermaid_chart = """
    graph TD
        subgraph "1. 关键词策略"
            K_Color["色系 (棕/红/亚麻...)"]
            K_Brand["品牌 (欧莱雅/施华蔻...)"]
            K_Tech["功效 (泡沫/植物...)"]
            K_Demand["诉求 (显白/黄皮...)"]
        end

        subgraph "2. 多源数据采集"
            P_TB["淘宝 (商品)"]
            P_JD["京东 (商品)"]
            P_XHS["小红书 (笔记)"]
            P_WB["微博 (帖子)"]
            P_Comm["淘宝 (评论)"]
        end
        
        subgraph "3. P-Tag 引擎处理"
            Engine["[智能标签化引擎]"]
        end
        
        subgraph "4. 产出四大洞察板块"
            O1["市场格局 (价格/品牌/区域)"]
            O2["产品拆解 (类型/功效)"]
            O3["社媒声量 (平台/热点)"]
            O4["核心诉求 (显白/口碑)"]
        end
        
        K_Color & K_Brand & K_Tech & K_Demand --> P_TB & P_JD & P_XHS & P_WB & P_Comm
        P_TB & P_JD & P_XHS & P_WB & P_Comm --> Engine
        Engine --> O1 & O2 & O3 & O4
    """
    return mermaid_chart

def plot_meta_source_volume(raw_counts):
    """图 2: 数据源总览"""
    df = pd.DataFrame.from_dict(raw_counts, orient='index', columns=['数据量']).reset_index().rename(columns={'index': '平台'})
    fig = px.bar(df, x='平台', y='数据量', title='图 2: 本次分析数据源总览',
                 text='数据量', color='平台', color_discrete_sequence=DEFAULT_COLOR_SEQUENCE)
    fig.update_layout(template=DEFAULT_TEMPLATE)
    fig.update_traces(textposition='outside')
    return fig

# --- 2B. 市场格局图表 ---
def plot_price_sales_matrix(df):
    """图 3: 市场价格区间分布"""
    bins = [0, 50, 100, 150, 200, 1000]
    labels = ["0-50元", "50-100元", "100-150元", "150-200元", "200+元"]
    df['price_bin'] = pd.cut(df['price'], bins=bins, labels=labels, right=False)
    
    plot_data = df.groupby('price_bin', observed=True).agg(
        total_sales=('sales', 'sum'),
        product_count=('title', 'count')
    ).reset_index()
    
    fig = px.scatter(
        plot_data, x='price_bin', y='product_count', size='total_sales', size_max=70,
        color='price_bin', color_discrete_sequence=DEFAULT_COLOR_SEQUENCE,
        title='图 3: 市场价格区间分布 (气泡大小 = 总销量)',
        labels={'price_bin': '价格区间', 'product_count': '商品链接数 (SKU数)', 'total_sales': '估算总销量'}
    )
    fig.update_layout(template=DEFAULT_TEMPLATE, yaxis_title='商品链接数 (SKU数)')
    return fig

def plot_brand_top10(df):
    """图 4: 热销品牌 Top 10"""
    brand_df = df.explode('tag_brand').dropna(subset=['tag_brand'])
    brand_data = brand_df.groupby('tag_brand')['sales'].sum().nlargest(10).sort_values(ascending=True)
    
    fig = px.bar(
        brand_data, x='sales', y=brand_data.index, orientation='h',
        title='图 4: 电商热销品牌 TOP 10 (按估算销量)', text='sales',
        color_discrete_sequence=[DEFAULT_COLOR_SEQUENCE[-1]] * 10
    )
    fig.update_traces(texttemplate='%{text:.2s}')
    fig.update_layout(template=DEFAULT_TEMPLATE, xaxis_title='估算总销量', yaxis_title=None)
    return fig

def plot_regional_treemaps(df):
    """图 5: [新] 区域洞察 (SKU vs 销量)"""
    location_df = df[(df['location'] != '未知') & (df['location'] != '海外') & (df['location'] != 'nan')]
    
    # SKU (卖家)
    sku_data = location_df.groupby('location')['title'].count().nlargest(15).reset_index()
    fig_sku = px.treemap(
        sku_data, path=[px.Constant("卖家 (SKU)"), 'location'], values='title',
        title='图 5a: 卖家分布 (SKU数 Top 15)',
        color_discrete_sequence=DEFAULT_COLOR_SEQUENCE
    )
    fig_sku.update_traces(textinfo="label+value+percent root")

    # Sales (买家)
    sales_data = location_df.groupby('location')['sales'].sum().nlargest(15).reset_index()
    fig_sales = px.treemap(
        sales_data, path=[px.Constant("销量"), 'location'], values='sales',
        title='图 5b: 销量分布 (总销量 Top 15)',
        color_discrete_sequence=DEFAULT_COLOR_SEQUENCE
    )
    fig_sales.update_traces(textinfo="label+value+percent root")
    
    return fig_sku, fig_sales

# --- 2C. 产品拆解图表 ---
def plot_color_share(df):
    """图 6: 主流色系市场销量占比"""
    color_df = df.explode('tag_color').dropna(subset=['tag_color'])
    color_data = color_df.groupby('tag_color')['sales'].sum().reset_index()
    
    fig = px.pie(
        color_data, names='tag_color', values='sales',
        title='图 6: 主流色系市场销量占比', hole=0.4,
        color_discrete_sequence=DEFAULT_COLOR_SEQUENCE
    )
    fig.update_traces(textinfo='percent+label')
    fig.update_layout(template=DEFAULT_TEMPLATE, legend_title_text='色系')
    return fig

def plot_product_archetype_matrix(df):
    """图 7: [新] 产品类型矩阵 (销量 vs 均价)"""
    plot_data = df[df['archetype'] != '其他'].groupby('archetype').agg(
        total_sales=('sales', 'sum'),
        avg_price=('price', 'mean'),
        product_count=('title', 'count')
    ).reset_index()

    fig = px.scatter(
        plot_data, x='total_sales', y='avg_price', size='product_count', size_max=60,
        color='archetype', text='archetype',
        title='图 7: 产品类型定位矩阵 (气泡大小 = SKU数)',
        labels={'total_sales': '估算总销量', 'avg_price': '平均价格 (元)', 'archetype': '产品类型'}
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(template=DEFAULT_TEMPLATE, xaxis_title='市场规模 (总销量)', yaxis_title='价格定位 (均价)', 
                      legend_title_text='产品类型')
    return fig

# --- 2D. 社交验证图表 ---
def plot_social_platform_share(df):
    """图 8: [新] 社交声量平台分布 (包含微博)"""
    platform_data = df.groupby('platform')['likes'].sum().reset_index()
    fig = px.pie(
        platform_data, names='platform', values='likes',
        title='图 8: 社交声量平台分布 (按总点赞)', hole=0.4,
        color_discrete_sequence=DEFAULT_COLOR_SEQUENCE
    )
    fig.update_traces(textinfo='percent+label')
    fig.update_layout(template=DEFAULT_TEMPLATE, showlegend=True)
    return fig

def plot_social_brand_buzz(df):
    """图 9: [新] 社交热门品牌 (Top 5)"""
    brand_df = df.explode('tag_brand').dropna(subset=['tag_brand'])
    brand_data = brand_df.groupby('tag_brand')['likes'].sum().nlargest(5).sort_values(ascending=True)
    
    fig = px.bar(
        brand_data, x='likes', y=brand_data.index, orientation='h',
        title='图 9: 社交热门品牌 TOP 5 (按总点赞)', text='likes',
        color_discrete_sequence=[DEFAULT_COLOR_SEQUENCE[-1]] * 5
    )
    fig.update_traces(texttemplate='%{text:.2s}')
    fig.update_layout(template=DEFAULT_TEMPLATE, xaxis_title='总点赞数', yaxis_title=None)
    return fig

# --- 2E. 核心洞察图表 ---
def plot_social_whitening_engagement(df):
    """图 10: "显白" 诉求的社媒溢价"""
    avg_likes_whitening = df[df['tag_whitening'] == True]['likes'].mean()
    avg_likes_normal = df[df['tag_whitening'] == False]['likes'].mean()
    
    plot_data = pd.DataFrame({
        '诉求类型': ['"显白" 相关笔记', '其他笔记'],
        '平均点赞数': [avg_likes_whitening, avg_likes_normal]
    })
    
    fig = px.bar(plot_data, x='诉求类型', y='平均点赞数', title='图 10: "显白" 诉求的社媒热度溢价 (XHS+Weibo)',
                 color='诉求类型', text='平均点赞数', color_discrete_sequence=[DEFAULT_COLOR_SEQUENCE[-1], GRAY_COLOR])
    fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
    fig.update_layout(template=DEFAULT_TEMPLATE, showlegend=False)
    return fig

def plot_comment_sentiment(df):
    """图 11: 真实评论情感声量"""
    fig = px.bar(df, x='sentiment', y='count', title='图 11: 真实评论情感声量对比',
                 color='sentiment', text='count', color_discrete_sequence=[DEFAULT_COLOR_SEQUENCE[-1], 'rgb(255, 100, 100)'])
    fig.update_traces(textposition='outside')
    fig.update_layout(template=DEFAULT_TEMPLATE, xaxis_title='情感关键词', yaxis_title='提及次数', showlegend=False)
    return fig

# --- 3. Streamlit 仪表盘主应用 ---
def main():
    
    # --- 0. 加载数据 ---
    try:
        data = load_and_process_data(Path('.'))
    except Exception as e:
        st.error(f"致命错误：数据加载或处理失败。请检查 JSON 文件是否存在且格式正确。错误: {e}")
        st.stop()

    # --- 1. 标题与执行摘要 ---
    st.title("🎨 染发消费品市场数据故事 (Data Story)")
    st.markdown("---")
    
    st.header("1. 执行摘要 (Executive Summary)")
    st.markdown("""
    本报告基于对 **{:,}** 条电商商品和 **{:,}** 条社媒帖子的深度分析，旨在为品牌方提供客观的市场洞察。
    """.format(
        data['raw_counts']['淘宝商品'] + data['raw_counts']['京东商品'],
        data['raw_counts']['小红书笔记'] + data['raw_counts']['微博帖子']
    ))
    
    st.success(
        """
        **核心结论 (TL;DR):**
        * **市场基本盘:** `50-100元` 价位段的 `棕色系`、`泡沫型` 产品是满足大众需求的绝对主力。
        * **竞争格局:** `欧莱雅` 与 `施华蔻` 在电商销量上遥遥领先；但市场货源高度集中于 `广东`，而 `江苏`、`重庆` 存在超级大卖。
        * **第一刚需 (The "Why"):** “**显白**” 是贯穿社交讨论与真实口碑的第一刚需。它是社媒的“流量密码”（平均点赞更高），也是用户满意的“核心防线”（“显白”好评 69 次 vs “显黑”差评 1 次）。
        """
    )
    
    st.markdown("---")

    # --- 2. 分析方法论 ---
    st.header("2. 分析方法论与数据漏斗")
    st.markdown("我们的洞察不来自猜想，而来自严谨的数据处理流程。我们开发了 **P-Tag 引擎（产品语义标签化系统）**，将非结构化的海量文本转化为可分析的洞察。")
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        st.subheader("图 1: 洞察分析流程")
        # st.mermaid(plot_methodology_flow())
        st_mermaid(plot_methodology_flow())
    with col2:
        st.subheader("图 2: 数据源总览")
        st.plotly_chart(plot_meta_source_volume(data['raw_counts']), use_container_width=True)
    
    st.markdown("---")

    # --- 3. 市场宏观格局：钱在哪里？ ---
    st.header("3. 市场宏观格局：钱在哪里？")
    st.markdown("我们首先分析电商大盘，回答三个核心问题：什么价位卖得好？谁在卖？货从哪里来？")
    
    # 图 3
    st.plotly_chart(plot_price_sales_matrix(data['ecom']), use_container_width=True)
    
    # 图 4 & 5
    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(plot_brand_top10(data['ecom']), use_container_width=True)
    with col4:
        # 两个 Treemap
        fig_sku, fig_sales = plot_regional_treemaps(data['ecom'])
        st.plotly_chart(fig_sku, use_container_width=True)
        st.plotly_chart(fig_sales, use_container_width=True)

    st.info(
        """
        **格局洞察:**
        1.  **价格带 (图 3):** `50-100元` 是竞争最激烈的红海，SKU数和总销量均是第一。`150-200元` 价位段 SKU 不多，但总销量可观，是溢价机会点。
        2.  **品牌 (图 4):** `欧莱雅` 与 `施华蔻` 构成第一梯队，销量断层领先。
        3.  **区域 (图 5a/5b):** 市场呈“产销分离”。`广东广州` 是最大的“货源集散地”（SKU最多），而 `江苏苏州`、`重庆` 则是“超级卖场”（SKU不多，但总销量极高）。
        """
    )
    
    st.markdown("---")
    
    # --- 4. 产品深度拆解：什么在热卖？ ---
    st.header("4. 产品深度拆解：什么在热卖？")
    st.markdown("在主流价位下，具体是哪些产品形态在驱动市场？我们创新性地将产品归纳为五大类型。")

    col5, col6 = st.columns([1, 1.5]) # 左窄右宽
    with col5:
        # 图 6
        st.plotly_chart(plot_color_share(data['ecom']), use_container_width=True)
    with col6:
        # 图 7
        st.plotly_chart(plot_product_archetype_matrix(data['ecom']), use_container_width=True)
        
    st.info(
        """
        **产品洞察:**
        1.  **色系 (图 6):** `棕色系` 是市场的绝对基本盘，占据近半销量，是大众消费者的“安全牌”。
        2.  **产品类型 (图 7):**
            * **跑量冠军 (右下):** `便捷型(泡沫)` 拥有最高的市场规模（总销量），但价格偏低。
            * **溢价蓝海 (左上):** `健康型(植物/无氨)` 销量不高，但成功占据了“高均价”心智，是品牌升级方向。
            * **稳定基石 (左下):** `功能型(盖白发)` 销量和均价都偏低，但需求稳定。
            * **时尚先锋 (中间):** `时尚型(潮色)` 处在中间地带，是连接大众与溢价的关键。
        """
    )

    st.markdown("---")

    # --- 5. 社媒声量验证：人们在谈论什么？ ---
    st.header("5. 社媒声量验证：人们在谈论什么？")
    st.markdown(f"电商数据告诉我们 *卖了什么*，**{len(data['social']):,}** 条社媒数据告诉我们 *人们关心什么*。")
    
    col7, col8 = st.columns(2)
    with col7:
        # 图 8
        st.plotly_chart(plot_social_platform_share(data['social']), use_container_width=True)
    with col8:
        # 图 9
        st.plotly_chart(plot_social_brand_buzz(data['social']), use_container_width=True)
    
    st.info(
        """
        **社媒洞察:**
        1.  **平台 (图 8):** `小红书` 是染发话题的绝对声量中心，总点赞量远超微博。
        2.  **品牌 (图 9):** 社媒声量与电商销量 **不完全匹配**。`欧莱雅` 和 `施华蔻` 依然热门，但 `爱茉莉`（美妆仙）在社媒的声量极高，是“社媒爆款”品牌，与其实际销量存在差距，值得关注。
        """
    )
    
    st.markdown("---")

    # --- 6. 核心洞察（The 'Why'）：“显白”是第一刚需 ---
    st.header("6. 核心洞察（The 'Why'）：“显白”是第一刚需")
    st.markdown("在所有功效和诉求中，我们发现“显白”是串联社媒热度与用户口碑的第一刚需。")

    col9, col10 = st.columns(2)
    with col9:
        # 图 10
        st.plotly_chart(plot_social_whitening_engagement(data['social']), use_container_width=True)
        st.markdown("**洞察 1: “显白”是社媒流量密码。**")
        st.markdown("在小红书和微博，提及“显白”的笔记，平均点赞数显著高于其他笔记，是驱动社交爆款的核心引擎。")

    with col10:
        # [新] 评论分析漏斗
        st.markdown("**评论分析漏斗：**")
        st.code(
            """
            1. 筛选高优/高销商品 (P0-P2)
            2. 采集 100 个商品链接
            3. 爬取 935 条真实用户评论
            4. 搜索核心口碑词 ("显白" vs "显黑")
            """,
            language=None
        )
        # 图 11
        st.plotly_chart(plot_comment_sentiment(data['comments_insight']), use_container_width=True)
        st.markdown("**洞察 2: “显白”是用户口碑红线。**")
        st.markdown("在 935 条真实评论中，对“显白”的正面提及 (69次) **压倒性地超过** 了对“显黑”的负面提及 (仅1次)。这证明“显黑”是用户绝对的雷区。")

    st.success(
        """
        **结论：** “显白”绝非营销噱头。它是 **社媒的“引爆点”**，更是 **口碑的“护城河”**。
        品牌在营销中强调“显白”，在产品研发中规避“显黑”，是赢得市场的双重保险。
        """
    )
    
    st.markdown("---")

    # --- 7. 结论与未来方向 ---
    st.header("7. 结论与未来方向")
    
    st.subheader("A. 客观结论")
    st.markdown(
        """
        1.  **市场在“消费降级”吗？** 没有。`50-100元` 的红海和 `150-200元` 的蓝海并存。消费者不是只买便宜的，而是在 `便捷(泡沫)` 和 `健康(植物)` 之间做不同取舍。
        2.  **销量 = 声量吗？** 不完全是。电商销冠 `欧莱雅` 和社媒声量冠军 `爱茉莉` 并非同一品牌。品牌需要“两条腿”走路。
        3.  **核心抓手是什么？** “显白”。这是唯一一个在社媒端被验证为“爆款密码”，又在用户口碑端被验证为“满意刚需”的诉求。
        """
    )
    
    st.subheader("B. 当前局限与未来方向")
    st.warning(
        """
        本次“闪电报告”数据量充足，但仍有局限性，未来可从以下方向完善：
        1.  **评论数据量不足：** 935 条评论只能做定性洞察，无法支撑大规模的“肤色-发色”匹配模型。未来需扩大评论爬取量至 10万+ 级别。
        2.  **社交数据清洗度：** 社交平台噪声数据多，当前的关键词清洗（如过滤“小红书网页版”）仍显粗糙，未来需引入 NLP 模型进行主题聚类。
        3.  **缺失京东评论：** 本次只分析了淘宝评论，未能获取京东的 `评价人数` 对应的真实评论，缺失了京东侧的口碑验证。
        4.  **微博数据价值低：** 分析显示微博数据多为营销和新闻，用户UGC价值远低于小红书，未来应将爬取重心**彻底转向小红书**。
        """
    )


if __name__ == "__main__":
    logging.info("启动 Streamlit 应用...")
    main()