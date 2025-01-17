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
        self.base_url = 'https://movie.douban.com/subject/'
        self.top250_url = 'https://movie.douban.com/top250'
        self.columns = ['Title', 'Year', 'Rated', 'Released', 'Season', 'Episode', 
                       'Runtime', 'Genre', 'Director', 'Writer', 'Actors', 'Plot',
                       'Language', 'Country', 'Awards', 'Poster', 'Metascore',
                       'imdbRating', 'imdbVotes', 'imdbID', 'seriesID', 'Type', 'MovieID']
        
        # 定义电影ID区间
        self.id_ranges = [
            (1290000, 1300000),  # 经典老电影
            (1400000, 1500000),  # 较早期电影
            (3000000, 3500000),  # 近期电影
            (25800000, 26000000)  # 最新电影
        ]
        
        self.csv_file = 'douban_movies.csv'
        self.batch_size = 25
        self.max_entries = 10000
        
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
        
    def get_csv_info(self):
        """获取CSV文件信息"""
        if not os.path.exists(self.csv_file):
            print("CSV文件不存在")
            return 0
            
        try:
            # 读取CSV文件，指定列名
            df = pd.read_csv(self.csv_file, names=self.columns)
            
            # 删除所有空行
            df = df.dropna(how='all')
            
            # 获取实际的数据行数
            total_entries = len(df)
            print(f"\n当前CSV文件中有效数据行数: {total_entries}")
            return total_entries
            
        except pd.errors.EmptyDataError:
            print("CSV文件为空")
            return 0
        except Exception as e:
            print(f"读取CSV文件失败: {str(e)}")
            return 0
            
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

    def parse_movie_detail(self, url=None, movie_id=None):
        """解析电影详情页"""
        if movie_id:
            url = f"{self.base_url}{movie_id}/"
            
        if not self.get_page(url):
            return None
            
        try:
            # 检查页面是否存在
            if "页面不存在" in self.driver.title or "条目不存在" in self.driver.title:
                logging.info(f"电影ID {movie_id} 不存在")
                return None
                
            movie = {}
            
            # 添加电影ID
            if movie_id:
                movie['MovieID'] = movie_id
            else:
                movie['MovieID'] = url.split('/')[-2]
            
            # 标题
            try:
                movie['Title'] = self.driver.find_element(By.XPATH, '//h1/span[1]').text.strip()
            except:
                logging.info(f"无法获取电影标题，跳过 ID: {movie_id}")
                return None
            
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
            
            logging.info(f"成功解析电影: {movie['Title']} (ID: {movie['MovieID']})")
            return movie
            
        except Exception as e:
            logging.error(f"解析电影详情页失败: {str(e)}")
            return None
            
    def save_to_csv(self, movies):
        """保存数据到CSV文件"""
        if not movies:
            logging.warning("没有电影数据可保存")
            return
            
        try:
            df = pd.DataFrame(movies)
            # 确保列的顺序一致
            df = df.reindex(columns=self.columns)
            
            if os.path.exists(self.csv_file):
                # 追加模式
                df.to_csv(self.csv_file, mode='a', header=False, index=False, encoding='utf-8-sig')
            else:
                # 新建文件
                df.to_csv(self.csv_file, index=False, encoding='utf-8-sig')
            logging.info(f"保存 {len(movies)} 部电影数据到 {self.csv_file}")
        except Exception as e:
            logging.error(f"保存数据失败: {str(e)}")
            
    def crawl_by_id_ranges(self):
        """按ID区间爬取电影数据"""
        total_entries = self.get_csv_info()  # 只取总数
        batch_movies = []
        
        try:
            for start_id, end_id in self.id_ranges:
                if total_entries >= self.max_entries:
                    break
                    
                logging.info(f"开始爬取ID区间: {start_id} - {end_id}")
                current_id = start_id
                
                while current_id <= end_id and total_entries < self.max_entries:
                    try:
                        # 增加更长的随机等待时间
                        wait_time = random.uniform(3, 10)
                        logging.info(f"等待 {wait_time:.1f} 秒后继续...")
                        time.sleep(wait_time)
                        
                        movie_data = self.parse_movie_detail(movie_id=current_id)
                        
                        if movie_data:
                            batch_movies.append(movie_data)
                            total_entries += 1
                            logging.info(f"成功爬取第 {total_entries} 条数据")
                            
                            # 每25条保存一次
                            if len(batch_movies) >= self.batch_size:
                                self.save_to_csv(batch_movies)
                                batch_movies = []
                                # 保存后额外等待，降低频率
                                time.sleep(random.uniform(5, 15))
                                
                            # 检查是否达到目标条数
                            if total_entries >= self.max_entries:
                                if batch_movies:  # 保存最后的批次
                                    self.save_to_csv(batch_movies)
                                logging.info(f"已达到目标条目数 {self.max_entries}，程序终止")
                                return
                                
                        else:
                            logging.info(f"ID {current_id} 未获取到有效数据，跳过")
                            
                    except TimeoutException:
                        logging.error(f"访问ID {current_id} 超时，等待后继续")
                        time.sleep(random.uniform(10, 20))  # 超时后等待更长时间
                        continue
                    except Exception as e:
                        logging.error(f"处理ID {current_id} 时出错: {str(e)}")
                        time.sleep(random.uniform(5, 10))
                        continue
                    finally:
                        current_id += 1
                        
                # 每个区间结束后保存剩余数据
                if batch_movies:
                    self.save_to_csv(batch_movies)
                    batch_movies = []
                    
                # 每个区间结束后额外等待
                time.sleep(random.uniform(10, 20))
                    
        except KeyboardInterrupt:
            logging.info("用户手动停止爬取")
            if batch_movies:
                self.save_to_csv(batch_movies)
        except Exception as e:
            logging.error(f"爬取过程中出错: {str(e)}")
            if batch_movies:
                self.save_to_csv(batch_movies)
        finally:
            if batch_movies:
                self.save_to_csv(batch_movies)
                
    def crawl_top250(self):
        """爬取豆瓣Top250电影"""
        all_movies = []
        
        try:
            for start in range(0, 250, 25):
                url = f"{self.top250_url}?start={start}"
                logging.info(f"正在访问第 {start//25 + 1} 页: {url}")
                
                if not self.get_page(url):
                    logging.error(f"获取第 {start//25 + 1} 页失败")
                    self.random_sleep(3, 8)
                    continue
                
                movie_links = self.parse_movie_list()
                page_movies = []
                
                for link in movie_links:
                    movie_data = self.parse_movie_detail(url=link)
                    if movie_data:
                        page_movies.append(movie_data)
                    self.random_sleep(2, 5)
                    
                if page_movies:
                    all_movies.extend(page_movies)
                    self.save_to_csv(page_movies)
                
                if start < 225:
                    wait_time = random.uniform(3, 10)
                    logging.info(f"等待 {wait_time:.1f} 秒后继续下一页...")
                    time.sleep(wait_time)
                    
        except Exception as e:
            logging.error(f"爬取Top250过程中出错: {str(e)}")
            
        return len(all_movies)
            
    def run(self):
        """运行爬虫"""
        print("\n开始爬取豆瓣电影数据...")
        
        try:
            # 第一步：检查现有数据量
            total_entries = self.get_csv_info()
            
            # 第二步：判断是否需要继续爬取
            if total_entries >= self.max_entries:
                print(f"已达到目标条目数 {self.max_entries}，程序终止")
                return
                
            # 第三步：登录豆瓣
            self.driver.get('https://www.douban.com')
            input("\n请登录豆瓣账号，登录完成后按回车继续...")
            print("用户已确认登录完成")
            
            # 第四步：根据数据量决定爬取策略
            has_enough_data = total_entries >= 250
            print(f"\n>>> 判断结果: 数据量({total_entries}) >= 250 ? {has_enough_data}")
            
            if has_enough_data:
                print(f"\n>>> CSV文件中已有 {total_entries} 条数据，开始按ID区间爬取...")
                self.crawl_by_id_ranges()
            else:
                print(f"\n>>> CSV文件中只有 {total_entries} 条数据，开始爬取Top250...")
                self.crawl_top250()
                # 更新数据量
                total_entries = self.get_csv_info()
                # 如果还未达到目标数量，继续按ID区间爬取
                if total_entries < self.max_entries:
                    print("\n>>> 继续按ID区间爬取更多电影...")
                    self.crawl_by_id_ranges()
                
        except KeyboardInterrupt:
            print("\n用户手动停止爬取")
        except Exception as e:
            print(f"\n爬取过程中出错: {str(e)}")
        finally:
            self.driver.quit()
            final_count = self.get_csv_info()
            print(f"\n爬取完成，当前共有 {final_count} 条数据")

if __name__ == '__main__':
    spider = DoubanMovieSpider()
    spider.run() 