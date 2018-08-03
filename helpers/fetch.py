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
            return random.choice(self.proxyPools)
        except Exception as e:
            return None

    def remove_proxy(self, proxy):
        self.redisdb.lrem('ips', 1, proxy.split('://')[1])
        self.proxyPools.remove(proxy)
    
    async def fetch(self, session, url):
            while True:
                proxy = self.get_proxy()
                try:
                    async with session.get(url, proxy=proxy) as resp:
                        if resp.status == 200:
                            return await resp.text(encoding=None, errors='ignore')
                        return await ''
                except Exception as e:
                    print('fetch error:', e)
                    if proxy:
                        self.remove_proxy(proxy) 
    
    async def test(self):
        async with aiohttp.ClientSession() as session:
            resp = await self.fetch(session, 'http://search.taojindi.com/list/c_1033987/?pn=3')
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