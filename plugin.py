#coding: utf-8

from pymongo import MongoClient
import redis

rdb = redis.StrictRedis(host='localhost', port=6379, db=1)
mongoConn = MongoClient(host='182.92.190.100', port=15693)
mdb = mongoConn.crawl
mdb.authenticate('guoss', 'nuan20?15xin')