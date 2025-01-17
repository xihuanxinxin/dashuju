import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging
from datetime import datetime
import os

class DoubanMovieSpider:
    def __init__(self):
        self.base_url = 'https://movie.douban.com/top250'
        self.columns = ['Title', 'Year', 'Rated', 'Released', 'Season', 'Episode', 
                       'Runtime', 'Genre', 'Director', 'Writer', 'Actors', 'Plot',
                       'Language', 'Country', 'Awards', 'Poster', 'Metascore',
                       'imdbRating', 'imdbVotes', 'imdbID', 'seriesID', 'Type']
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='douban_spider.log'
        )
        
        # 配置Chrome选项
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--start-maximized')
        self.options.add_experimental_option('excludeSwitches', ['enable-automation'])
        
        # 初始化浏览器
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=self.options)
        
    def random_sleep(self, min_time=3, max_time=7):
        """随机等待"""
        time.sleep(random.uniform(min_time, max_time))
        
    def get_page(self, url):
        """获取页面内容"""
        try:
            self.driver.get(url)
            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'content'))
            )
            self.random_sleep()
            return True
        except TimeoutException:
            logging.error(f"页面加载超时: {url}")
            return False
        except Exception as e:
            logging.error(f"获取页面失败: {str(e)}")
            return False
            
    def parse_movie_list(self):
        """解析电影列表获取详情页链接"""
        try:
            movie_links = []
            items = self.driver.find_elements(By.CSS_SELECTOR, 'ol.grid_view li')
            
            for item in items:
                try:
                    href = item.find_element(By.CSS_SELECTOR, '.hd a').get_attribute('href')
                    movie_links.append(href)
                except Exception as e:
                    logging.error(f"获取电影链接失败: {str(e)}")
                    continue
                    
            return movie_links
            
        except Exception as e:
            logging.error(f"解析电影列表失败: {str(e)}")
            return []

    def parse_movie_detail(self, url):
        """解析电影详情页"""
        if not self.get_page(url):
            return None
            
        try:
            movie = {}
            
            # 标题
            movie['Title'] = self.driver.find_element(By.XPATH, '//h1/span[1]').text.strip()
            
            # 基本信息
            info = self.driver.find_element(By.ID, 'info').text
            info_dict = {}
            for line in info.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    info_dict[key.strip()] = value.strip()
            
            # 提取各字段
            movie['Year'] = info_dict.get('年份', '')
            movie['Director'] = info_dict.get('导演', '')
            movie['Writer'] = info_dict.get('编剧', '')
            movie['Actors'] = info_dict.get('主演', '')
            movie['Genre'] = info_dict.get('类型', '')
            movie['Country'] = info_dict.get('制片国家/地区', '')
            movie['Language'] = info_dict.get('语言', '')
            movie['Runtime'] = info_dict.get('片长', '')
            
            # 评分
            try:
                movie['Rated'] = self.driver.find_element(By.CLASS_NAME, 'rating_num').text
            except:
                movie['Rated'] = ''
                
            # 剧情简介
            try:
                movie['Plot'] = self.driver.find_element(By.ID, 'link-report').text.strip()
            except:
                movie['Plot'] = ''
                
            # 海报
            try:
                movie['Poster'] = self.driver.find_element(By.ID, 'mainpic').find_element(By.TAG_NAME, 'img').get_attribute('src')
            except:
                movie['Poster'] = ''
                
            # 获奖情况
            try:
                movie['Awards'] = self.driver.find_element(By.CLASS_NAME, 'award').text
            except:
                movie['Awards'] = ''
                
            # IMDb信息
            try:
                imdb_link = self.driver.find_element(By.XPATH, "//div[@id='info']/a[contains(@href, 'imdb.com')]")
                movie['imdbID'] = imdb_link.get_attribute('href').split('/')[-1]
            except:
                movie['imdbID'] = ''
                
            # 其他字段设为空值
            movie['Released'] = ''
            movie['Season'] = ''
            movie['Episode'] = ''
            movie['Metascore'] = ''
            movie['imdbRating'] = ''
            movie['imdbVotes'] = ''
            movie['seriesID'] = ''
            movie['Type'] = 'movie'
            
            logging.info(f"成功解析电影: {movie['Title']}")
            return movie
            
        except Exception as e:
            logging.error(f"解析电影详情页失败: {str(e)}")
            return None
            
    def save_to_csv(self, movies, filename='douban_movies.csv'):
        """保存数据到CSV文件"""
        if not movies:
            logging.warning("没有电影数据可保存")
            return
            
        try:
            df = pd.DataFrame(movies)
            # 确保列的顺序一致
            df = df.reindex(columns=self.columns)
            
            if os.path.exists(filename):
                # 追加模式
                df.to_csv(filename, mode='a', header=False, index=False, encoding='utf-8-sig')
            else:
                # 新建文件
                df.to_csv(filename, index=False, encoding='utf-8-sig')
            logging.info(f"保存 {len(movies)} 部电影数据到 {filename}")
        except Exception as e:
            logging.error(f"保存数据失败: {str(e)}")
            
    def run(self):
        """运行爬虫"""
        logging.info("开始爬取豆瓣电影数据...")
        all_movies = []
        
        try:
            # 先访问豆瓣首页并等待用户登录
            self.driver.get('https://www.douban.com')
            input("请登录豆瓣账号，登录完成后按回车继续...")
            logging.info("用户已确认登录完成")
            
            # 从第三页开始爬取 (start=50)
            for start in range(50, 250, 25):
                url = f"{self.base_url}?start={start}"
                logging.info(f"正在访问第 {start//25 + 1} 页: {url}")
                
                if not self.get_page(url):
                    logging.error(f"获取第 {start//25 + 1} 页失败")
                    self.random_sleep(3, 8)  # 失败后随机等待
                    continue
                
                # 获取当前页面所有电影链接
                movie_links = self.parse_movie_list()
                page_movies = []
                
                # 遍历电影详情页
                for link in movie_links:
                    movie_data = self.parse_movie_detail(link)
                    if movie_data:
                        page_movies.append(movie_data)
                    self.random_sleep(2, 5)  # 缩短详情页之间等待时间
                    
                if page_movies:
                    all_movies.extend(page_movies)
                    self.save_to_csv(page_movies)  # 每页保存一次
                
                # 每页爬取后随机等待
                if start < 225:
                    wait_time = random.uniform(3, 10)  # 随机等待3-10秒
                    logging.info(f"等待 {wait_time:.1f} 秒后继续下一页...")
                    time.sleep(wait_time)
                    
        except KeyboardInterrupt:
            logging.info("用户手动停止爬取")
        except Exception as e:
            logging.error(f"爬取过程中出错: {str(e)}")
        finally:
            self.driver.quit()
            logging.info(f"爬取完成，共获取 {len(all_movies)} 部电影信息")

if __name__ == '__main__':
    spider = DoubanMovieSpider()
    spider.run() 