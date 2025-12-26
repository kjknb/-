import time
import csv
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import traceback
import re


class VeteransGravesiteScraper:
    def __init__(self):
        """初始化爬虫"""
        print("正在初始化浏览器...")

        # Chrome选项
        options = webdriver.ChromeOptions()
        # 先不使用headless，方便调试
        # options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        # 自动安装和管理ChromeDriver
        print("正在安装/检查ChromeDriver...")
        service = Service(ChromeDriverManager().install())

        # 创建驱动
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 20)
        self.base_url = "https://gravelocator.cem.va.gov/ngl"
        self.results_data = []
        print("浏览器初始化完成")

    def search_by_last_name(self, last_name: str):
        """搜索姓氏"""
        try:
            print(f"正在搜索姓氏: {last_name}")
            self.driver.get(self.base_url)
            time.sleep(3)

            # 等待页面加载
            self.wait.until(EC.presence_of_element_located((By.ID, "lname")))
            print("页面加载成功")

            # 输入姓氏
            last_name_input = self.driver.find_element(By.ID, "lname")
            last_name_input.clear()
            last_name_input.send_keys(last_name)
            print(f"已输入姓氏: {last_name}")

            # 设置搜索选项为"begins with"
            last_name_option = Select(self.driver.find_element(By.ID, "lnameopt"))
            last_name_option.select_by_value("2")
            print("已设置搜索选项")

            # 找到搜索按钮
            search_button = self.driver.find_element(By.ID, "searchb")

            # 如果按钮被禁用，先点击其他元素
            if search_button.get_attribute("disabled"):
                print("搜索按钮被禁用，尝试激活...")
                self.driver.find_element(By.ID, "fname").click()
                time.sleep(1)

            # =========== 添加确认步骤 ===========
            print("\n" + "="*50)
            print("已定位到搜索按钮，等待您的确认...")
            print(f"当前搜索条件: 姓氏 {last_name} (begins with)")
            print("请检查浏览器中的搜索条件是否正确")
            input("确认无误后，按 Enter 键开始搜索 (或按 Ctrl+C 取消)... ")
            print("="*50 + "\n")
            # =========== 确认步骤结束 ===========

            # 点击搜索
            search_button.click()
            print("点击搜索按钮")

            # 等待结果
            time.sleep(5)
            print("等待结果页面...")

            # 检查是否有结果
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, "searchResults")))
                print("结果页面加载成功")
                return True
            except:
                print("未找到结果页面，但继续处理...")
                return True

        except Exception as e:
            print(f"搜索时发生错误: {str(e)}")
            return False

    def parse_page(self):
        """解析当前页面数据 - 使用简单的文本解析方法"""
        try:
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # 查找结果信息
            results_info = soup.find('p', {'id': 'results-content'})
            if results_info:
                text = results_info.get_text(strip=True)
                print(f"结果信息: {text}")

            # 使用简单的正则表达式匹配整个表格内容
            # 查找所有tr元素，每个tr可能有多个数据
            records = []

            # 查找所有包含 "Name:" 的行
            all_trs = soup.find_all('tr')

            current_record = {}
            record_number = 0

            for i, tr in enumerate(all_trs):
                # 检查是否是记录开始（有item-number类）
                item_number = tr.find('th', class_='table_row_labels item-number text-center')
                if item_number:
                    # 保存上一个记录
                    if current_record and 'Name:' in current_record and 'Date of Birth:' in current_record:
                        # 处理这个记录
                        processed = self.process_record(current_record)
                        if processed:
                            records.append(processed)

                    # 开始新记录
                    current_record = {}
                    try:
                        record_number = int(item_number.get_text(strip=True))
                        current_record['Record_Number'] = record_number
                    except:
                        pass

                # 提取数据行
                ths = tr.find_all('th', class_='row-header')
                tds = tr.find_all('td', class_='results-info')

                if ths and tds and len(ths) >= 1 and len(tds) >= 1:
                    label = ths[0].get_text(strip=True)
                    value = tds[0].get_text(strip=True)
                    current_record[label] = value

            # 处理最后一个记录
            if current_record and 'Name:' in current_record and 'Date of Birth:' in current_record:
                processed = self.process_record(current_record)
                if processed:
                    records.append(processed)

            print(f"本页找到 {len(records)} 条记录")

            # 调试：显示前几条记录
            if records:
                print("\n前3条记录示例:")
                for i, rec in enumerate(records[:3]):
                    print(
                        f"  {i + 1}. {rec.get('Full_Name', 'N/A')} | {rec.get('Date_of_Birth', 'N/A')} | {rec.get('Rank_Branch', 'N/A')}")

            return records

        except Exception as e:
            print(f"解析页面时出错: {str(e)}")
            traceback.print_exc()
            return []

    def process_record(self, record_dict):
        """处理单个记录字典，提取所需信息"""
        try:
            # 获取姓名
            name = record_dict.get('Name:', '').strip()

            # 获取军衔和分支
            rank_branch = record_dict.get('Rank & Branch:', '').strip()

            # 获取出生日期
            dob = record_dict.get('Date of Birth:', '').strip()

            if not name or not dob:
                return None

            # 提取出生年份
            birth_year = 0
            if dob and '/' in dob:
                try:
                    year_part = dob.split('/')[-1]
                    if len(year_part) == 4:
                        birth_year = int(year_part)
                except:
                    birth_year = 0

            # 只保留出生年份>=1980的记录
            if birth_year >= 1960:
                result = {
                    'Full_Name': name,
                    'Rank_Branch': rank_branch,
                    'Date_of_Birth': dob,
                    'Birth_Year': birth_year
                }
                return result

            return None

        except Exception as e:
            print(f"处理记录时出错: {str(e)}")
            return None

    def go_to_next_page(self):
        """跳转到下一页"""
        try:
            # 使用JavaScript滚动到页面底部
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # 查找下一页链接 - 使用更精确的选择器
            next_links = self.driver.find_elements(By.XPATH, "//nav[@id='pagination']//a[contains(text(), 'Next')]")

            if not next_links:
                # 尝试其他可能的选择器
                next_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Next')]")

            if not next_links:
                print("未找到下一页链接")
                return False

            next_link = next_links[0]

            # 使用JavaScript点击，避免元素被遮挡
            self.driver.execute_script("arguments[0].click();", next_link)
            print("已点击下一页")

            # 等待页面加载
            time.sleep(5)

            # 检查是否成功跳转
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, "searchResults")))
                return True
            except:
                print("等待结果超时，但继续处理...")
                return True

        except Exception as e:
            print(f"跳转下一页时出错: {str(e)}")
            return False

    def run_scraper(self, last_name: str, max_pages: int = 5):
        """运行爬虫主程序"""
        print(f"\n{'=' * 50}")
        print(f"开始爬取姓氏: {last_name}")
        print(f"{'=' * 50}\n")

        # 搜索
        if not self.search_by_last_name(last_name):
            print("搜索失败，程序结束")
            return

        # 解析页面
        page_num = 1
        all_records = []

        while page_num <= max_pages:
            print(f"\n正在处理第 {page_num} 页...")

            # 解析当前页
            records = self.parse_page()
            all_records.extend(records)

            print(f"本页找到 {len(records)} 条符合条件的记录")
            print(f"已累计找到 {len(all_records)} 条记录")

            # 尝试下一页
            if not self.go_to_next_page():
                print("无法跳转到下一页，可能已到最后一页")
                break

            page_num += 1

        # 保存所有记录
        self.results_data = all_records

        # 显示结果
        print(f"\n{'=' * 50}")
        print(f"爬取完成！")
        print(f"总共找到 {len(all_records)} 条记录")
        print(f"{'=' * 50}")

        if all_records:
            print("\n所有符合条件的记录:")
            for i, record in enumerate(all_records):
                name = record.get('Full_Name', 'N/A')
                dob = record.get('Date_of_Birth', 'N/A')
                rank = record.get('Rank_Branch', 'N/A')
                year = record.get('Birth_Year', 'N/A')
                print(f"{i + 1}. {name} | {dob} ({year}) | {rank}")

            # 保存到CSV
            self.save_to_csv(last_name)
        else:
            print("未找到符合条件的记录")
            # 保存一个空的CSV文件以记录
            self.save_empty_csv(last_name)

    def save_to_csv(self, last_name: str):
        """保存数据到CSV"""
        if not self.results_data:
            print("没有数据可保存")
            self.save_empty_csv(last_name)
            return

        filename = f"{last_name}_veterans.csv"

        # 处理姓名分割
        processed_data = []
        for record in self.results_data:
            name = record['Full_Name']
            if ',' in name:
                parts = name.split(',', 1)
                last_name_part = parts[0].strip()
                first_name_part = parts[1].strip() if len(parts) > 1 else ""
            else:
                last_name_part = name
                first_name_part = ""

            processed_data.append({
                'Last_Name': last_name_part,
                'First_Name': first_name_part,
                'Full_Name': record['Full_Name'],
                'Rank_Branch': record['Rank_Branch'],
                'Date_of_Birth': record['Date_of_Birth'],
                'Birth_Year': record.get('Birth_Year', '')
            })

        # 写入CSV
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f,
                                    fieldnames=['Last_Name', 'First_Name', 'Full_Name', 'Rank_Branch', 'Date_of_Birth',
                                                'Birth_Year'])
            writer.writeheader()
            writer.writerows(processed_data)

        print(f"\n数据已保存到: {filename}")

        # 同时保存为Excel
        try:
            df = pd.DataFrame(processed_data)
            excel_file = filename.replace('.csv', '.xlsx')
            df.to_excel(excel_file, index=False)
            print(f"数据已保存为Excel: {excel_file}")
        except Exception as e:
            print(f"保存Excel时出错: {str(e)}")

    def save_empty_csv(self, last_name: str):
        """保存空的CSV文件"""
        filename = f"{last_name}_veterans.csv"
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Last_Name', 'First_Name', 'Full_Name', 'Rank_Branch', 'Date_of_Birth', 'Birth_Year'])
            writer.writerow(['No records found with birth year >= 1980'])
        print(f"空数据文件已保存到: {filename}")

    def close(self):
        """关闭浏览器"""
        self.driver.quit()
        print("浏览器已关闭")


