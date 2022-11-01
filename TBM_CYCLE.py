#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_CYCLE for python                                           *
# * Version:  3.1.0                                                          *
# * Date:     2022-10-31 20:00:00                                            *
# * Last update: 2022-10-28 20:00:00                                         *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import csv
import os
import shutil
import sys
import time
import warnings
from functools import reduce
import pandas as pd
import psutil
import concurrent.futures


HISTORY = "最后更改时间:2022-10-31  修改人:刘建国  修改内容:暂无"  # 每次修改后添加修改人、修改时间和改动的功能


warnings.filterwarnings("ignore")  # 忽略警告信息
TIME_VAL = []  # 初始化时间存储
PARAMETERS = ['导向盾首里程', '日期', '刀盘转速', '推进给定速度']


class TBM_CYCLE(object):
    def __init__(self):
        self.Number = 1  # 初始化循环段编号
        self.D_before = 0  # 初始化上一时刻的掘进状态
        self.interval_time = 0  # 初始化两个相邻掘进段的时间间隔为0
        self.first_write = True  # 将索引文件写入次数初始化为第一次
        self.add_temp = pd.DataFrame(None)  # 初始化dataframe类型数组，便于对连续部分数据进行存储
        self.out_path = ''  # 初始化输出路径
        self.parameter = PARAMETERS  # 掘进状态判定参数
        self.label_parameter = []  # 用于文件保存的桩号和时间

    def create_class_Dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out_path):
            os.mkdir(self.out_path)
        else:
            shutil.rmtree(self.out_path)
            os.mkdir(self.out_path)

    def write_index(self, _inf_):
        index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Index-File.csv')  # 索引文件路径
        if self.first_write:  # 判断是否为第一次写入，如果是，新建文件夹和索引文件
            if os.path.isfile(index_path):
                os.remove(index_path)  # 若索引文件存在，则删除
            with open(index_path, 'w', encoding='gb2312', newline='') as f:  # 新建索引文件
                csv.writer(f).writerow(['循环段', '桩号', '日期', '掘进时间'])  # 写入标签数据
                self.first_write = False  # 第一次写入完成
        input_csv = open(index_path, 'a', newline='')  # 打开索引文件
        csv.writer(input_csv).writerow([_inf_['num'], _inf_['stake'], _inf_['date'], _inf_['time']])  # 写入数据记录

    def determine_tunneling(self, _Data_value_):
        """完成对掘进状态的实时判定，结合历史数据返回掘进段开始和结束位置"""
        Boring_cycle, key_type, Fx = False, None, []  # 初始化变量，是否处于掘进状态（Boring_cycle），掘进段开始和结束标志（key_type），判定函数（Fx）
        for parameter_value in _Data_value_:
            if parameter_value > 0:  # *                 | 1  x> 0
                Fx.append(1)  # *                 F(x) = |
            else:  # *                                   | 0  x<=0
                Fx.append(0)
        D_now = reduce(lambda x, y: x * y, Fx)  # D(x) = F(x1)·F(x2)...F(Xn)
        if D_now:  # *                                   | 1  boring_cycle
            Boring_cycle = True  # *              D(x) = | 0  downtime
        if D_now - self.D_before < 0:
            key_type = 'Finish'  # *                                               | -1  'Finish'
        if D_now - self.D_before > 0:  # *             当前时刻D(x) - 上一时刻D(x‘) = |
            key_type = 'Start'  # *                                                |  1  'Start'
        self.D_before = D_now
        return Boring_cycle, key_type  # 掘进状态判定结果Boring_cycle（True/False）和掘进段开始或结束标志key_type（‘beg’/‘end’/None）

    def continuous_data_process(self, _Data_):
        """处理原始数据中相邻两天数据存在连续性的情况"""
        operate_state = []  # 定义一个空列表，用于存储每一时刻掘进状态（处于掘进状态：True，处于停机状态：False ）
        col_name = list(_Data_.index.values)  # 获取原始数据的行索引，并保存为list形式
        _Data_value_ = _Data_.loc[:, self.parameter[:-1]].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
        for col in col_name[::-1]:  # 从后往前，对每一时刻的掘进状态进行判定
            operate_state.append(self.determine_tunneling(_Data_value_[col, :])[0])  # 将该时刻的掘进状态存储至operate_state中
            if (len(operate_state) > self.interval_time) and (not any(operate_state[-self.interval_time:-1])):
                break  # 判定两个相邻掘进段的时间间隔内（limit_value）盾构是否处于掘进状态，若未处于掘进状态，则返回该时刻的行索引值
        _Out_data_ = pd.concat([self.add_temp, _Data_.loc[:col + 1, :]], ignore_index=True)  # 将前一天与当天连续部分数据进行拼接，形成一个数据集
        self.add_temp = _Data_.loc[col + 1:, :]  # 将当天与后一天连续部分的数据进行单独保存，便于和后一天的数据进行拼接
        _Out_data_ = _Out_data_.reset_index(drop=True)  # 重建提取数据的行索引
        return _Out_data_  # 返回拼接后的新数据集

    def boring_cycle_extract(self, _Data_):
        """完成对原始数据中的掘进段进行实时提取"""
        key = {'now-S': 0, 'now-F': 0, 'last-S': 0, 'last-F': 0}  # 当前掘进段开始与结束的行索引,上一个掘进段开始与结束的行索引
        first_cycle = True  # 是否是第一个掘进段（是：True，否：False）
        col_name = list(_Data_.index.values)  # 获取原始数据的行索引，并保存为list形式
        _Data_value_ = _Data_.loc[:, self.parameter[:-1]].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
        for row in col_name:  # 从前往后，对每一时刻的掘进状态进行判定
            result = self.determine_tunneling(_Data_value_[row, :])[1]  # 调用掘进状态判定函数并返回掘进段开始或结束标志
            if result == 'Start':
                key['now-S'] = row  # 保存掘进段开始时的行索引
            if result == 'Finish':
                key['now-F'] = row  # 保存掘进段结束时的行索引
            V_set_max = _Data_.loc[key['now-S']:key['now-F'], self.parameter[-1]].max()  # V-set的最大值
            if (key['now-F'] > key['now-S']) and V_set_max > 0:  # 获取到掘进段开始和结束索引是否完整
                if first_cycle:  # 由于在获取到下一个完整掘进段的开始和结束的行索引后才对上一个循环段进行保存，因此要对第一个掘进段进行特殊处理
                    key['last-S'], key['last-F'] = key['now-S'], key['now-F']  # 首个掘进段开始和结束的行索引进行赋值
                    first_cycle = False  # 第一个掘进段索引数据读取完成，将其赋值为False
                if key['now-S'] - key['last-F'] > self.interval_time or row == col_name[-1]:  # 判断两个掘进段时间间隔是否满足要求
                    self.boring_cycle_save(_Data_, [key['last-S'], key['last-F']])  # 两个掘进段时间间隔满足要求，对上一掘进段进行保存
                else:
                    key['now-S'] = key['last-S']  # 两个掘进段时间间隔不满足要求，需要将上一掘进段和当前掘进段进行合并
                key['last-S'], key['last-F'] = key['now-S'], key['now-F']  # 将当前掘进段的开始和结束的行索引信息进行保存

    def read_file(self, _input_path_, _out_path_, _par_name_, _interval_time_=100, History=False):
        """完成对原始数据的读取
        :param _input_path_: 文件读取路径
        :param _out_path_: 文件保存路径
        :param _par_name_: 参数名称
        :param _interval_time_: 时间间隔
        :param History: 展示历史修改记录
        """
        if History: print('\n', '='*100, '\n', HISTORY, '\n', '='*100, '\n')  # 打印文件修改记录
        if (not _input_path_) or (not _out_path_) or (not _par_name_):  # 检查传入参数是否正常
            print('->-> %s' % os.path.basename(__file__), '\033[0;31mParameters abnormal, Please check!!!\033[0m')
            sys.exit()
        self.label_parameter, self.parameter = _par_name_[:2], _par_name_[2:]  # 对应掘进参数赋值
        self.out_path, self.interval_time = _out_path_, _interval_time_  # 将输出路径和时间间隔赋值给全局变量
        self.create_class_Dir()
        file_name_list = os.listdir(_input_path_)  # 获取输入文件夹下的所有文件名，并将其保存
        for num, file in zip([i + 1 for i in range(len(file_name_list))], file_name_list):  # 遍历每个文件
            start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            try:  # 首先尝试使用默认方式进行csv文件读取
                data_raw = pd.read_csv(os.path.join(_input_path_, file), index_col=0)  # 读取文件
            except UnicodeDecodeError:  # 若默认方式读取csv文件失败，则添加'gb2312'编码后重新进行尝试
                data_raw = pd.read_csv(os.path.join(_input_path_, file), index_col=0, encoding='gb2312')  # 读取文件
            data_raw.index = [i for i in range(data_raw.shape[0])]  # 重建新数据集的行索引
            data_raw.drop(data_raw.tail(1).index, inplace=True)  # 删除文件最后一行
            data_raw = data_raw.loc[:, ~data_raw.columns.str.contains('Unnamed')]  # 删除Unnamed空列
            after_process = self.continuous_data_process(data_raw)  # 调用continuous_data_process函数对相邻两天数据存在连续性的情况进行处理
            self.boring_cycle_extract(after_process)  # 调用boring_cycle_extract函数对原始数据中的循环段进行提取
            end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            visual('Boring-cycle extract', cycle=num, Sum=len(file_name_list), start=start, end=end, Clear=False)
        visual('Boring-cycle extract', cycle=-1, Clear=True)

    def boring_cycle_save(self, _Data_, _key_):
        """对已经划分出的循环段文件进行保存"""
        boring_cycle_data = _Data_.iloc[_key_[0]:_key_[1], :]  # 提取掘进段数据
        boring_cycle_data = boring_cycle_data.reset_index(drop=True)  # 重建提取数据的行索引
        Mark = round(boring_cycle_data.loc[0, self.label_parameter[0]], 2)  # 获取每个掘进段的起始桩号
        Time = boring_cycle_data.loc[0, self.label_parameter[1]]  # 获取每个掘进段的时间记录
        Time = pd.to_datetime(Time, format='%Y-%m-%d %H:%M:%S')  # 对时间类型记录进行转换
        year, mon, d, h, m, s = Time.year, Time.month, Time.day, Time.hour, Time.minute, Time.second  # 获取时间记录的时分秒等
        csv_name = (self.Number, Mark, year, mon, d, h, m, s)
        csv_path = os.path.join(self.out_path, '%00005d %.2f-%s年%s月%s日 %s时%s分%s秒.csv' % csv_name)  # 循环段保存路径
        boring_cycle_data.to_csv(csv_path, index=False, encoding='gb2312')  # 保存csv文件
        self.write_index({'num': self.Number, 'stake': Mark, 'date': Time, 'time': (_key_[1] - _key_[0])})  # 索引文件记录
        self.Number += 1  # 循环段自增


