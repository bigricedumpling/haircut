import json
import os
import re
from collections import defaultdict
from datetime import datetime

# 核心关键词库 - 使用短词和灵活表达式
WHITENING_KEYWORDS = ["显白", "黄皮", "肤色", "亲妈", "天菜", "素颜", "提亮", "去黄", "衬肤"]
COLOR_CATEGORIES = {
    # 棕色系 - 使用核心色系词+修饰词组合
    "棕色系": ["棕", "茶", "摩卡", "巧", "奶茶", "蜜", "焦糖", "栗", "咖啡", "可可"],
    
    # 红色/橘色系 - 短词+流行色名
    "红色/橘色系": ["红", "橘", "玫瑰", "酒红", "莓", "樱", "石榴", "番茄", "辣椒", "枫叶"],
    
    # 亚麻/青色系 - 核心色+修饰词
    "亚麻/青色系": ["亚麻", "青", "闷青", "灰绿", "橄榄", "抹茶", "薄荷", "牛油果"],
    
    # 灰色/蓝色/紫色系 - 核心色+流行色
    "灰色/蓝色/紫色系": ["灰", "蓝", "紫", "芋泥", "烟灰", "雾霾", "宝蓝", "葡萄", "香芋"],
    
    # 金色/浅色系 - 核心色+修饰词
    "金色/浅色系": ["金", "白金", "米金", "浅金", "香槟", "砂金", "铂金", "漂", "浅色"],
    
    # 高饱和色系 - 潮流关键词
    "高饱和色系": ["潮色", "霓虹", "荧光", "女团", "动漫", "海王", "湄拉", "芭比", "电光"]
}

# 技术关键词 - 产品特性
TECH_KEYWORDS = ["植物", "无氨", "护理", "固色", "护发", "免漂", "泡泡", "膏", "剂", "DIY"]

# 人群关键词 - 目标用户
USER_KEYWORDS = ["学生", "通勤", "上班", "约会", "拍照", "妈生", "千金", "辣妹", "甜酷"]

def match_keywords(title):
    """匹配商品标题中的关键词"""
    matched = set()
    
    # 显白相关匹配
    for kw in WHITENING_KEYWORDS:
        if kw in title:
            matched.add("显白相关")
    
    # 色系匹配
    for category, keywords in COLOR_CATEGORIES.items():
        for kw in keywords:
            if kw in title:
                matched.add(category)
                break  # 匹配到一个即停止
    
    # 技术特性匹配
    for kw in TECH_KEYWORDS:
        if kw in title:
            matched.add(kw)
    
    # 人群匹配
    for kw in USER_KEYWORDS:
        if kw in title:
            matched.add(kw)
    
    return list(matched)

def extract_payment_count(payment_str):
    """转换付款人数字符串为整数"""
    if not payment_str:
        return 0
        
    if "万+" in payment_str:
        return int(float(payment_str.split("万")[0]) * 10000)
    
    # 使用正则表达式提取数字
    match = re.search(r'(\d+)', payment_str)
    if match:
        return int(match.group(1))
    return 0

def get_selection_reason(item, keywords, payment_count):
    """生成选择原因备注"""
    reasons = []
    
    if "显白相关" in keywords:
        reasons.append("显白相关关键词匹配")
    
    if payment_count > 10000:
        reasons.append("高销量商品(>1万)")
    elif payment_count > 5000:
        reasons.append("中等销量商品(>5千)")
    
    # 色系覆盖原因
    color_categories = [cat for cat in COLOR_CATEGORIES if cat in keywords]
    if color_categories:
        reasons.append(f"色系覆盖: {', '.join(color_categories)}")
    
    # 技术特性
    tech_features = [kw for kw in TECH_KEYWORDS if kw in item.get("产品名称", "")]
    if tech_features:
        reasons.append(f"技术特性: {', '.join(tech_features)}")
    
    return "; ".join(reasons) if reasons else "其他原因选中"

