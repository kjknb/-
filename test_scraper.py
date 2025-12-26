import time
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By


def test_chromedriver():
    """测试ChromeDriver是否能正常工作"""
    try:
        print("1. 测试ChromeDriver...")

        # 尝试不使用headless模式，这样可以看到浏览器
        options = webdriver.ChromeOptions()
        # 先注释掉headless，看看浏览器是否能打开
        # options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        print("2. 创建WebDriver实例...")
        driver = webdriver.Chrome(options=options)

        print("3. 访问测试网站...")
        driver.get("https://www.google.com")
        time.sleep(2)

        print(f"4. 页面标题: {driver.title}")
        print("5. ChromeDriver测试成功！")

        # 测试目标网站
        print("6. 访问目标网站...")
        driver.get("https://gravelocator.cem.va.gov/ngl")
        time.sleep(3)

        print(f"7. 目标网站标题: {driver.title}")

        # 查找姓氏输入框
        try:
            last_name_input = driver.find_element(By.ID, "lname")
            print(f"8. 找到姓氏输入框: {last_name_input}")
            last_name_input.send_keys("TEST")
            print("9. 成功在输入框中输入文本")
        except Exception as e:
            print(f"8. 未找到姓氏输入框: {str(e)}")

        driver.quit()
        print("10. 测试完成！")

    except Exception as e:
        print(f"测试失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")


if __name__ == "__main__":
    test_chromedriver()