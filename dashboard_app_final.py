import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import pandas as pd
from streamlit_mermaid import st_mermaid
import data_processor_final as data_processor # 导入我们最终的数据处理器
import logging
import math # 导入数学库用于布局
import numpy as np # 导入 numpy 用于布局
import networkx as nx # 【【【 新增：用于生成力导向知识图谱 】】】
from itertools import combinations # 【【【 新增：用于计算边的权重 】】】
from collections import Counter

# --- 0. 页面配置与样式加载 ---
st.set_page_config(
    page_title="染发消费品深度洞察 (V-Final-4)",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 视觉优化
PLOT_TEMPLATE = "plotly_white"
PLOT_COLOR = "rgb(70, 130, 180)" # 主色: SteelBlue (钢蓝色)
PLOT_COLOR_SEQUENCE = px.colors.sequential.Blues # 渐变: V1的"蓝色渐变"
GRAY_COLOR = 'rgb(200, 200, 200)' # 辅色: 浅灰

def load_css(file_name):
    try:
        with open(file_name, encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("style.css 文件未找到。将使用默认样式。")

def create_insight_box(text):
    st.markdown(f"<div class='custom-insight-box'>{text}</div>", unsafe_allow_html=True)

# --- 1. 图表绘制模块 (Plotters) ---

# --- 1A. 方法论图表 (无改动) ---
def plot_methodology_flow():
    """图 1: 分析方法论 (Mermaid 流程图)"""
    mermaid_code = """
    graph TD
        A(1. 关键词策略<br/>全品类关键词库) --> B(2. 多源数据采集<br/>淘宝/京东/小红书/微博/评论);
        B --> C{3. P-Tag 引擎<br/>数据清洗与标签化};
        C --> D[4. 市场格局分析<br/>价格/品牌/区域];
        C --> E[5. 产品矩阵分析<br/>色系/功效/产品类型];
        C --> F[6. 社媒声量验证<br/>平台/热点/溢价];
        C --> G[7. 核心诉求深挖<br/>语义共现/知识图谱];
        C --> H[8. 用户口碑验证<br/>评论情感];
        D & E & F & G & H --> I((<b>最终洞察报告</b>));

        classDef default fill:#fff,stroke:#ddd,stroke-width:1px,font-size:14px;
        class C fill:#0068c9,color:#fff,font-weight:bold,stroke-width:0px;
        class I fill:#1a1a1a,color:#fff,font-weight:bold,stroke-width:0px;
    """
    try:
        st_mermaid(mermaid_code, height="550px")
    except Exception as e:
        st.error(f"Mermaid 流程图渲染失败: {e}")
        st.code(mermaid_code, language="mermaid")

def plot_meta_data_funnel(raw_counts):
    """图 2: 数据采集漏斗 (KPI指标卡)"""
    st.subheader("图 2: 数据采集漏斗")
    cols = st.columns(5)
    cols[0].metric("电商商品 (SKU)", f"{raw_counts['淘宝商品'] + raw_counts['京东商品']:,}")
    cols[1].metric("社媒帖子 (Posts)", f"{raw_counts['小红书笔记'] + raw_counts['微博帖子']:,}")
    cols[2].metric("用户评论 (UGC)", f"{raw_counts['淘宝评论']:,}")
    cols[3].metric("电商关键词 (Query)", f"{raw_counts['电商关键词']:,}")
    cols[4].metric("社交关键词 (Query)", f"{raw_counts['社交关键词']:,}")

def plot_meta_source_volume(raw_data_counts):
    """图 3: 本次分析数据源总览 (柱状图)"""
    st.subheader("图 3: 本次分析数据源总览")
    data = {
        '平台': ['淘宝商品', '京东商品', '小红书笔记', '微博帖子', '淘宝评论'],
        '数据量': [
            raw_data_counts.get('淘宝商品', 0), 
            raw_data_counts.get('京东商品', 0), 
            raw_data_counts.get('小红书笔记', 0), 
            raw_data_counts.get('微博帖子', 0), 
            raw_data_counts.get('淘宝评论', 0)
        ]
    }
    df = pd.DataFrame(data)
    df = df[df['数据量'] > 0].sort_values('数据量', ascending=False)
    
    fig = px.bar(df, x='平台', y='数据量', 
                 text='数据量', color='平台', 
                 color_discrete_sequence=px.colors.sequential.Blues_r[::2])
    fig.update_layout(template=PLOT_TEMPLATE, showlegend=False)
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

def plot_keyword_analysis_treemap(keyword_strategy):
    """图 4: 核心搜索词词频 (Treemap)"""
    st.subheader("图 4: 核心搜索词词频 (Top 10)")
    
    ecom_df = keyword_strategy['电商关键词 (Top 10)'].copy()
    ecom_df['type'] = '电商搜索'
    
    social_df = keyword_strategy['社交关键词 (Top 10)'].copy()
    social_df['type'] = '社交搜索'
    
    df = pd.concat([ecom_df, social_df])
    
    fig = px.treemap(df, path=[px.Constant("全平台"), 'type', 'keyword'], 
                     values='count', color='count',
                     color_continuous_scale='Blues')
    fig.update_traces(textinfo="label+value+percent root")
    fig.update_layout(template=PLOT_TEMPLATE, margin=dict(t=50, l=0, r=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

# --- 1B. 市场格局图表 (无改动) ---
def plot_price_sales_matrix(df):
    """图 5: 市场价格区间分布"""
    st.subheader("图 5: 市场价格区间分布 (气泡大小 = 总销量)")
    bins = [0, 50, 100, 150, 200, 300, 1000]
    labels = ["0-50元", "50-100元", "100-150元", "150-200元", "200-300元", "300+元"]
    df['price_bin'] = pd.cut(df['price'], bins=bins, labels=labels, right=False)
    
    plot_data = df.groupby('price_bin', observed=True).agg(
        total_sales=('sales', 'sum'),
        product_count=('title', 'count')
    ).reset_index()
    
    fig = px.scatter(
        plot_data, x='price_bin', y='product_count', size='total_sales', size_max=70,
        color='price_bin', color_discrete_sequence=PLOT_COLOR_SEQUENCE,
        labels={'price_bin': '价格区间', 'product_count': '商品链接数 (SKU数)', 'total_sales': '估算总销量'}
    )
    fig.update_layout(template=PLOT_TEMPLATE, yaxis_title='商品链接数 (SKU数)', legend_title_text='价格区间')
    st.plotly_chart(fig, use_container_width=True)

def plot_brand_top10(df):
    """图 6: 热销品牌 Top 10 (柱状图)"""
    st.subheader("图 6: 电商热销品牌 TOP 10 (按估算销量)")
    brand_df = df.explode('tag_brand').dropna(subset=['tag_brand'])
    brand_df = brand_df[brand_df['tag_brand'] != 'Other'] 
    brand_data = brand_df.groupby('tag_brand')['sales'].sum().nlargest(10).sort_values(ascending=True)
    
    fig = px.bar(
        brand_data, x='sales', y=brand_data.index, orientation='h',
        text='sales', color_discrete_sequence=[PLOT_COLOR] * 10
    )
    fig.update_traces(texttemplate='%{text:.2s}')
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title='估算总销量', yaxis_title=None, 
                      yaxis_automargin=True)
    st.plotly_chart(fig, use_container_width=True)

def plot_brand_treemap(df):
    """图 7: 热销品牌矩阵 (Treemap)"""
    st.subheader("图 7: 电商热销品牌矩阵 (按估算销量)")
    brand_df = df.explode('tag_brand').dropna(subset=['tag_brand'])
    brand_df = brand_df[brand_df['tag_brand'] != 'Other']
    brand_data = brand_df.groupby('tag_brand')['sales'].sum().nlargest(15).reset_index()
    
    fig = px.treemap(brand_data, path=[px.Constant("所有品牌"), 'tag_brand'], 
                     values='sales', color='sales',
                     color_continuous_scale='Blues')
    fig.update_traces(textinfo="label+value+percent root")
    fig.update_layout(template=PLOT_TEMPLATE, margin=dict(t=50, l=0, r=0, b=0))
    st.plotly_chart(fig, use_container_width=True)


def plot_regional_competition(df):
    """图 8: 区域竞争格局"""
    st.subheader("图 8: 区域竞争格局 (SKU数 vs 总销量)")
    location_df = df[(df['location'] != '未知') & (df['location'] != '海外') & (df['location'] != 'nan')].copy()
    
    plot_data = location_df.groupby('location').agg(
        total_sales=('sales', 'sum'),
        product_count=('title', 'count')
    ).reset_index()
    
    plot_data = plot_data[(plot_data['total_sales'] > 100000) & (plot_data['product_count'] > 50)]
    
    fig = px.scatter(
        plot_data, x='product_count', y='total_sales', size='total_sales', size_max=50,
        color='location', text='location',
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={'product_count': '商品链接数 (SKU数)', 'total_sales': '估算总销量'},
        log_x=True, log_y=True
    )
    fig.update_traces(textposition='top center', textfont_size=10) 
    fig.update_layout(template=PLOT_TEMPLATE, showlegend=False, xaxis_title="SKU数 (货源地)", yaxis_title="总销量 (市场)")
    st.plotly_chart(fig, use_container_width=True)

def plot_color_price_heatmap(df):
    """图 9: 色系-价格交叉热力图"""
    st.subheader("图 9: 色系-价格交叉热力图 (销量)")
    if 'price_bin' not in df.columns:
        bins = [0, 50, 100, 150, 200, 300, 1000] 
        labels = ["0-50元", "50-100元", "100-150元", "150-200元", "200-300元", "300+元"]
        df['price_bin'] = pd.cut(df['price'], bins=bins, labels=labels, right=False)
    
    color_df = df.explode('tag_color').dropna(subset=['tag_color'])
    color_df = color_df[color_df['tag_color'] != '未明确色系']
    
    heatmap_data = color_df.groupby(['tag_color', 'price_bin'], observed=True)['sales'].sum().reset_index()
    heatmap_pivot = heatmap_data.pivot_table(index='tag_color', columns='price_bin', values='sales', fill_value=0)
    
    fig = px.imshow(
        heatmap_pivot, text_auto='.2s', aspect="auto",
        color_continuous_scale='Blues',
        labels={'x': '价格区间', 'y': '色系', 'color': '估算总销量'}
    )
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title="价格区间", yaxis_title="色系", 
                      yaxis_automargin=True)
    st.plotly_chart(fig, use_container_width=True)

# --- 1C. 产品深度拆解 (无改动) ---
def plot_color_share_donut(df):
    """图 10: 主流色系市场销量占比"""
    st.subheader("图 10: 主流色系市场销量占比")
    color_df = df.explode('tag_color').dropna(subset=['tag_color'])
    color_df = color_df[color_df['tag_color'] != '未明确色系'] 
    color_data = color_df.groupby('tag_color')['sales'].sum().reset_index()
    
    fig = px.pie(
        color_data, names='tag_color', values='sales',
        hole=0.4, color_discrete_sequence=PLOT_COLOR_SEQUENCE
    )
    fig.update_traces(textinfo='percent+label', pull=[0.05 if i == 0 else 0 for i in range(len(color_data))])
    fig.update_layout(template=PLOT_TEMPLATE, legend_title_text='色系')
    st.plotly_chart(fig, use_container_width=True)

def plot_product_archetype_matrix(df):
    """图 11: 产品类型定位矩阵 (V2)"""
    st.subheader("图 11: 产品类型定位矩阵 (气泡大小 = SKU数)")
    plot_data = df[df['archetype'] != '其他'].groupby('archetype').agg(
        total_sales=('sales', 'sum'),
        avg_price=('price', 'mean'),
        product_count=('title', 'count')
    ).reset_index()

    fig = px.scatter(
        plot_data, x='total_sales', y='avg_price', size='product_count', size_max=60,
        color='archetype', text='archetype',
        color_discrete_sequence=PLOT_COLOR_SEQUENCE,
        labels={'total_sales': '估算总销量', 'avg_price': '平均价格 (元)', 'archetype': '产品类型'}
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title='市场规模 (总销量)', yaxis_title='价格定位 (均价)', 
                      legend_title_text='产品类型')
    st.plotly_chart(fig, use_container_width=True)

def plot_efficacy_bubble(df):
    """图 12: 核心功效诉求市场表现 (V1)"""
    st.subheader("图 12: 核心功效诉求市场表现 (气泡大小 = SKU数)")
    tech_df = df.explode('tag_tech').dropna(subset=['tag_tech'])
    tech_df = tech_df[tech_df['tag_tech'] != '基础款']
    
    plot_data = tech_df.groupby('tag_tech').agg(
        total_sales=('sales', 'sum'),
        avg_price=('price', 'mean'),
        product_count=('title', 'count')
    ).reset_index()

    fig = px.scatter(
        plot_data, x='total_sales', y='avg_price', size='product_count', size_max=60,
        color='tag_tech', text='tag_tech',
        color_discrete_sequence=PLOT_COLOR_SEQUENCE,
        labels={'total_sales': '估算总销量', 'avg_price': '平均价格 (元)', 'product_count': '商品链接数'}
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title='估算总销量', yaxis_title='平均价格 (元)', 
                      legend_title_text='功效标签')
    st.plotly_chart(fig, use_container_width=True)

# --- 1D. 社媒声量验证 (无改动) ---
def get_filtered_social_df(df, platform_choice):
    """辅助函数：获取过滤后的社交DF"""
    if platform_choice == 'XHS':
        return df[df['platform'] == 'XHS'].copy()
    elif platform_choice == 'Weibo':
        return df[df['platform'] == 'Weibo'].copy()
    else:
        return df.copy()

def plot_social_hot_topics(df):
    """图 13: 社媒热点话题声量 (总提及数)"""
    st.subheader(f"图 13: 社媒热点话题声量 (按总提及次数)")
    
    tech_counts = df.explode('tag_tech')['tag_tech'].value_counts()
    tech_counts = tech_counts.drop('基础款', errors='ignore')
    
    color_counts = df.explode('tag_color')['tag_color'].value_counts()
    color_counts = color_counts.drop('未明确色系', errors='ignore')
    
    topic_df = pd.concat([
        tech_counts.nlargest(5).reset_index().rename(columns={'index': 'topic', 'tag_tech': 'topic', 'count': 'mentions'}),
        color_counts.nlargest(5).reset_index().rename(columns={'index': 'topic', 'tag_color': 'topic', 'count': 'mentions'})
    ])
    topic_df = topic_df.sort_values('mentions', ascending=False)
    
    fig = px.treemap(topic_df, path=[px.Constant("所有话题"), 'topic'], 
                     values='mentions', color='mentions',
                     color_continuous_scale='Blues')
    fig.update_traces(textinfo="label+value+percent root")
    fig.update_layout(template=PLOT_TEMPLATE, margin=dict(t=50, l=0, r=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

def plot_social_brand_buzz_bar(df):
    """图 14: 社交热门品牌 (条形图)"""
    st.subheader(f"图 14: 社交热门品牌 Top 10 (按总点赞数)")
    brand_df = df.explode('tag_brand').dropna(subset=['tag_brand'])
    brand_df = brand_df[brand_df['tag_brand'] != 'Other']
    brand_data = brand_df.groupby('tag_brand')['likes'].sum().nlargest(10).sort_values(ascending=True)
    
    fig = px.bar(
        brand_data, x='likes', y=brand_data.index, orientation='h',
        text='likes', color_discrete_sequence=[PLOT_COLOR] * 10
    )
    fig.update_traces(texttemplate='%{text:.2s}')
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title='总点赞数', yaxis_title=None, 
                      yaxis_automargin=True)
    st.plotly_chart(fig, use_container_width=True)

def plot_social_topic_engagement(avg_likes_df):
    """图 15: 社媒热点话题平均点赞（热度）"""
    st.subheader(f"图 15: 社媒热点话题平均点赞 (热度)")
    
    # 筛选出有意义的话题
    whitening_topic = avg_likes_df[avg_likes_df['topic'] == '显白']
    
    all_tech_topics = list(data_processor.DEFINITIONS["TECH"].keys())
    top_tech = avg_likes_df[avg_likes_df['topic'].isin(all_tech_topics)].nlargest(5, 'avg_likes')
    
    all_color_topics = list(data_processor.DEFINITIONS["COLOR"].keys())
    top_color = avg_likes_df[avg_likes_df['topic'].isin(all_color_topics)].nlargest(5, 'avg_likes')
    
    plot_df = pd.concat([whitening_topic, top_tech, top_color]).drop_duplicates(subset=['topic'])
    plot_df = plot_df.sort_values('avg_likes', ascending=True)
    
    plot_df['color'] = plot_df['topic'].apply(lambda x: PLOT_COLOR if x == '显白' else GRAY_COLOR)
    
    fig = px.bar(
        plot_df, x='avg_likes', y='topic', orientation='h',
        text='avg_likes', color='color',
        color_discrete_map={PLOT_COLOR: PLOT_COLOR, GRAY_COLOR: GRAY_COLOR},
        labels={'topic': '话题', 'avg_likes': '平均点赞数'}
    )
    fig.update_traces(texttemplate='%{text:.0f}')
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title='平均点赞数', yaxis_title=None, 
                      yaxis_automargin=True, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# --- 1E. 核心洞察: "WHAT IS 显白?" ---

@st.cache_data(show_spinner=False)
def get_network_graph_data(social_df, ecom_df, co_occurrence_data):
    """
    【【【 新增：知识图谱数据处理函数 】】】
    为 "显白" 话题构建一个二级网络图数据
    """
    logging.info("开始构建二级知识图谱...")
    
    # 1. 定义核心节点 (Top 5 色系, Top 5 品牌, Top 5 功效)
    top_colors = [tag for tag, count in co_occurrence_data['color'].most_common(5)]
    top_brands = [tag for tag, count in co_occurrence_data['brand'].most_common(5)]
    top_techs = [tag for tag, count in co_occurrence_data['tech'].most_common(5)]
    
    # 颜色映射
    color_map = {}
    for tag in top_colors: color_map[tag] = (data_processor.DEFINITIONS["COLOR"].get(tag, []), "色系", "#0068c9")
    for tag in top_brands: color_map[tag] = (data_processor.DEFINITIONS["BRAND"].get(tag, []), "品牌", "#42a5f5")
    for tag in top_techs: color_map[tag] = (data_processor.DEFINITIONS["TECH"].get(tag, []), "功效", "#90caf9")
    
    core_nodes = set(top_colors + top_brands + top_techs)
    
    # 2. 筛选出所有“显白”的帖子
    all_df = pd.concat([
        ecom_df[['tag_brand', 'tag_color', 'tag_tech', 'tag_whitening']],
        social_df[['tag_brand', 'tag_color', 'tag_tech', 'tag_whitening']]
    ])
    whitening_df = all_df[all_df['tag_whitening'] == True]

    # 3. 计算节点大小 (总提及次数)
    node_sizes = Counter()
    
    # 4. 计算边的权重 (二级共现)
    edge_weights = Counter()
    
    for _, row in whitening_df.iterrows():
        tags_in_row = set()
        for tag in row['tag_color']:
            if tag in core_nodes: tags_in_row.add(tag)
        for tag in row['tag_brand']:
            if tag in core_nodes: tags_in_row.add(tag)
        for tag in row['tag_tech']:
            if tag in core_nodes: tags_in_row.add(tag)
        
        for tag in tags_in_row:
            node_sizes[tag] += 1
        
        # 计算所有组合的边
        for u, v in combinations(sorted(list(tags_in_row)), 2):
            edge_weights[(u, v)] += 1
            
    # 5. 准备 NetworkX 数据
    G = nx.Graph()
    
    # 添加节点
    for tag, size in node_sizes.items():
        if tag in color_map:
            G.add_node(tag, size=size, type=color_map[tag][1], color=color_map[tag][2])
            
    # 添加边
    for (u, v), weight in edge_weights.items():
        if u in G.nodes and v in G.nodes and weight > 1: # 过滤掉太弱的连接
            G.add_edge(u, v, weight=weight)
            
    # 6. 计算布局
    # k 是节点间的理想距离，iterations 是迭代次数
    # 增加 k 和 iterations 可以让图更松散，减少重叠
    pos = nx.spring_layout(G, k=0.8, iterations=50, seed=42)
    
    return G, pos

def plot_whitening_network_graph(G, pos):
    """
    【【【 全新：力导向网络图 】】】
    图 16: "显白" 核心话题网络图 (NetworkX + Plotly)
    """
    st.subheader("图 16: “显白” 核心话题网络图 (二级关联)")
    
    # 1. 准备边的轨迹
    edge_x, edge_y, edge_weights_norm = [], [], []
    max_weight = max((d['weight'] for u, v, d in G.edges(data=True)), default=1)
    
    for u, v, data in G.edges(data=True):
        edge_x.extend([pos[u][0], pos[v][0], None])
        edge_y.extend([pos[u][1], pos[v][1], None])
        # 归一化线宽
        edge_weights_norm.append((data['weight'] / max_weight) * 10 + 0.5)

    # 创建多个 edge trace (Plotly Bug: 无法在一个trace中指定不同线宽)
    edge_traces = []
    i = 0
    for u, v, data in G.edges(data=True):
        edge_traces.append(go.Scatter(
            x=[pos[u][0], pos[v][0]],
            y=[pos[u][1], pos[v][1]],
            mode='lines',
            line=dict(width=edge_weights_norm[i], color=GRAY_COLOR),
            hoverinfo='text',
            text=f"共现: {data['weight']}"
        ))
        i += 1
        
    # 2. 准备节点轨迹
    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    max_size = max((d['size'] for n, d in G.nodes(data=True)), default=1)
    
    for node, data in G.nodes(data=True):
        node_x.append(pos[node][0])
        node_y.append(pos[node][1])
        node_color.append(data['color'])
        # 归一化节点大小
        node_size.append((data['size'] / max_size) * 50 + 10)
        node_text.append(f"{node}<br>类型: {data['type']}<br>提及: {data['size']}")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(width=2, color='#333')
        ),
        hoverinfo='text'
    )
    
    # 3. 绘图
    fig = go.Figure(data=edge_traces + [node_trace],
                 layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20, l=20, r=20, t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    template=PLOT_TEMPLATE,
                    height=700 # 给予更多空间
                    ))
    st.plotly_chart(fig, use_container_width=True)


