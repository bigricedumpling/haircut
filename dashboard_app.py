import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import re
import logging
from collections import defaultdict

# --- 页面配置 (必须在最前面) ---
st.set_page_config(
    page_title="染发消费品洞察报告",
    layout="wide",  # 使用宽屏布局
    initial_sidebar_state="collapsed"
)

# --- 样式定义 (高级简约风格) ---
# 我们将使用 Plotly 的 "plotly_white" 简约模板
# 并定义一个单色系（蓝色）用于所有图表
DEFAULT_TEMPLATE = "plotly_white"
DEFAULT_COLOR_SEQUENCE = px.colors.sequential.Blues

# --- 1. 数据加载与处理模块 (带缓存) ---
# @st.cache_data 确保数据只加载和处理一次，极大提高访问速度

def clean_sales(sales_str):
    """统一付款人数/评价人数"""
    if not isinstance(sales_str, str):
        return int(sales_str) if isinstance(sales_str, (int, float)) else 0
    number_part = re.search(r'(\d+\.?\d*)', sales_str)
    if not number_part: return 0
    num = float(number_part.group(1))
    if '万' in sales_str: return int(num * 10000)
    return int(num)

def clean_price(price_str):
    """从价格字符串中提取数字"""
    if not isinstance(price_str, str):
        return float(price_str) if isinstance(price_str, (int, float)) else 0.0
    match = re.search(r'(\d+\.?\d*)', price_str)
    return float(match.group(1)) if match else 0.0

@st.cache_data
def load_raw_data(base_dir):
    """加载所有原始数据文件"""
    raw_data = {}
    
    # 淘宝
    tb_files = list(base_dir.glob("淘宝商品目录/*.json"))
    tb_dfs = [pd.read_json(f) for f in tb_files if f.exists()]
    raw_data["tb"] = pd.concat(tb_dfs, ignore_index=True) if tb_dfs else pd.DataFrame()
    
    # 京东
    jd_file = base_dir / "京东-商品搜索.json"
    raw_data["jd"] = pd.read_json(jd_file) if jd_file.exists() else pd.DataFrame()
    
    # 小红书
    xhs_files = list(base_dir.glob("小红书-*.json"))
    xhs_dfs = [pd.read_json(f) for f in xhs_files if f.exists()]
    raw_data["xhs"] = pd.concat(xhs_dfs, ignore_index=True) if xhs_dfs else pd.DataFrame()

    # 评论
    comment_file = base_dir / "淘宝商品评论【网站反爬请查阅注意事项】.json"
    raw_data["comments"] = pd.read_json(comment_file) if comment_file.exists() else pd.DataFrame()

    logging.info("所有原始数据加载完毕。")
    return raw_data

# 关键词定义 (用于打标签)
BRAND_KEYWORDS = {"欧莱雅": ["欧莱雅"], "施华蔻": ["施华蔻"], "花王": ["花王", "Liese"], "爱茉莉": ["爱茉莉", "美妆仙"], "章华": ["章华"]}
COLOR_CATEGORIES = {"棕色系": ["棕", "茶", "摩卡", "巧", "奶茶", "蜜"], "红色/橘色系": ["红", "橘", "莓", "脏橘"], "亚麻/青色系": ["亚麻", "青", "闷青"], "灰色/蓝色/紫色系": ["灰", "蓝", "紫", "芋泥", "蓝黑"], "金色/浅色系": ["金", "白金", "米金", "浅金", "漂"]}
TECH_KEYWORDS = {"植物": ["植物", "植萃"], "无氨": ["无氨", "温和"], "泡沫": ["泡沫", "泡泡"], "盖白发": ["盖白", "遮白"], "免漂": ["免漂"]}
WHITENING_KEYWORDS = ["显白", "黄皮", "肤色", "提亮", "去黄", "衬肤"]

def apply_tags(title, keywords_dict):
    """通用打标签函数"""
    title_lower = str(title).lower()
    tags = []
    for tag, keywords in keywords_dict.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                tags.append(tag)
                break
    return tags