def select_items_for_comments(items):
    """筛选需要评论的商品"""
    # 第一步：识别高优先级商品（显白相关+高销量）
    priority_items = []
    for item in items:
        title = item.get("产品名称", "")
        keywords = match_keywords(title)
        payment = extract_payment_count(item.get("付款人数", ""))
        
        # 显白相关且销量高
        if "显白相关" in keywords and payment > 5000:
            item["selection_priority"] = "P0"
            item["matched_keywords"] = keywords
            item["selection_reason"] = get_selection_reason(item, keywords, payment)
            priority_items.append(item)
    
    # 第二步：按销量降序排序
    items.sort(key=lambda x: extract_payment_count(x.get("付款人数", "")), reverse=True)
    
    # 第三步：分层抽样
    selected = []
    
    # 1. 添加所有高优先级商品
    selected.extend(priority_items)
    
    # 2. 添加头部高销量商品（前10）
    for i, item in enumerate(items[:10]):
        if item not in selected:
            title = item.get("产品名称", "")
            keywords = match_keywords(title)
            payment = extract_payment_count(item.get("付款人数", ""))
            
            item["selection_priority"] = "P1"
            item["matched_keywords"] = keywords
            item["selection_reason"] = get_selection_reason(item, keywords, payment)
            selected.append(item)
    
    # 3. 确保色系覆盖
    color_coverage = {category: 0 for category in COLOR_CATEGORIES}
    for item in items:
        if len(selected) >= 30:  # 控制总量
            break
            
        if item in selected:
            continue
            
        title = item.get("产品名称", "")
        keywords = match_keywords(title)
        payment = extract_payment_count(item.get("付款人数", ""))
        
        for category in COLOR_CATEGORIES:
            if category in keywords and color_coverage[category] < 2:
                item["selection_priority"] = "P2"
                item["matched_keywords"] = keywords
                item["selection_reason"] = get_selection_reason(item, keywords, payment)
                selected.append(item)
                color_coverage[category] += 1
                break
    
    # 去重
    seen = set()
    unique_items = []
    for item in selected:
        link = item.get("商品链接", "")
        if link and link not in seen:
            seen.add(link)
            unique_items.append(item)
    
    return unique_items

def save_links_in_batches(links, batch_size=100, prefix="selected_links"):
    """将链接分批保存到多个txt文件"""
    # 创建输出目录
    output_dir = "links_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 分批保存
    batches = []
    for i in range(0, len(links), batch_size):
        batch_links = links[i:i+batch_size]
        batch_num = i // batch_size + 1
        filename = f"{prefix}_batch_{batch_num}.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            for link in batch_links:
                f.write(link + "\n")
        
        batches.append({
            "batch_num": batch_num,
            "filename": filename,
            "filepath": filepath,
            "link_count": len(batch_links)
        })
    
    return batches

