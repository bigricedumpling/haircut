import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import pandas as pd
from streamlit_mermaid import st_mermaid
import data_processor_final as data_processor # V7: 导入修复后的处理器
import logging
import math 
import numpy as np 
import networkx as nx 
from itertools import combinations 
from collections import Counter, defaultdict 

# --- 0. V7.5 页面配置与美学定义 ---
st.set_page_config(
    page_title="染发消费品深度洞察",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- V7.5: 全局美学常量 (低饱和度、温和、纸质感) ---
PLOT_TEMPLATE = "plotly_white"
PLOT_COLOR = "#B85C40" # 主色: 檀棕/赤陶色 (来自 CSS)

PLOT_CONTINUOUS_SCALE_MAIN = px.colors.sequential.OrRd # 主渐变 (暖色)
CUSTOM_HEATMAP_SCALE = ['#F8F5F0', '#EAE0D1', '#DDCAB2', '#CFAE93', '#B88D6F', '#A07655', '#8C5A4A']

PLOT_CONTINUOUS_SCALE_HEALTH = px.colors.sequential.YlGn # 功效渐变 (健康绿)

PLOT_DISCRETE_SEQUENCE_R = px.colors.sequential.OrRd_r

GRAY_COLOR = 'rgb(200, 200, 200)' # 辅色: 浅灰
GRID_COLOR = 'rgba(180, 180, 180, 0.3)' # V5: 虚线网格颜色 

# 知识图谱节点配色 (V5 低饱和度)
NODE_COLORS = {
    "色系": "#B85C5C", # 赤红
    "品牌": "#B85C40", # 檀棕 (主色)
    "功效": "#E08A6F"  # 橘
}

# V7.5: 全局字体定义 
FONT_FAMILY = "方正国美进道体"
FONT_COLOR = "#333333"
FONT_TITLE = 18
FONT_AXIS_TITLE = 14
FONT_TICK = 12

# --- V7.5: CSS 加载与辅助函数 ---
def load_css(file_name):
    """加载 style.css 文件"""
    try:
        with open(file_name, encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"错误: 'style.css' 文件未找到。请确保 'style.css' 以及你的字体/纹理文件都在同一目录。")

def create_insight_box(text):
    """(V5 布局修复) 创建洞察框并增加额外间距"""
    text_cleaned = text.replace("“", "<b>").replace("”", "</b>").replace("‘", "<b>").replace("’", "</b>")
    st.markdown(f"<div class='custom-insight-box'>{text_cleaned}</div>", unsafe_allow_html=True)
    st.write("") 

# 【【【 V7.5 修复#移除 title_font，这是导致 'undefined' 的根源 】】】
GLOBAL_FONT_LAYOUT = dict(
    font=dict(family=FONT_FAMILY, size=FONT_TICK, color=FONT_COLOR),
    # title_font=... <-- 导致 "undefined" 的错误行已被删除
    xaxis=dict(
        title_font=dict(family=FONT_FAMILY, size=FONT_AXIS_TITLE, color=FONT_COLOR),
        tickfont=dict(family=FONT_FAMILY, size=FONT_TICK, color=FONT_COLOR)
    ),
    yaxis=dict(
        title_font=dict(family=FONT_FAMILY, size=FONT_AXIS_TITLE, color=FONT_COLOR),
        tickfont=dict(family=FONT_FAMILY, size=FONT_TICK, color=FONT_COLOR)
    ),
    legend=dict(
        title_font=dict(family=FONT_FAMILY, size=FONT_TICK, color=FONT_COLOR),
        font=dict(family=FONT_FAMILY, size=FONT_TICK, color=FONT_COLOR)
    )
)

def add_light_gridlines(fig):
    """为图表添加统一的浅色虚线网格和透明背景"""
    fig.update_layout(
        xaxis_showgrid=True, yaxis_showgrid=True,
        xaxis_gridcolor=GRID_COLOR, yaxis_gridcolor=GRID_COLOR,
        xaxis_gridwidth=0.5, yaxis_gridwidth=0.5,
        xaxis_griddash='dash', yaxis_griddash='dash',
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)'  
    )
    # V7.5 字体修复#应用全局字体
    fig.update_layout(GLOBAL_FONT_LAYOUT)
    return fig

# --- 1. 图表绘制模块 (Plotters) ---
# --- 1A. 方法论图表 (V7.5 Mermaid 语法修复) ---
def plot_methodology_flow():
    """图 1: 分析方法论 (V7.5 修复)"""
    
    # 【【【 Gemini 最终修复 3: 规避 v10.2.4 解析器 Bug 】】】
    # 错误日志 "Parse error on line 2: ...rgb(...),fill-o..." 证明
    # Mermaid v10.2.4 的解析器在 classDef 中无法处理以 rgb() 函数开头的样式。
    # 它在第一个逗号处即告失败。
    # 解决方案:
    # 1. 必须使用逗号 (,) 分隔。
    # 2. 必须将 classDef 放在顶部。
    # 3. (关键) 必须将 rgb(255,255,255) 替换为解析器能理解的简单 Hex 值: #ffffff
    
    mermaid_code = """
    graph TD
        %% 1. 样式定义
        classDef default fill:#ffffff,fill-opacity:0.8,stroke:#ddd,stroke-width:0.5px,font-size:14px;
        class C fill:#A03000,color:#fff,font-weight:bold,stroke-width:0px; 
        class I fill:#1a1a1a,color:#fff,font-weight:bold,stroke-width:0px;
        
        %% 2. 图表内容
        subgraph " "
            A(1. 关键词策略<br/>全品类关键词库) --> B(2. 多源数据采集<br/>淘宝/京东/小红书/微博/评论);
            B --> C{3. P-Tag 引擎<br/>数据清洗与标签化};
            C --> D[4. 市场格局分析<br/>价格/品牌/区域];
            C --> E[5. 产品矩阵分析<br/>色系/功效/产品类型];
            C --> F[6. 社媒声量验证<br/>平台/热点/溢价];
            C --> G[7. 核心诉求深挖<br/>语义共现/知识图谱];
            C --> H[8. 用户口碑验证<br/>评论情感];
            
            D & E & F & G & H --> I((最终洞察报告));
        end
    """
    try:
        st_mermaid(mermaid_code, height="550px") 
    except Exception as e:
        st.error(f"Mermaid 流程图渲染失败 (V7.5 尝试): {e}。")
        st.code(mermaid_code, language="mermaid")

