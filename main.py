# cron:10 0 * * *
# new Env('NS&DF一体化签到');
"""
NodeSeek&DeepFlood论坛-自动签到Cookie版
Version: 1.1.0
create Time: 2025-5-13 16:21:43
Last Updated: 2025-10-2 15:30:00
Author: G.E.N.G
GitHub: https://github.com/wugeng20
Description: 用于 NodeSeek 、DeepFlood 论坛的每日自动签到，支持消息推送通知（调用青龙系统通知API或钉钉机器人）。
"""
import base64
import hashlib
import hmac
import os
import random
import time
import urllib.parse

import cloudscraper

# ==============================================
# 常量定义（Constant Definitions）
# ==============================================
# 论坛基础URL
NODESEEK_URL = "https://www.nodeseek.com"
DEEPFLOOD_URL = "https://www.deepflood.com"

# 随机等待时间配置（秒）
SIGNIN_WAIT_MIN = 5
SIGNIN_WAIT_MAX = 20
INFO_WAIT_MIN = 10
INFO_WAIT_MAX = 20


# ==============================================
# 初始化网络请求器（Initialize Network Scraper）
# ==============================================
def init_scraper():
    """初始化cloudscraper实例，用于处理带Cloudflare验证的请求"""
    # 从环境变量获取代理（格式：http://ip:port,https://ip:port）
    proxies = []
    ns_proxies = os.environ.get("NS_PROXIES", "")
    if not ns_proxies:
        ns_proxies = os.environ.get("PROXIES", "")

    if ns_proxies:
        proxies = [proxy.strip() for proxy in ns_proxies.split(",") if proxy.strip()]

    # 配置scraper参数，模拟浏览器行为以绕过反爬
    return cloudscraper.create_scraper(
        rotating_proxies=proxies,
        proxy_options={
            "rotation_strategy": "smart",  # 智能代理轮换策略
            "ban_time": 300,  # 代理被封禁后5分钟内不再使用
        },
        interpreter="js2py",  # 使用js2py解析JavaScript
        delay=6,  # 请求延迟（秒）
        enable_stealth=True,  # 启用隐身模式
        stealth_options={
            "min_delay": 5.0,
            "max_delay": 10.0,
            "human_like_delays": True,  # 模拟人类操作延迟
            "randomize_headers": True,  # 随机化请求头
            "browser_quirks": True,  # 模拟浏览器特性
        },
        browser="chrome",  # 模拟Chrome浏览器
        debug=False,  # 关闭调试模式
    )


# 初始化全局scraper实例
scraper = init_scraper()


# ==============================================
# 环境变量配置（Environment Configuration）
# ==============================================
class EnvConfig:
    """环境变量配置类，集中管理所有配置参数"""

    # NodeSeek配置
    ns_cookie = os.environ.get("NS_COOKIE", "")  # 用户Cookie
    ns_random = os.environ.get("NS_RANDOM", "true").lower() == "true"  # 随机签到开关
    ns_member_id = os.environ.get("NS_MEMBER_ID", "")  # 成员ID（从个人空间URL获取）

    # DeepFlood配置
    df_cookie = os.environ.get("DF_COOKIE", "")  # 用户Cookie
    df_random = os.environ.get("DF_RANDOM", "true").lower() == "true"  # 随机签到开关
    df_member_id = os.environ.get("DF_MEMBER_ID", "")  # 成员ID（从个人空间URL获取）

    # 钉钉通知配置
    dd_bot_enable = (
        os.environ.get("DD_BOT_ENABLE", "false").lower() == "true"
    )  # 钉钉开关
    dd_bot_token = os.environ.get("DD_BOT_TOKEN", "")  # 机器人Token
    dd_bot_secret = os.environ.get("DD_BOT_SECRET", "")  # 机器人密钥


# 实例化配置对象
env = EnvConfig()


# ==============================================
# 工具函数（Utility Functions）
# ==============================================
def random_wait(min_sec, max_sec):
    """
    随机等待一段时间，模拟人类操作间隔

    :param min_sec: 最小等待时间（秒）
    :param max_sec: 最大等待时间（秒）
    """
    delay = random.uniform(min_sec, max_sec)
    print(f"随机等待 {delay:.2f} 秒后继续操作...")
    time.sleep(delay)
    print("等待结束，执行下一步")


def get_current_time():
    """获取当前时间的格式化字符串"""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


