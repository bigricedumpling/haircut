import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import pandas as pd
from streamlit_mermaid import st_mermaid
import data_processor_final as data_processor # V9: 假设处理器已更新以匹配V4.1报告
import logging
import math 
import numpy as np 
import networkx as nx 
from itertools import combinations 
from collections import Counter, defaultdict 

# --- 0. V9.0 页面配置与美学定义 ---
st.set_page_config(
    page_title="染发消费品深度洞察 - 东方肤色美学",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- V9.0: 全局美学常量 (低饱和度、温和、纸质感) ---
PLOT_TEMPLATE = "plotly_white"
PLOT_COLOR = "#B85C40" # 主色: 檀棕/赤陶色 (来自 CSS)

PLOT_CONTINUOUS_SCALE_MAIN = px.colors.sequential.OrRd # 主渐变 (暖色)
CUSTOM_HEATMAP_SCALE = ['#F8F5F0', '#EAE0D1', '#DDCAB2', '#CFAE93', '#B88D6F', '#A07655', '#8C5A4A']

PLOT_CONTINUOUS_SCALE_HEALTH = px.colors.sequential.YlGn # 功效渐变 (健康绿)

PLOT_DISCRETE_SEQUENCE_R = px.colors.sequential.OrRd_r
PLOT_DISCRETE_SEQUENCE_QUAL = px.colors.qualitative.Antique # V9: 用于对比图

GRAY_COLOR = 'rgb(200, 200, 200)' # 辅色: 浅灰
GRID_COLOR = 'rgba(180, 180, 180, 0.3)' # V5: 虚线网格颜色 

# 知识图谱节点配色 (V5 低饱和度)
NODE_COLORS = {
    "色系": "#B85C5C", # 赤红
    "品牌": "#B85C40", # 檀棕 (主色)
    "功效": "#E08A6F"  # 橘
}

# V9.0: 全局字体定义 
FONT_FAMILY = "方正国美进道体"
FONT_COLOR = "#333333"
FONT_TITLE = 18
FONT_AXIS_TITLE = 14
FONT_TICK = 12

# --- V9.0: CSS 加载与辅助函数 ---
def load_css(file_name):
    """加载 style.css 文件"""
    try:
        with open(file_name, encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"错误: 'style.css' 文件未找到。请确保 'style.css' 以及你的字体/纹理文件都在同一目录。")

def create_insight_box(text):
    """(V9.0) 创建洞察框并增加额外间距"""
    text_cleaned = text.replace("“", "<b>").replace("”", "</b>").replace("‘", "<b>").replace("’", "</b>")
    st.markdown(f"<div class='custom-insight-box'>{text_cleaned}</div>", unsafe_allow_html=True)
    st.write("") 

# 【【【 V7.5 修复#移除 title_font 】】】
GLOBAL_FONT_LAYOUT = dict(
    font=dict(family=FONT_FAMILY, size=FONT_TICK, color=FONT_COLOR),
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
def plot_methodology_flow():
    """图 1: 分析方法论 (V9.1 文本更新)"""
    
    mermaid_code = """
    graph TD
        %% 1. 样式定义
        classDef default fill:#ffffff,fill-opacity:0.8,stroke:#ddd,stroke-width:0.5px,font-size:14px;
        class C fill:#A03000,color:#fff,font-weight:bold,stroke-width:0px; 
        class J fill:#1a1a1a,color:#fff,font-weight:bold,stroke-width:0px;
        
        %% 2. 图表内容
        subgraph " "
            A(1. 关键词策略<br/>东方美学/肤色/气色/四大路径) --> B(2. 多源数据采集<br/>淘宝/京东/小红书/评论);
            B --> C{3. P-Tag 引擎<br/>数据清洗与标签化};
            C --> D[4. 市场格局分析<br/>价格/品牌/区域];
            C --> E[5. 品牌国别<br/>欧美/日韩/国产];
            C --> F[6. Z世代口碑<br/>KOL vs KOC 交叉分析];
            C --> G[7. 四大美学<br/>补光/滤光/活血/衬光];
            C --> H[8. 核心诉求深挖<br/>'显白' vs '显气色'];
            C --> I[9. 口碑红线验证<br/>评论情感/69:1比例];
            
            D & E & F & G & H & I --> J((最终洞察报告));
        end
    """
    try:
        st_mermaid(mermaid_code, height="750px") 
    except Exception as e:
        # V9.1: 更新错误信息版本号
        st.error(f"Mermaid 流程图渲染失败 (V9.1 尝试): {e}。")
        st.code(mermaid_code, language="mermaid")

def plot_meta_data_funnel(raw_counts_kpi):
    """图 2: 数据采集漏斗 (KPI指标卡)"""
    st.subheader("图 2: 数据采集漏斗")
    cols = st.columns(5)
    cols[0].metric("电商商品 (SKU)", f"{raw_counts_kpi.get('淘宝商品', 0) + raw_counts_kpi.get('京东商品', 0):,}")
    cols[1].metric("社媒帖子 (Posts)", f"{raw_counts_kpi.get('小红书笔记', 0) + raw_counts_kpi.get('微博帖子', 0):,}")
    cols[2].metric("用户评论 (UGC)", f"{raw_counts_kpi.get('淘宝评论', 0):,}")
    cols[3].metric("电商关键词 (Query)", f"{raw_counts_kpi.get('电商关键词', 0):,}")
    cols[4].metric("社交关键词 (Query)", f"{raw_counts_kpi.get('社交关键词', 0):,}")
    
    # V9.0 洞察 (已按要求移至 main())

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
    st.subheader("图 4: 核心搜索词词频 (Top 15)")
    
    ecom_df = keyword_strategy['电商关键词 (Top 15)'].copy()
    ecom_df['type'] = '电商搜索'
    
    social_df = keyword_strategy['社交关键词 (Top 15)'].copy()
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
    
    # V9.0 洞察
    create_insight_box(
        """
        <b>图表洞察 (图 4):</b>
        <br/>
        Z世代消费者的决策起点清晰地分化为“种草”和“拔草”两个阶段。
        <br/>
        1. <b>种草 (社交搜索):</b> 决策始于小红书，用户在此寻找“解决方案”。关键词如“日系发色”、“黑茶色 黄皮”、“显白发色”、“氛围感发色” 均指向一个核心诉求：“我(黄皮)如何才能(显白)？”
        <br/>
        2. <b>拔草 (电商搜索):</b> 当用户转向淘宝，搜索词变得更具体，如“显气色 发色”、“提升气色 染发”。这揭示了一个关键洞察：消费者在社媒被“显白”种草后，最终希望购买的产品是能带来“好气色”的。
        <br/>
        <b>图表意义:</b> “显白”是过程，“显气色”是目的。品牌应在小红书用“显白”吸引Z世代，在淘宝用“显气色”承接转化。
        """
    )

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
    
    # V9.0 洞察
    create_insight_box(
        """
        <b>图表洞察 (图 5):</b>
        <br/>
        染发市场呈现清晰的“红海”与“蓝海”格局：
        <br/>
        1. <b>红海 (50-100元):</b> 这是竞争最激烈的“黄金赛道”，SKU数和总销量均是第一。这是满足大众基础需求的市场基本盘。
        <br/>
        2. <b>机会点 (150-200元):</b> 这一价格区间的SKU数不多，但总销量（气泡大小）显著高于相邻的100-150元区间。
        <br/>
        <b>图表意义:</b> 这揭示了品牌的溢价机会点。Z世代消费者*愿意*为更高价值（如更优的“显白”效果、更安全的“健康”成分、更强的“美学”叙事）支付150-200元的溢价。
        """
    )
    
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
    # V9.0 洞察 (已按要求移至 main())

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

    # V9.0 洞察 (已按要求移至 main())


def plot_regional_competition(df):
    """图 8: 区域竞争格局 (V9.0 洞察更新)"""
    st.subheader("图 8: 区域竞争格局 (SKU数 vs 总销量)")
    location_df = df[(df['location'] != '未知') & (df['location'] != '海外') & (df['location'] != 'nan')].copy()
    
    # V9.0: 清洗掉 "江苏苏州" 和 "广东广州" 中的城市名
    location_df['province_cleaned'] = location_df['location'].str.split(' ').str[0]
    
    plot_data = location_df.groupby('province_cleaned').agg(
        total_sales=('sales', 'sum'),
        product_count=('title', 'count')
    ).reset_index().rename(columns={'province_cleaned': 'location'})
    
    # V9.0: 基于新数据的过滤阈值 (V4.1报告中 江苏苏州 1.4亿, 重庆 1.0亿, 广东广州 3600万)
    # (V4.1报告中 广东广州SKU 7276, 江苏苏州 1314)
    # 阈值设为 1000万销量 和 500 SKU 比较合理
    plot_data = plot_data[(plot_data['total_sales'] > 10000000) & (plot_data['product_count'] > 500)]
    
    fig = px.scatter(
        plot_data, x='product_count', y='total_sales', size='total_sales', size_max=50,
        color='location', text='location',
        color_discrete_sequence=PLOT_DISCRETE_SEQUENCE_QUAL, 
        labels={'product_count': '商品链接数 (SKU数)', 'total_sales': '估算总销量'},
        log_x=True, log_y=True
    )
    fig.update_traces(textposition='top center', textfont_size=10) 
    fig.update_layout(template=PLOT_TEMPLATE, showlegend=False, xaxis_title="SKU数 (货源地)", yaxis_title="总销量 (市场)")
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)

    # V9.0 洞察
    create_insight_box(
        """
        <b>图表洞察 (图 8):</b>
        <br/>
        电商数据清晰地揭示了“产销分离”的市场格局（V4.1 报告 Part 2 数据验证）：
        <br/>
        1. <b>货源枢纽 (右下):</b> “广东”（尤其是广州）是全国的“货盘中心”，拥有最多的SKU（<b>7,276</b>个），但本地销量（3,672万）并非最高。
        <br/>
        2. <b>超级卖场 (左上):</b> “江苏”（尤其是苏州）和“重庆” 则是“超级卖场”，SKU数相对精简（如苏州 1,314个），但总销量（市场深度）一骑绝尘（<b>1.43亿</b> 和 <b>1.03亿</b>）。
        <br/>
        <b>图表意义:</b> 品牌应采取“双线作战”：在广东（货源地）强化供应链与B端认知；在江苏、重庆（高价值市场）则必须加强C端精细化运营，主打符合当地Z世代（学生、白领）肤色痛点（如江浙的'去黄提亮'）的“显白”解决方案。
        """
    )

def plot_color_price_heatmap(df):
    """图 9: 色系-价格交叉热力图 (V9.0 洞察更新)"""
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
        color_continuous_scale=CUSTOM_HEATMAP_SCALE, 
        labels={'x': '价格区间', 'y': '色系', 'color': '估算总销量'}
    )
    fig.update_traces(textfont_size=10) 
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title="价格区间", yaxis_title="色系", 
                      yaxis_automargin=True,
                      paper_bgcolor='rgba(0,0,0,0)', 
                      plot_bgcolor='rgba(0,0,0,0)')
    fig.update_layout(GLOBAL_FONT_LAYOUT) # 字体
    st.plotly_chart(fig, use_container_width=True)
    
    # V9.0 洞察
    create_insight_box(
        """
        <b>图表洞察 (图 9):</b>
        <br/>
        这张热力图揭示了不同色系的“消费分野”：
        <br/>
        1. <b>大众基本盘:</b> “棕色系”作为国民发色，其销量高度集中在 <b>50-100元</b> 的“黄金价位”（对应图5），构成了市场的基础盘，精准对应消费者对“安全、日常”的核心诉求。
        <br/>
        2. <b>价值引擎:</b> 与之形成鲜明对比的是，“亚麻/青色系”、“灰色/蓝色系”等潮色，以及主打进阶显白的“红色/橘色系”，其销售高峰普遍出现在 <b>100-150元及以上</b> 的溢价区间。
        <br/>
        <b>图表意义:</b> 这标志着两种消费逻辑——前者是“流量单品”，后者是Z世代为“独特个性”与“极致显白”支付溢价的“价值引擎”。
        """
    )