def plot_meta_data_funnel(raw_counts):
    """图 2: 数据采集漏斗 (KPI指标卡)"""
    st.subheader("图 2: 数据采集漏斗")
    cols = st.columns(5)
    cols[0].metric("电商商品 (SKU)", f"{raw_counts.get('淘宝商品', 0) + raw_counts.get('京东商品', 0):,}")
    cols[1].metric("社媒帖子 (Posts)", f"{raw_counts.get('小红书笔记', 0) + raw_counts.get('微博帖子', 0):,}")
    cols[2].metric("用户评论 (UGC)", f"{raw_counts.get('淘宝评论', 0):,}")
    cols[3].metric("电商关键词 (Query)", f"{raw_counts.get('电商关键词', 0):,}")
    cols[4].metric("社交关键词 (Query)", f"{raw_counts.get('社交关键词', 0):,}")
    st.write("") 

def plot_meta_source_volume(raw_data_counts):
    """图 3: 本次分析数据源总览"""
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
                 color_discrete_sequence=PLOT_DISCRETE_SEQUENCE_R[::2]) 
    fig.update_layout(template=PLOT_TEMPLATE, showlegend=False)
    fig.update_traces(textposition='outside')
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)

def plot_keyword_analysis_treemap(keyword_strategy):
    """图 4: 核心搜索词词频"""
    st.subheader("图 4: 核心搜索词词频 (Top 10)")
    
    ecom_df = keyword_strategy['电商关键词 (Top 10)'].copy()
    ecom_df['type'] = '电商搜索'
    
    social_df = keyword_strategy['社交关键词 (Top 10)'].copy()
    social_df['type'] = '社交搜索'
    
    df = pd.concat([ecom_df, social_df])
    
    fig = px.treemap(df, path=[px.Constant("全平台"), 'type', 'keyword'], 
                     values='count', color='count',
                     color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN) 
    fig.update_traces(textinfo="label+value+percent root")
    fig.update_layout(template=PLOT_TEMPLATE, margin=dict(t=50, l=0, r=0, b=0),
                      paper_bgcolor='rgba(0,0,0,0)', 
                      plot_bgcolor='rgba(0,0,0,0)')
    fig.update_layout(GLOBAL_FONT_LAYOUT) # 字体
    st.plotly_chart(fig, use_container_width=True)

# --- 1B. 市场格局图表 ---
def plot_price_sales_matrix(df):
    """图 5: 市场价格区间分布"""
    st.subheader("图 5: 市场价格区间分布 (气泡大小 = 总销量)")
    bins = [0, 50, 100, 150, 200, 300, 1000]
    labels = ["0-50元", "50-100元", "100-150元", "150-200元", "200-300元", "300+元"]
    
    df_copy = df.copy()
    df_copy['price_bin'] = pd.cut(df_copy['price'], bins=bins, labels=labels, right=False)
    
    plot_data = df_copy.groupby('price_bin', observed=True).agg(
        total_sales=('sales', 'sum'),
        product_count=('title', 'count')
    ).reset_index()
    
    fig = px.scatter(
        plot_data, x='price_bin', y='product_count', size='total_sales', size_max=70,
        color='price_bin', 
        color_discrete_sequence=px.colors.sequential.OrRd, 
        labels={'price_bin': '价格区间', 'product_count': '商品链接数 (SKU数)', 'total_sales': '估算总销量'}
    )
    fig.update_layout(template=PLOT_TEMPLATE, yaxis_title='商品链接数 (SKU数)', legend_title_text='价格区间')
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)
    
    return df_copy


def plot_brand_top10(df):
    """图 6: 热销品牌 Top 10"""
    st.subheader("图 6: 电商热销品牌 TOP 10 (按估算销量)")
    brand_df = df.explode('tag_brand').dropna(subset=['tag_brand'])
    brand_df = brand_df[brand_df['tag_brand'] != 'Other'] 
    brand_data = brand_df.groupby('tag_brand')['sales'].sum().nlargest(10).sort_values(ascending=False)
    
    fig = px.bar(
        brand_data, x=brand_data.index, y='sales', 
        text='sales', 
        color='sales', 
        color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN
    )
    fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    fig.update_layout(template=PLOT_TEMPLATE, yaxis_title='估算总销量', xaxis_title=None, 
                      xaxis_automargin=True, coloraxis_showscale=False)
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)

def plot_brand_treemap(df):
    """图 7: 热销品牌矩阵"""
    st.subheader("图 7: 电商热销品牌矩阵 (按估算销量)")
    brand_df = df.explode('tag_brand').dropna(subset=['tag_brand'])
    brand_df = brand_df[brand_df['tag_brand'] != 'Other']
    brand_data = brand_df.groupby('tag_brand')['sales'].sum().nlargest(15).reset_index()
    
    fig = px.treemap(brand_data, path=[px.Constant("所有品牌"), 'tag_brand'], 
                     values='sales', color='sales',
                     color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN) 
    fig.update_traces(textinfo="label+value+percent root")
    fig.update_layout(template=PLOT_TEMPLATE, margin=dict(t=50, l=0, r=0, b=0),
                      paper_bgcolor='rgba(0,0,0,0)', 
                      plot_bgcolor='rgba(0,0,0,0)')
    fig.update_layout(GLOBAL_FONT_LAYOUT) # 字体
    st.plotly_chart(fig, use_container_width=True)


def plot_regional_competition(df):
    """图 8: 区域竞争格局 (V7 美学修复)"""
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
        color_discrete_sequence=px.colors.qualitative.Antique, #替换色卡
        labels={'product_count': '商品链接数 (SKU数)', 'total_sales': '估算总销量'},
        log_x=True, log_y=True
    )
    #缩小字体防重叠
    fig.update_traces(textposition='top center', textfont_size=10) 
    fig.update_layout(template=PLOT_TEMPLATE, showlegend=False, xaxis_title="SKU数 (货源地)", yaxis_title="总销量 (市场)")
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)

def plot_color_price_heatmap(df):
    """图 9: 色系-价格交叉热力图 (V7 美学修复)"""
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
        heatmap_pivot, text_auto=True, aspect="auto",
        color_continuous_scale=CUSTOM_HEATMAP_SCALE, #使用自定义色卡
        labels={'x': '价格区间', 'y': '色系', 'color': '估算总销量'}
    )
    fig.update_traces(textfont_size=10) 
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title="价格区间", yaxis_title="色系", 
                      yaxis_automargin=True,
                      paper_bgcolor='rgba(0,0,0,0)', 
                      plot_bgcolor='rgba(0,0,0,0)')
    fig.update_layout(GLOBAL_FONT_LAYOUT) # 字体
    st.plotly_chart(fig, use_container_width=True)

