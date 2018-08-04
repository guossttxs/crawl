#codinf: utf-8

import asyncio
import aiohttp
import random

class AsyncFetch():
    def __init__(self, rdb):
        self.redisdb = rdb
        self.proxyPools = self.get_proxy_pool()
        self.header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.94 Safari/537.36'}
    
    def get_proxy_pool(self):
        proxy_list = []
        ip_list = []
        for i in range(0, self.redisdb.llen('ips')):
            proxy_list.append(self.redisdb.lindex('ips', i).decode())
        for ip in proxy_list:
            ip_list.append('http://' + ip)
        return ip_list

    def get_proxy(self):
        try:
            pool = self.get_proxy_pool()
            return random.choice(pool)
        except Exception as e:
            print('get proxy error:', e)
            return None

    def remove_proxy(self, proxy):
        self.redisdb.lrem('ips', 1, proxy.split('://')[1])
        self.proxyPools.remove(proxy)
    
    async def fetch(self, session, url):
            while True:
                proxy = self.get_proxy()
                print('proxy:', proxy)
                try:
                    if proxy:
                        async with session.get(url, timeout=10, proxy=proxy) as resp:
                            print(resp.status, url)
                            if resp.status == 200:
                                return await resp.text(encoding=None, errors='ignore')
                            return ''
                    else:
                        await asyncio.sleep(random.choice([2,3,4,5]))
                        async with session.get(url, timeout=10) as resp:
                            print(resp.status, url)
                            if resp.status == 200:
                                print(resp.text())
                                return await resp.text(encoding=None, errors='ignore')
                            return  ''
                except Exception as e:
                    print('fetch error:', str(e))
                    print(proxy)
                    if proxy:
                        self.remove_proxy(proxy) 
    
    async def test(self):
        async with aiohttp.ClientSession() as session:
            resp = await self.fetch(session, 'http://www.taojindi.com/product/142999859.html')
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp, ['lxml', 'xml'])
            return soup

    def runtest(self):
        loop = asyncio.get_event_loop()
        resp = loop.run_until_complete(self.test())
        print(resp)
        return resp

if __name__ == '__main__':
    pass
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