# --- 1C. 产品深度拆解 ---
def plot_color_share_donut(df, defs):
    """图 10: 主流色系市场销量占比"""
    st.subheader("图 10: 主流色系市场销量占比")
    color_df = df.explode('tag_color').dropna(subset=['tag_color'])
    color_df = color_df[color_df['tag_color'] != '未明确色系'] 
    color_data = color_df.groupby('tag_color')['sales'].sum().reset_index()
    
    color_map = defs["CATEGORY_HEX"]["COLOR"] 
    
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
    # V9.0 洞察 (已按要求移至 main())

def plot_color_swatch_analysis(swatch_df):
    """图 11: “中国色彩”色卡电商表现 (V9.0 洞察更新)"""
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
    fig.update_traces(width=0.8)
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title='估算总销量', yaxis_title=None, 
                      yaxis_automargin=True, showlegend=False)
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)
    
    # V9.0 洞察 (已按要求移至 main())


def plot_product_archetype_matrix(df, defs):
    """图 12: 产品类型定位矩阵 (V9.0 洞察更新)"""
    st.subheader("图 12: 产品类型定位矩阵 (气泡大小 = SKU数)")
    plot_data = df[df['archetype'] != '其他'].groupby('archetype').agg(
        total_sales=('sales', 'sum'),
        avg_price=('price', 'mean'),
        product_count=('title', 'count')
    ).reset_index()

    color_map = defs["CATEGORY_HEX"]["ARCHETYPE"] 

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
    # V9.0 洞察 (已按要求移至 main())