# --- 1C. 产品深度拆解 ---
def plot_color_share_donut(df, defs):
    """图 10: 主流色系市场销量占比"""
    st.subheader("图 10: 主流色系市场销量占比")
    color_df = df.explode('tag_color').dropna(subset=['tag_color'])
    color_df = color_df[color_df['tag_color'] != '未明确色系'] 
    color_data = color_df.groupby('tag_color')['sales'].sum().reset_index()
    
    color_map = defs["CATEGORY_HEX"]["COLOR"] # V7: 使用新色卡
    
    fig = px.pie(
        color_data, names='tag_color', values='sales',
        hole=0.4, 
        color='tag_color', 
        color_discrete_map=color_map 
    )
    fig.update_traces(textinfo='percent+label', textfont_size=13, pull=[0.05 if i == 0 else 0 for i in range(len(color_data))])
    fig.update_layout(template=PLOT_TEMPLATE, legend_title_text='色系',
                      paper_bgcolor='rgba(0,0,0,0)', 
                      plot_bgcolor='rgba(0,0,0,0)')
    fig.update_layout(GLOBAL_FONT_LAYOUT) # 字体
    st.plotly_chart(fig, use_container_width=True)

def plot_color_swatch_analysis(swatch_df):
    """图 11: “中国色彩”色卡电商表现 (V7 美学修复)"""
    st.subheader("图 11: “中国色彩”色卡电商表现 (按销量)")
    
    plot_df = swatch_df.sort_values('total_sales', ascending=True)
    
    color_map = {row['tag_swatch']: row['hex'] for index, row in plot_df.iterrows() if pd.notna(row['hex'])}
    
    fig = px.bar(
        plot_df, x='total_sales', y='tag_swatch', orientation='h',
        text='total_sales', color='tag_swatch',
        color_discrete_map=color_map, 
        pattern_shape="tag_swatch", 
        pattern_shape_map={s: "/" for s in plot_df['tag_swatch']} 
    )
    fig.update_traces(texttemplate='%{text:.2s}')
    #加粗柱状图
    fig.update_traces(width=0.8)
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title='估算总销量', yaxis_title=None, 
                      yaxis_automargin=True, showlegend=False)
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)


def plot_product_archetype_matrix(df, defs):
    """图 12: 产品类型定位矩阵 (V7 美学修复)"""
    st.subheader("图 12: 产品类型定位矩阵 (气泡大小 = SKU数)")
    plot_data = df[df['archetype'] != '其他'].groupby('archetype').agg(
        total_sales=('sales', 'sum'),
        avg_price=('price', 'mean'),
        product_count=('title', 'count')
    ).reset_index()

    color_map = defs["CATEGORY_HEX"]["ARCHETYPE"] # V7: 使用新色卡

    fig = px.scatter(
        plot_data, x='total_sales', y='avg_price', size='product_count', size_max=70, 
        color='archetype', text='archetype',
        color_discrete_map=color_map, 
        labels={'total_sales': '估算总销量', 'avg_price': '平均价格 (元)', 'archetype': '产品类型'}
    )
    fig.update_traces(
        textposition='top center',
        marker=dict(
            line=dict(width=0.5, color='rgba(255, 255, 255, 0.5)'),
            gradient_type='radial'
        )
    )
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title='市场规模 (总销量)', yaxis_title='价格定位 (均价)', 
                      legend_title_text='产品类型')
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)

def plot_efficacy_bubble(df):
    """图 13: 核心功效诉求市场表现 (V6 美学修复)"""
    st.subheader("图 13: 核心功效诉求市场表现 (气泡大小 = SKU数)")
    tech_df = df.explode('tag_tech').dropna(subset=['tag_tech'])
    tech_df = tech_df[tech_df['tag_tech'] != '基础款']
    
    plot_data = tech_df.groupby('tag_tech').agg(
        total_sales=('sales', 'sum'),
        avg_price=('price', 'mean'),
        product_count=('title', 'count')
    ).reset_index()

    fig = px.scatter(
        plot_data, x='total_sales', y='avg_price', size='product_count', size_max=70, 
        color='avg_price', 
        text='tag_tech',
        color_continuous_scale=PLOT_CONTINUOUS_SCALE_HEALTH, 
        labels={'total_sales': '估算总销量', 'avg_price': '平均价格 (元)', 'product_count': '商品链接数'}
    )
    fig.update_traces(
        textposition='top center',
        marker=dict(
            line=dict(width=0.5, color='rgba(255, 255, 255, 0.5)'),
            gradient_type='radial'
        )
    )
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title='估算总销量', yaxis_title='平均价格 (元)', 
                      legend_title_text='功效标签', coloraxis_showscale=True, 
                      coloraxis_colorbar_title='均价')
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)

# --- 1D. 社媒声量验证 (V7 BUG 修复) ---
def get_filtered_social_df(df, platform_choice):
    """辅助函数#获取过滤后的社交DF"""
    if platform_choice == 'XHS':
        return df[df['platform'] == 'XHS'].copy()
    elif platform_choice == 'Weibo':
        return df[df['platform'] == 'Weibo'].copy()
    else:
        return df.copy()

def plot_social_hot_topics(df):
    """图 14: 社媒热点话题声量 (V7 BUG 修复)"""
    st.subheader(f"图 14: 社媒热点话题声量 (按总提及次数)")
    
    try:
        tech_counts = df.explode('tag_tech')['tag_tech'].value_counts()
        tech_counts = tech_counts.drop('基础款', errors='ignore')
        
        color_counts = df.explode('tag_color')['tag_color'].value_counts()
        color_counts = color_counts.drop('未明确色系', errors='ignore')
        
        # V7 BUG 修复# 'tag_tech'/'tag_color' 是 value_counts() 后 index 的 name
        tech_df = tech_counts.nlargest(5).reset_index().rename(columns={'tag_tech': 'topic', 'count': 'mentions'})
        color_df = color_counts.nlargest(5).reset_index().rename(columns={'tag_color': 'topic', 'count': 'mentions'})
        
        topic_df = pd.concat([tech_df, color_df]).sort_values('mentions', ascending=False)
        
        if topic_df.empty:
            st.warning("社媒话题数据不足，无法生成图 14。")
            return
            
        fig = px.treemap(topic_df, path=[px.Constant("所有话题"), 'topic'], 
                         values='mentions', color='mentions',
                         color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN) 
        fig.update_traces(textinfo="label+value+percent root")
        fig.update_layout(template=PLOT_TEMPLATE, margin=dict(t=50, l=0, r=0, b=0),
                          paper_bgcolor='rgba(0,0,0,0)', 
                          plot_bgcolor='rgba(0,0,0,0)')
        fig.update_layout(GLOBAL_FONT_LAYOUT) # 字体
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"渲染图 14 (社媒热点) 失败: {e}")
        logging.error(f"Fig 14 Error: {e}")