def save_selection_details_in_batches(selected_items, batch_size=100, prefix="selection_details"):
    """将详细选择信息分批保存到JSON文件"""
    # 创建输出目录
    output_dir = "details_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 总体选择信息
    overall_info = {
        "total_selected": len(selected_items),
        "selection_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "selection_criteria": {
            "whitening_keywords": WHITENING_KEYWORDS,
            "color_categories": list(COLOR_CATEGORIES.keys()),
            "priority_explanation": {
                "P0": "显白相关高销量商品",
                "P1": "头部高销量商品",
                "P2": "色系覆盖商品"
            }
        },
        "batches": []
    }
    
    # 统计信息
    priority_count = defaultdict(int)
    color_coverage = defaultdict(int)
    
    for item in selected_items:
        priority = item.get("selection_priority", "未知")
        priority_count[priority] += 1
        
        keywords = item.get("matched_keywords", [])
        for category in COLOR_CATEGORIES:
            if category in keywords:
                color_coverage[category] += 1
    
    overall_info["priority_distribution"] = dict(priority_count)
    overall_info["color_coverage"] = dict(color_coverage)
    
    # 分批保存详细数据
    batches = []
    for i in range(0, len(selected_items), batch_size):
        batch_items = selected_items[i:i+batch_size]
        batch_num = i // batch_size + 1
        filename = f"{prefix}_batch_{batch_num}.json"
        filepath = os.path.join(output_dir, filename)
        
        # 创建批次详细数据
        batch_details = {
            "batch_info": {
                "batch_num": batch_num,
                "item_count": len(batch_items),
                "items": []
            }
        }
        
        # 添加批次统计
        batch_priority_count = defaultdict(int)
        for item in batch_items:
            priority = item.get("selection_priority", "未知")
            batch_priority_count[priority] += 1
        
        batch_details["batch_info"]["priority_distribution"] = dict(batch_priority_count)
        batch_details["batch_info"]["items"] = batch_items
        
        # 保存批次文件
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(batch_details, f, ensure_ascii=False, indent=2)
        
        batches.append({
            "batch_num": batch_num,
            "filename": filename,
            "filepath": filepath,
            "item_count": len(batch_items)
        })
    
    # 保存总体信息文件
    overall_info["batches"] = batches
    overall_filepath = os.path.join(output_dir, "selection_overview.json")
    with open(overall_filepath, "w", encoding="utf-8") as f:
        json.dump(overall_info, f, ensure_ascii=False, indent=2)
    
    return batches, overall_filepath

def main():
    # 加载所有商品数据
    all_items = []
    
    # 假设JSON文件在当前目录下的data文件夹中
    data_dir = "淘宝商品目录"  # 修改为您的实际数据目录
    
    if not os.path.exists(data_dir):
        print(f"数据目录 {data_dir} 不存在，请检查路径")
        return
    
    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 假设每个JSON文件是一个商品列表
                    if isinstance(data, list):
                        all_items.extend(data)
                    else:
                        print(f"警告: {filename} 不是列表格式")
            except Exception as e:
                print(f"读取文件 {filename} 时出错: {e}")
    
    if not all_items:
        print("未找到任何商品数据")
        return
    
    print(f"共加载 {len(all_items)} 个商品数据")
    
    # 筛选需要评论的商品
    selected_items = select_items_for_comments(all_items)
    
    # 提取商品链接
    links = [item.get("商品链接", "") for item in selected_items if item.get("商品链接")]
    
    # 分批保存链接文件
    link_batches = save_links_in_batches(links, batch_size=100)
    
    # 分批保存详细选择信息
    detail_batches, overview_file = save_selection_details_in_batches(selected_items, batch_size=100)
    
    # 显示统计信息
    print(f"\n=== 选择统计 ===")
    print(f"总共选中商品: {len(selected_items)}")
    print(f"生成链接文件批次: {len(link_batches)}")
    print(f"生成详情文件批次: {len(detail_batches)}")
    
    # 优先级分布
    priority_count = defaultdict(int)
    for item in selected_items:
        priority_count[item.get("selection_priority", "未知")] += 1
    
    for priority, count in priority_count.items():
        print(f"{priority}优先级: {count}个商品")
    
    # 显示批次信息
    print(f"\n=== 批次文件信息 ===")
    for i, batch in enumerate(link_batches):
        print(f"批次 {batch['batch_num']}: {batch['link_count']}个链接 -> {batch['filename']}")
    
    # 显示前几个商品的详细信息作为示例
    print(f"\n=== 前3个选中商品详情 ===")
    for i, item in enumerate(selected_items[:3]):
        print(f"{i+1}. {item.get('产品名称', '')}")
        print(f"   链接: {item.get('商品链接', '')}")
        print(f"   付款人数: {item.get('付款人数', '')}")
        print(f"   优先级: {item.get('selection_priority', '')}")
        print(f"   匹配关键词: {', '.join(item.get('matched_keywords', []))}")
        print(f"   选择原因: {item.get('selection_reason', '')}")
        print()
    
    print(f"总体概览文件: {overview_file}")

if __name__ == "__main__":
    main()