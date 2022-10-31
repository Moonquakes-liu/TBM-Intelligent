#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_SPLIT for python                                           *
# * Version:  3.0.0                                                          *
# * Date:     2022-10-31 20:00:00                                            *
# * Last update: 2022-10-28 20:00:00                                         *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import copy
import os
import shutil
import sys
import time
import pandas as pd
import psutil
from scipy import signal
import scipy


HISTORY = "最后更改时间:2022-10-31  修改人:刘建国  修改内容:暂无"  # 每次修改后添加修改人、修改时间和改动的功能


TIME_VAL = []  # 初始化时间存储
PARAMETERS = ['推进位移', '推进速度(nn/M)', '刀盘贯入度', '推进给定速度']
SPLIT_SUB_FOLDERS = ['Free running', 'Loading', 'Boring', 'Loading and Boring', 'Boring cycle']


class TBM_SPLIT(object):
    def __init__(self):
        self.time_min_len = 100  # 最小掘进时长
        self.out_path = ''  # 初始化输出路径
        self.sub_folder = SPLIT_SUB_FOLDERS  # 子文件夹
        self.first_write = True  # 第一次写入索引
        self.line = []  # 索引数据保存
        self.RS_index = {'rise': 0, 'steadyS': 0, 'steadyE': 0}  # 初始化空推、上升、稳定、下降的关键点
        self.parameter = PARAMETERS  # 初始化程序处理过程中需要用到的参数
        self.number = 1  # 索引行位置

    def create_Result_Dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out_path):
            os.mkdir(self.out_path)
        else:
            shutil.rmtree(self.out_path)
            os.mkdir(self.out_path)
        for number, Dir in zip([i for i in range(len(self.sub_folder))], self.sub_folder):
            new_dir = '\\%d-' % (number + 1) + Dir
            self.sub_folder[number] = new_dir
            if not os.path.exists(self.out_path + new_dir):
                os.mkdir(self.out_path + new_dir)

    def write_index(self, _inf_, _Num_):
        Root_Path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Index-File.csv')  # 索引文件存放根目录
        except_name = ['上升段起点', '稳定段起点', '稳定段终点']  # 新添加索引数据标题
        if self.first_write:  # 第一次写入索引时要写入标题
            with open(os.path.join(Root_Path, 'Index-File.csv'), 'r+', newline='', encoding='gb2312') as f:  # 只写模式打开文件
                self.line = copy.deepcopy(f.readlines())  # 将文件内容保存
                f.truncate(0)  # 清空文件内容，准备重新写入数据
            with open(os.path.join(Root_Path, 'Index-File.csv'), 'a', encoding='gb2312') as fw:  # 用读写模式打开文件
                line = self.line[0].replace('\r\n', ',' + str(','.join([str(i) for i in except_name])) + '\n')
                fw.write(line)  # 写入标题
            self.first_write = False
        while self.number < _Num_:
            _inf_empty = ['', '', '']
            with open(os.path.join(Root_Path, 'Index-File.csv'), 'a', encoding='gb2312') as fw:  # 用读写模式打开文件
                line = self.line[self.number].replace('\r\n', ',' + str(','.join([str(i) for i in _inf_empty])) + '\n')
                fw.write(line)  # 写入数据
            self.number += 1
        with open(os.path.join(Root_Path, 'Index-File.csv'), 'a', encoding='gb2312') as fw:  # 用读写模式打开文件
            line = self.line[_Num_].replace('\r\n', ',' + str(','.join([str(i) for i in _inf_])) + '\n')  # 新数据
            fw.write(line)  # 写入数据
        self.number += 1

    def segment_save(self, _data_, _file_, _Index_):
        """对已经分割好的循环段文件进行保存"""
        Time_Loading = _Index_['steadyS'] - _Index_['rise']  # 上升段持续时间
        Time_Boring = _Index_['steadyE'] - _Index_['steadyS']  # 上升段持续时间
        if _Index_['rise'] > 0 and Time_Loading > 30 and Time_Boring > 50:  # 空推段持续时间不为0，上升段持续时间>30s，稳定段持续时间>50s
            Free_running_df = _data_.iloc[:_Index_['rise'], :]  # 空推段
            Loading_df = _data_.iloc[_Index_['rise']:_Index_['steadyS'], :]  # 上升段
            Boring_df = _data_.iloc[_Index_['steadyS']:_Index_['steadyE'], :]  # 稳定段
            Loading_Boring_df = _data_.iloc[_Index_['rise']:_Index_['steadyE'], :]  # 上升段和稳定段
            Free_running_df.to_csv(os.path.join(self.out_path + self.sub_folder[0], _file_), index=False, encoding='gb2312')
            Loading_df.to_csv(os.path.join(self.out_path + self.sub_folder[1], _file_), index=False, encoding='gb2312')
            Boring_df.to_csv(os.path.join(self.out_path + self.sub_folder[2], _file_), index=False, encoding='gb2312')
            Loading_Boring_df.to_csv(os.path.join(self.out_path + self.sub_folder[3], _file_), index=False, encoding='gb2312')
            _data_.to_csv(os.path.join(self.out_path + self.sub_folder[4], _file_), index=False, encoding='gb2312')

    def data_Split(self, _input_path_, _out_path_, _par_name_, _sub_folder_, History=False):
        """对数据进行整体和细部分割"""
        if History: print('\n', '='*100, '\n', HISTORY, '\n', '='*100, '\n')  # 打印文件修改记录
        if (not _input_path_) or (not _out_path_) or (not _par_name_):  # 检查传入参数是否正常
            print('->-> %s' % os.path.basename(__file__), '\033[0;31mParameters abnormal, Please check!!!\033[0m')
            sys.exit()
        self.out_path, self.parameter, self.sub_folder = _out_path_, _par_name_, _sub_folder_
        self.create_Result_Dir()
        file_name_list = os.listdir(_input_path_)  # 获取输入文件夹下的所有文件名，并将其保存
        for num, file in zip([i + 1 for i in range(len(file_name_list))], file_name_list):  # 遍历每个文件
            start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            data_cycle = pd.read_csv(os.path.join(_input_path_, file), encoding='gb2312')  # 读取循环段文件
            except_type = ['' for _ in range(3)]  # 创建列表用来存储异常类型
            if data_cycle.shape[0] >= self.time_min_len:  # 判断是否为有效循环段
                length = (data_cycle.loc[data_cycle.shape[0] - 1, self.parameter[0]] - data_cycle.loc[0, self.parameter[0]]) / 1000
                if length > 0.1:  # 推进位移要大于0.1m,实际上推进位移有正有负
                    RS_Index = self.get_RS_index(data_cycle)  # 调用函数，获取空推、上升、稳定、下降的变化点
                    self.segment_save(data_cycle, file, RS_Index)  # 数据保存
                    except_type[0] = str(RS_Index['rise'])
                    except_type[1] = str(RS_Index['steadyS'])
                    except_type[2] = str(RS_Index['steadyE'])
            self.write_index(except_type, int(file[:5]))
            end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            visual('Data_Split', cycle=num, Sum=len(file_name_list), start=start, end=end, Clear=False)
        visual('Data_Split', cycle=-1, Clear=True)

    def get_RS_index(self, _data_):
        """获取空推、上升、稳定、下降的关键点"""
        RS_index = self.RS_index
        V_mean = int(_data_[self.parameter[1]].mean())  # 推进速度索引（self.parameter[1]）
        mid_point = 0  # 中点位置索引
        while _data_[self.parameter[1]][mid_point] < V_mean:  # 推进速度索引（self.parameter[1]）
            mid_point += 5
        steadyE = _data_.shape[0] - 1  # 稳定段结束位置索引
        while _data_[self.parameter[1]][steadyE] <= V_mean:  # 推进速度索引（self.parameter[1]）
            steadyE -= 1
        if mid_point:
            rise = mid_point  # 上升段开始位置处索引
            while _data_[self.parameter[2]][rise] > 2 and rise > 10:  # 刀盘贯入度度索引（self.parameter[2]）
                rise -= 1
            steadyS = mid_point  # 稳定段开始位置处索引
            V_set_mean = int(_data_[self.parameter[3]].mean())  # 推进速度设定值索引（self.parameter[3]）
            V_assist = _data_[self.parameter[1]] / V_set_mean  # 推进速度索引（self.parameter[1]）
            while V_assist[steadyS] - V_assist.mean() <= 0:
                steadyS += 1
            steady_V_mean = V_assist.iloc[steadyS:steadyE].mean()  # 整个稳定段推进速度均值
            while V_assist.iloc[steadyS] < steady_V_mean:  # 稳定段开始位置处的均值是否大于整个稳定段推进速度均值
                steadyS += 1
            RS_index['rise'], RS_index['steadyS'], RS_index['steadyE'] = rise, steadyS, steadyE
        else:
            RS_index['rise'], RS_index['steadyS'], RS_index['steadyE'] = \
                int(_data_.shape[0] * 0.1), int(_data_.shape[0] * 0.3), steadyE
        return RS_index


