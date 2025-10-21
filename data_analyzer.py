import json
import os
from pathlib import Path
import logging

# 配置日志，用于捕获可能的错误
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# 定义文件的相对路径
# 我们假设这个脚本就运行在 'data_analizy' 目录中
BASE_DIR = Path('.')

# 根据你的文件列表，定义我们要分析的数据文件
# 我们将它们按分析目的分组
DATA_FILES_MAP = {
    "电商商品-淘宝": [
        "淘宝商品目录/淘宝网-商品列表页采集【网站反爬请查阅注意事项】.json",
        "淘宝商品目录/淘宝网-商品列表页采集【网站反爬请查阅注意事项】-2.json"
    ],
    "电商商品-京东": [
        "京东-商品搜索.json"
    ],
    "社交内容-小红书": [
        "小红书-关键词笔记采集.json",
        "小红书-关键词笔记采集2.json"
    ],
    "社交内容-微博": [
        "微博搜索关键词采集.json"
    ],
    "电商评论-淘宝": [
        "淘宝商品评论【网站反爬请查阅注意事项】.json"
    ],
    "分析过程-筛选详情": [
        "details_output/selection_overview.json",
        "details_output/selection_details_batch_1.json" # 抽样检查第一个batch的结构
    ],
    "分析过程-筛选链接": [
        "links_output/selected_links_batch_1.txt" # 抽样检查
    ]
}

def analyze_json_file(file_path: Path) -> dict:
    """分析单个JSON文件，返回其结构和统计信息"""
    analysis = {
        "file_name": file_path.name,
        "status": "OK",
        "record_count": 0,
        "data_type": "Unknown",
        "keys": [],
        "error_message": None
    }

    if not file_path.exists():
        analysis["status"] = "ERROR"
        analysis["error_message"] = "File not found."
        return analysis

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            if isinstance(data, list):
                analysis["data_type"] = "List (Array of records)"
                analysis["record_count"] = len(data)
                if analysis["record_count"] > 0:
                    # 提取第一条记录的键，作为代表
                    if isinstance(data[0], dict):
                        analysis["keys"] = list(data[0].keys())
                    else:
                        analysis["keys"] = [f"Data is a list of non-dict items, e.g., {type(data[0])}"]
                else:
                    analysis["keys"] = ["List is empty, cannot determine keys."]
                    
            elif isinstance(data, dict):
                analysis["data_type"] = "Dictionary (Single object)"
                analysis["record_count"] = 1 # 视为1个记录
                analysis["keys"] = list(data.keys())
                
            else:
                analysis["data_type"] = f"Other ({type(data)})"
                analysis["record_count"] = 1
                analysis["keys"] = ["Data is not a list or dict."]

    except json.JSONDecodeError:
        analysis["status"] = "ERROR"
        analysis["error_message"] = "JSONDecodeError. File might be empty, malformed, or not JSON."
    except FileNotFoundError:
        analysis["status"] = "ERROR"
        analysis["error_message"] = "FileNotFoundError. (Should be caught earlier, but for safety)"
    except Exception as e:
        analysis["status"] = "ERROR"
        analysis["error_message"] = f"An unexpected error occurred: {e}"

    return analysis

def analyze_txt_file(file_path: Path) -> dict:
    """分析单个TXT文件，返回行数"""
    analysis = {
        "file_name": file_path.name,
        "status": "OK",
        "record_count": 0,
        "data_type": "Text (Lines)",
        "keys": ["N/A (Text file)"],
        "error_message": None
    }

    if not file_path.exists():
        analysis["status"] = "ERROR"
        analysis["error_message"] = "File not found."
        return analysis

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            analysis["record_count"] = len(lines)
            
    except Exception as e:
        analysis["status"] = "ERROR"
        analysis["error_message"] = f"An unexpected error occurred: {e}"

    return analysis

def main():
    """主执行函数，遍历所有文件并打印报告"""
    print("============================================")
    print("   正在开始... 数据资产结构盘点报告   ")
    print("============================================")
    print(f"基准目录: {BASE_DIR.resolve()}\n")

    overall_stats = {}

    for group_name, file_list in DATA_FILES_MAP.items():
        print(f"\n--- [数据组]: {group_name} ---")
        group_total_records = 0
        
        for file_rel_path in file_list:
            file_path = BASE_DIR / file_rel_path
            
            if file_path.suffix == ".json":
                report = analyze_json_file(file_path)
            elif file_path.suffix == ".txt":
                report = analyze_txt_file(file_path)
            else:
                logging.warning(f"Skipping unsupported file type: {file_path.name}")
                continue
                
            # 打印单个文件的分析结果
            print(f"  > 文件: {file_rel_path}")
            print(f"    状态: {report['status']}")
            
            if report["status"] == "OK":
                print(f"    类型: {report['data_type']}")
                print(f"    计数: {report['record_count']} 条记录/行")
                print(f"    字段 (Keys): {report['keys']}")
                group_total_records += report['record_count']
            else:
                print(f"    错误: {report['error_message']}")
        
        overall_stats[group_name] = group_total_records

    print("\n\n============================================")
    print("           数据资产总量汇总           ")
    print("============================================")
    
    for group_name, total in overall_stats.items():
        print(f"  - {group_name:<20}: {total:>8} 条记录")

    print("\n============================================")
    print("           盘点完成           ")
    print("============================================")
    print("请将以上所有输出内容复制并发送给我，我将基于此为你定制下一步的可视化方案。")

if __name__ == "__main__":
    main()