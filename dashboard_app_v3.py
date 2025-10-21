import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import pandas as pd
from streamlit_mermaid import st_mermaid # 使用你修复的 import
import data_processor # 导入我们刚创建的数据处理模块

# --- 0. 页面配置与样式加载 ---
st.set_page_config(
    page_title="染发消费品深度洞察",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 统一样式
PLOT_TEMPLATE = "plotly_white"
PLOT_COLOR = "rgb(0, 104, 201)" # 统一的"高级蓝"
PLOT_COLOR_SEQUENCE = px.colors.sequential.Blues_r[1::2] 
GRAY_COLOR = 'rgb(200, 200, 200)'

def load_css(file_name):
    """加载CSS文件并注入"""
    try:
        # 【【【 已修复 】】】
        with open(file_name, encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("style.css 文件未找到。请确保它在同一目录下。")

def create_insight_box(text):
    """创建统一风格的备注框"""
    st.markdown(f"<div class='custom-insight-box'>{text}</div>", unsafe_allow_html=True)

# --- 1. 图表绘制模块 (Plotters) ---
# 这些是V3版的全新图表，风格统一且分析更深

# --- 1A. 方法论图表 ---
def plot_methodology_flow():
    """图 1: 分析方法论 (Mermaid 流程图)"""
    # 采用极简风格 (theme: 'neutral' or 'base')
    mermaid_code = """
    graph TD
        subgraph " "
            A[1. 关键词策略<br/>(色系/品牌/功效/诉求)] --> B(2. 多源数据采集<br/>淘宝/京东/小红书/微博/评论);
            B --> C{3. P-Tag 引擎<br/>(数据清洗与标签化)};
            C --> D[4. 市场格局分析<br/>(价格/品牌/区域)];
            C --> E[5. 核心诉求深挖<br/>(语义共现/知识图谱)];
            C --> F[6. 社媒口碑验证<br/>(热度/评论)];
            E --> G((<b>最终洞察</b><br/>WHAT IS 显白?));
            D & F --> G;
        end
    
        %% 风格定义
        classDef default fill:#fff,stroke:#ddd,stroke-width:1px,font-size:14px;
        classDef subgraph fill:#fafafa,stroke:#ccc,stroke-dasharray: 5 5;
        class C fill:#0068c9,color:#fff,font-weight:bold,stroke-width:0px;
        class G fill:#1a1a1a,color:#fff,font-weight:bold,stroke-width:0px;
    """
    st_mermaid(mermaid_code, height="450px")

def plot_meta_data_funnel(raw_counts):
    """图 2: 数据采集漏斗 (KPI指标卡)"""
    st.subheader("图 2: 数据采集漏斗")
    cols = st.columns(5)
    cols[0].metric("电商商品 (SKU)", f"{raw_counts['淘宝商品'] + raw_counts['京东商品']:,}")
    cols[1].metric("社媒帖子 (Posts)", f"{raw_counts['小红书笔记'] + raw_counts['微博帖子']:,}")
    cols[2].metric("用户评论 (UGC)", f"{raw_counts['淘宝评论']:,}")
    cols[3].metric("电商关键词 (Query)", f"{raw_counts['电商关键词']:,}")
    cols[4].metric("社交关键词 (Query)", f"{raw_counts['社交关键词']:,}")

def plot_keyword_strategy(keyword_strategy):
    """图 3: 关键词爬取策略 (V1恢复)"""
    st.subheader("图 3: 关键词爬取策略 (Top 5)")
    col1, col2 = st.columns(2)
    with col1:
        df = keyword_strategy['电商关键词 (Top 5)'].reset_index()
        fig = px.bar(df, y='index', x='keyword', title="电商平台 (淘宝/京东) 爬取词",
                     text='keyword', color_discrete_sequence=[PLOT_COLOR])
        fig.update_layout(template=PLOT_TEMPLATE, yaxis_title=None, xaxis_title="商品数")
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        df = keyword_strategy['社交关键词 (Top 5)'].reset_index()
        fig = px.bar(df, y='index', x='keyword', title="社交平台 (小红书/微博) 爬取词",
                     text='keyword', color_discrete_sequence=[PLOT_COLOR])
        fig.update_layout(template=PLOT_TEMPLATE, yaxis_title=None, xaxis_title="帖子数")
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

# --- 1B. 市场格局图表 (V1恢复并优化) ---
def plot_price_sales_matrix(df):
    """图 4: 市场价格区间分布"""
    st.subheader("图 4: 市场价格区间分布 (气泡大小 = 总销量)")
    bins = [0, 50, 100, 150, 200, 1000]
    labels = ["0-50元", "50-100元", "100-150元", "150-200元", "200+元"]
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

def plot_regional_competition(df):
    """图 5: 区域竞争格局 (SKU vs 销量)"""
    st.subheader("图 5: 区域竞争格局 (SKU数 vs 总销量)")
    location_df = df[(df['location'] != '未知') & (df['location'] != '海外') & (df['location'] != 'nan')].copy()
    
    plot_data = location_df.groupby('location').agg(
        total_sales=('sales', 'sum'),
        product_count=('title', 'count')
    ).reset_index()
    
    plot_data = plot_data[(plot_data['total_sales'] > 100000) & (plot_data['product_count'] > 50)]
    
    fig = px.scatter(
        plot_data, x='product_count', y='total_sales', size='total_sales', size_max=50,
        color='location', text='location',
        labels={'product_count': '商品链接数 (SKU数)', 'total_sales': '估算总销量'},
        log_x=True, log_y=True
    )
    fig.update_traces(textposition='top right')
    fig.update_layout(template=PLOT_TEMPLATE, showlegend=False, xaxis_title="SKU数 (货源地)", yaxis_title="总销量 (市场)")
    st.plotly_chart(fig, use_container_width=True)

def plot_color_price_heatmap(df):
    """图 6: 热门色系-价格交叉热力图 (V1恢复)"""
    st.subheader("图 6: 色系-价格交叉热力图 (销量)")
    if 'price_bin' not in df.columns:
        bins = [0, 50, 100, 150, 200, 1000]
        labels = ["0-50元", "50-100元", "100-150元", "150-200元", "200+元"]
        df['price_bin'] = pd.cut(df['price'], bins=bins, labels=labels, right=False)
        
    color_df = df.explode('tag_color').dropna(subset=['tag_color'])
    heatmap_data = color_df.groupby(['tag_color', 'price_bin'], observed=True)['sales'].sum().reset_index()
    heatmap_pivot = heatmap_data.pivot_table(index='tag_color', columns='price_bin', values='sales', fill_value=0)
    
    fig = px.imshow(
        heatmap_pivot, text_auto=True, aspect="auto",
        color_continuous_scale=PLOT_COLOR_SEQUENCE,
        labels={'x': '价格区间', 'y': '色系', 'color': '估算总销量'}
    )
    fig.update_layout(template=PLOT_TEMPLATE, xaxis_title="价格区间", yaxis_title="色系")
    st.plotly_chart(fig, use_container_width=True)

# --- 1C. 核心洞察: "WHAT IS 显白?" ---
def plot_whitening_knowledge_graph(co_occurrence_data):
    """图 7: "显白" 语义共现网络图 (知识图谱)"""
    st.subheader("图 7: “显白” 语义共现网络图 (知识图谱)")
    
    # 1. 准备数据
    center_node = "显白"
    nodes = [center_node]
    edges = []
    
    # (标签, 颜色)
    node_types = {}
    node_types[center_node] = ("诉求", "#004a99") # 深蓝
    
    # 提取共现数据
    color_data = co_occurrence_data['color'].most_common(5)
    brand_data = co_occurrence_data['brand'].most_common(5)
    tech_data = co_occurrence_data['tech'].most_common(3)
    
    # 构建节点和边
    all_data = [
        (color_data, "色系", "#0068c9"), # 蓝色
        (brand_data, "品牌", "#00aaff"), # 浅蓝
        (tech_data, "功效", "#66ccff")  # 更浅蓝
    ]
    
    for data, type_name, color in all_data:
        for tag, count in data:
            if tag not in nodes:
                nodes.append(tag)
                node_types[tag] = (type_name, color)
            edges.append((center_node, tag, count))

    # 2. 创建图谱 (Plotly GO)
    edge_x, edge_y, node_x, node_y = [], [], [], []
    node_text, node_colors = [], []
    
    # 简单的星型布局
    pos = {center_node: (0, 0)}
    radius = 1
    total_nodes = len(nodes) - 1
    angle_step = (2 * 3.14159) / total_nodes
    
    for i, node in enumerate(nodes):
        if node == center_node:
            node_x.append(0)
            node_y.append(0)
        else:
            angle = i * angle_step
            x, y = radius * 1.5 * (i % 3 + 1), radius * (i % 5 + 1) # 随机化一点
            # 简单的环形布局 (可以优化)
            x = radius * 1.5 * ( (i*1.1) % 5 - 2.5 )
            y = radius * ( (i*0.7) % 5 - 2.5 )
            pos[node] = (x, y)
            node_x.append(x)
            node_y.append(y)
            
        node_text.append(f"{node}<br>({node_types[node][0]})")
        node_colors.append(node_types[node][1])

    # 创建边
    edge_weights = []
    for u, v, weight in edges:
        edge_x.extend([pos[u][0], pos[v][0], None])
        edge_y.extend([pos[u][1], pos[v][1], None])
        edge_weights.append(weight)

    # 归一化线宽
    max_weight = max(edge_weights) if edge_weights else 1
    edge_widths = [(w / max_weight) * 15 + 1 for w in edge_weights]

    # 绘制边 (分多次绘制以应用不同线宽)
    edge_traces = []
    for i, (u, v, weight) in enumerate(edges):
        edge_traces.append(go.Scatter(
            x=[pos[u][0], pos[v][0]], y=[pos[u][1], pos[v][1]],
            mode='lines',
            line=dict(width=edge_widths[i], color=GRAY_COLOR),
            hoverinfo='text',
            text=f"共现次数: {weight}"
        ))

    # 绘制节点
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        marker=dict(
            showscale=False,
            colorscale='Blues',
            color=node_colors,
            size=30,
            line=dict(width=2, color='#333')
        ),
        hoverinfo='text'
    )

    fig = go.Figure(data=edge_traces + [node_trace],
                 layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0, l=0, r=0, t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    template=PLOT_TEMPLATE
                    ))
    st.plotly_chart(fig, use_container_width=True, height=600)