def Key_Parameter_Extraction(_input_path_, _out_path_, _key_name_, History=False):
    """关键数据提取
    :param _input_path_: 文件读取路径
    :param _out_path_: 文件保存路径
    :param _key_name_: 参数名称
    :param History: 展示历史修改记录
    """
    if History: print('\n', '='*100, '\n', HISTORY, '\n', '='*100, '\n')  # 打印文件修改记录
    if (not _input_path_) or (not _out_path_) or (not _key_name_):  # 检查传入参数是否正常
        print('->-> %s' % os.path.basename(__file__), '\033[0;31mParameters abnormal, Please check!!!\033[0m')
        sys.exit()
    if not os.path.exists(_out_path_):
        os.mkdir(_out_path_)
    else:
        shutil.rmtree(_out_path_)
        os.mkdir(_out_path_)
    file_name_list = os.listdir(_input_path_)  # 获取输入文件夹下的所有文件名，并将其保存
    for num, file_name in zip([i + 1 for i in range(len(file_name_list))], file_name_list):  # 遍历每个文件
        start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
        cycle_data = pd.read_csv(os.path.join(_input_path_, file_name), encoding='gb2312')  # 读取文件
        be_extract, raw_rule = [], []  # 定义变量，待提取参数列（be_extract），待提取参数列在原始数据中的位置（raw_rule）
        col_name = list(cycle_data)  # 获取所有列名
        for key_par in _key_name_:  # 提取关键参数
            be_extract.append(cycle_data.loc[:, key_par])
            raw_rule.append(col_name.index(key_par))
        after_extract = pd.concat(be_extract, axis=1)  # 合并关键参数
        after_extract.to_csv(os.path.join(_out_path_, file_name), index=False, encoding='gb2312')  # 保存关键参数
        end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
        visual('Key-Data extract', cycle=num, Sum=len(file_name_list), start=start, end=end, Clear=False)
    visual('Key-Data extract', cycle=-1, Clear=True)


