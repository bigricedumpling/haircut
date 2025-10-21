import pandas as pd
import json
import re
from pathlib import Path
from collections import Counter, defaultdict
import logging

# --- 配置 ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- 1. 核心关键词定义 (复用我们之前的成果) ---
# (这里我们只定义分析评论和"显白"相关的)

# 显白关键词
WHITENING_KEYWORDS = ["显白", "黄皮", "肤色", "亲妈", "天菜", "素颜", "提亮", "去黄", "衬肤"]

# 评论情感分析词典
COMMENT_SENTIMENT_KEYWORDS = {
    "positive_general": ["好用", "不错", "推荐", "喜欢", "满意", "回购", "值得"],
    "positive_color": ["显白", "好看", "颜色正", "黄皮", "爱了", "提亮"],
    "negative_general": ["踩雷", "难用", "失望", "别买", "垃圾", "智商税"],
    "negative_color": ["显黑", "不显白", "荧光", "芭比", "村", "难看", "不适合黄皮"]
}

# --- 2. 数据加载模块 (使用你的盘点报告中的准确路径) ---

def load_data(base_dir):
    """加载所有核心数据源"""
    data = {}
    
    # 1. 淘宝
    tb_files = [
        base_dir / "淘宝商品目录/淘宝网-商品列表页采集【网站反爬请查阅注意事项】.json",
        base_dir / "淘宝商品目录/淘宝网-商品列表页采集【网站反爬请查阅注意事项】-2.json"
    ]
    tb_dfs = [pd.read_json(f) for f in tb_files if f.exists()]
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
    data["xhs"] = pd.concat(xhs_dfs, ignore_index=True) if xhs_dfs else pd.DataFrame()

    # 4. 微博
    weibo_file = base_dir / "微博搜索关键词采集.json"
    data["weibo"] = pd.read_json(weibo_file) if weibo_file.exists() else pd.DataFrame()

    # 5. 淘宝评论
    comment_file = base_dir / "淘宝商品评论【网站反爬请查阅注意事项】.json"
    data["comments"] = pd.read_json(comment_file) if comment_file.exists() else pd.DataFrame()

    logging.info("所有数据加载完毕。")
    return data

# --- 3. 分析模块 ---

def clean_sales(sales_str):
    """统一付款人数/评价人数"""
    if not isinstance(sales_str, str):
        return int(sales_str) if isinstance(sales_str, (int, float)) else 0
    number_part = re.search(r'(\d+\.?\d*)', sales_str)
    if not number_part: return 0
    num = float(number_part.group(1))
    if '万' in sales_str: return int(num * 10000)
    return int(num)

def analyze_meta_data(data):
    """
    进行元分析 (你要求的，关于爬取过程本身的分析)
    """
    print_header("Part 1: 元数据分析 (数据源与关键词)")
    
    # 1. 数据量总览
    print(f"  - 淘宝商品 (Taobao) 总计: {len(data['tb'])} 条")
    print(f"  - 京东商品 (JD) 总计: {len(data['jd'])} 条")
    print(f"  - 小红书笔记 (XHS) 总计: {len(data['xhs'])} 条")
    print(f"  - 微博帖子 (Weibo) 总计: {len(data['weibo'])} 条")
    print(f"  - 淘宝评论 (Comments) 总计: {len(data['comments'])} 条")
    print("-" * 30)
    
    # 2. 爬取关键词分析 (从数据中反推)
    if "关键词" in data['tb'].columns:
        print("  - 淘宝爬取关键词词频 Top 10:")
        tb_keywords = data['tb']['关键词'].value_counts().head(10)
        for k, v in tb_keywords.items():
            print(f"    - {k}: {v} 条")
            
    if "搜索关键词" in data['jd'].columns:
        print("\n  - 京东爬取关键词词频 Top 10:")
        jd_keywords = data['jd']['搜索关键词'].value_counts().head(10)
        for k, v in jd_keywords.items():
            print(f"    - {k}: {v} 条")

    if "搜索词" in data['xhs'].columns:
        print("\n  - 小红书爬取关键词词频 Top 10:")
        xhs_keywords = data['xhs']['搜索词'].value_counts().head(10)
        for k, v in xhs_keywords.items():
            print(f"    - {k}: {v} 条")

def analyze_regional_data(tb_df):
    """
    进行区域分析 (复刻PDF报告 [cite: 55, 57, 94])
    我们只用淘宝数据，因为它有 '地理位置' 字段
    """
    print_header("Part 2: 区域分析 (来自淘宝数据)")
    
    if '地理位置' not in tb_df.columns:
        print("  - 淘宝数据中未找到 '地理位置' 字段，跳过区域分析。")
        return

    # 简单清洗地理位置
    tb_df['province'] = tb_df['地理位置'].apply(lambda x: str(x).split(' ')[0] if isinstance(x, str) else '未知')
    tb_df['sales'] = tb_df['付款人数'].apply(clean_sales)
    
    # 1. 按省份统计总销量
    prov_sales = tb_df.groupby('province')['sales'].sum().sort_values(ascending=False)
    print("  - 按[省份]估算总销量 Top 10:")
    for p, s in prov_sales.head(10).items():
        if p == '未知': continue
        print(f"    - {p}: {s:,.0f} 人付款")
        
    # 2. 按省份统计商品数量 (SKU数)
    prov_sku = tb_df['province'].value_counts()
    print("\n  - 按[省份]商品链接数 (SKU数) Top 10:")
    for p, s in prov_sku.head(10).items():
        if p == '未知': continue
        print(f"    - {p}: {s} 个商品")
        
    print("\n  - [可行性洞察]:")
    print("    - '地理位置' 字段可用，可以复刻PDF中的区域分析。")
    print("    - 我们可以进一步将省份映射到'华东'、'华北'、'西部'等大区 [cite: 57]，制作更高级的图表。")


