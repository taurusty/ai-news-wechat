import asyncio


def run(coro):
    """在同步上下文运行一次协程。

    注意：不要在同一进程里反复用 asyncio.run() 分段跑多个协程并交叉关闭网络资源，
    Windows ProactorEventLoop 下容易触发 'Event loop is closed'。

    我们在 app.main 中会改成只调用一次 run(async_main()).
    """
    return asyncio.run(coro)