def visual(Print, **kwargs):
    """可视化输出"""
    global TIME_VAL
    cpu_percent = psutil.cpu_percent()  # CPU占用
    mem_percent = psutil.Process(os.getpid()).memory_percent()  # 内存占用
    if kwargs['cycle'] != -1:
        time_diff = kwargs['end'] - kwargs['start']  # 执行一个文件所需的时间
        TIME_VAL.append(time_diff)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(TIME_VAL) / len(TIME_VAL)  # 计算平均时间
        sum_time = round(sum(TIME_VAL) / 3600, 3)  # 计算程序执行的总时间
        print('\r', '->->', '[第%d个 / 共%d个]  ' % (kwargs['cycle'], kwargs['Sum']), '[所用时间%ds / 平均时间%ds]'
              % (int(time_diff), int(mean_time)), ' ', '[CPU占用: %5.2f%% / 内存占用: %5.2f%%]'
              % (cpu_percent, mem_percent), '  ', '\033[0;33m累积时间:%6.3f小时\033[0m' % sum_time, end='')
    else:
        sum_time = round(sum(TIME_VAL) / 3600, 3)  # 计算程序执行的总时间
        print('\r', '->->', '\033[0;32m%s completed, which took %6.3f hours\033[0m' % (Print, sum_time))
    if kwargs['Clear']:
        TIME_VAL = []
