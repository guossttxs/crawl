#coding: utf-8

import re
import os
import sys
import xlwt
import xlrd
import asyncio
import aiohttp
from xlutils.copy import copy
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
            companys = self.mdb.tjd_company.find({'industry.name': industry}, no_cursor_timeout=True)
            for company in companys:
                if not company.get('name') and not company.get('getSuc'):
                    async with aiohttp.ClientSession(headers=self.header) as session:
                        while True:
                            url = company.get('url')
                            content = await self.Fetch.fetch(session, url)
                            info = self.parseCompanyInfo(content)
                            if info is not None:
                                print('company name:', info.get('name'))
                                print('company info', info)
                                if info:
                                    has_company = self.mdb.tjd_company.find_one({'name': info.get('name')})
                                    if not has_company:
                                        info['getSuc'] = True
                                        company.update(info)
                                        self.mdb.tjd_company.save(company)
                                    else:
                                        self.mdb.tjd_company.remove(company)
                                else:
                                    print(url)
                                    company['getSuc'] = False
                                    self.mdb.tjd_company.save(company)
                                break

    def parseCompanyInfo(self, content):
        company_info = {}
        soup = BeautifulSoup(content, 'lxml-xml')
        title = soup.find(text=re.compile('有道首页'))
        if title:
            return None
        company_name = soup.find('div', class_=re.compile('name'))
        print(company_name)
        if company_name:
            if isinstance(company_name, str):
                company_info['name'] = company_name.strip()
            else:
                company_info['name'] = company_name.text.strip()
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
                    if len(sinfo) == 1:
                        rinfo = sinfo[0].strip()
                    else:
                        rinfo = sinfo[1].strip()
                    company_info[key] = rinfo
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
                    company = self.mdb.tjd_company.find({'industry.category': category})
                    if not company.count():
                        page = 1
                    else:
                        if company.count() == 1:
                            end_company = company[0]
                        else:
                            end_company = company.skip(company.count()-1).limit(1)
                        page = end_company.get('industry').get('pageNum')
                        page = page if page else 1
                    async with aiohttp.ClientSession(headers=self.header) as session:
                        url = srcurl
                        while True:
                            if not maxPage or page < maxPage:
                                print('start request:', url)
                                content = await self.Fetch.fetch(session, url)
                                companys, isEndPage = self.parseComponylist(content)
                                if companys:
                                    await self.saveCompanylist(companys, industry, category['title'], page)
                                    page += 1
                                    url = '{}?pn={}'.format(srcurl, page)
                                else:
                                    break

    async def saveCompanylist(self, companys, industry, category, page):
        print('save {}行业 {}类别 company'.format(industry, category))
        for company in companys:
            company['industry'] = {
                'name': industry,
                'category': category,
                'pageNum': page
            }
            url = company.get('url')
            if not self.mdb.tjd_company.find_one({'url': url}):
                async with aiohttp.ClientSession(headers=self.header) as session:
                    while True:
                        content = await self.Fetch.fetch(session, url)
                        info = self.parseCompanyInfo(content)
                        if info is not None:
                            if info:
                                has_company = self.mdb.tjd_company.find_one({'name': info.get('name')})
                                if not has_company:
                                    info['getSuc'] = True
                                    company.update(info)
                                    self.mdb.tjd_company.save(company)
                                else:
                                    self.mdb.tjd_company.remove(company)
                            else:
                                company['getSuc'] = False
                                self.mdb.tjd_company.save(company)
                            break
            
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

    def init_excel_file(self, filename):
        titles = ['公司', '行业', '联系人', '联系电话', '手机', '地址']
        if not os.path.isfile(filename):
            wb = xlwt.Workbook(encoding='utf-8')
            sheet_name = 'tjd'
            sheet_obj = wb.add_sheet(sheet_name, cell_overwrite_ok=True)
            for i, v in enumerate(titles):
                sheet_obj.write(0, i, v)
            wb.save(filename)

    def saveToExcel(self):
        '''
        存到execl文件
        compiles = {
            'contact_name': '联系人', 
            'tel': '电话', 
            'mobile': '手机', 
            'fax': '传真', 
            'zipCode': '邮编', 
        }
        '''
        root = '/Users/guoss/Desktop/'
        filename = '{}tjd.xls'.format(root)
        self.init_excel_file(filename)
        companys = self.mdb.tjd_company.find({'getSuc': True})
        rb = xlrd.open_workbook(filename, formatting_info=True)
        wb = copy(rb)
        wsheet = wb.get_sheet(0)
        for index, company in enumerate(companys):
            col_data = [
                company.get('name'), 
                company.get('industry').get('name'),
                company.get('contact_name'),
                company.get('tel'),
                company.get('mobile'),
                company.get('address')
            ]
            for j, col in enumerate(col_data):
                wsheet.write(index, j, col)
        wb.save(filename)


if __name__ == '__main__':
    tjd = Tjd()
    industrys_obj = mdb.tjd_industry.find()
    has_save_industry = ['珠宝首饰', '环保', '安防']
    industrys = [industry.get('industry') for industry in industrys_obj if industry not in has_save_industry]
    loop = asyncio.get_event_loop()
    tasks = [tjd.getComponyList(industrys, 1000)]
    loop.run_until_complete(asyncio.wait(tasks))
    #tjd.saveToExcel()
