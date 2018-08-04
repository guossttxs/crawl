#coding: utf-8

import re
import os
import sys
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from ..plugin import mdb, rdb
from ..cfgs import tjd_cfg
from ..helpers.fetch import AsyncFetch

'''淘金地接口'''
class Tjd():
    def __init__(self):
        self.mdb = mdb
        self.rdb = rdb
        self.cfg = tjd_cfg
        self.Fetch = AsyncFetch(self.rdb)
        self.header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.94 Safari/537.36'}

    async def getIndustry(self):
        '''
        获取首页行业列表信息
        '''
        async with aiohttp.ClientSession(headers=self.header) as session:
            content = await self.Fetch.fetch(session, self.cfg.first_page)
            if content:
                self.parseIndustryDocument(content)
    
    async def getCompanyInfo(self, industrys):
        '''
        获取公司信息
        '''
        for industry in industrys:
            companys = self.mdb.tjd_company.find({'industry.name': industry})
            for company in companys:
                if not company.get('name'):
                    async with aiohttp.ClientSession(headers=self.header) as session:
                        while True:
                            url = company.get('url')
                            content = await self.Fetch.fetch(session, url)
                            info = self.parseCompanyInfo(content)
                            print('company name:', info.get('name'))
                            print('company info', info)
                            if info is not None:
                                if info:
                                    has_company = self.mdb.tjd_company.find_one({'name': info.get('name')})
                                    if not has_company:
                                        info['getSuc'] = True
                                        company.update(info)
                                        self.mdb.tjd_company.update({})
                                    else:
                                        self.mdb.tjd_company.remove(company)
                                else:
                                    print(url)
                                    company['getSuc'] = False
                                    self.mdb.tjd_company.save(company)
                                return

    def parseCompanyInfo(self, content):
        company_info = {}
        soup = BeautifulSoup(content, 'lxml-xml')
        title = soup.find('title').text
        if title == '有道首页':
            return None
        company_name = soup.find('div', class_='name')
        if company_name:
            if isinstance(company_name, str):
                company_info['name'] = company_name
            else:
                company_info['name'] = company_name.text
            compiles = {
                'contact_name': '联系人', 
                'tel': '电话', 
                'mobile': '手机', 
                'fax': '传真', 
                'zipCode': '邮编', 
            }
            for key, value in compiles.items():
                info = soup.find(text=re.compile(value))
                if info:
                    sinfo = info.split('：')
                    company_info[key] = sinfo[1]
            address_div = soup.find('div', class_='address_line')
            address = address_div.text
            address = address.split('：')[1]
            company_info['address'] = address
        return company_info
        
    async def getComponyList(self, industrys, maxPage):
        '''
        获取公司列表
        '''
        for industry in industrys:
            industry_obj = self.mdb.tjd_industry.find_one({'industry': industry})
            if industry_obj:
                categorys = industry_obj.get('category')
                for category in categorys:
                    srcurl = category.get('href')
                    page = 1
                    async with aiohttp.ClientSession(headers=self.header) as session:
                        url = srcurl
                        while True:
                            if not maxPage or page < maxPage:
                                print('start request:', url)
                                content = await self.Fetch.fetch(session, url)
                                companys, isEndPage = self.parseComponylist(content)
                                if companys:
                                    self.saveCompanylist(companys, industry, category['title'], page)
                                    page += 1
                                    url = '{}?pn={}'.format(srcurl, page)
                                else:
                                    break
                            
    def saveCompanylist(self, companys, industry, category, page):
        print('save {}行业 {}类别 company'.format(industry, category))
        for company in companys:
            company['industry'] = {
                'name': industry,
                'category': category,
                'pageNum': page
            }
            if not self.mdb.tjd_company.find_one({'url': company.get('url')}):
                self.mdb.tjd_company.save(company)

    def parseComponylist(self, content):
        soup = BeautifulSoup(content, 'lxml-xml')
        #print(soup)
        clis = soup.find_all('a', href=re.compile('product/\w*.html'))
        companys = []
        for cli in clis:
            href = cli.get('href')
            document = {
                'url': href,
            }
            companys.append(document)
        
        isEndPage = False
        nextPage = soup.find('a', '下一页')
        if not nextPage:
            isEndPage = True
        return companys, isEndPage
    
    def parseIndustryDocument(self, content):
        soup = BeautifulSoup(content, 'lxml-xml')
        dd = soup.find_all('dd')
        for d in dd:
            parent_d = d.find_previous_sibling('dt')
            if parent_d:
                href_ = parent_d.find('a')
            else:
                href_ = d.find_previous_sibling('a')
            if href_:
                industry = href_.text
                industry_href = href_.get('href')
                cls_href = []
                cls_a = d.find_all('a')
                for i in cls_a:
                    title = i.text
                    href = i.get('href')
                    cls_href.append({
                        'title': title,
                        'href': href,
                        'isEnd': False
                    })
                document = {
                    'industry': industry,
                    'url': industry_href,
                    'category': cls_href
                }
                print(document['industry'])
                industry_obj = self.mdb.tjd_industry.find_one({'industry': industry})
                if not industry_obj:
                    self.mdb.tjd_industry.save(document)
                    print('保存成功')
                else:
                    print('已存在，跳过')

if __name__ == '__main__':
    tjd = Tjd()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(tjd.getComponyList(['珠宝首饰'], 1000))