def Butter_Worth_Filter(_input_path_, _out_path_, History=False):
    """巴特沃斯滤波器"""
    if History: print('\n', '='*100, '\n', HISTORY, '\n', '='*100, '\n')  # 打印文件修改记录
    if (not _input_path_) or (not _out_path_):  # 检查传入参数是否正常
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
        TBM_Data = pd.read_csv(os.path.join(_input_path_, file_name), encoding='gb2312')  # 读取文件
        for col in range(TBM_Data.shape[1]):
            if type(TBM_Data.iloc[0, col]) != type('str'):
                TBM_Data.iloc[:, col] = scipy.signal.savgol_filter(TBM_Data.iloc[:, col], 19, 4)
        TBM_Data.to_csv(os.path.join(_out_path_, file_name), index=False, encoding='gb2312')  # 保存关键参数
        end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
        visual('Data Filter', cycle=num, Sum=len(file_name_list), start=start, end=end, Clear=False)
    visual('Data Filter', cycle=-1, Clear=True)


def visual(Print, **kwargs):
    """可视化输出"""
    global TIME_VAL
    p = psutil.Process(os.getpid())
    cpu_percent = p.cpu_percent()  # CPU占用
    mem_percent = p.memory_percent()  # 内存占用
    if kwargs['cycle'] != -1:
        time_diff = kwargs['end'] - kwargs['start']  # 执行一个文件所需的时间
        TIME_VAL.append(time_diff)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(TIME_VAL) / len(TIME_VAL)  # 计算平均时间
        sum_time = round(sum(TIME_VAL) / 3600, 3)  # 计算程序执行的总时间
        print('\r', '->->', '[第%d个 / 共%d个]  ' % (kwargs['cycle'], kwargs['Sum']), '[所用时间%ds / 平均时间%ds]'
              % (int(time_diff), int(mean_time)), ' ', '[CPU占用: %4.2f%%  内存占用: %4.2f%%]'
              % (cpu_percent, mem_percent), '  ', '\033[0;33m累积时间:%6.3f小时\033[0m' % sum_time, end='')
    else:
        sum_time = round(sum(TIME_VAL) / 3600, 3)  # 计算程序执行的总时间
        print('\r', '->->', '\033[0;32m%s completed, which took %6.3f hours\033[0m' % (Print, sum_time))
    if kwargs['Clear']:
        TIME_VAL = []