def plot_social_brand_buzz_bar(df):
    """图 15: 社交热门品牌"""
    st.subheader(f"图 15: 社交热门品牌 Top 10 (按总点赞数)")
    brand_df = df.explode('tag_brand').dropna(subset=['tag_brand'])
    brand_df = brand_df[brand_df['tag_brand'] != 'Other']
    brand_data = brand_df.groupby('tag_brand')['likes'].sum().nlargest(10).sort_values(ascending=False)
    
    fig = px.bar(
        brand_data, x=brand_data.index, y='likes', 
        text='likes', 
        color='likes', 
        color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN
    )
    fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    fig.update_layout(template=PLOT_TEMPLATE, yaxis_title='总点赞数', xaxis_title=None, 
                      xaxis_automargin=True, coloraxis_showscale=False)
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)

def plot_social_topic_engagement(avg_likes_df, defs):
    """图 16: 社媒热点话题平均点赞"""
    st.subheader(f"图 16: 社媒热点话题平均点赞 (热度)")
    
    if avg_likes_df.empty:
        st.warning("当前平台无足够数据进行热度分析。")
        return

    whitening_topic = avg_likes_df[avg_likes_df['topic'] == '显白']
    qise_topic = avg_likes_df[avg_likes_df['topic'] == '显气色'] 
    
    aesthetics_topics = list(defs.get("AESTHETICS", {}).keys())
    aesthetics_topic = avg_likes_df[avg_likes_df['topic'].isin(aesthetics_topics)]
    
    all_tech_topics = list(defs["TECH"].keys())
    top_tech = avg_likes_df[avg_likes_df['topic'].isin(all_tech_topics)].nlargest(3, 'avg_likes')
    
    all_color_topics = list(defs["COLOR"].keys())
    top_color = avg_likes_df[avg_likes_df['topic'].isin(all_color_topics)].nlargest(3, 'avg_likes')
    
    plot_df = pd.concat([whitening_topic, qise_topic, aesthetics_topic, top_tech, top_color]).drop_duplicates(subset=['topic'])
    plot_df = plot_df.sort_values('avg_likes', ascending=True)
    
    highlight_topics = ['显白', '显气色'] + aesthetics_topics
    plot_df['color'] = plot_df['topic'].apply(
        lambda x: PLOT_COLOR if x in highlight_topics else GRAY_COLOR
    )
    
    fig = px.bar(
        plot_df, x='avg_likes', y='topic', orientation='h',
        text='avg_likes', color='color',
        color_discrete_map={PLOT_COLOR: PLOT_COLOR, GRAY_COLOR: GRAY_COLOR},
        labels={'topic': '话题', 'avg_likes': '平均点赞数'}
    )
    fig.update_traces(texttemplate='%{text:.0f}')
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title='平均点赞数', yaxis_title=None, 
                      yaxis_automargin=True, showlegend=False)
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)

# --- 1E. 核心洞察: "WHAT IS 显白?" ---
@st.cache_data(show_spinner="构建知识图谱中...", max_entries=10)
def get_network_graph_data(social_df, ecom_df, co_occurrence_data, defs, analysis_target="whitening"):
    """
    (V7) 为 "显白" 或 "显气色" 话题构建一个二级网络图数据
    """
    logging.info(f"V7: 开始构建'{analysis_target}'二级知识图谱...")
    
    # 检查 co_occurrence_data 是否为空
    if not co_occurrence_data or not co_occurrence_data.get('color'):
        logging.warning(f"'{analysis_target}' 的 co_occurrence_data 为空，无法构建图谱。")
        return nx.Graph(), {} # 返回空图
        
    top_colors = [tag for tag, count in co_occurrence_data['color'].most_common(5)]
    top_brands = [tag for tag, count in co_occurrence_data['brand'].most_common(5)]
    top_techs = [tag for tag, count in co_occurrence_data['tech'].most_common(5)]
    
    color_map = {}
    for tag in top_colors: color_map[tag] = (defs["COLOR"].get(tag, []), "色系", NODE_COLORS["色系"])
    for tag in top_brands: color_map[tag] = (defs["BRAND"].get(tag, []), "品牌", NODE_COLORS["品牌"])
    for tag in top_techs: color_map[tag] = (defs["TECH"].get(tag, []), "功效", NODE_COLORS["功效"])
    
    core_nodes = set(top_colors + top_brands + top_techs)
    
    all_df = pd.concat([
        ecom_df[['tag_brand', 'tag_color', 'tag_tech', 'tag_whitening', 'tag_qise']],
        social_df[['tag_brand', 'tag_color', 'tag_tech', 'tag_whitening', 'tag_qise']]
    ])
    
    if analysis_target == "whitening":
        target_df = all_df[all_df['tag_whitening'] == True]
    elif analysis_target == "qise":
        target_df = all_df[all_df['tag_qise'] == True]
    else:
        target_df = pd.DataFrame() 

    if target_df.empty:
        logging.warning(f"'{analysis_target}' 的 target_df 为空。")
        return nx.Graph(), {} # 返回空图

    node_sizes = Counter()
    edge_weights = Counter()
    
    for _, row in target_df.iterrows():
        tags_in_row = set()
        # V7 修复检查: row['tag_color'] 是 list, tag 是 str
        for tag in row['tag_color']: 
            if tag in core_nodes: tags_in_row.add(tag)
        for tag in row['tag_brand']: 
            if tag in core_nodes: tags_in_row.add(tag)
        for tag in row['tag_tech']: 
            if tag in core_nodes: tags_in_row.add(tag)
        
        for tag in tags_in_row:
            node_sizes[tag] += 1
        
        for u, v in combinations(sorted(list(tags_in_row)), 2):
            edge_weights[(u, v)] += 1
            
    G = nx.Graph()
    for tag, size in node_sizes.items():
        if tag in color_map:
            G.add_node(tag, size=size, type=color_map[tag][1], color=color_map[tag][2])
            
    for (u, v), weight in edge_weights.items():
        if u in G.nodes and v in G.nodes and weight > 1: 
            G.add_edge(u, v, weight=weight)
            
    if len(G.nodes) == 0:
        logging.warning(f"'{analysis_target}' 图谱节点为空。")
        return G, {} 
        
    pos = nx.spring_layout(G, k=0.8, iterations=50, seed=42)
    
    logging.info(f"'{analysis_target}' 图谱构建完成。")
    return G, pos