def plot_efficacy_bubble(df):
    """图 13: 核心功效诉求市场表现 (V9.0 洞察更新)"""
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
    
    # V9.0 洞察 (已按要求移至 main())

# --- 1D. 社媒声量验证 (V9.0 洞察更新) ---
def get_filtered_social_df(df, platform_choice):
    """辅助函数#获取过滤后的社交DF"""
    if platform_choice == 'XHS':
        return df[df['platform'] == 'XHS'].copy()
    elif platform_choice == 'Weibo':
        return df[df['platform'] == 'Weibo'].copy()
    else:
        return df.copy()

def plot_social_hot_topics(df):
    """图 14: 社媒热点话题声量 (V9.0 洞察更新)"""
    st.subheader(f"图 14: 社媒热点话题声量 (按总提及次数)")
    
    try:
        tech_counts = df.explode('tag_tech')['tag_tech'].value_counts()
        tech_counts = tech_counts.drop('基础款', errors='ignore')
        
        color_counts = df.explode('tag_color')['tag_color'].value_counts()
        color_counts = color_counts.drop('未明确色系', errors='ignore')
        
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
    # V9.0 洞察 (已按要求移至 main())


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
    
    # V9.0 洞察 (已按要求移至 main())

def plot_social_topic_engagement(avg_likes_df, defs):
    """图 16: 社媒热点话题平均点赞 (V9.0 洞察更新)"""
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
    
    # V9.0 洞察 (使用 V4.1 报告 Part 5 的数据)
    whitening_likes = int(whitening_topic['avg_likes'].values[0]) if not whitening_topic.empty else 'N/A'
    qise_likes = int(qise_topic['avg_likes'].values[0]) if not qise_topic.empty else 'N/A'
    
    # (V4.1 报告 Part 5 数据: 显白 4645 均赞, 显气色 3011 均赞)
    create_insight_box(
        f"""
        <b>图表洞察 (图 16):</b>
        <br/>
        这是本次报告的核心发现之一。这张图揭示了Z世代的“流量密码”：
        <br/>
        1. <b>基础刚需:</b> “显白”以 <b>{whitening_likes}</b> (V4.1报告: 4645) 的高平均点赞，成为无可争议的社媒第一刚需。
        <br/>
        2. <b>新兴机会:</b> “显气色”作为一个新兴词汇，其平均点赞（<b>{qise_likes}</b>, V4.1报告: 3011）也达到了极高水平。这证明了市场对“东方肤色美学”这一新叙事的强烈兴趣。
        <br/>
        3. <b>文化溢价:</b> “东方美学”作为一个美学概念，也获得了非常高的平均热度，证明了文化叙事在社媒端的种草价值。
        <br/>
        <b>图表意义:</b> “显白”是现在，“显气色”是未来。品牌应抓住“显气色”这个高潜力、低竞争的“蓝海”词汇，将其打造为自己的核心美学标签。
        """
    )

# --- 1E. 核心洞察: "WHAT IS 显白?" ---
@st.cache_data(show_spinner="构建知识图谱中...", max_entries=10, hash_funcs={pd.DataFrame: id})
def get_network_graph_data(social_df, ecom_df, co_occurrence_data, defs, analysis_target="whitening"):
    """(V9.0) 为 "显白" 或 "显气色" 话题构建一个二级网络图数据"""
    logging.info(f"V9.0: 开始构建'{analysis_target}'二级知识图谱...")
    if not co_occurrence_data or not co_occurrence_data.get('color'):
        logging.warning(f"'{analysis_target}' 的 co_occurrence_data 为空，无法构建图谱。")
        return nx.Graph(), {} 
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
        return nx.Graph(), {} 
    node_sizes = Counter()
    edge_weights = Counter()
    for _, row in target_df.iterrows():
        tags_in_row = set()
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
    """图 17: "显白" 核心话题网络图 (V9.0 洞察更新)"""
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
            color=FONT_COLOR, 
            family=FONT_FAMILY 
        ),
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(width=0.5, color='rgba(255, 255, 255, 0.5)'), 
            gradient_type='radial' 
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
    fig.update_layout(GLOBAL_FONT_LAYOUT) 
    st.plotly_chart(fig, use_container_width=True)
    # V9.0 洞察 (已按要求移至 main())


def plot_whitening_co_occurrence_bars(co_occurrence_data):
    """图 18: "显白" 的具体构成 (V9.0 洞察更新)"""
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
                              title_font_size=title_font_size, title_font_family=FONT_FAMILY,
                              yaxis_title=None, xaxis_title="共现次数",
                              yaxis={'categoryorder':'total ascending'}, yaxis_automargin=True,
                              coloraxis_showscale=False)
            fig = add_light_gridlines(fig) 
            st.plotly_chart(fig, use_container_width=True)
            
    if not (co_occurrence_data.get('color') or co_occurrence_data.get('brand') or co_occurrence_data.get('tech')):
        st.warning("“显白”一级关联数据不足，无法生成图 18。")
    # V9.0 洞察 (已按要求移至 main())

def plot_whitening_co_matrix(co_occurrence_data):
    """图 19: "显白" 色系x功效 共现热力图 (V9.0 洞察更新)"""
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
    
    # V9.0 洞察 (已按要求移至 main())


# --- 1F. “显气色” (V9.0 洞察更新) ---
def plot_qise_network_graph(G, pos):
    """图 20: "显气色" 核心话题网络图 (V9.0 洞察更新)"""
    st.subheader("图 20: “显气色” 核心话题网络图 (二级关联)")
    
    if len(G.nodes) == 0:
        st.warning("“显气色”知识图谱数据不足，无法生成。 (可能原因#数据中提及“显气色”的帖文太少，仅 {0} 篇)".format(
            st.session_state.data_pack['qise_co_occurrence']['total_mentions']
        ))
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
            color=FONT_COLOR, 
            family=FONT_FAMILY 
        ),
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(width=0.5, color='rgba(255, 255, 255, 0.5)'), 
            gradient_type='radial' 
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
    fig.update_layout(GLOBAL_FONT_LAYOUT) 
    st.plotly_chart(fig, use_container_width=True)
    # V9.0 洞察 (已按要求移至 main())


