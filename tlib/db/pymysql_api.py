# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/16 15:12
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

""" pymysql for CPython : 2.7 and >= 3.4 """

import pymysql
import unittest

from tlib import log

# =============================
# --- Global
# =============================
logger = log.get_logger()


class MySQLObj(object):
    """
    MySQLdb obj
    """
    def __init__(self, host, user, password, port, database, show=True):
        super(MySQLObj, self).__init__()
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.database = database
        self.show = show
        self.conn = self.connect()
        self.cur = self.conn.cursor()

    def __del__(self):
        try:
            if self.cur is not None:
                if self.show:
                    print('Close MySQL cursor ...')
                self.cur.close()
            if self.conn is not None:
                if self.show:
                    print('Close MySQL connect ...')
                self.conn.close()
        finally:
            pass

    def connect(self):
        """
        connect to mysql
        :return:
        """
        logger.info("Connect to mysql {0}:{1}(DataBase:{2}) ...".format(
            self.host, self.port, self.database))
        try:
            conn = pymysql.connect(host=self.host, user=self.user,
                                   passwd=self.password, db=self.database,
                                   port=self.port, charset='utf8')
            return conn
        except Exception as e:
            raise e

    def execute(self, sql):
        """
        execute a sql cmd
        :param sql:
        :return:
        """
        logger.info(sql)

        try:
            rows = self.cur.execute(sql)
            self.conn.commit()
            return rows
        except Exception as e:
            logger.warning('{err}, rollback commit ...'.format(err=e))
            self.conn.rollback()
            return False

    def drop_table(self, table):
        """
        drop table
        :return:
        """

        if table is not None and table != '':
            sql = 'DROP TABLE IF EXISTS ' + table
            if self.show:
                logger.info('execute sql:[{}]'.format(sql))
            self.cur.execute(sql)
            self.conn.commit()
            logger.info('drop table [{}] success!'.format(table))
        else:
            logger.info('The table [{}] is empty or equal None!'.format(table))

        return True

    def create_table(self, sql):
        """
        create table
        :param sql:
        :return:
        """

        if sql is not None and sql != '':
            if self.show:
                logger.info('execute sql:[{}]'.format(sql))
            self.cur.execute(sql)
            self.conn.commit()
            logger.info('create tablle success')
        else:
            logger.info('the [{}] is empty or equal None!'.format(sql))

    def insert_update_delete(self, sql, data):
        if sql is not None and sql != '':
            if data is not None:
                for d in data:
                    if self.show:
                        logger.info('execute sql:[{}],args:[{}]'.format(sql, d))
                    self.cur.execute(sql, d)
                    self.conn.commit()
            else:
                if self.show:
                    logger.info('execute sql:[{}]'.format(sql))
                self.cur.execute(sql)
                self.conn.commit()
        else:
            logger.info('The [{}] is empty or equal None!'.format(sql))

    def fetchall(self, sql):
        if self.show:
            logger.info('execute sql:[{}]'.format(sql))

        try:
            self.cur.execute(sql)
            rows = self.cur.fetchall()
            if self.show:
                for row in rows:
                    logger.info(row)
                logger.info('=' * 50)
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