def plot_whitening_network_graph(G, pos):
    """
    图 17: "显白" 核心话题网络图 (V6 美学修复)
    """
    st.subheader("图 17: “显白” 核心话题网络图 (二级关联)")
    
    if len(G.nodes) == 0:
        st.warning("“显白”知识图谱数据不足，无法生成。 (可能原因#数据中未提及“显白”)")
        return

    edge_traces = []
    max_weight_edges = [d['weight'] for u, v, d in G.edges(data=True)]
    max_weight = max(max_weight_edges) if max_weight_edges else 1
    
    for u, v, data in G.edges(data=True):
        edge_width = (data['weight'] / max_weight) * 8 + 0.5 
        edge_traces.append(go.Scatter(
            x=[pos[u][0], pos[v][0]],
            y=[pos[u][1], pos[v][1]],
            mode='lines',
            line=dict(width=edge_width, color=GRID_COLOR), 
            hoverinfo='text',
            text=f"共现: {data['weight']}"
        ))
        
    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    max_size_nodes = [d['size'] for n, d in G.nodes(data=True)]
    max_size = max(max_size_nodes) if max_size_nodes else 1
    
    for node, data in G.nodes(data=True):
        node_x.append(pos[node][0])
        node_y.append(pos[node][1])
        node_color.append(data['color']) 
        node_size.append((data['size'] / max_size) * 50 + 10)
        node_text.append(f"{node}<br>类型: {data['type']}<br>提及: {data['size']}")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=[f"<b>{node}</b>" for node in G.nodes()], 
        textposition="top center",
        textfont=dict(
            size=12,
            color=FONT_COLOR, # V7 字体
            family=FONT_FAMILY # V7 字体
        ),
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(width=0.5, color='rgba(255, 255, 255, 0.5)'), # 白色描边
            gradient_type='radial' # 恢复渐变
        ),
        hoverinfo='text',
        hovertext=node_text 
    )
    
    fig = go.Figure(data=edge_traces + [node_trace],
                 layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20, l=20, r=20, t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    template=PLOT_TEMPLATE,
                    height=700,
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)'
                    ))
    fig.update_layout(GLOBAL_FONT_LAYOUT) # 字体
    st.plotly_chart(fig, use_container_width=True)


def plot_whitening_co_occurrence_bars(co_occurrence_data):
    """图 18: "显白" 的具体构成 (V7.5 修复)"""
    st.subheader("图 18: “显白” 的语义构成 (一级关联, Top 5)")
    st.write("") 
    col1, col2, col3 = st.columns(3)
    
    title_font_size = 16 

    with col1:
        data = co_occurrence_data.get('color')
        if data:
            df = pd.DataFrame(data.most_common(5), columns=['tag', 'count'])
            fig = px.bar(df, x='count', y='tag', orientation='h', title="“显白”色系",
                         color='count', 
                         color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN) 
            fig.update_layout(template=PLOT_TEMPLATE, 
                              # 【【【 V7.5 修复#手动加回标题字体 】】】
                              title_font_size=title_font_size, title_font_family=FONT_FAMILY,
                              yaxis_title=None, xaxis_title="共现次数", 
                              yaxis={'categoryorder':'total ascending'}, yaxis_automargin=True,
                              coloraxis_showscale=False)
            fig = add_light_gridlines(fig) 
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        data = co_occurrence_data.get('brand')
        if data:
            df = pd.DataFrame(data.most_common(5), columns=['tag', 'count'])
            fig = px.bar(df, x='count', y='tag', orientation='h', title="“显白”品牌", 
                         color='count', 
                         color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN) 
            fig.update_layout(template=PLOT_TEMPLATE, 
                              # 【【【 V7.5 修复#手动加回标题字体 】】】
                              title_font_size=title_font_size, title_font_family=FONT_FAMILY,
                              yaxis_title=None, xaxis_title="共现次数", 
                              yaxis={'categoryorder':'total ascending'}, yaxis_automargin=True,
                              coloraxis_showscale=False)
            fig = add_light_gridlines(fig) 
            st.plotly_chart(fig, use_container_width=True)
    with col3:
        data = co_occurrence_data.get('tech')
        if data:
            df = pd.DataFrame(data.most_common(3), columns=['tag', 'count']) 
            fig = px.bar(df, x='count', y='tag', orientation='h', title="“显白”功效", 
                         color='count', 
                         color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN) 
            fig.update_layout(template=PLOT_TEMPLATE, 
                              # 【【【 V7.5 修复#手动加回标题字体 】】】
                              title_font_size=title_font_size, title_font_family=FONT_FAMILY,
                              yaxis_title=None, xaxis_title="共现次数",
                              yaxis={'categoryorder':'total ascending'}, yaxis_automargin=True,
                              coloraxis_showscale=False)
            fig = add_light_gridlines(fig) 
            st.plotly_chart(fig, use_container_width=True)
            
    if not (co_occurrence_data.get('color') or co_occurrence_data.get('brand') or co_occurrence_data.get('tech')):
        st.warning("“显白”一级关联数据不足，无法生成图 18。")

def plot_whitening_co_matrix(co_occurrence_data):
    """图 19: "显白" 色系x功效 共现热力图 (V7 美学修复)"""
    st.subheader("图 19: “显白” 色系 x 功效 共现热力图")
    st.write("") 
    matrix = co_occurrence_data.get('co_matrix')
    
    if matrix is None or matrix.empty:
        st.warning("“显白”共现矩阵数据不足，无法生成图 19。")
        return
        
    fig = px.imshow(
        matrix, text_auto=True, aspect="auto",
        color_continuous_scale=CUSTOM_HEATMAP_SCALE, 
        labels={'x': '功效标签', 'y': '色系标签', 'color': '共现次数'}
    )
    fig.update_traces(textfont_size=10) 
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title="功效标签", yaxis_title="色系标签", 
                      yaxis_automargin=True,
                      paper_bgcolor='rgba(0,0,0,0)', 
                      plot_bgcolor='rgba(0,0,0,0)')
    fig.update_layout(GLOBAL_FONT_LAYOUT) # 字体
    st.plotly_chart(fig, use_container_width=True)


