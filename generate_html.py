import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import re
import os
from pathlib import Path
from collections import defaultdict
import logging

# --- 配置 ---
# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 1. 核心关键词定义 (P-Tag Engine) ---
# 这是我们分析的核心。我将使用你脚本中提供的关键词库，并补充品牌词。

# 品牌关键词
# 注意：键(key)是我们要打的标签，值(value)是搜索用的词根
BRAND_KEYWORDS = {
    "欧莱雅": ["欧莱雅"],
    "施华蔻": ["施华蔻"],
    "花王": ["花王", "Liese", "liese", "莉婕"],
    "爱茉莉": ["爱茉莉", "amore", "美妆仙"],
    "章华": ["章华"],
    "卡尼尔": ["卡尼尔"],
    "迪彩": ["迪彩"],
    "美源": ["美源", "Bigen"],
    "利尻昆布": ["利尻昆布", "Rishiri"],
    "三橡树": ["三橡树", "3 CHÊNES"],
}

# 显白关键词
WHITENING_KEYWORDS = ["显白", "黄皮", "肤色", "亲妈", "天菜", "素颜", "提亮", "去黄", "衬肤"]

# 色系分类 (来自你的脚本)
COLOR_CATEGORIES = {
    "棕色系": ["棕", "茶", "摩卡", "巧", "奶茶", "蜜", "焦糖", "栗", "咖啡", "可可"],
    "红色/橘色系": ["红", "橘", "玫瑰", "酒红", "莓", "樱", "石榴", "番茄", "辣椒", "枫叶", "脏橘"],
    "亚麻/青色系": ["亚麻", "青", "闷青", "灰绿", "橄榄", "抹茶", "薄荷", "牛油果"],
    "灰色/蓝色/紫色系": ["灰", "蓝", "紫", "芋泥", "烟灰", "雾霾", "宝蓝", "葡萄", "香芋", "蓝黑"],
    "金色/浅色系": ["金", "白金", "米金", "浅金", "香槟", "砂金", "铂金", "漂", "浅色"],
    "高饱和色系": ["潮色", "霓虹", "荧光", "女团", "动漫", "海王", "湄拉", "芭比", "电光"]
}

# 功效/技术关键词 (来自你的脚本和关键词列表)
TECH_KEYWORDS = {
    "植物": ["植物", "植萃"],
    "无氨": ["无氨", "温和"],
    "泡沫": ["泡沫", "泡泡"],
    "盖白发": ["盖白", "遮白"],
    "免漂": ["免漂", "无需漂"],
    "护理": ["护理", "护发", "不伤发", "焗油"],
}


# --- 2. 数据加载与清洗模块 (Loaders) ---

def clean_price(price_str):
    """从价格字符串中提取数字"""
    if not isinstance(price_str, str):
        return float(price_str) if isinstance(price_str, (int, float)) else 0.0
    
    match = re.search(r'(\d+\.?\d*)', price_str)
    return float(match.group(1)) if match else 0.0

def clean_sales(sales_str):
    """
    将 '100+人付款', '10万+', '1000+' 这样的字符串统一转换为整数。
    京东的 '评价人数' 和 淘宝的 '付款人数' 在这里统一处理。
    """
    if not isinstance(sales_str, str):
        return int(sales_str) if isinstance(sales_str, (int, float)) else 0
    
    number_part = re.search(r'(\d+\.?\d*)', sales_str)
    if not number_part:
        return 0
    
    num = float(number_part.group(1))
    
    if '万' in sales_str:
        return int(num * 10000)
    
    return int(num)