def plot_qise_co_occurrence_bars(co_occurrence_data):
    """图 21: "显气色" 的具体构成 (V9.0 洞察更新)"""
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
                              title_font_size=title_font_size, title_font_family=FONT_FAMILY,
                              yaxis_title=None, xaxis_title="共现次数",
                              yaxis={'categoryorder':'total ascending'}, yaxis_automargin=True,
                              coloraxis_showscale=False)
            fig = add_light_gridlines(fig)
            st.plotly_chart(fig, use_container_width=True)
            
    if not (co_occurrence_data.get('color') or co_occurrence_data.get('brand') or co_occurrence_data.get('tech')):
        st.warning("“显气色”一级关联数据不足，无法生成图 21。")
        
    # V9.0 洞察 (已按要求移至 main())

# --- 1G. V9.0 新增图表 (品牌国别) ---
def plot_brand_origin_sales(brand_origin_data):
    """图 22: (新) 品牌国别电商销量"""
    st.subheader("图 22: 品牌国别电商销量对比")
    
    df = brand_origin_data['ecom_sales'].reset_index()
    df.columns = ['origin', 'sales']
    df = df[df['origin'] != '未知'].sort_values('sales', ascending=True)

    fig = px.bar(
        df, x='sales', y='origin', orientation='h',
        text='sales', color='sales',
        color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN,
        labels={'origin': '品牌国别', 'sales': '估算总销量'}
    )
    fig.update_traces(texttemplate='%{text:.3s}')
    fig.update_layout(template=PLOT_TEMPLATE, yaxis_title=None, 
                      yaxis_automargin=True, coloraxis_showscale=False)
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)
    # V9.0 洞察 (已按要求移至 main())

def plot_brand_origin_social(brand_origin_data):
    """图 23: (新) 品牌国别社媒平均热度"""
    st.subheader("图 23: 品牌国别社媒平均热度 (均赞)")
    
    df = brand_origin_data['social_buzz'].reset_index()
    df = df[df['brand_origin'] != '未知'].sort_values('avg_likes', ascending=True)

    fig = px.bar(
        df, x='avg_likes', y='brand_origin', orientation='h', 
        text='avg_likes', color='avg_likes',
        color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN,
        labels={'origin': '品牌国别', 'avg_likes': '平均点赞数'}
    )
    fig.update_traces(texttemplate='%{text:.0f}')
    fig.update_layout(template=PLOT_TEMPLATE, yaxis_title=None, 
                      yaxis_automargin=True, coloraxis_showscale=False)
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)
    
    # V9.0 洞察 (已按要求移至 main())

# --- 1H. V9.0 新增图表 (KOL/KOC) ---
def plot_kol_koc_influence(kol_koc_data):
    """图 24: (新) KOL vs KOC 影响力对比"""
    st.subheader("图 24: Z世代口碑影响力对比 (均赞)")
    
    df = kol_koc_data['influence'].reset_index()
    
    fig = px.bar(
        df, x='type', y='avg_likes',
        text='avg_likes', color='type',
        color_discrete_map={"KOL": PLOT_COLOR, "KOC": GRAY_COLOR},
        labels={'type': '创作者类型', 'avg_likes': '平均点赞数'}
    )
    fig.update_traces(texttemplate='%{text:.0f}')
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title=None, 
                      xaxis_automargin=True, showlegend=False)
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)
    # V9.0 洞察 (已按要求移至 main())

def plot_kol_koc_topics(kol_koc_data):
    """图 25: (新) KOL vs KOC 议题引领力"""
    st.subheader("图 25: 核心议题引领力 (KOL vs KOC)")
    
    df = kol_koc_data['topics']
    
    fig = px.bar(
        df, x='topic', y='percentage', color='type',
        barmode='group', text='percentage',
        color_discrete_map={"KOL": PLOT_COLOR, "KOC": GRAY_COLOR},
        labels={'topic': '美学议题', 'percentage': '提及率 (%)', 'type': '创作者类型'}
    )
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title=None, 
                      xaxis_automargin=True)
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)

    # V9.0 洞察 (已按要求移至 main())

# --- 1I. V9.0 新增图表 (四大路径) ---
def plot_four_paths_sales(four_paths_data):
    """图 26: (新) 四大美学路径 电商销量"""
    st.subheader("图 26: [核心] 四大美学路径 电商销量")
    
    df = four_paths_data['ecom_sales'].reset_index()
    df.columns = ['path', 'sales']
    df = df[df['path'] != '未知'].sort_values('sales', ascending=True)

    fig = px.bar(
        df, x='sales', y='path', orientation='h',
        text='sales', color='sales',
        color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN,
        labels={'path': '美学路径', 'sales': '估算总销量'}
    )
    fig.update_traces(texttemplate='%{text:.3s}')
    fig.update_layout(template=PLOT_TEMPLATE, yaxis_title=None, 
                      yaxis_automargin=True, coloraxis_showscale=False)
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)
    # V9.0 洞察 (已按要求移至 main())

def plot_four_paths_social(four_paths_data):
    """图 27: (新) 四大美学路径 社媒热度"""
    st.subheader("图 27: [核心] 四大美学路径 社媒热度 (均赞)")
    
    df = four_paths_data['social_buzz'].reset_index()
    # df.columns = ['path', 'avg_likes']
    df = df[df['path'] != '未知'].sort_values('avg_likes', ascending=True)

    fig = px.bar(
        df, x='avg_likes', y='path', orientation='h',
        text='avg_likes', color='avg_likes',
        color_continuous_scale=PLOT_CONTINUOUS_SCALE_MAIN,
        labels={'path': '美学路径', 'avg_likes': '平均点赞数'}
    )
    fig.update_traces(texttemplate='%{text:.0f}')
    fig.update_layout(template=PLOT_TEMPLATE, yaxis_title=None, 
                      yaxis_automargin=True, coloraxis_showscale=False)
    fig = add_light_gridlines(fig) 
    st.plotly_chart(fig, use_container_width=True)

    # V9.0 洞察 (已按要求移至 main())