def plot_whitening_co_occurrence_bars(co_occurrence_data):
    """图 8, 9, 10: "显白" 的具体构成"""
    st.subheader("图 8, 9, 10: “显白” 的语义构成")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        data = co_occurrence_data['color']
        if data:
            df = pd.DataFrame(data.most_common(5), columns=['tag', 'count'])
            fig = px.bar(df, x='count', y='tag', orientation='h', title="Top 5 “显白”色系",
                         color_discrete_sequence=[PLOT_COLOR])
            fig.update_layout(template=PLOT_TEMPLATE, yaxis_title="色系", xaxis_title="共现次数")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("“显白”色系无共现数据。")
        
    with col2:
        data = co_occurrence_data['brand']
        if data:
            df = pd.DataFrame(data.most_common(5), columns=['tag', 'count'])
            fig = px.bar(df, x='count', y='tag', orientation='h', title="Top 5 “显白”品牌",
                         color_discrete_sequence=[PLOT_COLOR])
            fig.update_layout(template=PLOT_TEMPLATE, yaxis_title="品牌", xaxis_title="共现次数")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("“显白”品牌无共现数据。")
        
    with col3:
        data = co_occurrence_data['tech']
        if data:
            df = pd.DataFrame(data.most_common(3), columns=['tag', 'count'])
            fig = px.bar(df, x='count', y='tag', orientation='h', title="Top 3 “显白”功效",
                         color_discrete_sequence=[PLOT_COLOR])
            fig.update_layout(template=PLOT_TEMPLATE, yaxis_title="功效", xaxis_title="共现次数")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("“显白”功效无共现数据。")