# --- 1F. “显气色” ---
def plot_qise_network_graph(G, pos):
    """
    图 20: "显气色" 核心话题网络图 (V6 美学修复)
    """
    st.subheader("图 20: “显气色” 核心话题网络图 (二级关联)")
    
    if len(G.nodes) == 0:
        st.warning("“显气色”知识图谱数据不足，无法生成。 (可能原因#数据中未提及“显气色”)")
        return

    edge_traces = []
    max_weight_edges = [d['weight'] for u, v, d in G.edges(data=True)]
    max_weight = max(max_weight_edges) if max_weight_edges else 1
    
    for u, v, data in G.edges(data=True):
        edge_width = (data['weight'] / max_weight) * 8 + 0.5 
        edge_traces.append(go.Scatter(
            x=[pos[u][0], pos[v][0]],
            y=[pos[u][1], pos[v][1]],
            mode='lines',
            line=dict(width=edge_width, color=GRID_COLOR), 
            hoverinfo='text',
            text=f"共现: {data['weight']}"
        ))
        
    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    max_size_nodes = [d['size'] for n, d in G.nodes(data=True)]
    max_size = max(max_size_nodes) if max_size_nodes else 1
    
    for node, data in G.nodes(data=True):
        node_x.append(pos[node][0])
        node_y.append(pos[node][1])
        node_color.append(data['color']) 
        node_size.append((data['size'] / max_size) * 50 + 10)
        node_text.append(f"{node}<br>类型: {data['type']}<br>提及: {data['size']}")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=[f"<b>{node}</b>" for node in G.nodes()], 
        textposition="top center",
        textfont=dict(
            size=12,
            color=FONT_COLOR, # V7 字体
            family=FONT_FAMILY # V7 字体
        ),
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(width=0.5, color='rgba(255, 255, 255, 0.5)'), # 白色描边
            gradient_type='radial' # 恢复渐变
        ),
        hoverinfo='text',
        hovertext=node_text 
    )
    
    fig = go.Figure(data=edge_traces + [node_trace],
                 layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20, l=20, r=20, t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    template=PLOT_TEMPLATE,
                    height=700,
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)'
                    ))
    fig.update_layout(GLOBAL_FONT_LAYOUT) # 字体
    st.plotly_chart(fig, use_container_width=True)


def plot_qise_co_occurrence_bars(co_occurrence_data):
    """图 21: "显气色" 的具体构成 (V7.5 修复)"""
    st.subheader("图 21: “显气色” 的语义构成 (一级关联, Top 5)")
    st.write("") 
    col1, col2, col3 = st.columns(3)
    
    title_font_size = 16 

    with col1:
        data = co_occurrence_data.get('color')
        if data:
            df = pd.DataFrame(data.most_common(5), columns=['tag', 'count'])
            fig = px.bar(df, x='count', y='tag', orientation='h', title="“显气色”色系", 
                         color='count', 
                         color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN) 
            fig.update_layout(template=PLOT_TEMPLATE, 
                              # 【【【 V7.5 修复#手动加回标题字体 】】】
                              title_font_size=title_font_size, title_font_family=FONT_FAMILY,
                              yaxis_title=None, xaxis_title="共现次数", 
                              yaxis={'categoryorder':'total ascending'}, yaxis_automargin=True,
                              coloraxis_showscale=False)
            fig = add_light_gridlines(fig)
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        data = co_occurrence_data.get('brand')
        if data:
            df = pd.DataFrame(data.most_common(5), columns=['tag', 'count'])
            fig = px.bar(df, x='count', y='tag', orientation='h', title="“显气色”品牌", 
                         color='count', 
                         color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN) 
            fig.update_layout(template=PLOT_TEMPLATE, 
                              # 【【【 V7.5 修复#手动加回标题字体 】】】
                              title_font_size=title_font_size, title_font_family=FONT_FAMILY,
                              yaxis_title=None, xaxis_title="共现次数", 
                              yaxis={'categoryorder':'total ascending'}, yaxis_automargin=True,
                              coloraxis_showscale=False)
            fig = add_light_gridlines(fig)
            st.plotly_chart(fig, use_container_width=True)
    with col3:
        data = co_occurrence_data.get('tech')
        if data:
            df = pd.DataFrame(data.most_common(3), columns=['tag', 'count']) 
            fig = px.bar(df, x='count', y='tag', orientation='h', title="“显气色”功效", 
                         color='count', 
                         color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN) 
            fig.update_layout(template=PLOT_TEMPLATE, 
                              # 【【【 V7.5 修复#手动加回标题字体 】】】
                              title_font_size=title_font_size, title_font_family=FONT_FAMILY,
                              yaxis_title=None, xaxis_title="共现次数",
                              yaxis={'categoryorder':'total ascending'}, yaxis_automargin=True,
                              coloraxis_showscale=False)
            fig = add_light_gridlines(fig)
            st.plotly_chart(fig, use_container_width=True)
            
    if not (co_occurrence_data.get('color') or co_occurrence_data.get('brand') or co_occurrence_data.get('tech')):
        st.warning("“显气色”一级关联数据不足，无法生成图 21。")

# --- 1G. 口碑验证 ---
def plot_comment_sentiment(comments_insight):
    """图 22: 真实评论情感声量"""
    st.subheader(f"图 22: 真实评论情感声量 (基于 {comments_insight['total_comments']} 条评论)")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总评论数", f"{comments_insight['total_comments']} 条")
    col2.metric("正面口碑 (“显白”)", f"{comments_insight['whitening_mentions']} 次", delta="正面")
    col3.metric("正面口碑 (“显气色”)", f"{comments_insight['qise_mentions']} 次", delta="正面 (新兴)") 
    col4.metric("负面口碑 (“显黑”)", f"{comments_insight['blackening_mentions']} 次", delta="负面 (绝对雷区)", delta_color="normal")
    
    ratio = comments_insight['whitening_mentions'] / max(1, comments_insight['blackening_mentions'])
    
    create_insight_box(
        f"""
        <b>口碑红线洞察:</b> <br/>
        在用户的真实反馈中, “显白”的提及次数是“显黑”的 <b>{ratio:.0f} 倍</b>。这证明“显黑”是用户绝对的雷区和核心负面口碑来源。
        <br/><br/>
        <b>新机会点:</b> <br/>
        值得注意的是，“显气色” ( {comments_insight['qise_mentions']} 次) 作为一个新兴的正面口碑，其提及量已经不容忽视，验证了我们新策略的价值。
        """
    ) 