def analyze_whitening_insight(data):
    """
    核心洞察：'显白' 诉求分析 (电商 vs 社交)
    """
    print_header("Part 3: '显白' 核心诉求分析")
    
    # 1. '显白' 在电商中的表现
    tb_df = data['tb'].copy()
    tb_df['sales'] = tb_df['付款人数'].apply(clean_sales)
    
    # 使用正则表达式在 '产品名称' 中查找显白关键词
    whitening_pattern = '|'.join(WHITENING_KEYWORDS)
    tb_df['is_whitening'] = tb_df['产品名称'].str.contains(whitening_pattern, na=False, case=False)
    
    whitening_products = tb_df[tb_df['is_whitening']]
    normal_products = tb_df[~tb_df['is_whitening']]
    
    print("  - 电商 (淘宝) 平台 '显白' 诉求分析:")
    print(f"    - '显白' 相关商品数: {len(whitening_products)} / {len(tb_df)} ({len(whitening_products) / len(tb_df):.1%})")
    print(f"    - '显白' 商品平均销量: {whitening_products['sales'].mean():.0f} 人付款")
    print(f"    - '非显白' 商品平均销量: {normal_products['sales'].mean():.0f} 人付款")
    
    # 2. '显白' 在社交中的表现 (小红书)
    xhs_df = data['xhs'].copy()
    xhs_df['likes'] = xhs_df['点赞数'].apply(clean_sales)
    
    xhs_df['is_whitening'] = xhs_df['标题'].str.contains(whitening_pattern, na=False, case=False)
    
    whitening_posts = xhs_df[xhs_df['is_whitening']]
    normal_posts = xhs_df[~xhs_df['is_whitening']]

    print("\n  - 社交 (小红书) 平台 '显白' 诉求分析:")
    print(f"    - '显白' 相关笔记数: {len(whitening_posts)} / {len(xhs_df)} ({len(whitening_posts) / len(xhs_df):.1%})")
    print(f"    - '显白' 笔记平均点赞: {whitening_posts['likes'].mean():.0f} 赞")
    print(f"    - '非显白' 笔记平均点赞: {normal_posts['likes'].mean():.0f} 赞")

    print("\n  - [可行性洞察]:")
    print("    - 我们可以清晰地量化 '显白' 诉求在电商和社交上的热度差异。")
    print("    - 我们可以制作图表，对比 '显白' 标签对销量和点赞的'溢价'效应。")

def analyze_comments_qualitative(comments_df):
    """
    定性分析 935 条评论 (你要求的 '数据少的说法')
    """
    print_header(f"Part 4: 评论定性分析 ({len(comments_df)} 条)")
    
    if '评论内容' not in comments_df.columns or comments_df.empty:
        print("  - 未找到 '评论内容' 或评论数据为空，跳过分析。")
        return

    comments = comments_df['评论内容'].dropna().astype(str)
    
    sentiment_counts = defaultdict(int)
    total_keywords_found = 0
    
    for comment in comments:
        comment_lower = comment.lower()
        found_in_this_comment = False
        
        for sentiment, keywords in COMMENT_SENTIMENT_KEYWORDS.items():
            for kw in keywords:
                if kw in comment_lower:
                    sentiment_counts[sentiment] += 1
                    found_in_this_comment = True
    
    print("  - 评论关键词词频统计 (一条评论可匹配多个词):")
    if not sentiment_counts:
        print("    - 在935条评论中未匹配到任何预设的分析关键词。")
        return
        
    # 打印统计
    print("    --- [正面反馈] ---")
    print(f"    - (通用好评): {sentiment_counts['positive_general']} 次")
    print(f"    - (颜色好评): {sentiment_counts['positive_color']} 次")
    print("    --- [负面反馈] ---")
    print(f"    - (通用差评): {sentiment_counts['negative_general']} 次")
    print(f"    - (颜色差评): {sentiment_counts['negative_color']} 次")
    
    print("\n  - [可行性洞察]:")
    print("    - 尽管评论少，但我们'可以'通过关键词提取进行初步的情感倾向分析。")
    print("    - 我们可以做一个图表，展示'颜色好评' vs '颜色差评'的声量对比。")
    print("    - 比如，我们可以分析'显白' (正面) 和 '显黑' (负面) 两个词被提及的次数比。")
    
    # 深入洞察：显白 vs 显黑
    whitening_count = comments.str.contains("显白").sum()
    blackening_count = comments.str.contains("显黑").sum()
    print(f"\n  - [深度洞察：显白 vs 显黑]:")
    print(f"    - '显白' 被提及: {whitening_count} 次")
    print(f"    - '显黑' 被提及: {blackening_count} 次")


def print_header(title):
    """打印格式化的标题"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

# --- 4. 主执行函数 ---
def main():
    base_dir = Path('.') # 假设脚本在 data_analizy 根目录
    
    print("正在启动深度数据可行性分析...")
    
    # 加载
    try:
        data = load_data(base_dir)
    except Exception as e:
        logging.error(f"数据加载失败，请检查文件路径和格式: {e}")
        return

    # 1. 元分析
    analyze_meta_data(data)
    
    # 2. 区域分析
    if not data['tb'].empty:
        analyze_regional_data(data['tb'])
    
    # 3. '显白' 洞察
    if not data['tb'].empty and not data['xhs'].empty:
        analyze_whitening_insight(data)
        
    # 4. 评论分析
    if not data['comments'].empty:
        analyze_comments_qualitative(data['comments'])
        
    print_header("分析完成")
    print("请将以上所有输出内容复制并发送给我。")
    print("我将根据这份详细报告，为你设计'真正'的单页仪表盘框架。")

if __name__ == "__main__":
    main()