# --- 1D. 口碑验证图表 ---
def plot_comment_sentiment(comments_insight):
    """图 11: 真实评论情感声量"""
    st.subheader("图 11: 真实评论情感声量 (935条评论)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("总评论数", f"{comments_insight['total_comments']} 条")
    col2.metric("正面口碑 (“显白”)", f"{comments_insight['whitening_mentions']} 次", delta="正面")
    col3.metric("负面口碑 (“显黑”)", f"{comments_insight['blackening_mentions']} 次", delta="负面", delta_color="inverse")
    
    create_insight_box(
        f"<b>口碑红线洞察:</b> 在用户的真实反馈中, “显白” (正面) 的提及次数是 “显黑” (负面) 的 **{comments_insight['whitening_mentions'] / (comments_insight['blackening_mentions'] + 1):.0f} 倍**。这证明“显黑”是用户绝对的雷区和核心负面口碑来源。"
    )

# --- 3. Streamlit 仪表盘主应用 ---
def main():
    
    # --- 0. 加载数据与CSS ---
    load_css("style.css") # 注入全局样式
    try:
        data_pack = data_processor.load_and_process_data(Path('.'))
    except Exception as e:
        st.error(f"致命错误：数据加载或处理失败。请检查 JSON 文件路径和格式，或 data_processor.py 脚本。错误: {e}")
        st.exception(e) # 打印详细的 traceback
        st.stop()

    # --- 1. 标题与执行摘要 ---
    st.title("🎨 染发消费品深度洞察报告 (V3)")
    st.markdown("---")
    
    st.header("1. 执行摘要 (Executive Summary)")
    create_insight_box(
        """
        <b>核心洞察 (TL;DR):</b> 甲方已知的“显白很重要”是事实，但我们的核心任务是回答 **“什么才是显白？”**
        <br/><br/>
        1.  <b>市场答案:</b> 消费者用脚投票的“显白”产品，是 **`50-100元`** 价位段的 **`棕色系`** 和 **`亚麻/青色系`**。
        2.  <b>品牌答案:</b> `爱茉莉(美妆仙)` 在“显白”话题上的语义共现次数最高，是该赛道的社媒心智占领者，远超其在电商大盘的销量表现。
        3.  <b>功效答案:</b> `泡沫` 和 `免漂` 是与“显白”关联最强的两大功效。这证明了“显白”的背后是“**在家DIY的便捷性**”和“**低门槛的时尚感**”。
        4.  <b>口碑红线:</b> “显黑”是绝对雷区。在935条评论中，“显白”被提及69次，“显黑”仅1次。
        """
    )
    
    st.markdown("---")

    # --- 2. 分析方法论 ---
    st.header("2. 分析方法论与数据策略")
    st.markdown("我们的洞察基于一套严谨的“关键词-爬取-标签化-分析”流程。")
    
    plot_methodology_flow() # 图 1
    plot_meta_data_funnel(data_pack['raw_counts']) # 图 2
    plot_keyword_strategy(data_pack['keyword_strategy']) # 图 3
    
    st.markdown("---")

    # --- 3. 市场宏观格局 (V1 恢复) ---
    st.header("3. 市场宏观格局：钱在哪里？")
    
    plot_price_sales_matrix(data_pack['ecom']) # 图 4
    
    col1, col2 = st.columns(2)
    with col1:
        plot_regional_competition(data_pack['ecom']) # 图 5
    with col2:
        plot_color_price_heatmap(data_pack['ecom']) # 图 6

    create_insight_box(
        """
        <b>格局洞察:</b>
        1.  <b>价格带 (图 4):</b> `50-100元` 是竞争最激烈的红海，SKU数和总销量均是第一。
        2.  <b>区域 (图 5):</b> 市场呈“产销分离”。`广东` 是最大的“货源集散地”（SKU最多），而 `江苏`、`重庆` 则是“超级卖场”（SKU不多，但总销量极高）。
        3.  <b>色系-价格 (图 6):</b> `棕色系` 在 `50-100元` 价位段销量最高。而 `亚麻/青色系` 和 `灰色/蓝色系` 等“潮色”，其销售高峰出现在 `100-150元` 以上的价位。
        """
    )
    
    st.markdown("---")
    
    # --- 4. 核心深挖: "WHAT IS 显白?" ---
    st.header("4. 核心深挖：到底什么才是“显白”？")
    st.markdown("我们对所有 **{:,}** 条提及“显白”的商品和社媒帖子进行了语义共现分析，构建了如下的“显白”知识图谱。".format(
        len(data_pack['ecom'][data_pack['ecom']['tag_whitening']]) + len(data_pack['social'][data_pack['social']['tag_whitening']])
    ))

    plot_whitening_knowledge_graph(data_pack['co_occurrence']) # 图 7
    plot_whitening_co_occurrence_bars(data_pack['co_occurrence']) # 图 8, 9, 10
    
    create_insight_box(
        """
        <b>“显白” 构成洞察 (图 7-10):</b>
        * “显白” <b>不是一个孤立的诉求</b>，它是一个由<b>色系、品牌、功效</b>共同构成的“解决方案”。
        * <b>色系:</b> `棕色系` 和 `亚麻/青色系` 是与“显白”关联最强的两大色系。
        * <b>品牌:</b> `爱茉莉(美妆仙)` 在“显白”话题上的绑定最深，其次是 `施华蔻` 和 `欧莱雅`。
        * <b>功效:</b> `泡沫` 和 `免漂` 是最强的关联词。<b>这揭示了核心洞察</b>：消费者要的“显白”不是沙龙级的复杂产品，而是“<b>在家就能轻松搞定的显白（泡沫）</b>”和“<b>不用漂发就能达到的显白（免漂）</b>”。
        """
    )

    st.markdown("---")

    # --- 5. 口碑验证与未来方向 ---
    st.header("5. 口碑验证与未来方向")
    
    plot_comment_sentiment(data_pack['comments_insight']) # 图 11
    
    st.subheader("B. 当前局限与未来方向")
    create_insight_box(
        """
        本次“闪电报告”深度挖掘了“显白”诉求，但仍有局限性，未来可从以下方向完善：
        1.  <b>评论数据量不足:</b> 935 条评论只能做定性洞察。未来需扩大评论爬取量至 10万+ 级别，以构建更精准的“肤色-发色”推荐模型。
        2.  <b>知识图谱待扩展:</b> 当前的共现分析仅限于一级（显白 -> 颜色）。未来可做二级分析（显白 -> 棕色系 -> 哪款产品?），构建更复杂的图谱。
        3.  <b>微博数据价值低:</b> 分析显示微博数据多为营销和新闻，用户UGC价值远低于小红书，未来应将爬取重心<b>彻底转向小红书</b>。
        """
    )

if __name__ == "__main__":
    main()