def plot_whitening_co_occurrence_bars(co_occurrence_data):
    """图 17: "显白" 的具体构成 (三小图)"""
    st.subheader("图 17: “显白” 的语义构成 (一级关联, Top 5)")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        data = co_occurrence_data['color']
        if data:
            df = pd.DataFrame(data.most_common(5), columns=['tag', 'count'])
            fig = px.bar(df, x='count', y='tag', orientation='h', title="“显白”色系",
                         color_discrete_sequence=[PLOT_COLOR])
            fig.update_layout(template=PLOT_TEMPLATE, yaxis_title=None, xaxis_title="共现次数", yaxis={'categoryorder':'total ascending'}, yaxis_automargin=True)
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        data = co_occurrence_data['brand']
        if data:
            df = pd.DataFrame(data.most_common(5), columns=['tag', 'count'])
            fig = px.bar(df, x='count', y='tag', orientation='h', title="“显白”品牌",
                         color_discrete_sequence=[PLOT_COLOR])
            fig.update_layout(template=PLOT_TEMPLATE, yaxis_title=None, xaxis_title="共现次数", yaxis={'categoryorder':'total ascending'}, yaxis_automargin=True)
            st.plotly_chart(fig, use_container_width=True)
    with col3:
        data = co_occurrence_data['tech']
        if data:
            df = pd.DataFrame(data.most_common(5), columns=['tag', 'count']) 
            fig = px.bar(df, x='count', y='tag', orientation='h', title="“显白”功效",
                         color_discrete_sequence=[PLOT_COLOR])
            fig.update_layout(template=PLOT_TEMPLATE, yaxis_title=None, xaxis_title="共现次数", yaxis={'categoryorder':'total ascending'}, yaxis_automargin=True)
            st.plotly_chart(fig, use_container_width=True)

