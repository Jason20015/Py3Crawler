# -*- coding:UTF-8  -*-
"""
V聊视频公共方法
http://www.vchat6.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
from common import *
from common import crypto

USER_ID = ""
USER_KEY = ""
token_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "info\\session"))


# 检查登录信息
def check_login():
    global USER_ID, USER_KEY
    # 文件存在，检查格式是否正确
    if os.path.exists(token_file_path):
        api_info = tool.json_decode(crypto.Crypto().decrypt(tool.read_file(token_file_path)))
        if crawler.check_sub_key(("user_id", "user_key"), api_info):
            # 验证token是否有效
            if check_token(api_info["user_id"], api_info["user_key"]):
                # 设置全局变量
                USER_ID = api_info["user_id"]
                USER_KEY = api_info["user_key"]
                return True
            log.step("登录信息已过期")
        # token已经无效了，删除掉
        path.delete_dir_or_file(token_file_path)
    while True:
        input_str = input(crawler.get_time() + " 未检测到api信息，是否手动输入手机号码+密码登录(1)、或者直接输入api信息进行验证(2)、或者退出程序(E)xit？").lower()
        if input_str in ["e", "exit"]:
            tool.process_exit()
        elif input_str not in ["1", "2"]:
            continue
        elif input_str == "1":
            phone_number = input(crawler.get_time() + " 请输入手机号：")
            password = input(crawler.get_time() + " 请输入密码：")
            # 模拟登录
            login_status, error_message = login(phone_number, password)
            if login_status is False:
                log.step("登录失败，原因：%s" % error_message)
                continue
        elif input_str == "2":
            user_id = input(crawler.get_time() + " 请输入USER ID: ")
            user_key = input(crawler.get_time() + " 请输入USER KEY; ")
            # 验证token是否有效
            if not check_token(user_id, user_key):
                log.step("无效的登录信息，请重新输入")
                continue
            # 设置全局变量
            USER_ID = user_id
            USER_KEY = user_key
        # 加密保存到文件中
        tool.write_file(crypto.Crypto().encrypt(json.dumps({"user_id": USER_ID, "user_key": USER_KEY})), token_file_path, tool.WRITE_FILE_TYPE_REPLACE)
        return True
    return False


# 模拟使用手机号码+密码登录
def login(phone_number, password):
    global USER_ID, USER_KEY
    login_url = "http://sp40.vliao12.com/auth/phone-number-login"
    post_data = {
        "phoneNumber": phone_number,
        "password": password,
        "appVersion": "4.0",
    }
    login_response = net.http_request(login_url, method="POST", fields=post_data, json_decode=True)
    if login_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(login_response.status))
    if not crawler.check_sub_key(("result", "user"), login_response.json_data):
        raise crawler.CrawlerException("返回信息`result`或`user`字段不存在\n%s" % login_response.json_data)
    if login_response.json_data["result"] is False:
        if crawler.check_sub_key(("errorMsg",), login_response.json_data):
            return False, login_response.json_data["errorMsg"]
        raise crawler.CrawlerException("返回信息`result`字段取值不正确\n%s" % login_response.json_data)
    if not crawler.check_sub_key(("id", "userKey"), login_response.json_data["user"]):
        raise crawler.CrawlerException("返回信息`id`或`userKey`字段不存在\n%s" % login_response.json_data)
    USER_ID = login_response.json_data["user"]["id"]
    USER_KEY = login_response.json_data["user"]["userKey"]
    return True, ""


# 验证user_id和user_key是否匹配
def check_token(user_id, user_key):
    index_url = "http://v3.vliao3.xyz/v31/user/mydata"
    post_data = {
        "userId": user_id,
        "userKey": user_key,
    }
    index_response = net.http_request(index_url, method="POST", fields=post_data, json_decode=True)
    if index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        if crawler.check_sub_key(("result",), index_response.json_data) and index_response.json_data["result"] is True:
            return True
    return False