class MySQLTestCase(unittest.TestCase):
    """docstring for MySQLTestCase"""

    def setUp(self):
            pass

    def tearDown(self):
        pass

    def test_1(self):
        mysql_obj = MySQLObj(host='10.25.119.1', user='test',
                             password='password', port=3306, database='testdb')
        fetchall_sql = '''SELECT * FROM student'''

        mysql_obj.drop_table('student')

        create_table = '''CREATE TABLE `student` (
                              `id` int(11) NOT NULL,
                              `name` varchar(20) NOT NULL,
                              `gender` varchar(4) DEFAULT NULL,
                              `age` int(11) DEFAULT NULL,
                              `address` varchar(200) DEFAULT NULL,
                              `phone` varchar(20) DEFAULT NULL,
                               PRIMARY KEY (`id`)
                            )'''
        mysql_obj.create_table(create_table)
        mysql_obj.fetchall(fetchall_sql)

        insert_sql = '''INSERT INTO student values (%s, %s, %s, %s, %s, %s)'''
        data = [(1, 'Hongten', 'boy', 20, 'guangzhou', '13423****62'),
                (2, 'Tom', 'boy', 22, 'guangzhou', '15423****63'),
                (3, 'Jake', 'girl', 18, 'guangzhou', '18823****87'),
                (4, 'Cate', 'girl', 21, 'guangzhou', '14323****32')]
        mysql_obj.insert_update_delete(insert_sql, data)
        mysql_obj.fetchall(fetchall_sql)

        update_sql = 'UPDATE student SET name = %s WHERE ID = %s '
        data = [('HongtenAA2', 1),
                ('HongtenBB2', 2),
                ('HongtenCC2', 3),
                ('HongtenDD2', 4)]
        # mysql_obj.insert_update_delete(update_sql, data)
        mysql_obj.fetchall(fetchall_sql)

        # delete_sql = 'DELETE FROM student WHERE NAME = ? AND ID = ? '
        # data = [('HongtenAA', 1),
        #         ('HongtenCC', 3)]
        # mysql_obj.insert_update_delete(delete_sql, data)
        # mysql_obj.fetchall(fetchall_sql)

    def test_2(self):
        mysql_obj = MySQLObj(host='10.25.119.1', user='test',
                             password='password', port=3306, database='testdb')
        fetchall_sql = '''SELECT * FROM test'''

        mysql_obj.drop_table('test')

        create_table = '''
            CREATE TABLE `test` (
                `ID` int(11) NOT NULL AUTO_INCREMENT,
                `Version` varchar(40) NOT NULL,
                `Test` varchar(40) NOT NULL,
                `Status` varchar(20) DEFAULT NULL,
                `Results` varchar(40) DEFAULT NULL,
                `StartTime` varchar(40) DEFAULT NULL,
                `Elapsed` varchar(20) DEFAULT NULL,
                `Iteration` varchar(6) NOT NULL,
                `Tester` varchar(10) DEFAULT NULL,
                `Report` varchar(200) DEFAULT NULL,
                PRIMARY KEY (`id`)
            )
        '''

        mysql_obj.drop_table('test')

        mysql_obj.create_table(create_table)
        mysql_obj.fetchall(fetchall_sql)

        insert_sql = '''INSERT INTO test (Version, Test, Status, Results, 
        StartTime, Elapsed, Iteration, Tester, Report) values 
        (%s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        data = [
            ('1.0.0.261100', 'sanity', 'PASS',
             'ALL 36, Pass 36, Passing rate: 100%',
             '2018-12-20 06:55:07', '0:44:51', '1', 'tao.xu',
             'vizion-ut/sanity/ImageTAG-1.0.0.261100/vizion-ut-sanity-20181220065505.html'),
            ('1.0.0.261101', 'sanity_raw', 'PASS',
             'ALL 36, Pass 36, Passing rate: 100%',
             '2018-12-20 06:55:07', '0:44:51', '1', 'tao.xu',
             'vizion-ut/sanity/ImageTAG-1.0.0.261100/vizion-ut-sanity-20181220065505.html'),
            ('1.0.0.261102', 'sanity', 'FAIL',
             'ALL 36, Pass 36, Passing rate: 100%',
             '2018-12-20 06:55:07', '0:44:51', '1', 'tao.xu',
             'vizion-ut/sanity/ImageTAG-1.0.0.261100/vizion-ut-sanity-20181220065505.html'),
            ('1.0.0.261103', 'stability_raw', 'PASS',
             'ALL 36, Pass 36, Passing rate: 100%',
             '2018-12-20 06:55:07', '0:44:51', '1', 'tao.xu',
             'vizion-ut/sanity/ImageTAG-1.0.0.261100/vizion-ut-sanity-20181220065505.html'),
            ('1.0.0.261104', 'stability_raw', 'FAIL',
             'ALL 36, Pass 36, Passing rate: 100%',
             '2018-12-20 06:55:07', '0:44:51', '1', 'tao.xu',
             'vizion-ut/sanity/ImageTAG-1.0.0.261100/vizion-ut-sanity-20181220065505.html'),
            ('1.0.0.261104', 'stability_raw', 'FAIL',
             'ALL 36, Pass 36, Passing rate: 100%',
             '2018-12-20 06:55:07', '0:44:51', '1', 'tao.xu',
             'vizion-ut/sanity/ImageTAG-1.0.0.261100/vizion-ut-sanity-20181220065505.html'),
        ]
        mysql_obj.insert_update_delete(insert_sql, data)
        mysql_obj.fetchall(fetchall_sql)


if __name__ == '__main__':
    # test
    # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(MySQLTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
