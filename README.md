# 豆瓣电影爬虫

这是一个简单的豆瓣电影爬虫程序，用于获取豆瓣电影首页的正在热映电影信息。

## 功能特点

- 获取正在热映的电影信息
- 包含电影标题、评分和海报链接
- 自动保存为CSV文件
- 使用随机User-Agent避免被封禁

## 使用方法

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行爬虫：
```bash
python douban_spider.py
```

## 数据输出

程序会将爬取的数据保存在 `douban_movies.csv` 文件中，包含以下字段：
- title: 电影标题
- rating: 评分
- poster: 海报图片链接

## 注意事项

- 请合理控制爬取频率，避免对豆瓣服务器造成压力
- 遵守豆瓣的robots协议
- 仅供学习交流使用 