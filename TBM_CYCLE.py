#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: EX_CYCLE for python                                            *
# * Version:  2.0.0                                                          *
# * Date:     2022-10-20                                                     *
# * Last update: 2022-10-16                                                  *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import csv
import math
import os
import math
import time
import warnings
from functools import reduce
import pandas as pd


warnings.filterwarnings("ignore")  # 忽略警告信息
time_val = []  # 初始化时间存储


class TBM_CYCLE(object):
    def __init__(self):
        self.Number = 1  # 初始化循环段编号
        self.D_before = 0  # 初始化上一时刻的掘进状态
        self.interval_time = 0  # 初始化两个相邻掘进段的时间间隔为0
        self.first_write = True  # 将索引文件写入次数初始化为第一次
        self.add_temp = pd.DataFrame(None)  # 初始化dataframe类型数组，便于对连续部分数据进行存储
        self.out_path = ''  # 初始化输出路径
        self.state_parameter = []  # 掘进状态判定参数
        self.label_parameter = []  # 用于文件保存的桩号和时间

    def determine_tunneling(self, TBM_Data_value):
        """完成对掘进状态的实时判定，结合历史数据返回掘进段开始和结束位置"""
        Boring_cycle, key_type, Fx = False, None, []  # 初始化变量，是否处于掘进状态（Boring_cycle），掘进段开始和结束标志（key_type），判定函数（Fx）
        for parameter_value in TBM_Data_value:
            if parameter_value > 0:  # *                 | 1  x> 0
                Fx.append(1)  # *                 F(x) = |
            else:  # *                                   | 0  x<=0
                Fx.append(0)
        D_now = reduce(lambda x, y: x * y, Fx)  # D(x) = F(x1)·F(x2)...F(Xn)
        if D_now:  # *                                   | 1  boring_cycle
            Boring_cycle = True  # *              D(x) = | 0  downtime
        if D_now - self.D_before < 0:
            key_type = 'end'  # *                                             | -1  ’end‘
        if D_now - self.D_before > 0:  # *             当前时刻D(x) - 上一时刻D(x‘) = |
            key_type = 'beg'  # *                                             |  1  ’beg‘
        self.D_before = D_now
        return Boring_cycle, key_type  # 掘进状态判定结果Boring_cycle（True/False）和掘进段开始或结束标志key_type（‘beg’/‘end’/None）

    def continuous_data_process(self, TBM_Data):
        """处理原始数据中相邻两天数据存在连续性的情况"""
        operate_state = []  # 定义一个空列表，用于存储每一时刻掘进状态（处于掘进状态：True，处于停机状态：False ）
        col_name = list(TBM_Data.index.values)  # 获取原始数据的行索引，并保存为list形式
        TBM_Data_value = TBM_Data.loc[:, self.state_parameter[:-1]].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
        for col in col_name[::-1]:  # 从后往前，对每一时刻的掘进状态进行判定
            operate_state.append(
                self.determine_tunneling(TBM_Data_value[col, :])[0])  # 调用掘进状态判定函数，将该时刻的掘进状态存储至operate_state中
            if (len(operate_state) > self.interval_time) and (not any(operate_state[-self.interval_time:-1])):
                break  # 判定两个相邻掘进段的时间间隔内（limit_value）盾构是否处于掘进状态，若未处于掘进状态，则返回该时刻的行索引值
        Out_data = pd.concat([self.add_temp, TBM_Data.loc[:col + 1, :]], ignore_index=True)  # 将前一天与当天连续部分数据进行拼接，形成一个数据集
        self.add_temp = TBM_Data.loc[col + 1:, :]  # 将当天与后一天连续部分的数据进行单独保存，便于和后一天的数据进行拼接
        Out_data.index = [i for i in range(Out_data.shape[0])]  # 重建新数据集的行索引
        return Out_data  # 返回拼接后的新数据集

    def boring_cycle_extract(self, TBM_Data):
        """完成对原始数据中的掘进段进行实时提取"""
        key_beg, key_end, key_beg_temp, key_end_temp = 0, 0, 0, 0  # 当前掘进段开始与结束的行索引,上一个掘进段开始与结束的行索引
        first_cycle = True  # 是否是第一个掘进段（是：True，否：False）
        col_name = list(TBM_Data.index.values)  # 获取原始数据的行索引，并保存为list形式
        TBM_Data_value = TBM_Data.loc[:, self.state_parameter[:-1]].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
        for row in col_name:  # 从前往后，对每一时刻的掘进状态进行判定
            result = self.determine_tunneling(TBM_Data_value[row, :])[1]  # 调用掘进状态判定函数并返回掘进段开始或结束标志
            if result == 'beg':
                key_beg = row  # 保存掘进段开始时的行索引
            if result == 'end':
                key_end = row  # 保存掘进段结束时的行索引
            if (key_end > key_beg) and TBM_Data.loc[key_beg:key_end, self.state_parameter[-1]].max() > 0:  # 判断所获取到的掘进段开始和结束的行索引是否完整
                if first_cycle:  # 由于在获取到下一个完整掘进段的开始和结束的行索引后才对上一个循环段进行保存，因此要对第一个掘进段进行特殊处理
                    key_beg_temp, key_end_temp = key_beg, key_end  # 将第一个掘进段开始和结束的行索引赋值给key_beg_temp, key_end_temp
                    first_cycle = False  # 第一个掘进段索引数据读取完成，将其赋值为False
                if key_beg - key_end_temp > self.interval_time or row == col_name[-1]:  # 判断两个掘进段时间间隔是否满足要求
                    self.boring_cycle_save(TBM_Data, [key_beg_temp, key_end_temp])  # 两个掘进段时间间隔满足要求，对上一掘进段进行保存
                else:
                    key_beg = key_beg_temp  # 两个掘进段时间间隔不满足要求，需要将上一掘进段和当前掘进段进行合并
                key_beg_temp, key_end_temp = key_beg, key_end  # 将当前掘进段的开始和结束的行索引信息进行保存，用于和下一掘进段进行比较和保存

    def read_file(self, _input_path_, _out_path_, _interval_time_, _par_name_):
        """完成对原始数据的读取"""
        self.label_parameter, self.state_parameter = _par_name_[:2], _par_name_[2:]  # 对应掘进参数赋值
        self.out_path, self.interval_time = _out_path_, _interval_time_  # 将输出路径和时间间隔赋值给全局变量
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
            visual(num, len(file_name_list), start, end, 'Boring-cycle extract')
        visual(-1, len(file_name_list), None, None, 'Boring-cycle extract')

    def boring_cycle_save(self, TBM_Data, _key_):
        """对已经划分出的循环段文件进行保存"""
        boring_cycle_data = TBM_Data.iloc[_key_[0]:_key_[1], :]  # 提取掘进段数据
        boring_cycle_data.index = [i for i in range(boring_cycle_data.shape[0])]  # 重建提取数据的行索引
        Mark = round(boring_cycle_data.loc[0, self.label_parameter[0]], 2)  # 获取每个掘进段的起始桩号
        Time = boring_cycle_data.loc[0, self.label_parameter[1]]  # 获取每个掘进段的时间记录
        Time = pd.to_datetime(Time, format='%Y-%m-%d %H:%M:%S')  # 对时间类型记录进行转换
        year, mon, d, h, m, s = Time.year, Time.month, Time.day, Time.hour, Time.minute, Time.second  # 获取时间记录的时分秒等
        index_path = os.path.join(self.out_path[:-len(self.out_path.split('\\')[-1]) - 1], 'Index-File.csv')  # 索引文件路径
        if self.first_write:  # 判断是否为第一次写入，如果是，新建文件夹和索引文件
            with open(index_path, 'w', encoding='gb2312', newline='') as f:  # 新建索引文件
                csv.writer(f).writerow(['循环段', '桩号', '时间', '掘进时间'])  # 写入标签数据
                self.first_write = False  # 第一次写入完成
        csv_path = os.path.join(self.out_path, '%00005d %s-%s年%s月%s日 %s时%s分%s秒.csv' % (self.Number, Mark, year, mon, d, h, m, s))  # 循环段保存路径
        boring_cycle_data.to_csv(csv_path, index=False, encoding='gb2312')  # 保存csv文件
        input_csv = open(index_path, 'a', newline='')  # 打开索引文件
        csv.writer(input_csv, dialect='excel').writerow([self.Number, Mark, Time, _key_[1] - _key_[0]])  # 写入数据记录
        self.Number += 1  # 循环段自增