# 快速测试函数 - 只爬取1页并详细显示解析过程
def test_parsing():
    """测试解析功能"""
    print("测试解析功能...")

    # 创建爬虫实例
    scraper = VeteransGravesiteScraper()

    try:
        # 搜索
        if not scraper.search_by_last_name("MICHAEL"):
            print("搜索失败")
            return

        # 获取页面源代码并保存以供分析
        page_source = scraper.driver.page_source

        # 保存HTML以供分析
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(page_source)
        print("页面HTML已保存到 debug_page.html")

        # 解析页面
        records = scraper.parse_page()

        print(f"\n找到 {len(records)} 条记录")

        if records:
            print("\n所有记录详情:")
            for i, rec in enumerate(records):
                print(f"\n记录 {i + 1}:")
                print(f"  姓名: {rec.get('Full_Name', 'N/A')}")
                print(f"  军衔/分支: {rec.get('Rank_Branch', 'N/A')}")
                print(f"  出生日期: {rec.get('Date_of_Birth', 'N/A')}")
                print(f"  出生年份: {rec.get('Birth_Year', 'N/A')}")
        else:
            print("未找到任何记录")
            print("\n尝试使用不同的解析方法...")

            # 使用备用解析方法
            soup = BeautifulSoup(page_source, 'html.parser')

            # 查找所有div中的文本
            all_divs = soup.find_all('div', class_='p-2')
            print(f"\n找到 {len(all_divs)} 个p-2 div")

            # 显示前20个div的内容
            print("\n前20个p-2 div内容:")
            for i, div in enumerate(all_divs[:20]):
                text = div.get_text(strip=True)
                print(f"{i + 1}: {text}")

            # 查找所有包含"Date of Birth"的文本
            print("\n查找包含'Date of Birth'的内容:")
            for text in soup.stripped_strings:
                if 'Date of Birth' in text:
                    print(f"找到: {text}")

    except Exception as e:
        print(f"测试时出错: {str(e)}")
        traceback.print_exc()

    finally:
        scraper.close()