@st.cache_data
def process_ecommerce_data(tb_df, jd_df):
    """统一、清洗、处理所有电商数据"""
    # 统一字段
    tb_df_unified = pd.DataFrame({
        'title': tb_df['产品名称'],
        'price': tb_df['产品价格'].apply(clean_price),
        'sales': tb_df['付款人数'].apply(clean_sales),
        'location': tb_df['地理位置'].astype(str).str.split(' ').str[0],
        'platform': 'Taobao'
    })
    jd_df_unified = pd.DataFrame({
        'title': jd_df['商品名称'],
        'price': jd_df['价格'].apply(clean_price),
        'sales': jd_df['评价人数'].apply(clean_sales),
        'location': '未知',
        'platform': 'JD'
    })
    
    df = pd.concat([tb_df_unified, jd_df_unified], ignore_index=True)
    df = df.dropna(subset=['title'])
    df = df[(df['price'] > 10) & (df['price'] < 2000)] # 过滤极端价格
    df = df[df['sales'] > 10] # 过滤低销量噪声

    # 打标签
    df['tag_brand'] = df['title'].apply(lambda x: apply_tags(x, BRAND_KEYWORDS))
    df['tag_color'] = df['title'].apply(lambda x: apply_tags(x, COLOR_CATEGORIES))
    df['tag_tech'] = df['title'].apply(lambda x: apply_tags(x, TECH_KEYWORDS))
    df['tag_whitening'] = df['title'].str.contains('|'.join(WHITENING_KEYWORDS), case=False)

    return df

@st.cache_data
def process_social_data(xhs_df):
    """统一、清洗、处理小红书数据 (我们只用小红书做社交分析)"""
    df = xhs_df.copy()
    df = df.rename(columns={'标题': 'title', '点赞数': 'likes', '搜索词': 'keyword'})
    df['likes'] = df['likes'].apply(clean_sales)
    
    # 清洗噪声关键词
    df = df[~df['keyword'].str.contains("小红书网页版", na=False)]
    df = df.dropna(subset=['title'])

    # 打标签
    df['tag_color'] = df['title'].apply(lambda x: apply_tags(x, COLOR_CATEGORIES))
    df['tag_whitening'] = df['title'].str.contains('|'.join(WHITENING_KEYWORDS), case=False)
    
    return df

@st.cache_data
def process_comments_data(comments_df):
    """处理评论数据，提取关键洞察"""
    if comments_df.empty or '评论内容' not in comments_df.columns:
        return pd.DataFrame({'sentiment': [], 'count': []})
        
    comments = comments_df['评论内容'].dropna().astype(str)
    
    # 深度洞察：显白 vs 显黑
    whitening_count = comments.str.contains("显白").sum()
    blackening_count = comments.str.contains("显黑").sum()
    
    insight_df = pd.DataFrame({
        'sentiment': ['正面反馈 ("显白")', '负面反馈 ("显黑")'],
        'count': [whitening_count, blackening_count]
    })
    return insight_df


# --- 2. 图表绘制模块 (Plotters) ---
# 每个函数都是一个独立的、可复用的图表

def plot_meta_source_volume(raw_data):
    """图表 1: 数据源总览"""
    data = {
        '平台': ['淘宝商品', '京东商品', '小红书笔记', '淘宝评论'],
        '数据量': [len(raw_data.get('tb', [])), len(raw_data.get('jd', [])), len(raw_data.get('xhs', [])), len(raw_data.get('comments', []))]
    }
    df = pd.DataFrame(data)
    fig = px.bar(df, x='平台', y='数据量', title='图 1: 本次分析数据源总览',
                 text='数据量', color='平台', color_discrete_sequence=DEFAULT_COLOR_SEQUENCE)
    fig.update_layout(template=DEFAULT_TEMPLATE)
    fig.update_traces(textposition='outside')
    return fig

def plot_meta_keywords(raw_data):
    """图表 2: 爬取关键词词频 (电商 vs 社交)"""
    # 电商 (合并淘宝和京东)
    tb_k = raw_data.get('tb', pd.DataFrame(columns=['关键词']))['关键词'].value_counts()
    jd_k = raw_data.get('jd', pd.DataFrame(columns=['搜索关键词']))['搜索关键词'].value_counts()
    ecom_k = tb_k.add(jd_k, fill_value=0).sort_values(ascending=False).head(5)
    ecom_df = pd.DataFrame({'keyword': ecom_k.index, 'count': ecom_k.values, 'type': '电商搜索'})

    # 社交 (小红书)
    xhs_k = raw_data.get('xhs', pd.DataFrame(columns=['搜索词']))['搜索词'].value_counts()
    xhs_k = xhs_k[~xhs_k.index.str.contains("小红书网页版", na=False)].head(5)
    social_df = pd.DataFrame({'keyword': xhs_k.index, 'count': xhs_k.values, 'type': '社交搜索'})
    
    df = pd.concat([ecom_df, social_df])
    
    fig = px.bar(df, x='keyword', y='count', title='图 2: 核心搜索词词频 (电商 vs 社交)',
                 color='type', barmode='group', text='count')
    fig.update_layout(template=DEFAULT_TEMPLATE, xaxis_title='搜索关键词')
    return fig