# --- 3. Streamlit 仪表盘主应用 (V7.5) ---
def main():
    
    # --- 0. V7.5: 加载数据与CSS ---
    load_css("style.css") # 加载 V7 CSS
    try:
        data_pack = data_processor.load_and_process_data(Path('.'))
    except Exception as e:
        st.error(f"致命错误#数据加载或处理失败。请检查 JSON 文件路径和格式，或 data_processor_final.py 脚本。错误: {e}")
        st.exception(e)
        st.stop()
        
    ecom_df = data_pack['ecom']
    social_df_all = data_pack['social']
    social_avg_likes_all = data_pack['social_avg_likes'] 
    defs = data_pack['definitions'] 

    # --- 1. 标题与执行摘要 ---
    st.title("染发消费品市场深度洞察报告")
    # st.markdown("**(V-Final: 美学重构版)**")
    st.markdown("---")
    
    st.header("1. 执行摘要 (Executive Summary)")
    create_insight_box(
        f"""
        本报告基于对 <b>{data_pack['raw_counts_kpi']['淘宝商品'] + data_pack['raw_counts_kpi']['京东商品']:,}</b> 条电商商品和 <b>{data_pack['raw_counts_kpi']['小红书笔记'] + data_pack['raw_counts_kpi']['微博帖子']:,}</b> 条社媒帖子的深度分析，<br/>并融入了“东方美学”与“气色”的新分析维度，核心结论如下#
        <br/><br/>
        1.  <b>市场基本盘:</b> 50-100元价位段的“便捷型(泡沫)”产品是满足大众需求的绝对主力。
        <br/>2.  <b>品牌格局:</b> “欧莱雅”与“施华蔻”在电商销量上遥遥领先。而“爱茉莉(美妆仙)”则是社媒声量冠军，是“社媒种草”的标杆。
        <br/>3.  <b>产品机会点:</b> “健康型(植物/无氨)” 成功占据了“高均价”心智，是品牌溢价升级的方向。
        <br/>4.  <b>色彩新叙事 (图 11):</b> 消费者不再满足于泛泛的“棕色系”。市场正在向更具叙事感的“中国色彩”迭代。其中，“茶棕”、“乌木色”、“赤茶色”是电商销量和社媒声量最高的三个细分色卡。
        <br/>5.  <b>核心诉求升级 (图 16 & 20):</b> “显白”是第一刚需。但我们通过新数据发现，“显气色”正成为一个热度极高的新兴诉求，其社媒平均点赞数甚至超越了“显白”。
        <br/>6.  <b>“显气色”的构成 (图 20 & 21):</b> 知识图谱揭示了“显气色”的解决方案#它与“植物”、“无氨”等健康概念强相关，并且和“棕色系”、“红色/橘色系”的暖色调联系紧密。这说明“显气色”代表了一种更高级、更健康的“红润感”审美。
        <br/>7.  <b>口碑红线:</b> “显黑”是绝对雷区。在 {data_pack['comments_insight']['total_comments']} 条评论中，“显白”被提及 {data_pack['comments_insight']['whitening_mentions']} 次，“显黑”仅 {data_pack['comments_insight']['blackening_mentions']} 次。
        """
    )
    
    st.markdown("---")

    # --- 2. 分析方法论 ---
    st.header("2. 分析方法论与数据策略")
    st.markdown("我们的洞察基于一套严谨的“关键词-爬取-标签化-分析”流程，将海量非结构化数据转化为商业洞察。")
    st.write("") 
    
    col1, col2 = st.columns([1, 1.3])
    with col1:
        st.subheader("图 1: 洞察分析流程")
        plot_methodology_flow() # V7.5 修复
    with col2:
        plot_meta_data_funnel(data_pack['raw_counts_kpi']) 
        plot_meta_source_volume(data_pack['raw_counts']) 
        
    plot_keyword_analysis_treemap(data_pack['keyword_strategy']) 
    
    st.markdown("---")

    # --- 3. 市场宏观格局#钱在哪里？ ---
    st.header("3. 市场宏观格局#钱在哪里？")
    st.markdown("我们首先分析电商大盘，回答三个核心问题#什么价位卖得好？ 谁在卖？ 货从哪里来？")
    st.write("") 
    
    ecom_df_with_bins = plot_price_sales_matrix(ecom_df) 
    
    col3, col4 = st.columns(2)
    with col3:
        plot_brand_top10(ecom_df_with_bins) 
    with col4:
        plot_brand_treemap(ecom_df_with_bins) 
    
    plot_regional_competition(ecom_df_with_bins) 
    plot_color_price_heatmap(ecom_df_with_bins) 
    
    create_insight_box(
        """
        <b>格局洞察:</b>
        <br/>1.  <b>价格带 (图 5):</b> 50-100元是竞争最激烈的红海，SKU数和总销量均是第一。150-200元价位段是溢价机会点。
        <br/>2.  <b>品牌 (图 6 & 7):</b> 两种图表均验证“欧莱雅”与“施华蔻”构成第一梯队，销量断层领先。
        <br/>3.  <b>区域 (图 8):</b> 市场呈“产销分离”。“广东”是最大的“货源集散地”（SKU最多），而“江苏”、“重庆”则是“超级卖场”（SKU不多，但总销量极高）。
        <br/>4.  <b>色系-价格 (图 9):</b> “棕色系”在 50-100元价位段销量最高。而“亚麻/青色系”和“灰色/蓝色系”等“潮色”，其销售高峰出现在 100-150元以上的价位。
        """
    )
    
    st.markdown("---")
    
    # --- 4. 产品深度拆解#什么在热卖？ ---
    st.header("4. 产品深度拆解#什么在热卖？")
    st.markdown("在主流价位下，具体是哪些产品形态在驱动市场？ 我们将产品归纳为五大类型进行矩阵分析，并深挖“中国色彩”的崛起。")
    st.write("") 

    col5, col6 = st.columns([1, 1])
    with col5:
        plot_color_share_donut(ecom_df, defs) 
    with col6:
        plot_color_swatch_analysis(data_pack['swatch_analysis']) 
        
    plot_product_archetype_matrix(ecom_df, defs) 
    plot_efficacy_bubble(ecom_df) 
        
    create_insight_box(
        """
        <b>产品洞察:</b>
        <br/>1.  <b>色系 (图 10):</b> “棕色系”是市场的绝对基本盘，占据近半销量，是大众消费者的“安全牌”。(注#此图已按色系语义着色)。
        <br/>2.  <b>色彩升级 (图 11):</b> “安全牌”正在精细化。消费者不再满足于泛泛的“棕色”，而是追求更具美学叙事感的“中国色彩”。数据显示，“茶棕”、“乌木色”和“檀棕”是销量最高的棕色系变体。
        <br/>3.  <b>产品类型 (图 12):</b> (注#此图已按产品类型语义着色)
        <br/>    * <b>跑量冠军 (右下):</b> “便捷型(泡沫)”拥有最高的市场规模（总销量），但价格偏低。
        <br/>    * <b>溢价蓝海 (左上):</b> “健康型(植物/无氨)”销量不高，但成功占据了“高均价”心智，是品牌升级方向。
        <br/>4.  <b>功效 (图 13):</b> “泡沫”型产品销量最高。“植物”和“无氨”等健康概念，则成功实现了更高的“平均溢价”。(注#此图使用“健康绿”渐变)。
        """
    )

    st.markdown("---")

    # --- 5. 社媒声量验证#人们在谈论什么？ ---
    st.header("5. 社媒声量验证#人们在谈论什么？")
    
    platform_choice = st.radio(
        "选择分析平台#",
        ('全部', 'XHS', 'Weibo'),
        horizontal=True,
        label_visibility="collapsed"
    )
    
    social_df = get_filtered_social_df(social_df_all, platform_choice)
    
    if platform_choice == '全部':
        social_avg_likes = social_avg_likes_all
        st.markdown(f"**当前平台: {platform_choice}** (共 {len(social_df):,} 条帖子)")
    else:
        social_avg_likes = data_processor.get_avg_likes_by_topic(social_df, defs)
        st.markdown(f"**当前平台: {platform_choice}** (共 {len(social_df):,} 条帖子)")
    
    st.write("") 

    col7, col8 = st.columns(2)
    with col7:
        plot_social_hot_topics(social_df) # V7 BUG 修复
    with col8:
        plot_social_brand_buzz_bar(social_df) 
        
    plot_social_topic_engagement(social_avg_likes, defs) 
    
    create_insight_box(
        """
        <b>社媒洞察:</b>
        <br/>1.  <b>品牌 (图 15):</b> 社媒声量与电商销量 **不完全匹配**。“爱茉莉”（美妆仙）在社媒的声量极高，远超其电商表现，是“社媒爆款”的操盘手。
        <br/>2.  <b>流量密码 (图 16):</b> “显白”是社媒流量密码。但我们惊喜地发现，新加入的“显气色”话题，其平均点赞数甚至超越了“显白”，成为新的爆款引擎。
        <br/>3.  <b>文化溢价 (图 16):</b> “东方美学”作为一个新兴概念，也获得了非常高的平均热度，证明了文化叙事在社媒端的种草价值。
        """
    )
    
    st.markdown("---")

    # --- 6. 核心洞察（一）#“显白”是基础刚需 ---
    st.header("6. 核心深挖 (一)#“显白”是基础刚需")
    st.markdown("我们对所有提及“显白”的数据进行了语义共现分析，构建了如下的二级关联知识图谱。")
    st.write("") 

    G_whitening, pos_whitening = get_network_graph_data(social_df_all, ecom_df, data_pack['co_occurrence'], defs, analysis_target="whitening")
    plot_whitening_network_graph(G_whitening, pos_whitening) 
    
    col9, col10 = st.columns(2)
    with col9:
        plot_whitening_co_occurrence_bars(data_pack['co_occurrence']) # V7.5 修复
    with col10:
        plot_whitening_co_matrix(data_pack['co_occurrence']) 
    
    create_insight_box(
        """
        <b>“显白” 构成洞察 (图 17, 18, 19):</b>
        <br/>* <b>图 18 (一级关联):</b> “显白”与“棕色系”、“爱茉莉”、“泡沫”关联最强。
        <br/>* <b>图 17 (二级关联 - 知识图谱):</b> **这才是核心！** 节点图展示了这些热门标签彼此之间的联系。我们能清晰看到一个由“泡沫”、“棕色系”、“爱茉莉”构成的<b>强关联“铁三角”</b>。
        <br/>* <b>图 19 (二级关联 - 热力图):</b> 热力图量化了图17的发现，“泡沫” + “棕色系”的共现次数遥遥领先。<b>结论#</b> 消费者要的“显白”是一个“解决方案”，即“<b>爱茉莉的棕色系泡沫染发剂</b>”。
        """
    )
    
    st.markdown("---")

    # --- 7. V7 新增章节#核心洞察（二）#“显气色”是进阶诉求 ---
    st.header("7. 核心深挖 (二)#“显气色”是进阶诉求")
    st.markdown("“显白”满足了功能性。那么，“显气色”这个更偏向东方审美的词，又代表了什么？")
    st.write("") 

    G_qise, pos_qise = get_network_graph_data(social_df_all, ecom_df, data_pack['qise_co_occurrence'], defs, analysis_target="qise")
    plot_qise_network_graph(G_qise, pos_qise) 
    
    plot_qise_co_occurrence_bars(data_pack['qise_co_occurrence']) # V7.5 修复
    
    create_insight_box(
        """
        <b>“显气色” 构成洞察 (图 20 & 21):</b>
        <br/>* <b>图 21 (一级关联):</b> “显气色”与“棕色系”、“红色/橘色系”等暖色调关联最强。同时，它也与“植物”、“无氨”等健康功效联系紧密。
        <br/>* <b>图 20 (二级关联 - 知识图谱):</b> **这是“气色”的灵魂！** 与“显白”的铁三角不同，“显气色”的网络连接更分散、更高级。
        <br/>* <b>结论#</b> “显白”追求的是一种功能性的“冷白皮”效果。而“显气色”追求的是一种“<b>健康、温和、有红润感</b>”的美学。它不是工业化的“白”，而是东方式的、由内而外的“好气色”。这是一个绝佳的品牌故事切入点。
        """
    )
    
    st.markdown("---")

    # --- 8. 最终验证与结论 ---
    st.header("8. 最终验证#用户口碑与结论")
    st.write("") 
    
    plot_comment_sentiment(data_pack['comments_insight']) 
    
    st.subheader("B. 当前局限与未来方向")
    create_insight_box(
        f"""
        本次“闪电报告”数据量充足，但仍有局限性，未来可从以下方向完善#
        <br/>1.  <b>评论数据量不足:</b> {data_pack['comments_insight']['total_comments']} 条评论只能做定性洞察。未来需扩大评论爬取量至 10万+ 级别，以构建更精准的“肤色-发色”推荐模型。
        <br/>2.  <b>微博数据价值低:</b> (可切换平台查看) 微博数据多为营销和新闻，用户UGC价值远低于小红书，未来应将爬取重心<b>彻底转向小红书</b>。
        <br/>3.  <b>缺失京东评论:</b> 本次只分析了淘宝评论，未能获取京东的 `评价人数` 对应的真实评论，缺失了京东侧的口碑验证。
        """
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()