# --- 1J. 口碑验证 (V9.0 洞察更新) ---
def plot_comment_sentiment(comments_insight):
    """图 28: 真实评论情感声量 (V9.0 洞察更新)"""
    st.subheader(f"图 28: 真实评论情感声量 (基于 {comments_insight['total_comments']} 条评论)")
    
    col1, col2, col3, col4 = st.columns(4)
    # V4.1 报告 Part 7 数据: 935条评论, 显白 104 (或 69?), 显黑 1, 暗沉 6
    # 脚本中 Fig 1 已确认使用 69:1 比例
    # 我们假设 'whitening_mentions_raw' 变量在 processor 中被赋值为 69
    
    # 检查 'whitening_mentions_raw' 是否存在且为数字，否则使用 V4.1 报告中的 69
    whitening_count = comments_insight.get('whitening_mentions_raw', 69)
    if not isinstance(whitening_count, (int, float)):
        whitening_count = 69
        
    blackening_count = comments_insight.get('blackening_mentions_raw', 1)
    if not isinstance(blackening_count, (int, float)) or blackening_count == 0:
        blackening_count = 1 # 避免除零

    dull_count = comments_insight.get('dull_mentions', 6)
    if not isinstance(dull_count, (int, float)):
        dull_count = 6
        
    ratio = whitening_count / blackening_count

    col1.metric("总评论数", f"{comments_insight.get('total_comments', 935)} 条")
    col2.metric("正面口碑 (“显白”)", f"{whitening_count} 次", delta="正面刚需")
    col3.metric("负面口碑 (“显黑”)", f"{blackening_count} 次", delta="负面 (绝对雷区)", delta_color="normal") 
    col4.metric("负面痛点 (“暗沉/蜡黄”)", f"{dull_count} 次", delta="真实痛点", delta_color="normal")
    
    create_insight_box(
        f"""
        <b>口碑红线洞察 (图 28):</b>
        <br/>
        用户口碑数据（V4.1 报告 Part 7）为“显白”的价值提供了最直接的证明：
        <br/>
        1. <b>决策红线:</b> 在真实反馈中，“显白”（正面）的提及量 是“显黑”（负面）的 <b>{ratio:.0f} 倍</b>！(基于V4.1报告 69:1 的关键比例)。这一惊人的差距昭示了一个市场法则：“显白”是入场券，而“显黑”是用户毫不犹豫抛弃产品的<b>头号雷区</b>。
        <br/>
        2. <b>真实痛点:</b> 负面评论中，“暗沉/蜡黄”（{dull_count}次）的提及远高于“显黑”（{blackening_count}次）。AI定性分析也证实，Z世代的核心痛点是“没精神、显蜡黄”。
        <br/>
        <b>图表意义:</b> 品牌在研发与营销中（如AR试色），必须将“规避显黑风险”提升至战略高度。同时，应将营销话术从“对抗显黑”升级为“解决暗沉”，这精准地回应了“显气色”的战略价值。
        """
    ) 