def load_ecommerce_data(tb_files, jd_file):
    """加载、合并、清洗并统一化淘宝和京东的数据"""
    logging.info("开始加载电商数据...")
    all_dfs = []

    # 1. 加载淘宝数据
    for f in tb_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                tb_data = json.load(file)
            df = pd.DataFrame(tb_data)
            all_dfs.append(df)
            logging.info(f"成功加载淘宝文件: {f}, 记录数: {len(df)}")
        except Exception as e:
            logging.warning(f"加载淘宝文件 {f} 失败: {e}")
            
    tb_df = pd.concat(all_dfs, ignore_index=True)
    
    # 2. 加载京东数据
    try:
        with open(jd_file, 'r', encoding='utf-8') as file:
            jd_data = json.load(file)
        jd_df = pd.DataFrame(jd_data)
        logging.info(f"成功加载京东文件: {jd_file}, 记录数: {len(jd_df)}")
    except Exception as e:
        logging.error(f"加载京东文件 {jd_file} 失败: {e}")
        jd_df = pd.DataFrame() # 创建空的，以防失败

    # 3. 统一化字段 (最关键的一步)
    # 'title', 'price', 'sales', 'platform'
    tb_df_unified = pd.DataFrame({
        'title': tb_df['产品名称'],
        'price': tb_df['产品价格'].apply(clean_price),
        'sales': tb_df['付款人数'].apply(clean_sales),
        'platform': 'Taobao'
    })
    
    jd_df_unified = pd.DataFrame({
        'title': jd_df['商品名称'],
        'price': jd_df['价格'].apply(clean_price),
        'sales': jd_df['评价人数'].apply(clean_sales), # 注意：京东是评价人数
        'platform': 'JD'
    })
    
    # 4. 合并
    ecommerce_df = pd.concat([tb_df_unified, jd_df_unified], ignore_index=True)
    
    # 5. 清洗
    ecommerce_df = ecommerce_df.dropna(subset=['title'])
    ecommerce_df = ecommerce_df[ecommerce_df['price'] > 0] # 移除价格为0的
    ecommerce_df = ecommerce_df[ecommerce_df['sales'] > 10] # 移除销量过低的（噪声）
    
    logging.info(f"电商数据加载并统一化完毕。总记录数: {len(ecommerce_df)}")
    return ecommerce_df

def load_social_data(xhs_files, weibo_file):
    """加载、合并、清洗并统一化小红书和微博的数据"""
    logging.info("开始加载社交数据...")
    all_dfs = []
    
    # 1. 加载小红书
    for f in xhs_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                xhs_data = json.load(file)
            df = pd.DataFrame(xhs_data)
            all_dfs.append(df)
            logging.info(f"成功加载小红书文件: {f}, 记录数: {len(df)}")
        except Exception as e:
            logging.warning(f"加载小红书文件 {f} 失败: {e}")
            
    xhs_df = pd.concat(all_dfs, ignore_index=True)
    
    # 2. 加载微博
    try:
        with open(weibo_file, 'r', encoding='utf-8') as file:
            weibo_data = json.load(file)
        weibo_df = pd.DataFrame(weibo_data)
        logging.info(f"成功加载微博文件: {weibo_file}, 记录数: {len(weibo_df)}")
    except Exception as e:
        logging.error(f"加载微博文件 {weibo_file} 失败: {e}")
        weibo_df = pd.DataFrame()
        
    # 3. 统一化字段
    # 'title', 'likes', 'platform'
    xhs_df_unified = pd.DataFrame({
        'title': xhs_df['标题'],
        'likes': xhs_df['点赞数'].apply(clean_sales), # 复用clean_sales转数字
        'platform': 'XHS'
    })
    
    weibo_df_unified = pd.DataFrame({
        'title': weibo_df['博文内容'],
        'likes': weibo_df['点赞数'].apply(clean_sales), # 统一用点赞数
        'platform': 'Weibo'
    })
    
    # 4. 合并
    social_df = pd.concat([xhs_df_unified, weibo_df_unified], ignore_index=True)
    
    # 5. 清洗 (最重要：过滤噪声)
    social_df = social_df.dropna(subset=['title'])
    # 基础清洗：必须包含“染发”或“发色”或品牌词，否则视为噪声
    core_words = r'染发|发色|染了|染头|' + '|'.join(BRAND_KEYWORDS.keys())
    social_df = social_df[social_df['title'].str.contains(core_words, na=False, case=False)]
    
    logging.info(f"社交数据加载并清洗完毕。有效记录数: {len(social_df)}")
    return social_df


# --- 3. 数据处理模块 (P-Tag Engine) ---

