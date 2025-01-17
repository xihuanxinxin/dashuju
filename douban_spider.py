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
        # 重新定义更合理的列名
        self.columns = [
            'movie_id',          # 电影ID
            'title',             # 电影标题
            'original_title',    # 原始标题
            'year',              # 年份
            'director',          # 导演
            'screenwriter',      # 编剧
            'actors',            # 主演
            'genre',             # 类型
            'country',           # 制片国家/地区
            'language',          # 语言
            'release_date',      # 上映日期
            'runtime',           # 片长
            'rating_score',      # 评分
            'rating_count',      # 评分人数
            'summary',           # 简介
            'poster_url'         # 海报链接
        ]
        
        # 定义电影ID区间
        self.id_ranges = [
            (36766189, 36866189),  # 经典老电影
            (36666189, 36766189),  # 较早期电影
            (36566189, 36666189),  # 近期电影
            (36466189, 36566189)  # 最新电影
        ]
        
        self.csv_file = 'douban_movies.csv'
        self.batch_size = 50
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
            
    def random_sleep(self, min_time=1, max_time=3):
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
            
            # 获取电影ID
            movie['movie_id'] = movie_id if movie_id else url.split('/')[-2]
            
            # 获取标题
            try:
                title_element = self.driver.find_element(By.XPATH, '//h1/span[1]')
                movie['title'] = title_element.text.strip()
            except:
                logging.info(f"无法获取电影标题，跳过 ID: {movie_id}")
                return None
                
            # 获取原始标题
            try:
                original_title = self.driver.find_element(By.XPATH, '//span[@property="v:itemreviewed"]').text
                # 如果原始标题包含中文标题，去掉中文标题部分
                if movie['title'] in original_title:
                    original_title = original_title.replace(movie['title'], '').strip()
                movie['original_title'] = original_title
            except:
                movie['original_title'] = ''
            
            # 获取基本信息
            info = self.driver.find_element(By.ID, 'info').text
            info_dict = {}
            for line in info.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    info_dict[key.strip()] = value.strip()
            
            # 提取年份
            try:
                year_text = self.driver.find_element(By.XPATH, '//span[@class="year"]').text
                movie['year'] = year_text.strip('()')
            except:
                movie['year'] = info_dict.get('年份', '')
            
            # 提取其他信息
            movie['director'] = info_dict.get('导演', '')
            movie['screenwriter'] = info_dict.get('编剧', '')
            movie['actors'] = info_dict.get('主演', '')
            movie['genre'] = info_dict.get('类型', '')
            movie['country'] = info_dict.get('制片国家/地区', '')
            movie['language'] = info_dict.get('语言', '')
            movie['release_date'] = info_dict.get('上映日期', '')
            movie['runtime'] = info_dict.get('片长', '')
            
            # 获取评分信息
            try:
                movie['rating_score'] = self.driver.find_element(By.CLASS_NAME, 'rating_num').text
                rating_count_element = self.driver.find_element(By.CLASS_NAME, 'rating_people')
                movie['rating_count'] = rating_count_element.text.split('人评价')[0]
            except:
                movie['rating_score'] = ''
                movie['rating_count'] = ''
            
            # 获取剧情简介
            try:
                summary_element = self.driver.find_element(By.CSS_SELECTOR, 'span.all.hidden')
                # 处理简介文本，替换回车和换行符为空格
                summary_text = summary_element.text.strip()
                summary_text = ' '.join(summary_text.split())  # 将所有空白字符（包括回车换行）替换为单个空格
                movie['summary'] = summary_text
            except:
                try:
                    # 尝试获取短简介
                    summary_element = self.driver.find_element(By.CSS_SELECTOR, 'span[property="v:summary"]')
                    summary_text = summary_element.text.strip()
                    summary_text = ' '.join(summary_text.split())  # 同样处理短简介的换行
                    movie['summary'] = summary_text
                except:
                    movie['summary'] = ''
            
            # 获取海报URL
            try:
                movie['poster_url'] = self.driver.find_element(By.ID, 'mainpic').find_element(By.TAG_NAME, 'img').get_attribute('src')
            except:
                movie['poster_url'] = ''
            
            logging.info(f"成功解析电影: {movie['title']} (ID: {movie['movie_id']})")
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
                        # 减少等待时间
                        wait_time = random.uniform(1, 3)
                        logging.info(f"等待 {wait_time:.1f} 秒后继续...")
                        time.sleep(wait_time)
                        
                        movie_data = self.parse_movie_detail(movie_id=current_id)
                        
                        if movie_data:
                            batch_movies.append(movie_data)
                            total_entries += 1
                            logging.info(f"成功爬取第 {total_entries} 条数据")
                            
                            # 每50条保存一次，减少保存频率
                            if len(batch_movies) >= self.batch_size:
                                self.save_to_csv(batch_movies)
                                batch_movies = []
                                # 保存后等待时间也减少
                                time.sleep(random.uniform(2, 5))
                                
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
                        time.sleep(random.uniform(5, 10))  # 减少超时后的等待时间
                        continue
                    except Exception as e:
                        logging.error(f"处理ID {current_id} 时出错: {str(e)}")
                        time.sleep(random.uniform(2, 5))  # 减少错误后的等待时间
                        continue
                    finally:
                        current_id += 1
                        
                # 每个区间结束后等待时间也减少
                time.sleep(random.uniform(3, 7))
                    
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
                    self.random_sleep(1, 3)  # 减少每部电影之间的等待时间
                    
                if page_movies:
                    all_movies.extend(page_movies)
                    self.save_to_csv(page_movies)
                
                if start < 225:
                    wait_time = random.uniform(2, 5)  # 减少翻页等待时间
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