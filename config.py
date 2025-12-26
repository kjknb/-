# 配置文件
CONFIG = {
    "driver_path": "chromedriver",  # ChromeDriver路径
    "base_url": "https://gravelocator.cem.va.gov/ngl",
    "wait_timeout": 15,
    "page_load_delay": 3,
    "max_pages": 100,  # 最大爬取页数
    "min_birth_year": 1980,
    "output_dir": "data"
}