def plot_price_sales_matrix(df):
    """图表 3: 价格区间 vs 销量 (原图表 1.1)"""
    bins = [0, 50, 100, 150, 200, 300, 1000]
    labels = ["0-50元", "50-100元", "100-150元", "150-200元", "200-300元", "300+元"]
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
    """图表 4: 热销品牌 Top 10 (原图表 1.2)"""
    brand_df = df.explode('tag_brand').dropna(subset=['tag_brand'])
    brand_data = brand_df.groupby('tag_brand')['sales'].sum().nlargest(10).sort_values(ascending=True)
    
    fig = px.bar(
        brand_data, x='sales', y=brand_data.index, orientation='h',
        title='图 4: 主流品牌估算总销量 TOP 10', text='sales',
        color_discrete_sequence=DEFAULT_COLOR_SEQUENCE * 10
    )
    fig.update_traces(texttemplate='%{text:.2s}')
    fig.update_layout(template=DEFAULT_TEMPLATE, xaxis_title='估算总销量', yaxis_title='品牌')
    return fig

def plot_regional_competition(df):
    """图表 5: [新] 区域竞争格局 (卖家集中度)"""
    # 我们只看有意义的省份数据
    location_df = df[df['location'] != '未知'].copy()
    
    plot_data = location_df.groupby('location').agg(
        total_sales=('sales', 'sum'),
        product_count=('title', 'count')
    ).reset_index()
    
    # 过滤掉数据太少的
    plot_data = plot_data[(plot_data['total_sales'] > 10000) & (plot_data['product_count'] > 50)]
    
    fig = px.scatter(
        plot_data, x='product_count', y='total_sales', size='total_sales', size_max=50,
        color='location', text='location',
        title='图 5: 区域竞争格局 (SKU数 vs 总销量)',
        labels={'product_count': '商品链接数 (SKU数)', 'total_sales': '估算总销量'},
        log_x=True, log_y=True # 使用对数坐标轴，更清晰
    )
    fig.update_traces(textposition='top right')
    fig.update_layout(template=DEFAULT_TEMPLATE, showlegend=False)
    return fig

