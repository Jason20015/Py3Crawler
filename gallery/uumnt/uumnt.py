# -*- coding:UTF-8  -*-
"""
https://www.uumnt.cc/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import traceback
from pyquery import PyQuery as pq
from common import *

SUB_PATH_LIST = ["chemo", "qingchun", "rihan", "siwa", "xinggan", "zipai"]


# 获取图集首页
def get_index_page():
    index_url = "https://www.uumnt.cc/meinv/"
    index_response = net.http_request(index_url, method="GET")
    result = {
        "max_album_id": 0,  # 最新图集id
    }
    if index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    index_response_content = index_response.data.decode(errors="ignore")
    album_page_selector = pq(index_response_content).find("#mainbodypul .listmainrows>a")
    if album_page_selector.length == 0:
        raise crawler.CrawlerException("页面截取图集信息失败\n%s" % index_response_content)
    for album_index in range(0, album_page_selector.length):
        album_url = album_page_selector.eq(album_index).attr("href")
        if not album_url:
            raise crawler.CrawlerException("图集信息截取图集地址失败\n%s" % index_response_content)
        album_id = album_url[album_url.rfind("/") + 1:album_url.rfind(".")]
        if not crawler.is_integer(album_id):
            raise crawler.CrawlerException("图集信息截取图集id类型不正确\n%s" % index_response_content)
        result["max_album_id"] = max(result["max_album_id"], int(album_id))
    return result


# 获取指定id的图集
def get_album_page(album_id):
    page_count = max_page_count = 1
    sub_path = ""
    album_pagination_url = ""
    album_pagination_response = None
    result = {
        "album_title": "",  # 图集标题
        "album_url": None,  # 图集首页地址
        "photo_url_list": [],  # 全部图片地址
        "is_delete": False,  # 是否已删除
    }
    has_error = False
    # 每页有多少张图片，如果页面有异常时尝试进行图片地址修正
    photo_count_each_page = 1
    while page_count <= max_page_count:
        if page_count == 1:
            for sub_path in SUB_PATH_LIST:
                album_pagination_url = "https://www.uumnt.cc/%s/%s.html" % (sub_path, album_id)
                album_pagination_response = net.http_request(album_pagination_url, method="GET")
                if album_pagination_response.status == 404:
                    continue
                result["album_url"] = album_pagination_url
                break
        else:
            album_pagination_url = "https://www.uumnt.cc/%s/%s_%s.html" % (sub_path, album_id, page_count)
            album_pagination_response = net.http_request(album_pagination_url, method="GET")
        if page_count == 1 and album_pagination_response.status == 404:
            result["is_delete"] = True
            return result
        elif album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
        album_pagination_response_content = album_pagination_response.data.decode(errors="ignore")
        if album_pagination_response_content.find("[1040] Too many connections") >= 0:
            has_error = True
            page_count += 1
            continue
        if not result["album_title"]:
            # 获取图集标题
            album_title = pq(album_pagination_response_content).find("h1.center").html()
            if not album_title:
                raise crawler.CrawlerException(" %s 页面截取标题失败\n%s" % (album_pagination_url, album_pagination_response_content))
            result["album_title"] = album_title[:album_title.rfind("(")]
            # 获取总页数
            last_page_selector = pq(album_pagination_response_content).find(".page a:last")
            if last_page_selector.length == 1:
                if last_page_selector.html() != "末页":
                    raise crawler.CrawlerException(" %s 页面截取最后页按钮文字不正确\n%s" % (album_pagination_url, album_pagination_response_content))
                last_pagination_url = last_page_selector.attr("href")
                if last_pagination_url is None:
                    raise crawler.CrawlerException(" %s 页面截取最后页地址失败\n%s" % (album_pagination_url, album_pagination_response_content))
                max_page_count = tool.find_sub_string(last_pagination_url, "/%s/%s_" % (sub_path, album_id), ".html")
                if not crawler.is_integer(max_page_count):
                    raise crawler.CrawlerException(" %s 最后页地址截取最后页失败\n%s" % (album_pagination_url, album_pagination_response_content))
                max_page_count = int(max_page_count)
            else:
                if pq(album_pagination_response_content).find(".page").length != 1:
                    raise crawler.CrawlerException(" %s 页面截取最后页失败\n%s" % (album_pagination_url, album_pagination_response_content))
        # 获取图集图片地址
        photo_list_selector = pq(album_pagination_response_content).find(".imgac>a img")
        if photo_list_selector.length == 0:
            if pq(album_pagination_response_content).find(".imgac").length != 1:
                raise crawler.CrawlerException(" %s 页面截取图片列表失败\n%s" % (album_pagination_url, album_pagination_response_content))
        for photo_index in range(0, photo_list_selector.length):
            photo_url = photo_list_selector.eq(photo_index).attr("src")
            # 之前页有异常，无法访问，通过图片规则修正这些丢失的图片地址
            if has_error:
                temp_list = photo_url.split("/")
                # 之前正常的图片id
                if len(result["photo_url_list"]) > 0:
                    last_photo_url = result["photo_url_list"][-1]
                    last_photo_id = last_photo_url.split("/")[-1].split(".")[0]
                    if not crawler.is_integer(last_photo_id):
                        raise crawler.CrawlerException("修正异常图片时解析上一张图片id失败 %s" % last_photo_url)
                else:
                    last_photo_id = 1
                this_photo_id, photo_file_type = temp_list[-1].split(".")
                if not crawler.is_integer(this_photo_id):
                    raise crawler.CrawlerException("修正异常图片时解析当前图片id失败 %s" % photo_url)
                # 补上之间缺失的id
                for photo_id in range(int(last_photo_id) + 1, int(this_photo_id)):
                    temp_list[-1] = "%02d.%s" % (photo_id, photo_file_type)
                    result["photo_url_list"].append("/".join(temp_list))
                has_error = False
            result["photo_url_list"].append(photo_url)
        page_count += 1
    # 最后页有异常，无法访问，通过图片规则修正这些丢失的图片地址
    if has_error:
        if len(result["photo_url_list"]) == 0:
            raise crawler.CrawlerException("所有页访问异常")
        last_photo_url = result["photo_url_list"][-1]
        temp_list = last_photo_url.split("/")
        last_photo_id, photo_file_type = temp_list[-1].split(".")
        # 上限 = 总页数 * 平均每页的图片数量
        for photo_id in range(int(last_photo_id) + 1, max_page_count * photo_count_each_page + 1):
            temp_list[-1] = "%02d.%s" % (photo_id, photo_file_type)
            result["photo_url_list"].append("/".join(temp_list))
    return result


class UUMNT(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

    def main(self):
        # 解析存档文件，获取上一次的album id
        album_id = 1
        if os.path.exists(self.save_data_path):
            file_save_info = file.read_file(self.save_data_path)
            if not crawler.is_integer(file_save_info):
                log.error("存档内数据格式不正确")
                tool.process_exit()
            album_id = int(file_save_info)
        temp_path = ""

        try:
            # 获取图集首页
            try:
                index_response = get_index_page()
            except crawler.CrawlerException as e:
                log.error("图集首页解析失败，原因：%s" % e.message)
                raise

            log.step("最新图集id：%s" % index_response["max_album_id"])

            while album_id <= index_response["max_album_id"]:
                if not self.is_running():
                    tool.process_exit(0)
                log.step("开始解析图集%s" % album_id)

                # 获取图集
                try:
                    album_response = get_album_page(album_id)
                except crawler.CrawlerException as e:
                    log.error("图集%s解析失败，原因：%s" % (album_id, e.message))
                    raise

                if album_response["is_delete"]:
                    log.step("图集%s不存在，跳过" % album_id)
                    album_id += 1
                    continue

                log.trace("图集%s《%s》 %s 解析的全部图片：%s" % (album_id, album_response["album_title"], album_response["album_url"], album_response["photo_url_list"]))
                log.step("图集%s《%s》 %s 解析获取%s张图片" % (album_id, album_response["album_title"], album_response["album_url"], len(album_response["photo_url_list"])))

                photo_index = 1
                # 过滤标题中不支持的字符
                temp_path = album_path = os.path.join(self.photo_download_path, "%05d %s" % (album_id, path.filter_text(album_response["album_title"])))
                thread_list = []
                for photo_url in album_response["photo_url_list"]:
                    if not self.is_running():
                        break
                    log.step("图集%s《%s》开始下载第%s张图片 %s" % (album_id, album_response["album_title"], photo_index, photo_url))

                    # 开始下载
                    file_path = os.path.join(album_path, "%03d.%s" % (photo_index, net.get_file_type(photo_url)))
                    thread = Download(self, file_path, photo_url, photo_index)
                    thread.start()
                    thread_list.append(thread)
                    photo_index += 1

                # 等待所有线程下载完毕
                for thread in thread_list:
                    thread.join()
                    save_file_return = thread.get_result()
                    if self.is_running() and save_file_return["status"] != 1:
                        log.error("图集%s《%s》 %s 第%s张图片 %s 下载失败，原因：%s" % (album_id, album_response["album_title"], album_response["album_url"], thread.photo_index, thread.photo_url, crawler.download_failre(save_file_return["code"])))
                if self.is_running():
                    log.step("图集%s《%s》全部图片下载完毕" % (album_id, album_response["album_title"]))
                else:
                    tool.process_exit(0)

                # 图集内图片全部下载完毕
                temp_path = ""  # 临时目录设置清除
                self.total_photo_count += photo_index - 1  # 计数累加
                album_id += 1  # 设置存档记录
        except SystemExit as se:
            if se.code == 0:
                log.step("提前退出")
            else:
                log.error("异常退出")
            # 如果临时目录变量不为空，表示某个图集正在下载中，需要把下载了部分的内容给清理掉
            if temp_path:
                path.delete_dir_or_file(temp_path)
        except Exception as e:
            log.error("未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())

        # 重新保存存档文件
        file.write_file(str(album_id), self.save_data_path, file.WRITE_FILE_TYPE_REPLACE)
        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    def __init__(self, main_thread, file_path, photo_url, photo_index):
        crawler.DownloadThread.__init__(self, [], main_thread)
        self.file_path = file_path
        self.photo_url = photo_url
        self.photo_index = photo_index
        self.result = None

    def run(self):
        self.result = net.save_net_file(self.photo_url, self.file_path, header_list={"Referer": "https://www.uumnt.cc/"})
        self.notify_main_thread()

    def get_result(self):
        return self.result


if __name__ == "__main__":
    UUMNT().main()
