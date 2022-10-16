#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_SPLIT for python                                           *
# * Version:  1.1.1                                                          *
# * Date:     2022-10-16                                                     *
# * Last update: 2022-10-1                                                   *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************
import math
import os
import time
import pandas as pd
from scipy import signal

TBM_SPLIT_version = '1.1.1'  # 版本号，请勿修改！！！
DIR_OUT = ['\\Free running', '\\Loading', '\\Boring', '\\Loading and Boring', '\\Boring cycle']  # 分割后循环段文件保存文件夹
time_val = []  # 初始化时间存储


class TBM_SPLIT(object):
    def __init__(self):
        self.time_min_len = 100  # 最小掘进时长
        self.time_val = []  # 初始化时间存储
        self.out_path = ''  # 初始化输出路径
        self.create_dir = True  # 第一次保存文件时要创建相关文件夹
        self.RS_index = {'rise': 0, 'steadyS': 0, 'steadyE': 0}  # 初始化空推、上升、稳定、下降的关键点
        self.parameter = ['推进位移', '推进速度(nn/M)', '刀盘贯入度', '推进给定速度']

    def create_Result_Dir(self):
        """如果是第一次生成，需要创建相关文件夹"""
        if self.create_dir:
            for Dir in DIR_OUT:
                if not os.path.exists(self.out_path + Dir):
                    os.mkdir(self.out_path + Dir)
            self.create_dir = False

    def segment_save(self, _data_, _file_, _Index_):
        """对已经分割好的循环段文件进行保存"""
        self.create_Result_Dir()
        Time_Loading = _Index_['steadyS'] - _Index_['rise']  # 上升段持续时间
        Time_Boring = _Index_['steadyE'] - _Index_['steadyS']  # 上升段持续时间
        if _Index_['rise'] > 0 and Time_Loading > 30 and Time_Boring > 50:  # 空推段持续时间不为0，上升段持续时间>30s，稳定段持续时间>50s
            Free_running_df = _data_.iloc[:_Index_['rise'], :]  # 空推段
            Loading_df = _data_.iloc[_Index_['rise']:_Index_['steadyS'], :]  # 上升段
            Boring_df = _data_.iloc[_Index_['steadyS']:_Index_['steadyE'], :]  # 稳定段
            Loading_Boring_df = _data_.iloc[_Index_['rise']:_Index_['steadyE'], :]  # 上升段和稳定段
            Free_running_df.to_csv(os.path.join(self.out_path + DIR_OUT[0], _file_), index=False, encoding='gb2312')
            Loading_df.to_csv(os.path.join(self.out_path + DIR_OUT[1], _file_), index=False, encoding='gb2312')
            Boring_df.to_csv(os.path.join(self.out_path + DIR_OUT[2], _file_), index=False, encoding='gb2312')
            Loading_Boring_df.to_csv(os.path.join(self.out_path + DIR_OUT[3], _file_), index=False, encoding='gb2312')
            _data_.to_csv(os.path.join(self.out_path + DIR_OUT[4], _file_), index=False, encoding='gb2312')

    def data_Split(self, _input_path_, _out_path_):
        """对数据进行整体和细部分割"""
        self.out_path = _out_path_
        file_name_list = os.listdir(_input_path_)  # 获取输入文件夹下的所有文件名，并将其保存
        for num, file in zip([i + 1 for i in range(len(file_name_list))], file_name_list):  # 遍历每个文件
            start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            data_cycle = pd.read_csv(os.path.join(_input_path_, file), encoding='gb2312')  # 读取循环段文件
            if data_cycle.shape[0] >= self.time_min_len:  # 判断是否为有效循环段
                length = (data_cycle.loc[data_cycle.shape[0] - 1, self.parameter[0]] - data_cycle.loc[0, self.parameter[0]]) / 1000
                if length > 0.1:  # 推进位移要大于0.1m,实际上推进位移有正有负
                    RS_Index = self.get_RS_index(data_cycle)  # 调用函数，获取空推、上升、稳定、下降的变化点
                    self.segment_save(data_cycle, file, RS_Index)  # 数据保存
            end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            visual(num, len(file_name_list), start, end, 'Data_Split')
        visual(-1, len(file_name_list), None, None, 'Data_Split')

    def get_RS_index(self, _data_):
        """获取空推、上升、稳定、下降的关键点"""
        RS_index = self.RS_index
        V_set_mean = int(_data_[self.parameter[3]].mean())  # 推进速度设定索引
        mid_point = 0  # 中点位置索引
        while _data_[self.parameter[3]][mid_point] < (V_set_mean // 10) * 10:  # 推进速度设定索引
            mid_point += 10
        steadyE = _data_.shape[0] - 1  # 稳定段结束位置索引
        while _data_[self.parameter[1]][steadyE] <= V_set_mean:  # 推进速度
            steadyE -= 1
        if mid_point:
            rise = mid_point  # 上升段开始位置处索引
            while _data_[self.parameter[2]][rise] > 2 and rise > 10:  # 刀盘贯入度
                rise -= 1
            steadyS = mid_point  # 稳定段开始位置处索引
            while (_data_[self.parameter[1]][steadyS] / V_set_mean) < 2:  # 推进速度
                steadyS += 1
            RS_index['rise'], RS_index['steadyS'], RS_index['steadyE'] = rise, steadyS, steadyE
        else:
            RS_index['rise'], RS_index['steadyS'], RS_index['steadyE'] = \
                int(_data_.shape[0] * 0.1), int(_data_.shape[0] * 0.3), steadyE
        return RS_index


def butter_worth_filter(_input_path_, _out_path_, N=2, Wc=0.2):
    """巴特沃斯滤波器"""
    global time_val
    time_val = []
    file_name_list = os.listdir(_input_path_)  # 获取输入文件夹下的所有文件名，并将其保存
    for num, file_name in zip([i + 1 for i in range(len(file_name_list))], file_name_list):  # 遍历每个文件
        start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
        TBM_Data = pd.read_csv(os.path.join(_input_path_, file_name), encoding='gb2312')  # 读取文件
        b, a = signal.butter(N, Wc, btype='low')  # 配置滤波器阶数N及截止频率Wc
        for col in range(TBM_Data.shape[1]):
            if type(TBM_Data.iloc[0, col]) != type('str'):
                TBM_Data.iloc[:, col] = signal.filtfilt(b, a, TBM_Data.iloc[:, col])
        TBM_Data.to_csv(os.path.join(_out_path_, file_name), index=False, encoding='gb2312')  # 保存关键参数
        end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
        visual(num, len(file_name_list), start, end, 'Data filter')
    visual(-1, len(file_name_list), None, None, 'Data filter')


def visual(cycle, Sum, start, end, Print):
    """可视化输出"""
    global time_val
    if cycle != -1:
        time_diff = int(end - start)  # 执行一个文件所需的时间
        time_val.append(time_diff)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = int(sum(time_val) / len(time_val))  # 计算平均时间
        sum_time = round(sum(time_val) / 3600, 3)  # 计算程序执行的总时间
        print('\r', '->->', '[第%d个 / 共%d个]  ' % (cycle, Sum), '[所用时间%ds / 平均时间%ds]'
              % (time_diff, mean_time), '  ', '\033[0;33m累积时间:%6.3f小时\033[0m' % sum_time, end='')
    else:
        sum_time = round(sum(time_val) / 3600, 2)  # 计算程序执行的总时间
        print('\r', '->->', '\033[0;32m%s completed, which took %6.3f hours\033[0m' % (Print, sum_time))
