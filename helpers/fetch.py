#codinf: utf-8

import requests
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

    def get_new_proxy(self):
        return requests.get("http://127.0.0.1:5010/get/").content

    def del_new_proxy(self, proxy):
        requests.get("http://127.0.0.1:5010/delete/?proxy={}".format(proxy))    
   
    async def fetch(self, session, url):
            while True:
                proxy = self.get_new_proxy()
                proxy = proxy.decode()
                if proxy.startswith('no'):
                    proxy=''
                print('proxy:', proxy)
                try:
                    if proxy:
                        async with session.get(url, timeout=10, proxy='http://{}'.format(proxy)) as resp:
                            print(resp.status, url)
                            if resp.status == 200:
                                return await resp.text(encoding=None, errors='ignore')
                            elif resp.status in [404, 407, 403]:
                                return ''
                    else:
                        await asyncio.sleep(random.choice([2,3,4,5]))
                        async with session.get(url, timeout=10) as resp:
                            print(resp.status, url)
                            if resp.status == 200:
                                return await resp.text(encoding=None, errors='ignore')
                            elif resp.status == 404:
                                return  ''
                except Exception as e:
                    print('fetch error:', str(e))
                    print(proxy)
                    if proxy:
                        self.del_new_proxy(proxy) 
    
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
