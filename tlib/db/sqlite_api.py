# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/16 15:10
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

""" Python sqlite funs """
# DB-API 2.0 interface for SQLite databases

import sqlite3
import os
import unittest

'''
SQLite数据库是一款非常小巧的嵌入式开源数据库软件，也就是说
没有独立的维护进程，所有的维护都来自于程序本身。
在python中，使用sqlite3创建数据库的连接，当我们指定的数据库文件不存在的时候
连接对象会自动创建数据库文件；如果数据库文件已经存在，则连接对象不会再创建
数据库文件，而是直接打开该数据库文件。
    连接对象可以是硬盘上面的数据库文件，也可以是建立在内存中的，在内存中的数据库
    执行完任何操作后，都不需要提交事务的(commit)

    创建在硬盘上面： conn = sqlite3.connect('c:\\test\\test_sqlite.db')
    创建在内存上面： conn = sqlite3.connect('"memory:')

    下面我们以硬盘上面创建数据库文件为例来具体说明：
    conn = sqlite3.connect('c:\\test\\test_sqlite.db')
    其中conn对象是数据库链接对象，而对于数据库链接对象来说，具有以下操作：

        commit()            --事务提交
        rollback()          --事务回滚
        close()             --关闭一个数据库链接
        cursor()            --创建一个游标

    cu = conn.cursor()
    这样我们就创建了一个游标对象：cu
    在sqlite3中，所有sql语句的执行都要在游标对象的参与下完成
    对于游标对象cu，具有以下具体操作：

        execute()           --执行一条sql语句
        executemany()       --执行多条sql语句
        close()             --游标关闭
        fetchone()          --从结果中取出一条记录
        fetchmany()         --从结果中取出多条记录
        fetchall()          --从结果中取出所有记录
        scroll()            --游标滚动

'''


class SQLiteAPI(object):

    def __init__(self, db_path, show=True):
        super(SQLiteAPI, self).__init__()
        self.db_path = db_path
        self.show = show
        self.conn = self.connect()
        self.cur = self.conn.cursor()

    def __del__(self):
        try:
            if self.cur is not None:
                if self.show:
                    print('Close SQLite cursor ...')
                self.cur.close()
            if self.conn is not None:
                if self.show:
                    print('Close SQLite connect ...')
                self.conn.close()
        finally:
            pass

    def connect(self):
        """
        获取到数据库的连接对象，参数为数据库文件的绝对路径
        如果传递的参数是存在，并且是文件，那么就返回硬盘上面改
        路径下的数据库文件的连接对象；否则，返回内存中的数据接
        连接对象
        :return:
        """

        if os.path.exists(self.db_path) and os.path.isfile(self.db_path):
            if self.show:
                print('Connect SQLite: [{}]'.format(self.db_path))
            conn = sqlite3.connect(self.db_path)
            conn.text_factory = str
        else:
            if self.show:
                print('Connect SQLite: [:memory:]')
            conn = sqlite3.connect(':memory:')

        return conn

    def execute(self, sql):
        print(sql)

        try:
            rows = self.cur.execute(sql)
            self.conn.commit()
            return rows
        except Exception as e:
            self.conn.rollback()
            raise Exception(e)

    def drop_table(self, table):
        """
        drop table
        :return:
        """

        if table is not None and table != '':
            sql = 'DROP TABLE IF EXISTS ' + table
            if self.show:
                print('execute sql:[{}]'.format(sql))
            self.cur.execute(sql)
            self.conn.commit()
            print('drop table [{}] success!'.format(table))
        else:
            print('The table [{}] is empty or equal None!'.format(table))

        return True

    def create_table(self, sql):
        """
        create table
        :param sql:
        :return:
        """

        if sql is not None and sql != '':
            if self.show:
                print('execute sql:[{}]'.format(sql))
            self.cur.execute(sql)
            self.conn.commit()
            print('create tablle success')
        else:
            print('the [{}] is empty or equal None!'.format(sql))

    def insert_update_delete(self, sql, data):
        if sql is not None and sql != '':
            if data is not None:
                for d in data:
                    if self.show:
                        print('execute sql:[{}],args:[{}]'.format(sql, d))
                    self.cur.execute(sql, d)
                    self.conn.commit()
        else:
            print('The [{}] is empty or equal None!'.format(sql))

    def fetchall(self, sql):
        if self.show:
            print('execute sql:[{}]'.format(sql))

        try:
            self.cur.execute(sql)
            rows = self.cur.fetchall()
            if self.show:
                for row in rows:
                    print(row)
                print('=' * 50)
            return rows
        except Exception as e:
            self.conn.rollback()
            raise Exception(e)

    def fetchmany(self, sql, size):
        if self.show:
            print('execute sql:[{}]'.format(sql))

        try:
            self.cur.execute(sql)
            rows = self.cur.fetchmany(size)
            if self.show:
                for row in rows:
                    print(row)
                print('=' * 50)
            return rows
        except Exception as e:
            self.conn.rollback()
            raise Exception(e)

    def fetchone(self, sql):
        if self.show:
            print('execute sql:[{}]'.format(sql))

        try:
            self.cur.execute(sql)
            rows = self.cur.fetchone()
            if self.show:
                for row in rows:
                    print(row)
                print('=' * 50)
            return rows
        except Exception as e:
            self.conn.rollback()
            raise Exception(e)