def main():
    """主函数"""
    print("美国退伍军人墓地信息爬虫")
    print("只提取出生年份 >= 1980 的记录")
    print("=" * 50)

    print("\n请选择运行模式:")
    print("1. 完整爬取（搜索姓氏并爬取多页）")
    print("2. 测试解析（只爬取1页，详细显示解析过程）")

    choice = input("请输入选择 (1 或 2): ").strip()

    if choice == "2":
        test_parsing()
        return

    # 安装必要的包
    print("正在检查依赖...")
    try:
        import webdriver_manager
        print("✓ webdriver_manager 已安装")
    except ImportError:
        print("正在安装 webdriver_manager...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'webdriver_manager'])
        print("✓ webdriver_manager 安装完成")

    # 获取姓氏
    last_name = input("\n请输入要搜索的姓氏 (例如: SMITH，直接回车使用MICHAEL): ").strip()
    if not last_name:
        last_name = "MICHAEL"
        print(f"使用默认姓氏: {last_name}")

    # 获取最大页数
    max_pages_input = input("请输入最大爬取页数 (直接回车使用默认5页): ").strip()
    if max_pages_input:
        try:
            max_pages = int(max_pages_input)
        except:
            max_pages = 5
            print("输入无效，使用默认值5")
    else:
        max_pages = 5

    # 创建爬虫实例
    scraper = VeteransGravesiteScraper()

    try:
        # 运行爬虫
        scraper.run_scraper(last_name, max_pages)

    except Exception as e:
        print(f"\n程序运行出错: {str(e)}")
        traceback.print_exc()

    finally:
        # 关闭浏览器
        scraper.close()
        input("\n按Enter键退出程序...")


if __name__ == "__main__":
    main()