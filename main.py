import re

import click
from loguru import logger
from playwright.sync_api import Playwright, sync_playwright, expect, TimeoutError

PATTERN = re.compile(r'(\d+)%')
MAX_WATCH_TIME = 60 * 60 * 1000

logger.add('log.log')


def to_be_watch(text: str):
    try:
        process = int(PATTERN.search(text).group(1))
    except:
        return False
    else:
        return process < 100


def watch_course(page):
    page.click('#tab-study')
    # 等待课程信息加载完成
    page.wait_for_selector("//div[@class='el-collapse-item']", timeout=60 * 1000)
    for section in page.locator("//div[@class='myTree']/div/div").all():
        section.click()
        for content in page.locator("//div[@class='el-collapse-item is-active']//div[@class='content_box']").all():
            text = content.text_content()
            if not to_be_watch(text):
                continue

            content.click()
            logger.info(f'start learn {text}')
            page.locator("//div[@class='prism-big-play-btn']").click()
            expect(page.locator("//div[@class='prism-big-play-btn pause']")).to_be_visible(timeout=MAX_WATCH_TIME)
            logger.success(text)


def run(playwright: Playwright, username: str, password: str, course_id: int = None) -> None:
    browser = playwright.chromium.launch(headless=False, executable_path='/usr/bin/google-chrome')
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()

    page.goto("https://ndky.youkexuetang.cn/#/schoolHome/index")
    page.get_by_text("登录").click()
    page.get_by_placeholder("请输入账号").fill(username)
    page.get_by_placeholder("请输入密码").fill(password)
    page.get_by_role("button", name="登录", exact=True).click()
    expect(page.get_by_text('学习情况')).to_be_visible(timeout=30000)
    logger.success('login success!')

    ids = []
    if course_id:
        ids.append(course_id)
    else:
        with page.expect_response('https://ndky.youkexuetang.cn/manage/student/courseStudy/list') as info:
            page.goto('https://ndky.youkexuetang.cn/student/#/courseList/courseList')
        for data in info.value.json()['data']:
            for course in data['courseVOList']:
                ids.append(course['id'])
    logger.success(ids)

    for i, course_id in enumerate(ids):
        logger.info(f'start {course_id}, {i}th, remain {len(ids) - i}')
        page.goto(f'https://ndky.youkexuetang.cn/student/#/courseList/courseList/course?id={course_id}')
        # 强制刷新 否则课程内容不刷新 依旧为上个课程的内容
        page.reload()
        page.wait_for_selector('#tab-study')
        try:
            watch_course(page)
        except TimeoutError:
            logger.warning(f'course {course_id} timeout')

    context.close()
    browser.close()


@click.command()
@click.argument('username')
@click.argument('password')
@click.option('--course-id', '-I', type=int)
def start(username, password, course_id: int):
    with sync_playwright() as playwright:
        run(playwright, username, password, course_id)


if __name__ == '__main__':
    start()