def plot_whitening_co_matrix(co_occurrence_data):
    """图 18: "显白" 色系x功效 共现热力图"""
    st.subheader("图 18: “显白” 色系 x 功效 共现热力图")
    matrix = co_occurrence_data.get('co_matrix')
    
    if matrix is None or matrix.empty:
        st.warning("共现矩阵数据不足。")
        return
        
    fig = px.imshow(
        matrix, text_auto=True, aspect="auto",
        color_continuous_scale='Blues',
        labels={'x': '功效标签', 'y': '色系标签', 'color': '共现次数'}
    )
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title="功效标签", yaxis_title="色系标签", 
                      yaxis_automargin=True)
    st.plotly_chart(fig, use_container_width=True)

# --- 1F. 口碑验证 (无改动) ---
def plot_comment_sentiment(comments_insight):
    """图 19: 真实评论情感声量"""
    st.subheader("图 19: 真实评论情感声量 (935条评论)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("总评论数", f"{comments_insight['total_comments']} 条")
    col2.metric("正面口碑 (“显白”)", f"{comments_insight['whitening_mentions']} 次", delta="正面")
    col3.metric("负面口碑 (“显黑”)", f"{comments_insight['blackening_mentions']} 次", delta="负面 (绝对雷区)", delta_color="normal")
    
    ratio = comments_insight['whitening_mentions'] / max(1, comments_insight['blackening_mentions'])
    create_insight_box(
        f"<b>口碑红线洞察:</b> 在用户的真实反馈中, “显白” (正面) 的提及次数是 “显黑” (负面) 的 **{ratio:.0f} 倍**。这证明“显黑”是用户绝对的雷区和核心负面口碑来源。"
    )

# --- 3. Streamlit 仪表盘主应用 ---
def main():
    
    # --- 0. 加载数据与CSS ---
    load_css("style.css")
    try:
        data_pack = data_processor.load_and_process_data(Path('.'))
    except Exception as e:
        st.error(f"致命错误：数据加载或处理失败。请检查 JSON 文件路径和格式，或 data_processor_final.py 脚本。错误: {e}")
        st.exception(e)
        st.stop()
        
    ecom_df = data_pack['ecom']
    social_df_all = data_pack['social']
    social_avg_likes_all = data_pack['social_avg_likes']

    # --- 1. 标题与执行摘要 ---
    st.title("🎨 染发消费品市场深度洞察报告 (V-Final-4)")
    st.markdown("---")
    
    st.header("1. 执行摘要 (Executive Summary)")
    create_insight_box(
        f"""
        本报告基于对 **{data_pack['raw_counts_kpi']['淘宝商品'] + data_pack['raw_counts_kpi']['京东商品']:,}** 条电商商品和 **{data_pack['raw_counts_kpi']['小红书笔记'] + data_pack['raw_counts_kpi']['微博帖子']:,}** 条社媒帖子的深度分析，核心结论如下：
        <br/><br/>
        1.  <b>市场基本盘:</b> `50-100元` 价位段的 `棕色系`、`便捷型(泡沫)` 产品是满足大众需求的绝对主力。
        2.  <b>竞争与区域:</b> `欧莱雅` 与 `施华蔻` 在电商销量上遥遥领先。市场呈“产销分离”，`广东` 是最大货源地，而 `江苏`、`重庆` 存在“超级卖场”。
        3.  <b>产品机会点:</b> `健康型(植物/无氨)` 成功占据了“高均价”心智，是品牌溢价升级的方向。
        4.  <b>社媒声量王:</b> `小红书` 是染发话题的绝对中心。`爱茉莉(美妆仙)` 是社媒声量冠军，远超其电商表现，是“社媒种草”的标杆。
        5.  <b>核心洞察 (WHAT IS 显白?):</b> “显白”是第一刚需。知识图谱 (图 16) 和热力图 (图 18) 共同揭示了“显白”的**核心二级关联**：`泡沫`、`棕色系` 和 `爱茉莉` 是“显白”话题网络中最紧密的三个节点。
        6.  <b>口碑红线:</b> “显黑”是绝对雷区。在935条评论中，“显白”被提及 {data_pack['comments_insight']['whitening_mentions']} 次，“显黑”仅 {data_pack['comments_insight']['blackening_mentions']} 次。
        """
    )
    
    st.markdown("---")

    # --- 2. 分析方法论 ---
    st.header("2. 分析方法论与数据策略")
    st.markdown("我们的洞察基于一套严谨的“关键词-爬取-标签化-分析”流程，将海量非结构化数据转化为商业洞察。")
    
    col1, col2 = st.columns([1, 1.3])
    with col1:
        st.subheader("图 1: 洞察分析流程")
        plot_methodology_flow() # 图 1
    with col2:
        plot_meta_data_funnel(data_pack['raw_counts_kpi']) # 图 2 (KPI卡)
        plot_meta_source_volume(data_pack['raw_counts']) # 图 3 (V2柱状图)
        
    plot_keyword_analysis_treemap(data_pack['keyword_strategy']) # 图 4 (Treemap)
    
    st.markdown("---")

    # --- 3. 市场宏观格局：钱在哪里？ ---
    st.header("3. 市场宏观格局：钱在哪里？")
    st.markdown("我们首先分析电商大盘，回答三个核心问题：什么价位卖得好？ 谁在卖？ 货从哪里来？")
    
    plot_price_sales_matrix(ecom_df) # 图 5
    
    col3, col4 = st.columns(2)
    with col3:
        plot_brand_top10(ecom_df) # 图 6 (柱状图)
    with col4:
        plot_brand_treemap(ecom_df) # 图 7 (Treemap)
    
    plot_regional_competition(ecom_df) # 图 8
    plot_color_price_heatmap(ecom_df) # 图 9
    
    create_insight_box(
        """
        <b>格局洞察:</b>
        1.  <b>价格带 (图 5):</b> `50-100元` 是竞争最激烈的红海，SKU数和总销量均是第一。`150-200元` 价位段是溢价机会点。
        2.  <b>品牌 (图 6 & 7):</b> 两种图表均验证 `欧莱雅` 与 `施华蔻` 构成第一梯队，销量断层领先。
        3.  <b>区域 (图 8):</b> 市场呈“产销分离”。`广东` 是最大的“货源集散地”（SKU最多），而 `江苏`、`重庆` 则是“超级卖场”（SKU不多，但总销量极高）。
        4.  <b>色系-价格 (图 9):</b> `棕色系` 在 `50-100元` 价位段销量最高。而 `亚麻/青色系` 和 `灰色/蓝色系` 等“潮色”，其销售高峰出现在 `100-150元` 以上的价位。
        """
    )
    
    st.markdown("---")
    
    # --- 4. 产品深度拆解：什么在热卖？ ---
    st.header("4. 产品深度拆解：什么在热卖？")
    st.markdown("在主流价位下，具体是哪些产品形态在驱动市场？ 我们将产品归纳为五大类型进行矩阵分析。")

    col5, col6 = st.columns([1.2, 1])
    with col5:
        plot_product_archetype_matrix(ecom_df) # 图 11
    with col6:
        plot_color_share_donut(ecom_df) # 图 10
    
    plot_efficacy_bubble(ecom_df) # 图 12
        
    create_insight_box(
        """
        <b>产品洞察:</b>
        1.  <b>色系 (图 10):</b> `棕色系` 是市场的绝对基本盘，占据近半销量，是大众消费者的“安全牌”。
        2.  <b>产品类型 (图 11):</b>
            * <b>跑量冠军 (右下):</b> `便捷型(泡沫)` 拥有最高的市场规模（总销量），但价格偏低。
            * <b>溢价蓝海 (左上):</b> `健康型(植物/无氨)` 销量不高，但成功占据了“高均价”心智，是品牌升级方向。
            * <b>时尚先锋 (中间):</b> `时尚型(潮色)` 处在中间地带，是连接大众与溢价的关键。
        3.  <b>功效 (图 12):</b> “泡沫”型产品销量最高。“植物”和“无氨”等健康概念，则成功实现了更高的“平均溢价”。
        """
    )

    st.markdown("---")

    # --- 5. 社媒声量验证：人们在谈论什么？ ---
    st.header("5. 社媒声量验证：人们在谈论什么？")
    
    platform_choice = st.radio(
        "选择分析平台：",
        ('全部', 'XHS', 'Weibo'),
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # 根据选择过滤DF
    social_df = get_filtered_social_df(social_df_all, platform_choice)
    
    # 动态过滤 avg_likes_df (如果平台不是"全部"，则重算)
    if platform_choice == '全部':
        social_avg_likes = social_avg_likes_all
        st.markdown(f"**当前平台: {platform_choice}** (共 {len(social_df):,} 条帖子)")
    else:
        # 【【【 修复：重算平均点赞 】】】
        # (这是一个简化的重算，以保证过滤有效)
        avg_likes_data_filtered = data_processor.get_avg_likes_by_topic(social_df) # 假设 data_processor 有这个函数
        social_avg_likes = pd.DataFrame(avg_likes_data_filtered).sort_values('avg_likes', ascending=False)
        st.markdown(f"**当前平台: {platform_choice}** (共 {len(social_df):,} 条帖子)")

    
    col7, col8 = st.columns(2)
    with col7:
        plot_social_hot_topics(social_df) # 图 13
    with col8:
        plot_social_brand_buzz_bar(social_df) # 图 14
        
    plot_social_topic_engagement(social_avg_likes) # 图 15
    
    create_insight_box(
        """
        <b>社媒洞察:</b>
        1.  <b>热点话题 (图 13):</b> 在社媒端，`泡沫`、`免漂` 等便捷性功效，以及 `棕色系`、`亚麻/青色系` 等热门色系是讨论的绝对主流。
        2.  <b>品牌 (图 14):</b> 社媒声量与电商销量 **不完全匹配**。`爱茉莉`（美妆仙）在社媒的声量极高，是“社媒爆款”品牌。
        3.  <b>热度 (图 15):</b> “显白”是社媒流量密码。其平均点赞数显著高于其他所有具体功效或色系话题，是驱动社交爆款的核心引擎。
        """
    )
    
    st.markdown("---")

    # --- 6. 核心洞察（The 'Why'）：“显白”是第一刚需 ---
    st.header("6. 核心深挖：到底什么才是“显白”？")
    st.markdown("我们对所有提及“显白”的数据进行了语义共现分析，构建了如下的二级关联知识图谱。")

    # 【【【 核心修改：在这里计算并传入图谱数据 】】】
    G, pos = get_network_graph_data(social_df_all, ecom_df, data_pack['co_occurrence'])
    plot_whitening_network_graph(G, pos) # 图 16 (全新力导向图)
    
    col9, col10 = st.columns(2)
    with col9:
        plot_whitening_co_occurrence_bars(data_pack['co_occurrence']) # 图 17 (三小图)
    with col10:
        plot_whitening_co_matrix(data_pack['co_occurrence']) # 图 18 (热力图)
    
    create_insight_box(
        """
        <b>“显白” 构成洞察 (图 16, 17, 18):</b>
        * <b>图 17 (一级关联):</b> “显白”与 `棕色系`、`爱茉莉`、`泡沫` 关联最强。
        * <b>图 16 (二级关联 - 知识图谱):</b> **这才是核心！** 节点图展示了这些热门标签**彼此之间**的联系。我们能清晰看到一个由 `泡沫`、`棕色系`、`爱茉莉` 构成的**强关联“铁三角”**。
        * <b>图 18 (二级关联 - 热力图):</b> 热力图量化了图16的发现，`泡沫` + `棕色系` 的共现次数遥遥领先。**结论：** 消费者要的“显白”是一个“解决方案”，即“**爱茉莉的棕色系泡沫染发剂**”。
        """
    )
    
    st.markdown("---")

    # --- 7. 最终验证与结论 ---
    st.header("7. 最终验证：用户口碑与结论")
    
    plot_comment_sentiment(data_pack['comments_insight']) # 图 19
    
    st.subheader("B. 当前局限与未来方向")
    create_insight_box(
        """
        本次“闪电报告”数据量充足，但仍有局限性，未来可从以下方向完善：
        1.  <b>评论数据量不足:</b> 935 条评论只能做定性洞察。未来需扩大评论爬取量至 10万+ 级别，以构建更精准的“肤色-发色”推荐模型。
        2.  <b>微博数据价值低:</b> (可切换平台查看) 微博数据多为营销和新闻，用户UGC价值远低于小红书，未来应将爬取重心<b>彻底转向小红书</b>。
        3.  <b>缺失京东评论:</b> 本次只分析了淘宝评论，未能获取京东的 `评价人数` 对应的真实评论，缺失了京东侧的口碑验证。
        """
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # 在 data_processor_final.py 中添加一个函数用于重算 avg_likes
    # 为简化演示，这里假设 main() 可以访问 data_processor 内部
    
    def get_avg_likes_by_topic(social_df):
        topic_likes = defaultdict(lambda: {'total_likes': 0, 'count': 0})
        defs = data_processor.DEFINITIONS
        
        whitening_likes = social_df[social_df['tag_whitening'] == True]['likes']
        topic_likes['显白'] = {'total_likes': whitening_likes.sum(), 'count': len(whitening_likes)}
        
        tech_df = social_df.explode('tag_tech')
        for tag in defs["TECH"].keys():
            likes = tech_df[tech_df['tag_tech'] == tag]['likes']
            topic_likes[tag]['total_likes'] += likes.sum()
            topic_likes[tag]['count'] += len(likes)
            
        color_df = social_df.explode('tag_color')
        for tag in defs["COLOR"].keys():
            likes = color_df[color_df['tag_color'] == tag]['likes']
            topic_likes[tag]['total_likes'] += likes.sum()
            topic_likes[tag]['count'] += len(likes)

        avg_likes_data = []
        for topic, data in topic_likes.items():
            if data['count'] > 0:
                avg_likes = data['total_likes'] / data['count']
                avg_likes_data.append({'topic': topic, 'avg_likes': avg_likes, 'count': data['count']})
        return avg_likes_data

    # 将函数注入 data_processor 模块，以便 main() 可以调用
    data_processor.get_avg_likes_by_topic = get_avg_likes_by_topic
    
    main()