# ==============================================
# 论坛签到基类（Base Forum Sign-in Class）
# ==============================================
class BaseForum:
    """论坛签到基类，封装通用签到和信息获取逻辑"""

    def __init__(self, base_url, cookie, member_id, random_signin):
        """
        初始化论坛签到实例

        :param base_url: 论坛基础URL
        :param cookie: 用户登录Cookie
        :param member_id: 成员ID
        :param random_signin: 是否随机签到
        """
        self.base_url = base_url.rstrip("/")  # 确保URL不以/结尾
        self.cookie = cookie
        self.member_id = member_id
        self.random_signin = random_signin
        self.headers = self._init_headers()

    def _init_headers(self):
        """初始化请求头，模拟Chrome浏览器"""
        return {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": f"{self.base_url}",
            "Sec-CH-UA": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        }

    def get_member_info(self):
        """
        获取用户信息（需子类实现具体逻辑）

        :return: 格式化的用户信息字符串
        """
        raise NotImplementedError("子类必须实现get_member_info方法")

    def sign_in(self):
        """
        执行签到操作（需子类实现具体逻辑）

        :return: 签到结果信息
        """
        raise NotImplementedError("子类必须实现sign_in方法")


# ==============================================
# 具体论坛实现（Specific Forum Implementations）
# ==============================================
class NodeSeekForum(BaseForum):
    """NodeSeek论坛签到实现"""

    def get_member_info(self):
        """获取NodeSeek用户信息"""
        if not self.member_id:
            return "用户信息获取失败：未设置NS_MEMBER_ID环境变量"

        # 构造用户信息请求URL
        info_url = f"{self.base_url}/api/account/getInfo/{self.member_id}?readme=1"
        self.headers["Referer"] = f"{self.base_url}/space/{self.member_id}"

        try:
            # 发送请求获取用户信息
            response = scraper.get(info_url, headers=self.headers)
            data = response.json()

            if not data.get("success", False):
                return f"用户信息获取失败：{data.get('message', '未知错误')}"

            user_data = data["detail"]
            return (
                f"用户信息：\n"
                f"【用户】：{user_data['member_name']}\n"
                f"【等级】：{user_data['rank']}\n"
                f"【鸡腿数目】：{user_data['coin']}\n"
                f"【主题帖数】：{user_data['nPost']}\n"
                f"【评论数】：{user_data['nComment']}"
            )

        except Exception as e:
            return f"用户信息获取失败：{str(e)}（请检查成员ID是否正确）"

    def sign_in(self):
        """执行NodeSeek签到"""
        if not self.cookie:
            return "签到失败：未设置NS_COOKIE环境变量"

        # 构造签到请求URL
        sign_url = f"{self.base_url}/api/attendance?random={'true' if self.random_signin else 'false'}"
        self.headers["Referer"] = f"{self.base_url}/board"
        self.headers["Cookie"] = self.cookie

        try:
            response = scraper.post(sign_url, headers=self.headers)
            # 示例：{'success': False, 'message': '今天已完成签到，请勿重复操作'}
            data = response.json()

            msg = data.get("message", "签到状态未知")
            return f"签到信息：{msg}"

        except Exception as e:
            return f"签到失败：{str(e)}（请检查Cookie是否有效或官网是否加强反爬）"


class DeepFloodForum(BaseForum):
    """DeepFlood论坛签到实现"""

    def get_member_info(self):
        """获取DeepFlood用户信息"""
        if not self.member_id:
            return "用户信息获取失败：未设置DF_MEMBER_ID环境变量"

        # 构造用户信息请求URL
        info_url = f"{self.base_url}/api/account/getInfo/{self.member_id}?readme=1"
        self.headers["Referer"] = f"{self.base_url}/space/{self.member_id}"

        try:
            # 发送请求获取用户信息
            response = scraper.get(info_url, headers=self.headers)
            data = response.json()  # DeepFlood返回直接是用户数据对象

            if not data.get("success", False):
                return f"用户信息获取失败：{data.get('message', '未知错误')}"

            user_data = data["detail"]

            return (
                f"用户信息：\n"
                f"【用户】：{user_data['member_name']}\n"
                f"【等级】：{user_data['rank']}\n"
                f"【鸡腿数目】：{user_data['coin']}\n"
                f"【主题帖数】：{user_data['nPost']}\n"
                f"【评论数】：{user_data['nComment']}"
            )

        except Exception as e:
            return f"用户信息获取失败：{str(e)}（请检查成员ID是否正确）"

    def sign_in(self):
        """执行DeepFlood签到"""
        if not self.cookie:
            return "签到失败：未设置DF_COOKIE环境变量"

        # 构造签到请求URL
        sign_url = f"{self.base_url}/api/attendance?random={'true' if self.random_signin else 'false'}"
        self.headers["Referer"] = f"{self.base_url}/board"
        self.headers["Cookie"] = self.cookie

        try:
            response = scraper.post(sign_url, headers=self.headers)
            # 示例：{'success': False, 'message': '今天已完成签到，请勿重复操作'}
            data = response.json()

            msg = data.get("message", "签到状态未知")
            return f"签到信息：{msg}"

        except Exception as e:
            return f"签到失败：{str(e)}（请检查Cookie是否有效或官网是否加强反爬）"


