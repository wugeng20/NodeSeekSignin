import base64
import hashlib
import hmac
import os
import time
import urllib.parse

from curl_cffi import requests

# NodeSeek环境变量
## 获取NodeSeek Cookie环境变量
NS_COOKIE = os.environ.get("NS_COOKIE", "")

## NodeSeek签到模式：true->随机签到 false->固定签到，默认随机签到
NS_RANDOM = os.environ.get("NS_RANDOM", "true")

## NodeSeek成员ID，https://www.nodeseek.com/space/26589 ->26589就是成员ID
NS_MEMBER_ID = os.environ.get("NS_MEMBER_ID", "")

# 钉钉机器人通知
## 钉钉机器人Token,access_token=XXX 等于=符号后面的XXX即可
DD_BOT_TOKEN = os.environ.get("DD_BOT_TOKEN", "")

## 钉钉机器人Secret
DD_BOT_SECRET = os.environ.get("DD_BOT_SECRET", "")


# 延时函数
def delay(seconds):
    time.sleep(seconds)


# NodeSeek用户信息，不设置NodeSeek成员ID则不显示
def ns_info(ns_member_id):
    if not ns_member_id:
        print(
            "未设置NodeSeek成员ID，请检测NS_MEMBER_ID环境变量设置是否正确，跳过NodeSeek用户信息获取"
        )
        return

    url = f"https://www.nodeseek.com/api/account/getInfo/{ns_member_id}?readme=1"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://www.nodeseek.com",
        "Referer": "https://www.nodeseek.com/space/{ns_member_id}",
        "Sec-CH-UA": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    }
    try:
        response = requests.get(url, headers=headers, impersonate="chrome110")
        # 示例：{'success': True, 'detail': {'member_id': 26589, 'member_name': 'WG', 'isAdmin': 0, 'rank': 1, 'coin': 226, 'bio': '技术宅拯救世界！', 'created_at': '2025-02-02T05:52:33.000Z', 'nPost': 0, 'nComment': 5, 'follows': 0, 'fans': 0, 'created_at_str': '99days ago', 'roles': []}}
        data = response.json()
        ns_user_data = data["detail"]
        return f"用户信息：\n【用户】：{ns_user_data['member_name']}\n【等级】：{ns_user_data['rank']}\n【鸡腿数目】：{ns_user_data['coin']}\n【主题帖数】：{ns_user_data['nPost']}\n【评论数】：{ns_user_data['nComment']}"
    except Exception as e:
        print("NodeSeek用户信息获取失败，错误信息: ", str(e))
        return "用户信息报错：NodeSeek用户信息获取失败，请检查成员ID是否正确"


# NodeSeek签到
def ns_signin(ns_cookie, ns_random="true"):
    if not ns_cookie:
        print("未设置NodeSeek Cookie，请检查NS_COOKIE环境变量设置是否正确")
        return "签到失败：未设置NodeSeek Cookie，请检查NS_COOKIE环境变量设置是否正确"

    url = f"https://www.nodeseek.com/api/attendance?random={ns_random}"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Length": "0",
        "Origin": "https://www.nodeseek.com",
        "Referer": "https://www.nodeseek.com/board",
        "Sec-CH-UA": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Cookie": ns_cookie,
    }

    try:
        response = requests.post(url, headers=headers, impersonate="chrome110")
        # 示例：{'success': False, 'message': '今天已完成签到，请勿重复操作'}
        data = response.json()
        msg = data.get("message", "")
        return f"签到信息：{msg}"
    except Exception as e:
        print("NodeSeek签到报错，错误信息: ", str(e))
        return "签到报错：NodeSeek签到报错，请检查Cookie是否正确"


# 消息推送到钉钉
def send_to_dingtalk(token, secret, message):
    # 生成时间戳和签名
    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode("utf-8")
    string_to_sign = f"{timestamp}\n{secret}"
    string_to_sign_enc = string_to_sign.encode("utf-8")
    hmac_code = hmac.new(
        secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    # 生成请求URL
    url = f"https://oapi.dingtalk.com/robot/send?access_token={token}&timestamp={timestamp}&sign={sign}"
    headers = {"Content-Type": "application/json"}
    data = {
        "msgtype": "text",
        "text": {
            "content": f"「NodeSeek签到」\n{message}\n时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
        },
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        print("消息推送成功：", response)
    else:
        print("消息推送失败：", response)


if __name__ == "__main__":
    print("===========================正在进行NodeSeek签到==========================")
    # 示例输出：签到信息:今天已完成签到，请勿重复操作
    ns_signin_data = ns_signin(NS_COOKIE, NS_RANDOM)
    print(ns_signin_data)
    delay(3)  # 等待3秒
    print("=========================正在获取NodeSeek用户信息=========================")
    # 示例输出：用户信息：\n【用户】：WG\n【等级】：1\n【鸡腿数目】：226\n【主题帖数】：0\n【评论数】：5
    ns_info_data = ns_info(NS_MEMBER_ID)
    print(ns_info_data)
    print("=========================正在推送NodeSeek签到信息=========================")
    send_to_dingtalk(
        DD_BOT_TOKEN, DD_BOT_SECRET, str(ns_info_data) + "\n" + str(ns_signin_data)
    )
    print("=============================NodeSeek运行结束============================")