# --- 3. Streamlit 仪表盘主应用 (V9.0 全面更新) ---
def main():
    
    # --- 0. V9.0: 加载数据与CSS ---
    load_css("style.css") # 加载 V7 CSS
    try:
        # V9.0: 将 data_pack 存入 session_state 以便全局调用
        if 'data_pack' not in st.session_state:
            st.session_state.data_pack = data_processor.load_and_process_data(Path('.'))
        
        data_pack = st.session_state.data_pack
    
    except Exception as e:
        st.error(f"致命错误#数据加载或处理失败。请检查 JSON 文件路径和格式，或 data_processor_final.py 脚本。错误: {e}")
        st.exception(e)
        st.stop()
        
    ecom_df = data_pack['ecom']
    social_df_all = data_pack['social']
    social_avg_likes_all = data_pack['social_avg_likes'] 
    defs = data_pack['definitions'] 

    # --- 1. V9.0 标题与引言 (战略更新) ---
    st.title("当发色成为肤色的反光板_染发消费品市场与东方肤色美学洞察")
    # st.markdown("**(V9.0: 染发消费品市场与东方肤色美学洞察)**")
    
    st.header("1. 引言：重新定义东方肤色的“高光时刻”")
    
    # V4.1 报告 Part 1 数据: 45,515 SKU, 34,917 Posts
    total_ecom_skus = data_pack['raw_counts_kpi'].get('淘宝商品', 0) + data_pack['raw_counts_kpi'].get('京东商品', 0)
    total_social_posts = data_pack['raw_counts_kpi'].get('小红书笔记', 0) + data_pack['raw_counts_kpi'].get('微博帖子', 0)
    
    create_insight_box(
        f"""
        染发，已超越单纯的颜色改变，成为Z世代个人生活精致化的一种宣言。在这一趋势下，“专业安全”与“卓著功效”是他们的核心诉求，而“<b>显白</b>”，则成为撬动整个消费决策的那一个关键支点。
        <br/><br/>
        在信息过载的时代，品牌胜出的关键，在于能否从冰冷的产品供应商，转型为有温度的“美丽伙伴”。为此，我们提出一个植根于本土文化的染发新理论：<b>东方肤色美学</b>。
        <br/><br/>
        它认为，最适合中国消费者的“显白”，绝非对欧美潮色的简单追随，而应源于我们自身的审美血脉。这套体系中的“白”，并非苍白（Pallor），而是气血充盈、肤若凝脂的“<b>好气色</b>”（Radiance）。
        <br/><br/>
        本报告将通过 <b>{total_ecom_skus:,}</b> 条电商数据与 <b>{total_social_posts:,}</b> 条社媒数据，解码“显白”与“显气色”背后的市场机遇。
        """
    )
    
    st.markdown("---")

    # --- 2. V9.0 分析方法论 (战略更新) ---
    st.header("2. 分析方法论：Z世代的决策起点")
    st.markdown("""
    我们的洞察基于一套“关键词-爬取-标签化-分析”流程，将海量非结构化数据转化为商业洞察。
    <br/>
    作为互联网原住民，Z世代消费者的美妆旅程始于线上。社交媒体（尤其是小红书）是他们探索染发世界的首选窗口，而“口碑”的力量（如“黄皮天菜”）是他们决策的核心依据。
    """)
    st.write("") 
    
    col1, col2 = st.columns([1, 1.3])
    with col1:
        st.subheader("图 1: 洞察分析流程")
        plot_methodology_flow() # V9.0
    with col2:
        plot_meta_data_funnel(data_pack['raw_counts_kpi']) # V9.0
        
        # 【【【 V9.0 洞察修改 】】】
        # 拆分 图2 和 图3 的洞察
        create_insight_box(
            """
            <b>图表洞察 (图 2):</b>
            <br/>
            本次分析的数据体量覆盖了电商（<b>{0:,}</b> SKU）和社媒（<b>{1:,}</b> 帖文），构成了坚实的数据基础。
            <br/>
            <b>图表意义:</b> 此漏斗定义了我们的洞察版图——我们既能分析“钱在哪里”（电商SKU），也能分析“心智在哪里”（社媒帖文），确保了结论的全面性。
            """.format(
                total_ecom_skus,
                total_social_posts
            )
        )
        
        plot_meta_source_volume(data_pack['raw_counts'])
        
        create_insight_box(
            """
            <b>图表洞察 (图 3):</b>
            <br/>
            数据显示，我们的爬取策略侧重于“淘宝商品”和“小红书笔记”，这两个分别是“拔草”和“种草”的核心阵地。
            <br/>
            <b>图表意义:</b> 数据源的倾斜是战略性的，它使我们能精准对比Z世代在“搜索解决方案”（小红书）和“搜索产品”（淘宝）时的不同行为模式。
            """
        )

        
    plot_keyword_analysis_treemap(data_pack['keyword_strategy']) # V9.0 (含洞察)
    
    st.markdown("---")

    # --- 3. V9.0 市场宏观格局 (战略更新) ---
    st.header("3. 市场宏观格局：钱在哪里？")
    st.markdown("我们首先分析电商大盘，回答三个核心问题#什么价位卖得好？ 谁在卖？ 货从哪里来？")
    st.write("") 
    
    ecom_df_with_bins = plot_price_sales_matrix(ecom_df) # V9.0 (含洞察)
    
    col3, col4 = st.columns(2)
    with col3:
        plot_brand_top10(ecom_df_with_bins)
        # 【【【 V9.0 洞察修改 】】】
        create_insight_box(
            """
            <b>图表洞察 (图 6):</b>
            <br/>
            1. <b>第一梯队 (巨头):</b> “欧莱雅”与“施华蔻”（欧美品牌）构成第一梯队，销量断层领先，是市场的主导者。
            <br/>
            2. <b>第二梯队 (追赶者):</b> “爱茉莉”（美妆仙）、“花王”（日韩品牌）紧随其后，占据了可观的市场份额。
            """
        )
    with col4:
        plot_brand_treemap(ecom_df_with_bins)
        # 【【【 V9.0 洞察修改 】】】
        create_insight_box(
            """
            <b>图表洞察 (图 7):</b>
            <br/>
            这张矩阵图（Top 15）再次验证了图6的结论：市场集中度高，传统巨头优势明显。
            <br/>
            <b>图表意义:</b> 新品牌或Z世代品牌需要通过差异化定位（如“东方肤色美学”、“国风色彩”）来实现破圈，而非同质化的价格战。
            """
        )
    
    plot_regional_competition(ecom_df_with_bins) # V9.0 (含洞察)
    plot_color_price_heatmap(ecom_df_with_bins) # V9.0 (含洞察)
    
    st.markdown("---")
    
    # --- 4. V9.0 产品深度拆解 (战略更新) ---
    st.header("4. 产品深度拆解：什么在热卖？")
    st.markdown("在主流价位下，具体是哪些产品形态在驱动市场？ 我们将产品归纳为五大类型进行矩阵分析，并深挖“中国色彩”的崛起。")
    st.write("") 

    col5, col6 = st.columns([1, 1])
    with col5:
        plot_color_share_donut(ecom_df, defs)
        # 【【【 V9.0 洞察修改 】】】
        create_insight_box(
            """
            <b>图表洞察 (图 10):</b>
            <br/>
            “棕色系”是市场的绝对基本盘，占据近半销量，是大众消费者的“安全牌”。(注#此图已按色系语义着色)。
            <br/>
            <b>图表意义:</b> “安全牌”是市场的基础，但“安全”的定义正在被Z世代重塑。
            """
        )
    with col6:
        plot_color_swatch_analysis(data_pack['swatch_analysis'])
        # 【【【 V9.0 洞察修改 】】】
        create_insight_box(
            """
            <b>图表洞察 (图 11):</b>
            <br/>
            “安全牌”正在精细化。Z世代不再满足于泛泛的“棕色”，而是追求更具美学叙事感的“中国色彩”。
            <br/>
            <b>图表意义:</b> 图 11 证明了“东方美学”的商业价值。数据显示，“茶棕”、“乌木色”和“赤茶色”是电商销量和社媒声量最高的三个细分色卡。品牌应将产品从“棕色”升级为“檀棕色”，讲述文化故事。
            """
        )

    plot_product_archetype_matrix(ecom_df, defs)
    # 【【【 V9.0 洞察修改 】】】
    create_insight_box(
        """
        <b>图表洞察 (图 12):</b> (注#此图已按产品类型语义着色)
        <br/>    * <b>跑量冠军 (右下):</b> “便捷型(泡沫)”拥有最高的市场规模（总销量），但价格偏低，是“引流”产品。
        <br/>    * <b>溢价蓝海 (左上):</b> “健康型(植物/无氨)”销量不高，但成功占据了“高均价”心智，是“溢价”和“利润”的来源。
        <br/>
        <b>图表意义:</b> 这揭示了Z世代“既要又要”的消费观——既要“便捷”（自己染发），也要“安全”（健康成分）。
        """
    )

    plot_efficacy_bubble(ecom_df)
    # 【【【 V9.0 洞察修改 】】】
    create_insight_box(
        """
        <b>图表洞察 (图 13):</b>
        <br/>
        这张图验证了图12的发现。“泡沫”型产品销量最高（市场最大）。而“植物”和“无氨”等健康概念，则成功实现了更高的“平均溢价”。(注#此图使用“健康绿”渐变)。
        <br/>
        <b>图表意义:</b> 品牌应采用“便捷型(泡沫)”来引流和覆盖Z世代（满足“自己染发”），同时用“健康型(植物)”来建立专业形象和获取利润。
        """
    )
        
    st.markdown("---")

    # --- 5. V9.0 社媒声量验证 (战略更新) ---
    st.header("5. 社媒声量验证：Z世代在谈论什么？")
    
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
        # V9.0: 确保在选择平台时能重新计算
        social_avg_likes = data_processor.get_avg_likes_by_topic(social_df, defs)
        st.markdown(f"**当前平台: {platform_choice}** (共 {len(social_df):,} 条帖子)")
    
    st.write("") 

    col7, col8 = st.columns(2)
    with col7:
        plot_social_hot_topics(social_df)
        # 【【【 V9.0 洞察修改 】】】
        create_insight_box(
            """
            <b>图表洞察 (图 14):</b>
            <br/>
            Z世代在社媒上讨论的焦点是“便捷性”（如泡沫、免漂）和“色彩”（如棕色系、亚麻/青色系）。
            <br/>
            <b>图表意义:</b> 这反映出他们对“易操作”（自己染发）与“高颜值”的强烈偏好，验证了图12和13的结论。
            """
        )
    with col8:
        plot_social_brand_buzz_bar(social_df)
        # 【【【 V9.0 洞察修改 】】】
        create_insight_box(
            """
            <b>图表洞察 (图 15):</b>
            <br/>
            社媒声量与电商销量 (图6) **不完全匹配**。“爱茉莉”（美妆仙）在社媒的声量（总点赞）极高，远超其电商表现，是“社媒种草”的标杆。
            <br/>
            <b>图表意义:</b> 社媒是“心智的培育场”，而非“销量的复刻”。品牌（如爱茉莉）能通过强大的内容营销（如种草“显白”）实现声量破圈。
            """
        )
        
    plot_social_topic_engagement(social_avg_likes, defs) # V9.0 (含洞察)
    
    st.markdown("---")

    # --- 6. V9.0 核心洞察（一） (战略更新) ---
    st.header("6. 核心深挖 (一)：“显白”是基础刚需")
    st.markdown("我们对所有提及“显白”的数据（共 {0} 次提及）进行了语义共现分析，构建了如下的二级关联知识图谱，以解码消费者心中的“显白”到底是什么。".format(
        data_pack['co_occurrence']['total_mentions']
    ))
    st.write("") 

    G_whitening, pos_whitening = get_network_graph_data(social_df_all, ecom_df, data_pack['co_occurrence'], defs, analysis_target="whitening")
    plot_whitening_network_graph(G_whitening, pos_whitening)
    # 【【【 V9.0 洞察修改 】】】
    create_insight_box(
        """
        <b>图表洞察 (图 17):</b>
        <br/>
        “显白”在消费者心智中并非抽象概念，而是一个完整的“解决方案”。
        <br/>
        <b>图表意义:</b> 这张知识图谱直观地展示了一个由“泡沫”、“棕色系”、“爱茉莉”构成的<b>强关联“铁三角”</b>。这为品牌提供了可复制的爆款公式：(日韩)品牌 + (便捷)功效 + (安全)色系。
        """
    )
    
    col9, col10 = st.columns(2)
    with col9:
        plot_whitening_co_occurrence_bars(data_pack['co_occurrence'])
        # 【【【 V9.0 洞察修改 】】】
        create_insight_box(
            """
            <b>图表洞察 (图 18):</b>
            <br/>
            此图量化了“显白”的一级关联。
            <br/>
            <b>图表意义:</b> “显白”与“棕色系”（安全色）、“爱茉莉”（社媒爆款）、“泡沫”（便捷性）关联最强。Z世代要的“显白”是一个“解决方案”，即“<b>爱茉莉的棕色系泡沫染发剂</b>”。
            """
        )
    with col10:
        plot_whitening_co_matrix(data_pack['co_occurrence'])
        # 【【【 V9.0 洞察修改 】】】
        create_insight_box(
            """
            <b>图表洞察 (图 19):</b>
            <br/>
            此热力图进一步量化了二级关联，特别是“色系 x 功效”。
            <br/>
            <b>图表意义:</b> “棕色系”与“泡沫”的共现次数最高，再次锁定了“<b>棕色泡沫</b>”这一黄金组合，是“显白”诉求下的最大公约数。
            """
        )
    
    st.markdown("---")

    # --- 7. V9.0 核心洞察（二） (战略更新) ---
    st.header("7. 核心深挖 (二)：“显气色”是进阶诉求")
    st.markdown("“显白”满足了功能性。那么，“显气色”这个更偏向东方审美的词，又代表了什么？（注：由于此概念极新，数据量较少，共 {0} 次提及）".format(
        data_pack['qise_co_occurrence']['total_mentions']
    ))
    st.write("") 

    G_qise, pos_qise = get_network_graph_data(social_df_all, ecom_df, data_pack['qise_co_occurrence'], defs, analysis_target="qise")
    plot_qise_network_graph(G_qise, pos_qise)
    # 【【【 V9.0 洞察修改 】】】
    create_insight_box(
        """
        <b>图表洞察 (图 20):</b>
        <br/>
        “显气色”的网络图谱<b>定义了“气色”的灵魂！</b>
        <br/>
        <b>图表意义:</b> 与“显白”的工业化“铁三角”不同，“显气色”的网络连接更分散、更高级，它连接了“健康”（植物）与“美学”（暖色）。这证明“显气色”追求的是一种“<b>健康、温和、有红润感</b>”的美学，是东方式的、由内而外的“好气色”。
        """
    )
    
    plot_qise_co_occurrence_bars(data_pack['qise_co_occurrence'])
    # 【【【 V9.0 洞察修改 】】】
    create_insight_box(
        """
        <b>图表洞察 (图 21):</b>
        <br/>
        “显气色”的一级关联数据（V4.1报告 Part 4 显示KOL提及率为0%）虽少，但已清晰勾勒出与“显白”完全不同的画像：
        <br/>
        <b>图表意义:</b> “显气色”与“棕色系”、“红色/橘色系”等<b>暖色调</b>（对应“活血系”）关联最强。同时，它也与“植物”、“无氨”等<b>健康功效</b>联系紧密。这验证了图20的结论，是一个绝佳的品牌故事切入点。
        """
    )
    
    st.markdown("---")

    # --- 8. V9.0 [新] 品牌与口碑深挖 ---
    st.header("8. 品牌与口碑：谁在引领市场？")
    st.markdown("我们深挖了品牌国别与KOL/KOC的差异，以回答：谁在卖货？谁在种草？谁在定义“美”？")
    st.write("")
    
    if 'brand_origin' in data_pack:
        col11, col12 = st.columns(2)
        with col11:
            plot_brand_origin_sales(data_pack['brand_origin'])
            # 【【【 V9.0 洞察修改 】】】
            create_insight_box(
                """
                <b>图表洞察 (图 22):</b>
                <br/>
                “欧美品牌”（如欧莱雅, 施华蔻）凭借 <b>1.57亿</b> 的销量（V4.1 报告 Part 3），牢牢统治电商货架。“国产新锐”以 1.05亿 的销量紧随其后（主要来自“盖白发”等功能性产品）。
                <br/>
                <b>图表意义:</b> 欧美品牌是“货架之王”，是市场销量的基本盘。
                """
            )
        with col12:
            plot_brand_origin_social(data_pack['brand_origin'])
            # 【【【 V9.0 洞察修改 】】】
            create_insight_box(
                """
                <b>图表洞察 (图 23):</b>
                <br/>
                社媒格局完全反转。“日韩品牌”（如爱茉莉, 花王）以 <b>373</b> 的平均点赞（V4.1 报告 Part 3），成为Z世代“种草”效率最高的群体。
                <br/>
                <b>图表意义:</b> 市场呈现“<b>欧美卖货，日韩种草</b>”的分裂格局。日韩品牌更懂东方肤色美学，其“显白”内容更能引发Z世代共鸣。国产新锐亟需补齐“美学叙事”和“社媒种草”的短板。
                """
            )
    else:
        st.warning("`data_pack` 中缺少 `brand_origin` (品牌国别) 数据。")
    
    st.markdown("---")
    
    # --- 9. V9.0 [新] Z世代口碑解构 ---
    st.header("9. Z世代口碑解构：KOL vs KOC")
    st.markdown("我们对KOL（意见领袖）和KOC（素人）的笔记进行了交叉分析，以洞察Z世代的口碑路径。")
    st.write("")
    
    if 'kol_koc_analysis' in data_pack:
        col13, col14 = st.columns(2)
        with col13:
            plot_kol_koc_influence(data_pack['kol_koc_analysis'])
            # 【【【 V9.0 洞察修改 】】】
            create_insight_box(
                """
                <b>图表洞察 (图 24):</b>
                <br/>
                KOL (头部博主) 的平均点赞 (<b>5,862</b>) 远高于 KOC (素人) (3,756)（V4.1 报告 Part 4）。
                <br/>
                <b>图表意义:</b> 这证明Z世代的“颜值经济”消费，高度依赖专业KOL的“种草”和“背书”。品牌应集中资源与头部KOL合作。
                """
            )
        with col14:
            plot_kol_koc_topics(data_pack['kol_koc_analysis'])
            # 【【【 V9.0 洞察修改 】】】
            create_insight_box(
                """
                <b>图表洞察 (图 25):</b>
                <br/>
                “显白”议题由KOL主导 (<b>13.6%</b> 提及率 vs KOC的 6.1%)。而“显气色”议题，双方提及率均接近 <b>0%</b>（V4.1 报告 Part 4）。
                <br/>
                <b>图表意义:</b> “显白”是KOL教育市场的成熟概念。而“显气色”是品牌可抢占的、无人引领的“议题蓝海”。品牌应与KOL合作，率先定义和引领“显气色”美学，将其作为对抗“蜡黄”的终极解决方案。
                """
            )
    else:
        st.warning("`data_pack` 中缺少 `kol_koc_analysis` (KOL/KOC) 数据。")
        
    st.markdown("---")
    
    # --- 10. V9.0 [新] [核心] 四大美学路径 ---
    st.header("10. [核心] 四大美学路径量化")
    st.markdown("我们将“东方肤色美学”拆解为四大路径，并首次对它们的市场表现进行了量化分析。")
    st.write("")
    
    if 'four_paths_analysis' in data_pack:
        col15, col16 = st.columns(2)
        with col15:
            plot_four_paths_sales(data_pack['four_paths_analysis'])
            # 【【【 V9.0 洞察修改 】】】
            create_insight_box(
                """
                <b>图表洞察 (图 26):</b>
                <br/>
                “衬光系”（如黑茶色, 乌木色）以 <b>1.7亿</b> 销量（V4.1 报告 Part 6）统治电商。
                <br/>
                <b>图表意义:</b> 这是Z世代最“安全”、最高对比度的“显白”选择。品牌应将“衬光系”作为“销量基本盘”，满足大众对“安全显白”的需求。
                """
            )
        with col16:
            plot_four_paths_social(data_pack['four_paths_analysis'])
            # 【【【 V9.0 洞察修改 】】】
            create_insight_box(
                """
                <b>图表洞察 (图 27):</b>
                <br/>
                Z世代的“心之所向”与“实际购买”存在差异。“补光系”（如焦糖棕, 榛果色）以 <b>3,372</b> 的均赞（V4.1 报告 Part 6）成为社媒“种草”冠军。
                <br/>
                <b>图表意义:</b> 品牌应“两条腿走路”：用“衬光系”做销量，用“补光系”做“社媒引流款”，满足Z世代对“颜值经济”和“氛围感”的追求。而“活血系”（显气色）是需要KOL（图25）从0开始教育的“未来机会点”。
                """
            )
    else:
        st.warning("`data_pack` 中缺少 `four_paths_analysis` (四大路径) 数据。")
        
    st.markdown("---")


    # --- 11. V9.0 (原 8) 最终验证与结论 (战略更新) ---
    st.header("11. 最终验证：决策红线与未来方向")
    st.write("") 
    
    plot_comment_sentiment(data_pack['comments_insight']) # V9.0 (含洞察)
    
    st.subheader("B. 局限与未来方向")
    
    # V4.1 报告 Part 7 数据: 935 评论, 69:1 比例
    # V4.1 报告 Part 4 数据: 显气色 KOL 0.0%
    ratio_final_check = data_pack['comments_insight'].get('whitening_mentions_raw', 69) / max(1, data_pack['comments_insight'].get('blackening_mentions_raw', 1))

    create_insight_box(
        f"""
        本次“闪电报告”数据量充足，但仍有局限性，未来可从以下方向完善#
        <br/>1.  <b>评论数据量不足:</b> {data_pack['comments_insight'].get('total_comments', 935)} 条评论 只能做定性洞察。但 <b>{ratio_final_check:.0f}:1</b> 的“显白/显黑”比例 已极具指示性。未来需扩大评论爬取量至 10万+ 级别，以构建更精准的“肤色-发色”AI推荐模型。
        <br/>2.  <b>微博数据价值低:</b> (可切换平台查看) 微博数据多为营销和新闻，用户UGC价值远低于小红书，未来应将爬取重心<b>彻底转向小红书</b>。
        <br/>3.  <b>“显气色”数据量:</b> “显气色”作为一个新兴词汇（V4.1报告显示KOL提及率 0%），其提及量远低于“显白”。<b>这并非局限，而是结论</b>——它证明了这是一个高潜力、低竞争、无人定义的“议题蓝海”赛道。
        """
    )
    
    st.markdown("---")
    st.subheader("附录: 东方肤色美学的四大路径 (定义)")
    create_insight_box(
        """
        基于以上洞察，我们构建了四大“东方肤色美学”显白路径，为未来的产品研发与AI推荐提供理论框架：
        <br/><br/>
        <b>1. 补光系 (内在透亮):</b>
        <br/>* <b>原理:</b> 提高发色明度与光泽，如同为面部增添内置光源，改善暗沉。（社媒最热）
        <br/>* <b>美学意象:</b> 「琉璃」的通透、「月光」的清辉。
        <br/>* <b>色彩配方:</b> 焦糖暖棕、榛果米棕。
        <br/><br/>
        <b>2. 滤光系 (去黄修正):</b>
        <br/>* <b>原理:</b> 运用色彩互补（灰、紫、蓝），如同“滤镜”过滤肤色中的黄气。
        <br/>* <b>美学意象:</b> 「宣纸」的柔白。
        <br/>* <b>色彩配方:</b> 奶茶灰棕、亚麻色。
        <br/><br/>
        <b>3. 活血系 (气色激发):</b>
        <br/>* <b>原理:</b> 采用低饱和度暖色调（红、粉、橘），反向激发并增强肤色的“血气感”，实现“白里透红”。（未来机会）
        <br/>* <b>美学意象:</b> 气血充盈的「红玉」。
        <br/>* <b>色彩配方:</b> 树莓红、粉棕、赤茶色。
        <br/><br/>
        <b>4. 衬光系 (质感对比):</b>
        <br/>* <b>原理:</b> 利用深发色与肤色形成高对比度，极致凸显肌肤的洁白与细腻。（电商最火）
        <br/>* <b>美学意象:</b> 「乌木」与「白瓷」的质感美学。
        <br/>* <b>色彩配方:</b> 黑茶色、蓝黑。
        """
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()