# ==============================================
# 消息通知模块（Notification Module）
# ==============================================
def send_dingtalk_message(token, secret, content):
    """
    发送消息到钉钉机器人

    :param token: 钉钉机器人Token
    :param secret: 钉钉机器人密钥
    :param content: 消息内容
    """
    if not token:
        print("钉钉机器人Token未配置，跳过推送")
        return

    try:
        # 生成签名（钉钉机器人安全验证）
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode("utf-8")
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret_enc, string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

        # 发送消息
        url = f"https://oapi.dingtalk.com/robot/send?access_token={token}&timestamp={timestamp}&sign={sign}"
        headers = {"Content-Type": "application/json"}
        data = {"msgtype": "text", "text": {"content": f"「论坛签到通知」\n{content}"}}

        response = scraper.post(url, json=data, headers=headers)
        response.raise_for_status()
        print("钉钉消息推送成功")

    except Exception as e:
        print(f"钉钉消息推送失败：{str(e)}")


def send_ql_notification(title, content):
    """
    发送消息到青龙面板通知系统

    :param title: 消息标题
    :param content: 消息内容
    """
    if not QLAPI:
        print("非青龙环境，跳过青龙通知推送")
        return

    try:
        response = QLAPI.systemNotify({"title": title, "content": content})
        if response.get("code") == 200:
            print("青龙通知推送成功")
        else:
            print(f"青龙通知推送失败：{response.get('message', '未知错误')}")
    except Exception as e:
        print(f"青龙通知推送失败：{str(e)}")


def push_notification(forum_name, info, sign_result):
    """
    统一推送通知入口

    :param forum_name: 论坛名称
    :param info: 用户信息
    :param sign_result: 签到结果
    """
    content = (
        f"【{forum_name}】\n"
        f"{info}\n"
        f"{sign_result}\n"
        f"操作时间：{get_current_time()}"
    )

    try:
        if env.dd_bot_enable:
            send_dingtalk_message(env.dd_bot_token, env.dd_bot_secret, content)
        else:
            send_ql_notification(f"「{forum_name}签到」", content)
    except Exception as e:
        print(f"通知推送失败：{str(e)}")
        print("请检查通知配置：")
        print("1、本地运行：需开启DD_BOT_ENABLE并配置钉钉Token和Secret")
        print("2、青龙面板：需在系统设置中配置通知方式")


# ==============================================
# 主流程控制（Main Workflow Control）
# ==============================================
def run_forum_signin(forum, forum_name):
    """
    执行单个论坛的签到流程

    :param forum: 论坛实例
    :param forum_name: 论坛名称
    """
    print(f"\n======================= 开始{forum_name}签到流程 =======================")

    # 执行签到
    print(f"【1/3】正在进行{forum_name}签到...")
    random_wait(SIGNIN_WAIT_MIN, SIGNIN_WAIT_MAX)
    sign_result = forum.sign_in()
    print(sign_result)

    # 获取用户信息
    print(f"\n【2/3】正在获取{forum_name}用户信息...")
    random_wait(INFO_WAIT_MIN, INFO_WAIT_MAX)
    user_info = forum.get_member_info()
    print(user_info)

    # 推送通知
    print(f"\n【3/3】正在推送{forum_name}签到结果...")
    push_notification(forum_name, user_info, sign_result)

    print(f"======================= {forum_name}签到流程结束 =======================\n")


def main():
    """主程序入口"""
    # 执行NodeSeek签到
    if env.ns_cookie:  # 只有配置了Cookie才执行
        nodeseek = NodeSeekForum(
            base_url=NODESEEK_URL,
            cookie=env.ns_cookie,
            member_id=env.ns_member_id,
            random_signin=env.ns_random,
        )
        run_forum_signin(nodeseek, "NodeSeek")
    else:
        print("未配置NodeSeek的Cookie（NS_COOKIE），跳过NodeSeek签到")

    # 执行DeepFlood签到
    if env.df_cookie:  # 只有配置了Cookie才执行
        deepflood = DeepFloodForum(
            base_url=DEEPFLOOD_URL,
            cookie=env.df_cookie,
            member_id=env.df_member_id,
            random_signin=env.df_random,
        )
        run_forum_signin(deepflood, "DeepFlood")
    else:
        print("未配置DeepFlood的Cookie（DF_COOKIE），跳过DeepFlood签到")


if __name__ == "__main__":
    main()