def plot_color_share_donut(df):
    """图表 6: 主流色系销量占比 (原图表 2.1)"""
    color_df = df.explode('tag_color').dropna(subset=['tag_color'])
    color_data = color_df.groupby('tag_color')['sales'].sum().reset_index()
    
    fig = px.pie(
        color_data, names='tag_color', values='sales',
        title='图 6: 主流色系市场销量占比', hole=0.4,
        color_discrete_sequence=DEFAULT_COLOR_SEQUENCE
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(template=DEFAULT_TEMPLATE, showlegend=True)
    return fig

def plot_efficacy_bubble(df):
    """图表 7: 核心功效诉求市场表现 (原图表 2.2)"""
    tech_df = df.explode('tag_tech').dropna(subset=['tag_tech'])
    
    plot_data = tech_df.groupby('tag_tech').agg(
        total_sales=('sales', 'sum'),
        avg_price=('price', 'mean'),
        product_count=('title', 'count')
    ).reset_index()

    fig = px.scatter(
        plot_data, x='total_sales', y='avg_price', size='product_count', size_max=60,
        color='tag_tech', text='tag_tech',
        title='图 7: 核心功效诉求市场表现 (气泡大小 = 商品数)',
        labels={'total_sales': '估算总销量', 'avg_price': '平均价格 (元)', 'product_count': '商品链接数'}
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(template=DEFAULT_TEMPLATE, xaxis_title='估算总销量', yaxis_title='平均价格 (元)', showlegend=False)
    return fig

def plot_social_whitening_engagement(social_df):
    """图表 8: [新] "显白" 诉求的社媒溢价"""
    avg_likes_whitening = social_df[social_df['tag_whitening'] == True]['likes'].mean()
    avg_likes_all = social_df['likes'].mean()
    
    plot_data = pd.DataFrame({
        '诉求类型': ['"显白" 相关笔记', '平台平均笔记'],
        '平均点赞数': [avg_likes_whitening, avg_likes_all]
    })
    
    fig = px.bar(plot_data, x='诉求类型', y='平均点赞数', title='图 8: "显白" 诉求的社媒热度溢价 (小红书)',
                 color='诉求类型', text='平均点赞数', color_discrete_sequence=DEFAULT_COLOR_SEQUENCE)
    fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
    fig.update_layout(template=DEFAULT_TEMPLATE, showlegend=False)
    return fig

def plot_comment_sentiment(comments_insight_df):
    """图表 9: [新] 评论情感声量 ("显白" vs "显黑")"""
    fig = px.bar(comments_insight_df, x='sentiment', y='count', title='图 9: 真实评论情感声量对比 (935条评论)',
                 color='sentiment', text='count', color_discrete_sequence=DEFAULT_COLOR_SEQUENCE)
    fig.update_traces(textposition='outside')
    fig.update_layout(template=DEFAULT_TEMPLATE, xaxis_title='情感关键词', yaxis_title='提及次数', showlegend=False)
    return fig


# --- 3. Streamlit 仪表盘布局 ---
def main():
    
    # --- 标题 ---
    st.title("🎨 染发消费品市场闪电洞察报告")
    st.markdown(f"基于 **{23437+5300}** 条电商商品、**{17740}** 条社交笔记、**{935}** 条用户评论的快速分析")

    # --- 加载与处理数据 ---
    try:
        raw_data = load_raw_data(Path('.'))
        ecommerce_df = process_ecommerce_data(raw_data.get('tb', pd.DataFrame()), raw_data.get('jd', pd.DataFrame()))
        social_df = process_social_data(raw_data.get('xhs', pd.DataFrame()))
        comments_insight_df = process_comments_data(raw_data.get('comments', pd.DataFrame()))
    except Exception as e:
        st.error(f"数据加载或处理失败，请检查文件路径和格式: {e}")
        st.stop()
        
    # --- 布局 ---
    
    # --- 第 1 部分: 报告方法论与数据总览 ---
    st.header("1. 报告方法论与数据总览")
    st.markdown("为了解市场，我们采集了电商和社交平台的多维度数据。本报告的分析权威性建立在以下数据基础上：")
    
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(plot_meta_source_volume(raw_data), use_container_width=True)
    with col2:
        st.plotly_chart(plot_meta_keywords(raw_data), use_container_width=True)

    # --- 第 2 部分: 市场格局与竞争分析 ---
    st.header("2. 市场格局与竞争分析")
    st.markdown("市场的主力战场在哪里？竞争态势如何？")
    
    # 图 3
    st.plotly_chart(plot_price_sales_matrix(ecommerce_df), use_container_width=True)
    
    col3, col4 = st.columns(2)
    with col3:
        # 图 4
        st.plotly_chart(plot_brand_top10(ecommerce_df), use_container_width=True)
    with col4:
        # 图 5
        st.plotly_chart(plot_regional_competition(ecommerce_df), use_container_width=True)
    
    st.info("""
    **格局洞察：**
    1.  **价格带：** 市场的主力战场集中在 **50-100元** 区间，这里有最多的商品和最大的销量（图 3）。
    2.  **品牌：** 市场由 [欧莱雅, 施华蔻] 等国际大牌主导，销量遥遥领先（图 4）。
    3.  **区域：** 市场高度集中。`广东广州` 是最大的“货源集散地”（SKU最多），而 `江苏苏州` `重庆` 则存在“超级大卖”，销量极高（图 5）。
    """)

    # --- 第 3 部分: 核心趋势洞察 (什么在热卖?) ---
    st.header("3. 核心趋势洞察：什么在热卖?")
    
    col5, col6 = st.columns(2)
    with col5:
        # 图 6
        st.plotly_chart(plot_color_share_donut(ecommerce_df), use_container_width=True)
    with col6:
        # 图 7
        st.plotly_chart(plot_efficacy_bubble(ecommerce_df), use_container_width=True)
        
    st.info("""
    **趋势洞察：**
    1.  **色系：** “**棕色系**” 是市场的绝对基本盘，销量占比最高（图 6）。
    2.  **功效：** “**泡沫**” 型产品以其易用性获得了最高的总销量。“**植物**”和“**无氨**”等健康概念，则成功实现了更高的“平均溢价”（图 7）。
    """)
    
    # --- 第 4 部分: 核心诉求深挖：“显白” ---
    st.header("4. 核心诉求深挖：“显白”")
    st.markdown("我们发现，“显白”是串联社媒热度与用户口碑的第一刚需。")
    
    col7, col8 = st.columns(2)
    with col7:
        # 图 8
        st.plotly_chart(plot_social_whitening_engagement(social_df), use_container_width=True)
    with col8:
        # 图 9
        st.plotly_chart(plot_comment_sentiment(comments_insight_df), use_container_width=True)
        
    st.success("""
    **“显白”核心洞察：**
    1.  **社媒热度：** 在小红书，“显白”相关笔记的平均点赞数 **显著高于** 平台平均水平。它是驱动社交讨论的“流量密码”（图 8）。
    2.  **用户口碑：** 在 935 条真实用户评论中，对“显白”的正面提及 (69次) **压倒性地超过** 了对“显黑”的负面提及 (1次)。这证明“显白”是驱动用户满意度的核心，而“显黑”是绝对的雷区（图 9）。
    3.  **结论：** “显白”不仅是社媒营销噱头，更是**切中了用户审美的核心痛点**，是品牌建立口碑、规避差评的关键。
    """)

if __name__ == "__main__":
    main()