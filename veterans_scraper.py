import time
import traceback
import csv
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
from datetime import datetime


class VeteransGravesiteScraper:
    def __init__(self, driver_path: str = "chromedriver"):
        """
        初始化爬虫
        driver_path: ChromeDriver路径
        """
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # 无头模式
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.base_url = "https://gravelocator.cem.va.gov/ngl"
        self.results_data = []

    def search_by_last_name(self, last_name: str):
        """
        在首页搜索姓氏
        """
        try:
            print(f"正在搜索姓氏: {last_name}")
            self.driver.get(self.base_url)
            time.sleep(3)

            # 等待页面加载
            self.wait.until(EC.presence_of_element_located((By.ID, "lname")))

            # 输入姓氏
            last_name_input = self.driver.find_element(By.ID, "lname")
            last_name_input.clear()
            last_name_input.send_keys(last_name)

            # 设置搜索选项为"begins with" (选项值2)
            last_name_option = Select(self.driver.find_element(By.ID, "lnameopt"))
            last_name_option.select_by_value("2")  # begins with

            # 点击搜索按钮
            search_button = self.driver.find_element(By.ID, "searchb")

            # 启用按钮（如果被禁用）
            if search_button.get_attribute("disabled"):
                # 点击一下其他字段来启用按钮
                first_name_input = self.driver.find_element(By.ID, "fname")
                first_name_input.click()
                time.sleep(1)

            search_button.click()
            print("搜索请求已发送...")

            # 等待结果页面加载
            self.wait.until(EC.presence_of_element_located((By.ID, "searchResults")))
            print("结果页面加载完成")
            return True

        except Exception as e:
            print(f"搜索时发生错误: {str(e)}")
            return False

    def extract_name_parts(self, full_name: str) -> tuple:
        """
        将全名分割为姓和名
        格式: MICHAEL, BERNARD EDWARD -> 姓: MICHAEL, 名: BERNARD EDWARD
        """
        if ',' in full_name:
            parts = full_name.split(',', 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ""
            return last_name, first_name
        else:
            return full_name.strip(), ""

    def parse_birth_year(self, birth_date: str) -> int:
        """
        从出生日期提取年份
        格式: 01/17/1925 -> 1925
        """
        try:
            if '/' in birth_date:
                parts = birth_date.split('/')
                if len(parts) >= 3:
                    return int(parts[2])
        except:
            pass
        return 0

    def parse_results_page(self, min_birth_year: int = 1980) -> List[Dict]:
        """
        解析当前结果页面，提取符合条件的记录
        """
        try:
            page_data = []
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # 查找结果表格
            results_table = soup.find('table', {'id': 'searchResults'})
            if not results_table:
                print("未找到结果表格")
                return page_data

            # 查找所有记录组
            records = []
            tbody = results_table.find('tbody')

            if tbody:
                # 查找所有记录开始的tr（包含序号的行）
                record_start_trs = tbody.find_all('th', class_='table_row_labels item-number text-center')

                for record_start in record_start_trs:
                    # 获取包含此th的tr
                    start_row = record_start.find_parent('tr')
                    if not start_row:
                        continue

                    # 初始化记录字典
                    record = {}

                    # 提取名称
                    name_cells = start_row.find_all(['th', 'td'])
                    if len(name_cells) >= 3:
                        name_cell = name_cells[2]
                        name_div = name_cell.find('div', class_='p-2')
                        if name_div:
                            name_text = name_div.get_text(strip=True)
                            if name_text.startswith('Name:'):
                                name_text = name_text.replace('Name:', '').strip()
                            record['Full_Name'] = name_text

                    # 查找此记录的所有行
                    current_row = start_row
                    while current_row:
                        next_row = current_row.find_next_sibling('tr')

                        # 检查是否是下一条记录的开始或分隔符
                        if next_row and 'horizontal-line' in str(next_row):
                            break
                        if next_row and next_row.find('th', class_='table_row_labels item-number text-center'):
                            break

                        # 提取当前行的数据
                        cells = current_row.find_all(['th', 'td'])
                        if len(cells) >= 2:
                            label_cell = cells[1]
                            value_cell = cells[2] if len(cells) > 2 else None

                            if label_cell and value_cell:
                                label_div = label_cell.find('div', class_='p-2')
                                value_div = value_cell.find('div', class_='p-2')

                                if label_div and value_div:
                                    label = label_div.get_text(strip=True).replace(':', '')
                                    value = value_div.get_text(strip=True)

                                    if label == 'Rank & Branch':
                                        record['Rank_Branch'] = value
                                    elif label == 'Date of Birth':
                                        record['Date_of_Birth'] = value
                                        # 检查年份是否符合条件
                                        birth_year = self.parse_birth_year(value)
                                        if birth_year >= min_birth_year:
                                            record['Birth_Year'] = birth_year

                        current_row = next_row

                    # 只添加包含所需信息且出生年份>=1980的记录
                    if all(key in record for key in ['Full_Name', 'Rank_Branch', 'Date_of_Birth']):
                        if record.get('Birth_Year', 0) >= min_birth_year:
                            page_data.append(record)

            print(f"本页找到 {len(page_data)} 条符合条件记录")
            return page_data

        except Exception as e:
            print(f"解析页面时发生错误: {str(e)}")
            return []

    def go_to_next_page(self) -> bool:
        """
        跳转到下一页
        """
        try:
            # 查找下一页链接
            next_links = self.driver.find_elements(By.XPATH, "//nav[@id='pagination']//a[contains(text(), 'Next')]")

            for link in next_links:
                if link.is_displayed() and link.is_enabled():
                    print("跳转到下一页...")
                    link.click()
                    time.sleep(3)  # 等待页面加载

                    # 等待结果表格重新加载
                    self.wait.until(EC.presence_of_element_located((By.ID, "searchResults")))
                    return True

            print("已到最后一页")
            return False

        except Exception as e:
            print(f"跳转下一页时发生错误: {str(e)}")
            return False

    def scrape_all_pages(self, last_name: str, max_pages: int = 100, min_birth_year: int = 1980):
        """
        爬取所有页面
        """
        try:
            # 开始搜索
            if not self.search_by_last_name(last_name):
                print("搜索失败")
                return

            page_count = 1

            while page_count <= max_pages:
                print(f"\n正在处理第 {page_count} 页...")

                # 解析当前页面
                page_data = self.parse_results_page(min_birth_year)
                self.results_data.extend(page_data)

                # 尝试下一页
                if not self.go_to_next_page():
                    break

                page_count += 1
                time.sleep(2)  # 避免请求过快

            print(f"\n爬取完成！共找到 {len(self.results_data)} 条符合条件的记录")

        except Exception as e:
            print(f"爬取过程中发生错误: {str(e)}")

    def process_data(self):
        """
        处理数据：分割姓名字段
        """
        processed_data = []

        for record in self.results_data:
            # 分割姓名
            last_name, first_name = self.extract_name_parts(record['Full_Name'])

            processed_record = {
                'Last_Name': last_name,
                'First_Name': first_name,
                'Full_Name': record['Full_Name'],
                'Rank_Branch': record['Rank_Branch'],
                'Date_of_Birth': record['Date_of_Birth'],
                'Birth_Year': record.get('Birth_Year', '')
            }
            processed_data.append(processed_record)

        return processed_data

    def save_to_csv(self, filename: str = "veterans_data.csv"):
        """
        保存数据到CSV文件
        """
        if not self.results_data:
            print("没有数据可保存")
            return

        processed_data = self.process_data()

        # 定义CSV列名
        fieldnames = ['Last_Name', 'First_Name', 'Full_Name', 'Rank_Branch', 'Date_of_Birth', 'Birth_Year']

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(processed_data)

            print(f"数据已保存到 {filename}")

            # 同时保存为pandas DataFrame（可选）
            df = pd.DataFrame(processed_data)
            df.to_excel("veterans_data.xlsx", index=False)
            print("数据已保存为Excel格式")

        except Exception as e:
            print(f"保存文件时发生错误: {str(e)}")

    def get_summary(self):
        """
        获取数据摘要
        """
        if not self.results_data:
            print("没有数据")
            return

        processed_data = self.process_data()

        print("\n=== 数据摘要 ===")
        print(f"总记录数: {len(processed_data)}")

        # 按出生年份统计
        birth_years = [record.get('Birth_Year', 0) for record in processed_data if record.get('Birth_Year')]
        if birth_years:
            print(f"出生年份范围: {min(birth_years)} - {max(birth_years)}")

        # 显示前几条记录
        print("\n=== 前5条记录示例 ===")
        for i, record in enumerate(processed_data[:5]):
            print(
                f"{i + 1}. {record['Last_Name']}, {record['First_Name']} | {record['Date_of_Birth']} | {record['Rank_Branch']}")

    def close(self):
        """关闭浏览器"""
        self.driver.quit()
        print("浏览器已关闭")


# 主程序
def main():
    # 设置要搜索的姓氏
    last_name = input("请输入要搜索的姓氏 (例如: MICHAEL): ").strip()

    if not last_name:
        print("姓氏不能为空")
        return

    # 创建爬虫实例
    scraper = VeteransGravesiteScraper()

    try:
        # 爬取所有页面
        scraper.scrape_all_pages(last_name=last_name, max_pages=50, min_birth_year=1980)

        # 获取摘要
        scraper.get_summary()

        # 保存数据
        filename = f"veterans_{last_name.lower()}.csv"
        scraper.save_to_csv(filename)

    except Exception as e:
        print(f"主程序发生错误: {str(e)}")

    finally:
        # 关闭浏览器
        scraper.close()


# 快速使用示例
def quick_search():
    """
    快速搜索示例
    """
    print("开始快速搜索...")

    try:
        # 先检查ChromeDriver是否能正常启动
        print("尝试初始化ChromeDriver...")
        scraper = VeteransGravesiteScraper()
        print("ChromeDriver初始化成功")

        # 测试是否能访问网站
        print("正在访问网站...")
        scraper.driver.get("https://www.google.com")
        time.sleep(2)
        print(f"当前页面标题: {scraper.driver.title}")

        # 搜索特定姓氏
        print("开始爬取数据...")
        scraper.scrape_all_pages(last_name="MICHAEL", max_pages=3, min_birth_year=1980)

        # 获取摘要
        scraper.get_summary()

        # 保存数据
        scraper.save_to_csv("veterans_michael.csv")

    except Exception as e:
        print(f"发生错误: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")

    finally:
        if 'scraper' in locals():
            scraper.close()
        print("程序结束")

if __name__ == "__main__":
    print("=== 美国退伍军人墓地信息爬虫 ===")
    print("此程序将爬取Nationwide Gravesite Locator网站数据")
    print("只提取出生年份 >= 1980 的记录\n")

    # 选择运行方式
    print("请选择运行方式:")
    print("1. 输入姓氏进行完整搜索")
    print("2. 快速搜索示例 (MICHAEL)")

    choice = input("请输入选择 (1 或 2): ").strip()

    if choice == "1":
        main()
    elif choice == "2":
        quick_search()
    else:
        print("无效选择")