def key_parameter_extraction(_input_path_, _out_path_, key_name):
    """关键数据提取"""
    file_name_list = os.listdir(_input_path_)  # 获取输入文件夹下的所有文件名，并将其保存
    for num, file_name in zip([i + 1 for i in range(len(file_name_list))], file_name_list):  # 遍历每个文件
        start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
        cycle_data = pd.read_csv(os.path.join(_input_path_, file_name), encoding='gb2312')  # 读取文件
        be_extract, raw_rule = [], []  # 定义变量，待提取参数列（be_extract），待提取参数列在原始数据中的位置（raw_rule）
        col_name = list(cycle_data)  # 获取所有列名
        for key_par in key_name:  # 提取关键参数
            be_extract.append(cycle_data.loc[:, key_par])
            raw_rule.append(col_name.index(key_par))
        after_extract = pd.concat(be_extract, axis=1)  # 合并关键参数
        after_extract.to_csv(os.path.join(_out_path_, file_name), index=False, encoding='gb2312')  # 保存关键参数
        end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
        visual(num, len(file_name_list), start, end, 'Key-Data extract')
    visual(-1, len(file_name_list), None, None, 'Key-Data extract')


def visual(cycle, Sum, start, end, Print):
    """可视化输出"""
    global time_val
    if cycle != -1:
        time_diff = int(end - start)  # 执行一个文件所需的时间
        time_val.append(time_diff)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = int(sum(time_val) / len(time_val))  # 计算平均时间
        sum_time = round(sum(time_val) / 3600, 2)  # 计算程序执行的总时间
        print('\r', '->->', '[第%d个 / 共%d个]  ' % (cycle, Sum), '[所用时间%ds / 平均时间%ds]'
              % (time_diff, mean_time), '  ', '\033[0;33m累积时间:%6.2f小时\033[0m' % sum_time, end='')
    else:
        sum_time = round(sum(time_val) / 3600, 2)  # 计算程序执行的总时间
        print('\r', '->->', '\033[0;32m%s completed, which took %6.2f hours\033[0m' % (Print, sum_time))