class SQLiteTestCase(unittest.TestCase):
    """docstring for SQLiteTestCase"""

    def setUp(self):
        self.bd_path = 'c:\\test\\test_sqlite.db'
        pass

    def tearDown(self):
        pass

    def test_1(self):
        sqlite_obj = SQLiteAPI(self.bd_path, show=True)
        fetchall_sql = '''SELECT * FROM student'''

        sqlite_obj.drop_table('student')

        create_table = '''CREATE TABLE `student` (
                              `id` int(11) NOT NULL,
                              `name` varchar(20) NOT NULL,
                              `gender` varchar(4) DEFAULT NULL,
                              `age` int(11) DEFAULT NULL,
                              `address` varchar(200) DEFAULT NULL,
                              `phone` varchar(20) DEFAULT NULL,
                               PRIMARY KEY (`id`)
                            )'''
        sqlite_obj.create_table(create_table)
        sqlite_obj.fetchall(fetchall_sql)

        insert_sql = '''INSERT INTO student values (?, ?, ?, ?, ?, ?)'''
        data = [(1, 'Hongten', 'boy', 20, 'guangzhou', '13423****62'),
                (2, 'Tom', 'boy', 22, 'guangzhou', '15423****63'),
                (3, 'Jake', 'girl', 18, 'guangzhou', '18823****87'),
                (4, 'Cate', 'girl', 21, 'guangzhou', '14323****32')]
        sqlite_obj.insert_update_delete(insert_sql, data)
        sqlite_obj.fetchall(fetchall_sql)

        update_sql = 'UPDATE student SET name = ? WHERE ID = ? '
        data = [('HongtenAA', 1),
                ('HongtenBB', 2),
                ('HongtenCC', 3),
                ('HongtenDD', 4)]
        sqlite_obj.insert_update_delete(update_sql, data)
        sqlite_obj.fetchall(fetchall_sql)

        # delete_sql = 'DELETE FROM student WHERE NAME = ? AND ID = ? '
        # data = [('HongtenAA', 1),
        #         ('HongtenCC', 3)]
        # sqlite_obj.insert_update_delete(delete_sql, data)
        # sqlite_obj.fetchall(fetchall_sql)

    def test_2(self):
        sqlite_obj = SQLiteAPI(self.bd_path, show=True)
        fetchall_sql = '''SELECT * FROM student'''
        sqlite_obj.fetchall(fetchall_sql)


if __name__ == '__main__':
    # test
    # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(SQLiteTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