def apply_tags_to_dataframe(df, title_col='title'):
    """
    对DataFrame的标题列应用所有关键词标签，
    返回一个包含新标签列的新DataFrame。
    """
    logging.info(f"开始为 {len(df)} 条记录打标签...")
    tagged_df = df.copy()
    
    # 初始化标签列表
    brand_tags = []
    color_tags = []
    tech_tags = []
    whitening_tags = []
    
    # 转换为小写以便匹配
    titles = tagged_df[title_col].str.lower().astype(str)
    
    for title in titles:
        current_brand = "Other"
        current_colors = []
        current_techs = []
        current_whitening = "Not Mentioned"
        
        # 1. 匹配品牌 (找到一个即停止)
        for tag, keywords in BRAND_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in title:
                    current_brand = tag
                    break
            if current_brand != "Other":
                break
        
        # 2. 匹配色系 (可多选)
        for tag, keywords in COLOR_CATEGORIES.items():
            for kw in keywords:
                if kw.lower() in title:
                    current_colors.append(tag)
                    break # 匹配到一个色系即跳到下一个色系
                    
        # 3. 匹配功效 (可多选)
        for tag, keywords in TECH_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in title:
                    current_techs.append(tag)
                    break # 匹配到一个功效即跳到下一个
        
        # 4. 匹配显白
        for kw in WHITENING_KEYWORDS:
            if kw.lower() in title:
                current_whitening = "显白相关"
                break
                
        brand_tags.append(current_brand)
        # 如果没有匹配到色系，给一个 "未明确" 标签
        color_tags.append(current_colors if current_colors else ["未明确色系"])
        tech_tags.append(current_techs if current_techs else ["基础款"])
        whitening_tags.append(current_whitening)
        
    tagged_df['tag_brand'] = brand_tags
    tagged_df['tag_color'] = color_tags
    tagged_df['tag_tech'] = tech_tags
    tagged_df['tag_whitening'] = whitening_tags
    
    logging.info("打标签完成。")
    return tagged_df


# --- 4. 可视化图表生成模块 (Plotters) ---
# 每一张图表都封装成一个独立的函数

def plot_price_sales_matrix(df, output_dir):
    """
    图表 1.1：染发剂市场价格区间分布（销量-商品数矩阵）
    气泡图: X=价格区间, Y=商品数, Size=总销量
    """
    logging.info("生成图表 1.1：价格销量矩阵...")
    try:
        # 1. 创建价格区间
        bins = [0, 50, 100, 150, 200, 300, 1000]
        labels = ["0-50元", "50-100元", "100-150元", "150-200元", "200-300元", "300+元"]
        df['price_bin'] = pd.cut(df['price'], bins=bins, labels=labels, right=False)
        
        # 2. 按价格区间聚合
        plot_data = df.groupby('price_bin').agg(
            total_sales=('sales', 'sum'),
            product_count=('title', 'count')
        ).reset_index()
        
        # 3. 绘图
        fig = px.scatter(
            plot_data,
            x='price_bin',
            y='product_count',
            size='total_sales',
            size_max=80, # 控制气泡最大尺寸
            color='price_bin',
            text='price_bin',
            title='图 1.1: 市场价格区间分布 (气泡大小 = 总销量)',
            labels={'price_bin': '价格区间', 'product_count': '商品链接数 (SKU数)', 'total_sales': '估算总销量'}
        )
        fig.update_traces(textposition='top center')
        fig.update_layout(xaxis_title='价格区间', yaxis_title='商品链接数 (SKU数)')
        
        # 4. 保存
        outfile = output_dir / "1_price_sales_matrix.html"
        fig.write_html(outfile)
        logging.info(f"图表 1.1 已保存至 {outfile}")
        
    except Exception as e:
        logging.error(f"生成图表 1.1 失败: {e}")

def plot_brand_top10(df, output_dir):
    """
    图表 1.2：T-J平台热销品牌销量TOP 10
    横向条形图
    """
    logging.info("生成图表 1.2：热销品牌 TOP 10...")
    try:
        # 1. 按品牌聚合
        brand_data = df.groupby('tag_brand')['sales'].sum().reset_index()
        
        # 2. 过滤掉 "Other"
        brand_data = brand_data[brand_data['tag_brand'] != 'Other']
        
        # 3. 排序取Top 10
        top_10_brands = brand_data.nlargest(10, 'sales').sort_values('sales', ascending=True)
        
        # 4. 绘图
        fig = px.bar(
            top_10_brands,
            x='sales',
            y='tag_brand',
            orientation='h',
            title='图 1.2: 主流品牌估算总销量 TOP 10',
            labels={'tag_brand': '品牌', 'sales': '估算总销量'},
            text='sales'
        )
        fig.update_traces(texttemplate='%{text:.2s}') # 格式化文本, e.g., 5.0M
        fig.update_layout(yaxis_title='品牌', xaxis_title='估算总销量')
        
        # 5. 保存
        outfile = output_dir / "2_brand_top10.html"
        fig.write_html(outfile)
        logging.info(f"图表 1.2 已保存至 {outfile}")
        
    except Exception as e:
        logging.error(f"生成图表 1.2 失败: {e}")

def plot_color_share_donut(df, output_dir):
    """
    图表 2.1：主流色系市场销量占比
    环形图
    """
    logging.info("生成图表 2.1：主流色系销量占比...")
    try:
        # 1. "Explode" 列表，因为一个产品可以有多个色系
        color_df = df.explode('tag_color')
        
        # 2. 聚合
        color_data = color_df.groupby('tag_color')['sales'].sum().reset_index()
        
        # 3. 绘图
        fig = px.pie(
            color_data,
            names='tag_color',
            values='sales',
            title='图 2.1: 主流色系市场销量占比',
            hole=0.4 # 环形图
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        
        # 4. 保存
        outfile = output_dir / "3_color_share_donut.html"
        fig.write_html(outfile)
        logging.info(f"图表 2.1 已保存至 {outfile}")
        
    except Exception as e:
        logging.error(f"生成图表 2.1 失败: {e}")

def plot_efficacy_bubble(df, output_dir):
    """
    图表 2.2：核心功效诉求市场表现（销量 vs 均价）
    气泡图: X=总销量, Y=平均价格, Size=商品数
    """
    logging.info("生成图表 2.2：核心功效诉求气泡图...")
    try:
        # 1. "Explode" 功效标签
        tech_df = df.explode('tag_tech')
        
        # 2. 聚合
        tech_data = tech_df.groupby('tag_tech').agg(
            total_sales=('sales', 'sum'),
            avg_price=('price', 'mean'), # 用均价
            product_count=('title', 'count')
        ).reset_index()
        
        # 3. 过滤掉 "基础款"
        tech_data = tech_data[tech_data['tag_tech'] != '基础款']
        
        # 4. 绘图
        fig = px.scatter(
            tech_data,
            x='total_sales',
            y='avg_price',
            size='product_count',
            color='tag_tech',
            text='tag_tech',
            size_max=80,
            title='图 2.2: 核心功效诉求市场表现 (气泡大小 = 商品数)',
            labels={'total_sales': '估算总销量', 'avg_price': '平均价格 (元)', 'product_count': '商品链接数', 'tag_tech': '功效标签'}
        )
        fig.update_traces(textposition='top center')
        
        # 5. 保存
        outfile = output_dir / "4_efficacy_bubble.html"
        fig.write_html(outfile)
        logging.info(f"图表 2.2 已保存至 {outfile}")

    except Exception as e:
        logging.error(f"生成图表 2.2 失败: {e}")

def plot_color_price_heatmap(df, output_dir):
    """
    图表 2.3：热门色系-价格交叉热力图
    热力图: X=价格区间, Y=色系, Color=总销量
    """
    logging.info("生成图表 2.3：色系-价格热力图...")
    try:
        # 1. 确保有价格区间 (复用图1.1的)
        if 'price_bin' not in df.columns:
            bins = [0, 50, 100, 150, 200, 300, 1000]
            labels = ["0-50元", "50-100元", "100-150元", "150-200元", "200-300元", "300+元"]
            df['price_bin'] = pd.cut(df['price'], bins=bins, labels=labels, right=False)
            
        # 2. "Explode" 色系
        color_df = df.explode('tag_color')
        
        # 3. 聚合
        heatmap_data = color_df.groupby(['tag_color', 'price_bin'])['sales'].sum().reset_index()
        
        # 4. 转换为矩阵 (Pivot)
        heatmap_pivot = heatmap_data.pivot_table(
            index='tag_color', 
            columns='price_bin', 
            values='sales',
            fill_value=0 # 填充空值为0
        )
        
        # 5. 绘图
        fig = px.imshow(
            heatmap_pivot,
            text_auto=True, # 自动在格子上显示数值
            aspect="auto", # 自动调整宽高比
            color_continuous_scale='Reds', # 色阶
            title='图 2.3: 热门色系-价格交叉热力图 (销量)',
            labels={'x': '价格区间', 'y': '色系', 'color': '估算总销量'}
        )
        
        # 6. 保存
        outfile = output_dir / "5_color_price_heatmap.html"
        fig.write_html(outfile)
        logging.info(f"图表 2.3 已保存至 {outfile}")

    except Exception as e:
        logging.error(f"生成图表 2.3 失败: {e}")

def plot_social_interest_treemap(social_df, output_dir):
    """
    图表 3.1：社媒热门色系兴趣度
    矩形树图
    """
    logging.info("生成图表 3.1：社媒热门色系兴趣度...")
    try:
        # 1. "Explode" 色系
        color_df = social_df.explode('tag_color')
        
        # 2. 聚合
        color_data = color_df.groupby('tag_color')['likes'].sum().reset_index()
        
        # 3. 绘图
        fig = px.treemap(
            color_data,
            path=[px.Constant("全平台"), 'tag_color'], # 创建层级
            values='likes',
            color='likes',
            color_continuous_scale='Blues',
            title='图 3.1: 社媒热门色系兴趣度 (总点赞数)',
            labels={'likes': '总点赞数', 'tag_color': '色系'}
        )
        fig.update_traces(textinfo="label+value+percent root")
        
        # 4. 保存
        outfile = output_dir / "6_social_color_treemap.html"
        fig.write_html(outfile)
        logging.info(f"图表 3.1 已保存至 {outfile}")
        
    except Exception as e:
        logging.error(f"生成图表 3.1 失败: {e}")


# --- 5. 主执行函数 (Orchestrator) ---

def main():
    """主函数，用于调度所有步骤"""
    
    # --- 0. 定义文件路径和输出目录 ---
    base_dir = Path('.')
    output_dir = base_dir / "output_charts"
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 根据你的报告定义文件路径
    tb_files = [
        base_dir / "淘宝商品目录/淘宝网-商品列表页采集【网站反爬请查阅注意事项】.json",
        base_dir / "淘宝商品目录/淘宝网-商品列表页采集【网站反爬请查阅注意事项】-2.json"
    ]
    jd_file = base_dir / "京东-商品搜索.json"
    
    xhs_files = [
        base_dir / "小红书-关键词笔记采集.json",
        base_dir / "小红书-关键词笔记采集2.json"
    ]
    weibo_file = base_dir / "微博搜索关键词采集.json"
    
    # --- 1. 加载数据 ---
    logging.info("--- 步骤 1: 加载数据 ---")
    ecommerce_df = load_ecommerce_data(tb_files, jd_file)
    social_df = load_social_data(xhs_files, weibo_file)
    
    # --- 2. 处理和打标签 ---
    logging.info("--- 步骤 2: 处理数据 (打标签) ---")
    tagged_ecommerce_df = apply_tags_to_dataframe(ecommerce_df, title_col='title')
    tagged_social_df = apply_tags_to_dataframe(social_df, title_col='title')
    
    # (可选) 保存已处理的数据，方便调试
    tagged_ecommerce_df.to_csv(output_dir / "tagged_ecommerce_data.csv", index=False)
    tagged_social_df.to_csv(output_dir / "tagged_social_data.csv", index=False)

    # --- 3. 生成所有可视化图表 ---
    logging.info("--- 步骤 3: 生成可视化图表 ---")
    
    # 电商数据图表
    plot_price_sales_matrix(tagged_ecommerce_df, output_dir)
    plot_brand_top10(tagged_ecommerce_df, output_dir)
    plot_color_share_donut(tagged_ecommerce_df, output_dir)
    plot_efficacy_bubble(tagged_ecommerce_df, output_dir)
    plot_color_price_heatmap(tagged_ecommerce_df, output_dir)
    
    # 社交数据图表
    plot_social_interest_treemap(tagged_social_df, output_dir)
    
    logging.info("--- 全部完成！ ---")
    logging.info(f"所有图表已生成在 '{output_dir.resolve()}' 文件夹中。")

if __name__ == "__main__":
    main()