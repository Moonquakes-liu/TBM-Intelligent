#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_CYCLE for python                                           *
# * Version:  4.0.0                                                          *
# * Date:     2022-11-13 20:00:00                                            *
# * Last update: 2022-10-31 20:00:00                                         *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import os
import copy
import shutil
import sys
import csv
import time
import warnings
import numpy as np
import pandas as pd
import psutil
import scipy
from scipy import fft
from scipy.fftpack import fft
from scipy import signal
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table
from reportlab.lib.units import mm
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
from functools import reduce
from matplotlib import pyplot as plt


HISTORY = "最后更改时间:2022-10-31  修改人:刘建国  修改内容:暂无"  # 每次修改后添加修改人、修改时间和改动的功能


warnings.filterwarnings("ignore")  # 忽略警告信息
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置字体
plt.rcParams['axes.unicode_minus'] = False  # 坐标轴的负号正常显示
plt.rcParams.update({'font.size': 17})  # 设置字体大小
pdfmetrics.registerFont(TTFont('SimSun', 'C:/Windows/Fonts/STSONG.TTF'))
TIME_VAL = []  # 初始化时间存储


class TBM_CYCLE(object):
    """
    TBM_CYCLE(_input_path_, _out_path_, _debug_)为循环段分割配置模块，该模块需要传入的参数包括
    必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）} 可选参数：{程序调试/修复选项（_debug_）}
    read_file(_par_name_, _interval_time_)为循环段分割主模块，该模块需要传入的参数包括
    必要参数：{程序运行所需要的关键参数名称（_par_name_）} 可选参数：{相邻循环段时间间隔（s）（_interval_time_）默认100s}
    version()为展示程序版本及修改记录模块，该模块无需传入相关参数
    """
    PARAMETERS = ['导向盾首里程', '日期', '推进给定速度', '刀盘转速']  # 类中的全局变量

    def __init__(self, _input_path_=None, _out_path_=None, _debug_=False):  # 初始化函数
        self.input_path = _input_path_  # 初始化输入路径
        self.out_path = _out_path_  # 初始化输出路径
        self.parm = self.PARAMETERS  # 掘进状态判定参数
        self.index_exists = False  # 将索引文件是否存在
        self.add_temp = pd.DataFrame(None)  # 初始化dataframe类型数组，便于对连续部分数据进行存储
        self.Number = 1  # 初始化循环段编号
        self.D_last = 0  # 初始化上一时刻的掘进状态
        self.MTI = 0  # 初始化两个相邻掘进段的最小时间间隔为0（minimum time interval）
        self.debug = DEBUG(_debug_)  # 调试/修复程序

    def create_cycle_dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out_path):
            os.mkdir(self.out_path)  # 创建文件夹
        else:
            shutil.rmtree(self.out_path)  # 清空文件夹
            os.mkdir(self.out_path)  # 创建文件夹

    def check_parm(self):
        """检查传入参数是否正常"""
        current_class = self.__class__.__name__
        if (not self.input_path) or (not self.out_path):  # 检查输入输出路径是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if (not self.parm) or (len(self.parm) < len(self.PARAMETERS)):  # 检查传入参数是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input parameters are faulty, Please check!!!\033[0m')
            print(' ->-> %s' % current_class, '\033[0;31mSuch as %s\033[0m' % self.PARAMETERS)  # 给出正确示例
            sys.exit()  # 抛出异常并终止程序

    def version(self):
        """展示文件版本信息及修改记录"""
        try:
            __history__()
        except NameError:
            return self

    def write_index(self, _Num_, _inf_):
        """创建索引文件并写入索引"""
        index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Index-File.csv')  # 索引文件路径及名称
        if _Num_ == -1:
            if os.path.isfile(index_path):
                self.index_exists = True  # 判断索引文件是否存在
            if self.index_exists:  # 索引文件存在
                os.remove(index_path)  # 若索引文件存在，则删除
            with open(index_path, 'w', encoding='gb2312', newline='') as f:  # 创建索引文件
                csv.writer(f).writerow(['循环段', '桩号', '日期', '掘进时间'])  # 写入标签数据
        else:
            index_csv = open(index_path, 'a', newline='')  # 打开索引文件
            csv.writer(index_csv).writerow([_inf_['num'], _inf_['stake'], _inf_['date'], _inf_['time']])  # 写入索引数据记录

    def determine_tunnel(self, _data_np_):
        """完成对掘进状态的实时判定，结合历史数据返回掘进段开始和结束位置"""
        Fx = np.int64(_data_np_ > 0)  # 判定函数 F(x) = 1(x>0), 0(x<=0)
        D_now = reduce(lambda x, y: x * y, Fx)  # D(x) = F(x1)·F(x2)...F(Xn)        lambda为自定义函数
        Tunnel = False if D_now == 0 else True  # 掘进状态 D(x) = 0(downtime), 1(Tunnel)
        # 当前时刻D(x) - 上一时刻D(x‘) = Start(>0), Finish(<0), None(=0)
        key = 'None' if D_now - self.D_last == 0 else 'Start' if D_now - self.D_last > 0 else 'Finish'
        self.D_last = D_now  # 保存上一时刻状态
        return Tunnel, key  # 掘进状态判定结果Tunnel（True/False）和掘进段开始或结束标志key（Start/Finish/None）

    def associated_data_process(self, _data_):
        """处理原始数据中相邻两天数据存在连续性的情况"""
        state = []  # 定义一个空列表，用于存储每一时刻掘进状态（处于掘进状态：True，处于停机状态：False ）
        col_name = list(_data_.index.values)  # 获取原始数据的行索引，并保存为list形式
        _data_np_ = _data_.loc[:, self.parm[3:]].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
        for col in col_name[::-1]:  # 从后往前，对每一时刻的掘进状态进行判定
            state.append(self.determine_tunnel(_data_np_[col, :])[0])  # 将该时刻的掘进状态存储至state中
            if (len(state) > self.MTI) and (not any(state[-self.MTI:-1])):
                break  # 判定两个相邻掘进段的时间间隔内（self.MTI）盾构是否处于掘进状态，若未处于掘进状态，则返回该时刻的行索引值
        _out_data_ = pd.concat([self.add_temp, _data_.loc[:col + 1, :]], ignore_index=True)  # 将前一天与当天连续部分数据进行拼接，形成一个数据集
        self.add_temp = _data_.loc[col + 1:, :]  # 将当天与后一天连续部分的数据进行单独保存，便于和后一天的数据进行拼接
        return _out_data_  # 返回拼接后的新数据集

    def cycle_extract(self, _data_):
        """完成对原始数据中的掘进段进行实时提取"""
        key = {'now-S': 0, 'now-F': 0, 'last-S': 0, 'last-F': 0}  # 当前掘进段开始与结束的行索引,上一个掘进段开始与结束的行索引
        first_cycle = True  # 是否是第一个掘进段（是：True，否：False）
        data_np = _data_.loc[:, self.parm[2:]].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
        for index, item in enumerate(data_np):  # 从前往后，对每一时刻的掘进状态进行判定（index为行索引， item为每行数据）
            _, result = self.determine_tunnel(item[1:])  # 调用掘进状态判定函数并返回掘进段开始或结束标志
            if result == 'Start':
                key['now-S'] = index  # 保存掘进段开始时的行索引
            if result == 'Finish':
                key['now-F'] = index  # 保存掘进段结束时的行索引
            if key['now-F'] > key['now-S']:  # 获取到掘进段开始和结束索引是否完整
                if first_cycle:  # 由于在获取到下一个完整掘进段的开始和结束的行索引后才对上一个循环段进行保存，因此要对第一个掘进段进行特殊处理
                    key['last-S'], key['last-F'] = key['now-S'], key['now-F']  # 首个掘进段开始和结束的行索引进行赋值
                    first_cycle = False  # 第一个掘进段索引数据读取完成，将其赋值为False
                if (key['now-S'] - key['last-F'] > self.MTI) or (index == len(data_np) - 1):  # 判断两个掘进段时间间隔是否满足要求
                    if max(data_np[key['last-S']:key['last-F'], 0]) > 0:  # V-set的最大值大于0为有效循环段
                        self.debug.debug_print([self.Number, 'Cycle:', key['last-S'], key['last-F']])  # 用于调试程序
                        self.boring_cycle_save(_data_, [key['last-S'], key['last-F']])  # 两个掘进段时间间隔满足要求，对上一掘进段进行保存
                else:
                    key['now-S'] = key['last-S']  # 两个掘进段时间间隔不满足要求，需要将上一掘进段和当前掘进段进行合并
                key['last-S'], key['last-F'] = key['now-S'], key['now-F']  # 将当前掘进段的开始和结束的行索引信息进行保存

    def read_file(self, _par_name_=None, _interval_time_=100):
        """完成对原始数据的读取"""
        self.parm, self.MTI = _par_name_, _interval_time_  # 将掘进参数和时间间隔赋值
        self.check_parm()  # 检查参数是否正常
        self.write_index(-1, {})  # 检查索引文件是否正常
        self.create_cycle_dir()  # 创建文件夹
        file_list = os.listdir(self.input_path)  # 获取输入文件夹下的所有文件名，并将其保存
        Sum = len(file_list)
        for num, file in enumerate(file_list):  # 遍历每个文件
            ST = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            self.debug.debug_start(file)  # 用于调试程序
            try:  # 首先尝试使用默认方式进行csv文件读取
                data_raw = pd.read_csv(os.path.join(self.input_path, file), index_col=0)  # 读取文件
            except UnicodeDecodeError:  # 若默认方式读取csv文件失败，则添加'gb2312'编码后重新进行尝试
                data_raw = pd.read_csv(os.path.join(self.input_path, file), index_col=0, encoding='gb2312')  # 读取文件
            data_raw.drop(data_raw.tail(1).index, inplace=True)  # 删除文件最后一行
            data_raw = data_raw.loc[:, ~data_raw.columns.str.contains('Unnamed')]  # 删除Unnamed空列
            after_process = self.associated_data_process(data_raw)  # 调用associated_data_process函数对相邻两天数据存在连续性的情况进行处理
            self.cycle_extract(after_process)  # 调用cycle_extract函数对原始数据中的循环段进行提取
            self.debug.debug_draw_N(data_raw)  # 用于调试程序
            ED = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            visual('Boring-cycle extract', cycle=num, Sum=Sum, start=ST, end=ED, Clear=False, Debug=self.debug.debug)  # 可视化
        visual('Boring-cycle extract', cycle=-1, Clear=True, Debug=self.debug.debug)  # 可视化

    def boring_cycle_save(self, _data_, _key_):
        """对已经划分出的循环段文件进行保存"""
        cycle_data = _data_.iloc[_key_[0]:_key_[1], :]  # 提取掘进段数据
        cycle_data = cycle_data.reset_index(drop=True)  # 重建提取数据的行索引
        Mark = round(cycle_data.loc[0, self.parm[0]], 2)  # 获取每个掘进段的起始桩号
        Time = cycle_data.loc[0, self.parm[1]]  # 获取每个掘进段的时间记录
        Time = pd.to_datetime(Time, format='%Y-%m-%d %H:%M:%S')  # 对时间类型记录进行转换
        year, mon, d, h, m, s = Time.year, Time.month, Time.day, Time.hour, Time.minute, Time.second  # 获取时间记录的时分秒等
        csv_name = (self.Number, Mark, year, mon, d, h, m, s)  # 文件名
        csv_path = os.path.join(self.out_path, '%00005d %.2f-%s年%s月%s日 %s时%s分%s秒.csv' % csv_name)  # 循环段保存路径
        cycle_data.to_csv(csv_path, index=False, encoding='gb2312')  # 保存csv文件
        self.write_index(1, {'num': self.Number, 'stake': Mark, 'date': Time, 'time': (_key_[1] - _key_[0])})  # 索引文件记录
        self.Number += 1  # 循环段自增


class TBM_EXTRACT(object):
    """
    TBM_EXTRACT(_input_path_, _out_path_, _debug_)为破岩关键数据提取配置模块，该模块需要传入的参数包括
    必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）} 可选参数：{程序调试/修复选项（_debug_）}
    key_extract(_key_name_)为破岩关键数据提取主模块，该模块需要传入的参数包括
    必要参数：{程序运行所需要的关键参数名称（_par_name_）}
    version()为展示程序版本及修改记录模块，该模块无需传入相关参数
    """
    def __init__(self, _input_path_=None, _out_path_=None, _debug_=False):  # 初始化函数
        self.input_path = _input_path_  # 初始化输入路径
        self.out_path = _out_path_  # 初始化输出路径
        self.parm = ''  # 掘进状态判定参数
        self.debug = DEBUG(_debug_)  # 调试/修复程序

    def create_extract_dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out_path):
            os.mkdir(self.out_path)  # 创建文件夹
        else:
            shutil.rmtree(self.out_path)  # 清空文件夹
            os.mkdir(self.out_path)  # 创建文件夹

    def check_parm(self):
        """检查传入参数是否正常"""
        current_class = self.__class__.__name__
        if (not self.input_path) or (not self.out_path):  # 检查输入输出路径是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if not self.parm:  # 检查传入参数是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input parameters are null, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序

    def version(self):
        """展示文件版本信息及修改记录"""
        try:
            __history__()
        except NameError:
            return self

    def key_extract(self,  _key_name_=None):
        """关键数据提取"""
        self.parm = _key_name_  # 将掘进参数和时间间隔赋值
        self.check_parm()  # 检查参数是否正常
        self.create_extract_dir()  # 创建文件夹
        file_name_list = os.listdir(self.input_path)  # 获取输入文件夹下的所有文件名，并将其保存
        Sum = len(file_name_list)
        for num, file_name in enumerate(file_name_list):  # 遍历每个文件
            start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            cycle_data = pd.read_csv(os.path.join(self.input_path, file_name), encoding='gb2312')  # 读取文件
            col_name = list(cycle_data)  # 获取所有列名
            self.debug.debug_start(file_name)  # 用于调试程序
            for col in _key_name_:
                self.debug.debug_print([col, col_name.index(col)])  # 用于调试程序
            self.debug.debug_finish(file_name)  # 用于调试程序
            cycle_data = cycle_data.loc[:, _key_name_]
            cycle_data.to_csv(os.path.join(self.out_path, file_name), index=False, encoding='gb2312')  # 保存csv文件
            end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            visual('Key-Data extract', cycle=num, Sum=Sum, start=start, end=end, Clear=False, Debug=self.debug.debug)  # 可视化
        visual('Key-Data extract', cycle=-1, Clear=True, Debug=self.debug.debug)  # 可视化


class TBM_CLASS(object):
    """
    TBM_CLASS(_input_path_, _out_path_)为异常分类配置模块，该模块需要传入的参数包括
    必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）}
    data_class(_par_name_, _sub_folder_)为异常分类主模块，该模块需要传入的参数包括
    必要参数：{程序运行所需要的关键参数名称（_par_name_）} 可选参数：{程序运行需要创建的子目录（_sub_folder_）若不传入参数则采用默认子目录名称}
    version()为展示程序版本及修改记录模块，该模块无需传入相关参数
    """
    PROJECT_COEFFICIENT = {'引松': 1 / 40.731, '引额-361': 1.227, '引额-362': 1.354, '引绰-667': 1.763, '引绰-668': 2.356}
    PARAMETERS = ['日期', '导向盾首里程', '刀盘转速', '推进速度(nn/M)', '刀盘扭矩',
                  '总推力', '刀盘给定转速', '推进给定速度', '推进位移', '刀盘贯入度']
    SUB_FOLDERS = ['A1class-data', 'B1class-data', 'B2class-data', 'C1class-data',
                   'C2class-data', 'D1class-data', 'E1class-data', 'Norclass-data']  # 默认子文件夹

    def __init__(self, _input_path_=None, _out_path_=None):
        self.index_exists = False  # 索引文件是否存在
        self.index_content = []  # 索引数据保存
        self.input_path = _input_path_  # 初始化输入路径
        self.out_path = _out_path_  # 初始化输出路径
        self.sub_folder = self.SUB_FOLDERS  # 子文件夹
        self.parm = self.PARAMETERS  # 过程中用到的相关参数
        self.project_type = '引绰-668'  # 工程类型（'引松'、'引额-361'、'引额-362'、'引绰-667'、'引绰-668'）
        self.length_threshold_value = 0.3  # 掘进长度下限值
        self.V_threshold_value = 120  # 推进速度上限值，引松取120，额河取200
        self.V_set_variation = 15  # 推进速度设定值变化幅度
        self.missing_ratio = 0.2  # 数据缺失率

    def create_class_Dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out_path):
            os.mkdir(self.out_path)  # 创建文件夹
        else:
            shutil.rmtree(self.out_path)  # 清空文件夹
            os.mkdir(self.out_path)  # 创建文件夹
        for index, Dir in enumerate(self.sub_folder):  # 创建子文件夹
            self.sub_folder[index] = '%d-' % (index + 1) + Dir  # 子文件夹前面添加编号
            sub_folder_path = os.path.join(self.out_path, self.sub_folder[index])  # 子文件夹路径
            if not os.path.exists(sub_folder_path):
                os.mkdir(sub_folder_path)  # 创建子文件夹

    def check_parm(self):
        """检查传入参数是否正常"""
        current_class = self.__class__.__name__
        if (not self.input_path) or (not self.out_path):  # 检查输入输出路径是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if (not self.parm) or (len(self.parm) != len(self.PARAMETERS)):  # 检查传入参数是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input parameters are faulty, Please check!!!\033[0m')
            print(' ->-> %s' % current_class, '\033[0;31mSuch as %s\033[0m' % self.PARAMETERS)
            sys.exit()  # 抛出异常并终止程序

    def version(self):
        """展示文件版本信息及修改记录"""
        try:
            __history__()
        except NameError:
            return self

    def write_index(self, _Num_, _inf_):
        """索引文件写入数据"""
        index_path = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'Index-File.csv')  # 索引文件路径
        index_name = ['循环段', 'A', 'B1', 'B2', 'C1', 'C2', 'D', 'E', 'Normal']  # 索引文件中的标题
        if _Num_ == -1:  # 对索引文件内容进行配置
            if os.path.isfile(index_path):
                self.index_exists = True  # 判断索引文件是否存在
            if self.index_exists:  # 索引文件存在
                with open(index_path, 'r+', newline='', encoding='gb2312') as f:  # 只写模式打开索引文件
                    self.index_content = copy.deepcopy(f.readlines())  # 将原始索引文件内容进行保存
                    if self.index_content[0] != '\r\n':
                        f.truncate(0)  # 清空索引文件内容，准备重新写入数据
                    else:  # 若索引文件存在，则删除  # 若文件存在，但为空文件，将其删除
                        self.index_exists = False
                with open(index_path, 'w', encoding='gb2312', newline='') as f:  # 打开索引文件
                    title = self.index_content[0].replace('\r\n', '').split(',') + index_name[1:]  # 索引文件标题内容
                    csv.writer(f).writerow(title)  # 向索引文件写入标题
            else:  # 索引文件不存在
                with open(index_path, 'w', encoding='gb2312', newline='') as f:  # 创建新的索引文件
                    csv.writer(f).writerow(index_name)  # 写入标题内容
        else:
            if self.index_exists:  # 索引文件存在
                data = self.index_content[_Num_].replace('\r\n', '').split(',') + _inf_  # 数据内容
            else:
                data = [_Num_] + _inf_  # 数据内容
            with open(index_path, 'a', encoding='gb2312', newline='') as f:  # 打开索引文件
                csv.writer(f).writerow(data)  # 写入数据

    def A_premature(self, _cycle_):
        """判断数据类型是不是A_premature"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parm[1]]  # 获取桩号,导向盾首里程（self.parm[1]）
        start_length = _cycle_.loc[0, self.parm[8]]  # 获取循环段开始点位移,推进位移（self.parm[8]）
        end_length = _cycle_.loc[_cycle_.shape[0] - 1, self.parm[8]]  # 获取循环段结束点位移,推进位移（self.parm[8]）
        length = (end_length - start_length) / 1000  # 循环段掘进长度
        if length < self.length_threshold_value:
            Anomaly_classification = 'A'  # 异常分类A
        return Anomaly_classification, stake  # 数据分类的结果(Anomaly...),桩号(stake)

    def B1_markAndModify(self, _cycle_):
        """判断数据类型是不是B1_markAndModify"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parm[1]]  # 获取桩号，导向盾首里程（self.parm[1]）
        data_V = _cycle_.loc[:, self.parm[3]].values  # 获取推进速度并转化类型，推进速度（self.parm[3]）
        data_len = len(data_V)  # 获取循环段长度
        data_mean, data_std = np.mean(data_V), np.std(data_V)  # 获取推进速度均值和标准差
        for i in range(data_len):
            if data_V[i] > self.V_threshold_value and (data_V[i] > data_mean + 3 * data_std):
                Anomaly_classification = 'B1'  # 异常分类B1
                data_V[i] = sum(data_V[i - 10:i]) / 10.0  # 采用前10个推进速度的平均值进行替换
        _cycle_[self.parm[3]] = pd.DataFrame(data_V)  # 对异常推进速度值进行替换，推进速度（self.parm[3]）
        return Anomaly_classification, data_V, _cycle_, stake  # 数据分类的结果(Anomaly...),修正的速度(data_V),桩号(stake)

    def B2_constant(self, _cycle_):
        """判断数据类型是不是B2_constant"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parm[1]]  # 获取桩号，导向盾首里程（self.parm[1]）
        data_F = _cycle_.loc[:, self.parm[5]].values  # 获取刀盘推力并转化类型，刀盘推力（self.parm[5]）
        for i in range(len(data_F) - 4):
            if (not np.std(data_F[i:i + 5])) and (np.mean(data_F[i:i + 5])):  # 判断刀盘扭矩是否连续五个数值稳定不变
                Anomaly_classification = 'B2'
                break
        return Anomaly_classification, stake  # 数据分类的结果(Anomaly...),桩号(stake)

    def C1_sine(self, _cycle_):
        """判断数据类型是不是C1_sine"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parm[1]]  # 获取桩号，导向盾首里程（self.parm[1]）
        data_T = _cycle_.loc[:, self.parm[4]]  # 获取刀盘扭矩并转化类型，刀盘扭矩（self.parm[4]）
        T_mean = data_T.mean()
        df_T_fft = fft(data_T.values)
        power = np.abs(df_T_fft) ** 2
        df_T_freq = scipy.fft.fftfreq(data_T.size, d=1)
        df_data = pd.DataFrame(df_T_freq[2:int(df_T_freq.size / 2)], columns=['Freq'])
        df_data['power'] = power[2:int(df_T_freq.size / 2)]
        df_selected = df_data[lambda df: df['Freq'] > 0.03]
        df_selected = df_selected[lambda df: df['Freq'] < 0.09]
        energy = df_selected['power'].sum() / df_data['power'].sum()
        if energy > 0.15 and T_mean < 600:  # and length>0.3
            Anomaly_classification = 'C1'
        return Anomaly_classification, energy, stake

    def C2_shutdown(self, _cycle_):
        """判断数据类型是不是C2_shutdown"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parm[1]]  # 获取桩号，导向盾首里程（self.parm[1]）
        N_set = _cycle_.loc[:, self.parm[6]].values  # 获取刀盘转速设定值，刀盘转速设定值（self.parm[6]）
        V_set = _cycle_.loc[:, self.parm[7]].values  # 获取推进速度设定值，推进速度设定值（self.parm[7]）
        for N_set_value, V_set_value in zip(N_set, V_set):
            if V_set_value == 0 and N_set_value > 0.1:
                Anomaly_classification = 'C2'
                break
        return Anomaly_classification, stake

    def D_adjust_setting(self, _cycle_):
        """判断数据类型是不是D_adjust_setting"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parm[1]]  # 获取桩号，导向盾首里程（self.parm[1]）
        data_V = _cycle_.loc[:, self.parm[3]]  # 获取推进速度，推进速度（self.parm[3]）
        V_mean, V_std = data_V.mean(), data_V.std()  # 获取推进速度均值和标准差
        rule = ((data_V < 0) | (data_V > self.V_threshold_value) | (data_V > V_mean + 3 * V_std))  # 满足条件的数据
        index = np.arange(data_V.shape[0])[rule]  # 满足条件的索引
        _cycle_ = _cycle_.drop(index, axis=0)  # 删除相关数据
        _cycle_.index = [i for i in range(_cycle_.shape[0])]  # 重建新数据集的行索引
        data_V_set = (_cycle_.loc[:, self.parm[7]] * self.PROJECT_COEFFICIENT[self.project_type]).std()  # 获取推进速度设定值的方差
        if data_V_set > self.V_set_variation:
            Anomaly_classification = 'D'  # 异常分类D
        return Anomaly_classification, stake  # 数据分类的结果(Anomaly...),桩号(stake)

    def E_missing_ratio(self, _cycle_):
        """判断数据类型是不是E_missing_ratio"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parm[1]]  # 获取桩号，导向盾首里程（self.parm[1]）
        data_time = _cycle_.loc[:, self.parm[0]].values  # 获取日期并转化类型，日期（self.parm[0]）
        time_start = pd.to_datetime(data_time[0], format='%Y-%m-%d %H:%M:%S')  # 循环段开始日期
        time_end = pd.to_datetime(data_time[-1], format='%Y-%m-%d %H:%M:%S')  # 循环段结束日期
        time_diff = (time_end - time_start).seconds  # 时间差，以s为单位
        time_len = len(data_time)  # 实际时间
        missing_ratio = (time_diff - time_len) / time_diff  # 缺失率计算
        if missing_ratio > self.missing_ratio:
            Anomaly_classification = 'E'  # 异常分类E
        return Anomaly_classification, missing_ratio, stake  # 数据分类的结果(Anomaly...),缺失率(missing_ratio),桩号(stake)

    def data_class(self, _par_name_=None, _sub_folder_=None):
        """数据分类"""
        self.parm = _par_name_  # 所用到的参数
        if _sub_folder_:
            self.sub_folder = _sub_folder_
        self.check_parm()  # 检查参数是否正常
        self.write_index(-1, {})  # 检查索引文件是否正常
        self.create_class_Dir()  # 创建文件夹
        csv_list = os.listdir(self.input_path)  # 获取输入文件夹下的所有文件名，并将其保存
        for num, name in enumerate(csv_list):
            start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            local_csv_path = os.path.join(self.input_path, name)
            try:
                cycle = pd.read_csv(local_csv_path, encoding='gb2312')
            except UnicodeDecodeError:  # 若默认方式读取csv文件失败，则添加'gb2312'编码后重新进行尝试
                cycle = pd.read_csv(local_csv_path)
            except_type = ['' for _ in range(8)]  # 创建列表用来存储异常类型
            if_Normal = 0
            if self.A_premature(cycle)[0] == 'Normal':
                try:
                    RS_index = TBM_SPLIT().get_RS_index(cycle)
                except NameError:
                    RS_index = self.get_RS_index(cycle)
                this_cycle = cycle.loc[RS_index['rise']:RS_index['steadyE'], :]
                this_cycle = this_cycle.reset_index(drop=True)  # 重建提取数据的行索引  # 重建新数据集的行索引
                this_cycle_steady = cycle.loc[RS_index['steadyS']:RS_index['steadyE'], :]
                this_cycle_steady = this_cycle_steady.reset_index(drop=True)  # 重建新数据集的行索引
            else:
                except_type[0] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(os.path.join(self.out_path, self.sub_folder[0]), name))
                self.write_index(int(name[:5]), except_type)
                continue
            if self.B1_markAndModify(this_cycle_steady)[0] == 'B1':
                except_type[1] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(os.path.join(self.out_path, self.sub_folder[1]), name))
            if self.B2_constant(this_cycle)[0] == 'B2':
                except_type[2] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(os.path.join(self.out_path, self.sub_folder[2]), name))
            if self.C1_sine(this_cycle)[0] == 'C1':
                except_type[3] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(os.path.join(self.out_path, self.sub_folder[3]), name))
            if self.C2_shutdown(this_cycle_steady)[0] == 'C2':
                except_type[4] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(os.path.join(self.out_path, self.sub_folder[4]), name))
            if self.D_adjust_setting(this_cycle_steady)[0] == 'D':
                except_type[5] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(os.path.join(self.out_path, self.sub_folder[5]), name))
            if self.E_missing_ratio(this_cycle)[0] == 'E':
                except_type[6] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(os.path.join(self.out_path, self.sub_folder[6]), name))
            if not if_Normal:
                except_type[7] = 'True'
                shutil.copyfile(local_csv_path, os.path.join(os.path.join(self.out_path, self.sub_folder[7]), name))
            self.write_index(int(name[:5]), except_type)
            end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            visual('Data-Class', cycle=num, Sum=len(csv_list), start=start, end=end, Clear=False)
        visual('Data-Class', cycle=-1, Clear=True)

    def get_RS_index(self, _data_):
        """获取空推、上升、稳定、下降的关键点"""
        RS_index = {'rise': 0, 'steadyS': 0, 'steadyE': 0}  # 初始化空推、上升、稳定、下降的关键点
        V_mean = int(_data_[self.parm[3]].mean())  # 推进速度索引（self.parm[3]）
        mid_point = 0  # 中点位置索引
        while _data_[self.parm[3]][mid_point] < V_mean:  # 推进速度索引（self.parm[3]）
            mid_point += 5
        steadyE = _data_.shape[0] - 1  # 稳定段结束位置索引
        while _data_[self.parm[3]][steadyE] <= V_mean:  # 推进速度索引（self.parm[3]）
            steadyE -= 1
        if mid_point:
            rise = mid_point  # 上升段开始位置处索引
            while _data_[self.parm[9]][rise] > 2 and rise > 10:  # 刀盘贯入度度索引（self.parm[9]）
                rise -= 1
            steadyS = mid_point  # 稳定段开始位置处索引
            V_set_mean = int(_data_[self.parm[7]].mean())  # 推进速度设定值索引（self.parm[7]）
            V_assist = _data_[self.parm[3]] / V_set_mean  # 推进速度索引（self.parm[3]）
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


class TBM_CLEAN(object):
    """
    TBM_CLEAN(_input_path_, _out_path_)为异常数据清理修正配置模块，该模块需要传入的参数包括
    必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）}
    data_clean(_par_name_, _sub_folder_)为异常数据清理修正主模块，该模块需要传入的参数包括
    必要参数：{程序运行所需要的关键参数名称（_par_name_）} 可选参数：{程序运行需要创建的子目录（_sub_folder_）若不传入参数则采用默认子目录名称}
    version()为展示程序版本及修改记录模块，该模块无需传入相关参数
    """
    PARAMETERS = ['日期', '导向盾首里程', '刀盘转速', '推进速度(nn/M)', '刀盘扭矩', '总推力', '刀盘给定转速', '推进给定速度', '推进位移', '刀盘贯入度']
    SUB_FOLDERS = ['NorA1class-data', 'NorB1class-data', 'NorB2class-data', 'NorC1class-data',
                   'NorC2class-data', 'NorD1class-data', 'NorE1class-data', 'Norclass-data', ]

    def __init__(self, _input_path_=None, _out_path_=None):
        self.parm = self.PARAMETERS  # 过程中用到的相关参数
        self.input_path = _input_path_  # 初始化输入路径
        self.out_path = _out_path_  # 初始化输出路径
        self.sub_folder = self.SUB_FOLDERS  # 文件输出路径
        self.V_threshold_value = 120  # 推进速度上限值，引松取120，额河取200

    def create_clean_Dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out_path):
            os.mkdir(self.out_path)  # 创建文件夹
        else:
            shutil.rmtree(self.out_path)  # 清空文件夹
            os.mkdir(self.out_path)  # 创建文件夹
        for index, Dir in enumerate(self.sub_folder):  # 创建子文件夹
            self.sub_folder[index] = '%d-' % (index + 1) + Dir  # 子文件夹前面添加编号
            sub_folder_path = os.path.join(self.out_path, self.sub_folder[index])  # 子文件夹路径
            if not os.path.exists(sub_folder_path):
                os.mkdir(sub_folder_path)  # 创建子文件夹

    def check_parm(self):
        """检查传入参数是否正常"""
        current_class = self.__class__.__name__
        if (not self.input_path) or (not self.out_path):  # 检查输入输出路径是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if (not self.parm) or (len(self.parm) != len(self.PARAMETERS)):  # 检查传入参数是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input parameters are faulty, Please check!!!\033[0m')
            print(' ->-> %s' % current_class, '\033[0;31mSuch as %s\033[0m' % self.PARAMETERS)
            sys.exit()  # 抛出异常并终止程序

    def version(self):
        """展示文件版本信息及修改记录"""
        try:
            __history__()
        except NameError:
            return self

    def get_RS_index(self, _data_):
        """获取空推、上升、稳定、下降的关键点"""
        RS_index = {'rise': 0, 'steadyS': 0, 'steadyE': 0}  # 初始化空推、上升、稳定、下降的关键点
        V_mean = int(_data_[self.parm[3]].mean())  # 推进速度索引（self.parm[3]）
        mid_point = 0  # 中点位置索引
        while _data_[self.parm[3]][mid_point] < V_mean:  # 推进速度索引（self.parm[3]）
            mid_point += 5
        steadyE = _data_.shape[0] - 1  # 稳定段结束位置索引
        while _data_[self.parm[3]][steadyE] <= V_mean:  # 推进速度索引（self.parm[3]）
            steadyE -= 1
        if mid_point:
            rise = mid_point  # 上升段开始位置处索引
            while _data_[self.parm[9]][rise] > 2 and rise > 10:  # 刀盘贯入度度索引（self.parm[9]）
                rise -= 1
            steadyS = mid_point  # 稳定段开始位置处索引
            V_set_mean = int(_data_[self.parm[7]].mean())  # 推进速度设定值索引（self.parm[7]）
            V_assist = _data_[self.parm[3]] / V_set_mean  # 推进速度索引（self.parm[3]）
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

    def A_premature_Modify(self, _cycle_):
        """判断数据类型是不是A_premature"""
        pass

    def B1_mark_Modify(self, _cycle_):
        """判断数据类型是不是B1_markAndModify"""
        data_V = _cycle_.loc[:, self.parm[3]].values  # 推进速度（self.parm[3]）
        data_mean, data_std = np.mean(data_V), np.std(data_V)  # 获取推进速度均值和标准差
        for i in range(len(data_V)):
            if data_V[i] > self.V_threshold_value or (data_V[i] > data_mean + 3 * data_std):
                replace = sum(data_V[i - 10:i]) / 10.0  # 采用前10个推进速度的平均值进行替换
                _cycle_.loc[i, self.parm[3]] = replace  # 采用前10个推进速度的平均值进行替换
        return True  # 处理完成后的数据

    def B2_constant_Modify(self, _cycle_):
        """判断数据类型是不是B2_constant"""
        pass

    def C1_sine_Modify(self, _cycle_):
        """判断数据类型是不是C1_sine"""
        pass

    def C2_shutdown_Modify(self, _cycle_):
        """判断数据类型是不是C2_shutdown"""
        pass

    def D_adjust_setting_Modify(self, _cycle__):
        """判断数据类型是不是D_adjust_setting"""
        pass

    def E_missing_ratio_Modify(self, _cycle_):
        """判断数据类型是不是E_missing_ratio"""
        pass

    def data_clean(self, _par_name_=None, _sub_folder_=None):
        """将数据类型进行汇总并保存"""
        self.parm = _par_name_  # 所用到的参数
        if _sub_folder_:
            self.sub_folder = _sub_folder_
        self.check_parm()  # 检查参数是否正常
        self.create_clean_Dir()  # 创建文件夹
        except_name = ['A', 'B1', 'B2', 'C1', 'C2', 'D', 'E', 'Normal']  # 新添加索引数据标题
        for Type, Dir in zip(except_name, os.listdir(self.input_path)):
            csv_list = os.listdir(os.path.join(self.input_path, Dir))  # 获取输入文件夹下的所有文件名，并将其保存
            for num, csv_file in enumerate(csv_list):
                start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                local_csv_path = os.path.join(os.path.join(self.input_path, Dir), csv_file)
                if Type == 'Normal':
                    shutil.copyfile(local_csv_path,
                                    os.path.join(os.path.join(self.out_path, self.sub_folder[-1]), csv_file))
                    continue
                else:
                    cycle = pd.read_csv(local_csv_path, encoding='gb2312')
                local = -1
                if Type == 'A' and self.A_premature_Modify(cycle):
                    local = except_name.index(Type)
                if Type == 'B1' and self.B1_mark_Modify(cycle):
                    local = except_name.index(Type)
                if Type == 'B2' and self.B2_constant_Modify(cycle):
                    local = except_name.index(Type)
                if Type == 'C1' and self.C1_sine_Modify(cycle):
                    local = except_name.index(Type)
                if Type == 'C2' and self.C2_shutdown_Modify(cycle):
                    local = except_name.index(Type)
                if Type == 'D' and self.D_adjust_setting_Modify(cycle):
                    local = except_name.index(Type)
                if Type == 'E' and self.E_missing_ratio_Modify(cycle):
                    local = except_name.index(Type)
                if local != -1:
                    save_path = os.path.join(self.out_path + self.sub_folder[local], csv_file)
                    cycle.to_csv(save_path, index=False, encoding='gb2312')  # 保存csv文件
                end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                visual('Clean-Data extract', cycle=num, Sum=len(csv_list), start=start, end=end, Clear=False)
        visual('Clean-Data extract', cycle=-1, Clear=True)


class TBM_MERGE(object):
    """
    TBM_MERGE(_input_path_, _out_path_)为数据集合并配置模块，该模块需要传入的参数包括
    必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）}
    data_merge()为数据集合并主模块，该模块无需传入相关参数
    version()为展示程序版本及修改记录模块，该模块无需传入相关参数
    """
    def __init__(self, _input_path_=None, _out_path_=None):
        self.input_path = _input_path_  # 初始化输入路径
        self.out_path = _out_path_  # 初始化输出路径

    def create_merge_Dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out_path):
            os.mkdir(self.out_path)  # 创建文件夹
        else:
            shutil.rmtree(self.out_path)  # 清空文件夹
            os.mkdir(self.out_path)  # 创建文件夹

    def check_parm(self):
        """检查传入参数是否正常"""
        current_class = self.__class__.__name__
        if (not self.input_path) or (not self.out_path):  # 检查输入输出路径是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序

    def version(self):
        """展示文件版本信息及修改记录"""
        try:
            __history__()
        except NameError:
            return self

    def data_merge(self):
        """合并形成机器学习数据集"""
        self.check_parm()  # 检查参数是否正常
        self.create_merge_Dir()  # 创建文件夹
        for file in os.listdir(self.input_path):
            path = os.path.join(self.input_path, file)
            Sum = len(os.listdir(path))
            if os.path.isdir(path):
                for num, Csv in enumerate(os.listdir(path)):
                    start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                    now_csv = os.path.join(path, Csv)
                    target_csv = os.path.join(self.out_path, Csv)
                    shutil.copyfile(now_csv, target_csv)
                    end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                    visual('Merge-Data extract', cycle=num, Sum=Sum, start=start, end=end, Clear=False)
        visual('Merge-Data extract', cycle=-1, Clear=True)


class TBM_SPLIT(object):
    """
    TBM_SPLIT(_input_path_, _out_path_, _debug_)为内部段分割配置模块，该模块需要传入的参数包括
    必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）} 可选参数：{程序调试/修复选项（_debug_）}
    data_clean(_par_name_, _sub_folder_)为内部段分割主模块，该模块需要传入的参数包括
    必要参数：{程序运行所需要的关键参数名称（_par_name_）} 可选参数：{程序运行需要创建的子目录（_sub_folder_）若不传入参数则采用默认子目录名称}
    version()为展示程序版本及修改记录模块，该模块无需传入相关参数
    """
    SUB_FOLDERS = ['Free running', 'Loading', 'Boring', 'Loading and Boring', 'Boring cycle']
    PARAMETERS = ['推进位移', '推进速度(nn/M)', '刀盘贯入度', '推进给定速度']

    def __init__(self, _input_path_=None, _out_path_=None, _debug_=False):
        self.input_path = _input_path_  # 初始化输入路径
        self.out_path = _out_path_  # 初始化输出路径
        self.sub_folder = self.SUB_FOLDERS  # 初始化子文件夹
        self.parm = self.PARAMETERS  # 初始化程序处理过程中需要用到的参数
        self.index_exists = False  # 索引文件是否存在
        self.index_content = []  # 索引数据保存
        self.index_number = 1  # 索引文件行位置记录
        self.min_time = 100  # 最小掘进时长(s)
        self.min_length = 0.1  # 最小掘进距离(m)
        self.min_loading = 30  # 上升段最小掘进时长（s）
        self.min_boring = 50  # 稳定段最小掘进时长（s）
        self.debug = DEBUG(_debug_)  # 调试/修复程序

    def create_split_Dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out_path):
            os.mkdir(self.out_path)  # 创建文件夹
        else:
            shutil.rmtree(self.out_path)  # 清空文件夹
            os.mkdir(self.out_path)  # 创建文件夹
        for index, Dir in enumerate(self.sub_folder):  # 创建子文件夹
            self.sub_folder[index] = '%d-' % (index + 1) + Dir  # 子文件夹前面添加编号
            sub_folder_path = os.path.join(self.out_path, self.sub_folder[index])  # 子文件夹路径
            if not os.path.exists(sub_folder_path):
                os.mkdir(sub_folder_path)  # 创建子文件夹

    def check_parm(self):
        """检查传入参数是否正常"""
        current_class = self.__class__.__name__
        if (not self.input_path) or (not self.out_path):  # 检查输入输出路径是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if (not self.parm) or (len(self.parm) != len(self.PARAMETERS)):  # 检查传入参数是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input parameters are faulty, Please check!!!\033[0m')
            print(' ->-> %s' % current_class, '\033[0;31mSuch as %s\033[0m' % self.PARAMETERS)
            sys.exit()  # 抛出异常并终止程序

    def version(self):
        """展示文件版本信息及修改记录"""
        try:
            __history__()
        except NameError:
            return self

    def write_index(self, _Num_, _inf_):
        """索引文件写入数据"""
        index_path = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'Index-File.csv')  # 索引文件路径
        index_name = ['循环段', '上升段起点', '稳定段起点', '稳定段终点']  # 索引文件中的标题
        index_data = list(_inf_.values())  # 索引文件中的数据内容
        if _Num_ == -1:  # 对索引文件内容进行配置
            if os.path.isfile(index_path):
                self.index_exists = True  # 判断索引文件是否存在
            if self.index_exists:  # 索引文件存在
                with open(index_path, 'r+', newline='', encoding='gb2312') as f:  # 只写模式打开索引文件
                    self.index_content = copy.deepcopy(f.readlines())  # 将原始索引文件内容进行保存
                    if self.index_content[0] != '\r\n':
                        f.truncate(0)  # 清空索引文件内容，准备重新写入数据
                    else:  # 若索引文件存在，则删除  # 若文件存在，但为空文件，将其删除
                        self.index_exists = False
                with open(index_path, 'w', encoding='gb2312', newline='') as f:  # 打开索引文件
                    title = self.index_content[0].replace('\r\n', '').split(',') + index_name[1:]  # 索引文件标题内容
                    csv.writer(f).writerow(title)  # 向索引文件写入标题
            else:  # 索引文件不存在
                with open(index_path, 'w', encoding='gb2312', newline='') as f:  # 创建新的索引文件
                    csv.writer(f).writerow(index_name)  # 写入标题内容
        else:
            while self.index_number < _Num_:  # 对中间空行数据进行处理
                if self.index_exists:  # 索引文件存在
                    data = self.index_content[self.index_number].replace('\r\n', '').split(',') + ['', '', '']  # 索引文件数据
                else:  # 索引文件不存在
                    data = [_Num_] + ['', '', '']  # 索引文件数据
                with open(index_path, 'a', encoding='gb2312', newline='') as f:  # 创建索引文件
                    csv.writer(f).writerow(data)  # 写入标签数据
                self.index_number += 1
            if self.index_exists:  # 索引文件存在
                data = self.index_content[self.index_number].replace('\r\n', '').split(',') + index_data  # 索引文件数据
            else:  # 索引文件不存在
                data = [_Num_] + index_data  # 索引文件数据
            with open(index_path, 'a', encoding='gb2312', newline='') as f:  # 创建索引文件
                csv.writer(f).writerow(data)  # 写入标签数据
            self.index_number += 1

    def segment_save(self, _data_, _name_, _key_):
        """对已经分割好的循环段文件进行保存"""
        Time_Loading = _key_['steadyS'] - _key_['rise']  # 上升段持续时间
        Time_Boring = _key_['steadyE'] - _key_['steadyS']  # 上升段持续时间
        if Time_Loading > self.min_loading and Time_Boring > self.min_boring:  # 空推段持续时间不为0，上升段持续时间>30s，稳定段持续时间>50s
            out_data = [_data_.iloc[:_key_['rise'], :],  # 空推段数据
                        _data_.iloc[_key_['rise']:_key_['steadyS'], :],  # 上升段数据
                        _data_.iloc[_key_['steadyS']:_key_['steadyE'], :],  # 稳定段数据
                        _data_.iloc[_key_['rise']:_key_['steadyE'], :]]  # 上升段和稳定段
            for num, data in enumerate(out_data):
                out_path = os.path.join(os.path.join(self.out_path, self.sub_folder[num]), _name_)
                data.to_csv(out_path, index=False, encoding='gb2312')  # 保存数据

    def data_split(self, _par_name_=None, _sub_folder_=None):
        """对数据进行整体和细部分割"""
        self.parm = _par_name_  # 所用到的参数
        if _sub_folder_:
            self.sub_folder = _sub_folder_
        self.check_parm()  # 检查参数是否正常
        self.write_index(-1, {})  # 检查索引文件是否正常
        self.create_split_Dir()  # 创建文件夹
        file_name_list = os.listdir(self.input_path)  # 获取输入文件夹下的所有文件名，并将其保存
        Sum = len(file_name_list)
        for num, file in enumerate(file_name_list):  # 遍历每个文件
            start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            try:
                data_cycle = pd.read_csv(os.path.join(self.input_path, file), encoding='gb2312')  # 读取循环段文件
            except UnicodeDecodeError:
                data_cycle = pd.read_csv(os.path.join(self.input_path, file))  # 读取循环段文件
            if data_cycle.shape[0] >= self.min_time:  # 判断是否为有效循环段
                length = (data_cycle.loc[data_cycle.shape[0] - 1, self.parm[0]] - data_cycle.loc[
                    0, self.parm[0]]) / 1000
                if length > self.min_length:  # 推进位移要大于0.1m,实际上推进位移有正有负
                    self.debug.debug_start(file)  # 用于调试程序
                    RS_Index = self.get_RS_index(data_cycle)  # 调用函数，获取空推、上升、稳定、下降的变化点
                    self.debug.debug_print(list(RS_Index.values()))  # 用于调试程序
                    self.segment_save(data_cycle, file, RS_Index)  # 数据保存
                    self.write_index(int(file[:5]), RS_Index)
                    self.debug.debug_draw_V(data_cycle)  # 用于调试程序
            end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            visual('Data_Split', cycle=num, Sum=Sum, start=start, end=end, Clear=False, Debug=self.debug.debug)
        visual('Data_Split', cycle=-1, Clear=True, Debug=self.debug.debug)

    def data_filter(self, _data_, _par_name_=None):
        """参数滤波"""
        out_data = copy.deepcopy(_data_)
        if _par_name_:
            for col in _par_name_:
                out_data.loc[:, col] = scipy.signal.savgol_filter(out_data.loc[:, col], 19, 4)
        return out_data

    def get_RS_index(self, _data_):
        """获取空推、上升、稳定、下降的关键点"""
        data_filter = self.data_filter(_data_, ['推进速度(nn/M)'])
        V_mean = int(data_filter[self.parm[1]].mean())  # 推进速度索引（self.parm[3]）
        mid_point = 0  # 中点位置索引
        while data_filter[self.parm[1]][mid_point] < V_mean:  # 推进速度索引（self.parm[3]）
            mid_point += 5
        steadyE = _data_.shape[0] - 1  # 稳定段结束位置索引
        while data_filter[self.parm[1]][steadyE] <= V_mean:  # 推进速度索引（self.parm[3]）
            steadyE -= 1
        if mid_point:
            rise = mid_point  # 上升段开始位置处索引
            while _data_[self.parm[2]][rise] > 2 and rise > 10:  # 刀盘贯入度度索引（self.parm[9]）
                rise -= 1
            steadyS = mid_point  # 稳定段开始位置处索引
            V_set_mean = int(_data_[self.parm[3]].mean())  # 推进速度设定值索引（self.parm[7]）
            V_assist = data_filter[self.parm[1]] / V_set_mean  # 推进速度索引（self.parm[3]）
            while V_assist[steadyS] - V_assist.mean() <= 0:
                steadyS += 1
            steady_V_mean = V_assist.iloc[steadyS:steadyE].mean()  # 整个稳定段推进速度均值
            while V_assist.iloc[steadyS] < steady_V_mean:  # 稳定段开始位置处的均值是否大于整个稳定段推进速度均值
                steadyS += 1
            RS_index = {'rise': rise, 'steadyS': steadyS, 'steadyE': steadyE}  # 初始化空推、上升、稳定、下降的关键点
        else:
            RS_index = {'rise': int(_data_.shape[0] * 0.1), 'steadyS': int(_data_.shape[0] * 0.3), 'steadyE': steadyE}
        return RS_index


class TBM_FILTER(object):
    """
    TBM_FILTER(_input_path_, _out_path_)为数据降噪配置模块，该模块需要传入的参数包括
    必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）}
    data_filter(_par_name_)为数据降噪主模块，该模块需要传入的参数包括
    可选参数：{程序运行所需要的关键参数名称（_par_name_），若传入参数，则仅对传入的参数进行降噪，若不传入参数，则对所有参数进行降噪}
    version()为展示程序版本及修改记录模块，该模块无需传入相关参数
    """
    def __init__(self, _input_path_=None, _out_path_=None):  # 初始化函数
        self.input_path = _input_path_  # 初始化输入路径
        self.out_path = _out_path_  # 初始化输出路径
        self.parm = ''  # 掘进状态判定参数

    def create_filter_dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out_path):
            os.mkdir(self.out_path)  # 创建文件夹
        else:
            shutil.rmtree(self.out_path)  # 清空文件夹
            os.mkdir(self.out_path)  # 创建文件夹

    def check_parm(self):
        """检查传入参数是否正常"""
        current_class = self.__class__.__name__
        if (not self.input_path) or (not self.out_path):  # 检查输入输出路径是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序

    def version(self):
        """展示文件版本信息及修改记录"""
        try:
            __history__()
        except NameError:
            return self

    def data_filter(self, _par_name_=None):
        """巴特沃斯滤波器"""
        self.parm = _par_name_  # 将掘进参数和时间间隔赋值
        self.check_parm()  # 检查参数是否正常
        self.create_filter_dir()  # 创建文件夹
        file_name_list = os.listdir(self.input_path)  # 获取输入文件夹下的所有文件名，并将其保存
        Sum = len(file_name_list)
        for num, file_name in enumerate(file_name_list):  # 遍历每个文件
            start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            try:
                TBM_Data = pd.read_csv(os.path.join(self.input_path, file_name), encoding='gb2312')  # 读取文件
            except UnicodeDecodeError:
                TBM_Data = pd.read_csv(os.path.join(self.input_path, file_name))  # 读取文件
            if self.parm:
                for col in self.parm:
                    TBM_Data.loc[:, col] = scipy.signal.savgol_filter(TBM_Data.loc[:, col], 19, 4)
            else:
                for col in range(TBM_Data.shape[1]):
                    if type(TBM_Data.iloc[0, col]) != type('str'):
                        TBM_Data.iloc[:, col] = scipy.signal.savgol_filter(TBM_Data.iloc[:, col], 19, 4)
            TBM_Data.to_csv(os.path.join(self.input_path, file_name), index=False, encoding='gb2312')  # 保存关键参数
            end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            visual('Data filter', cycle=num, Sum=Sum, start=start, end=end, Clear=False)
        visual('Data filter', cycle=-1, Clear=True)


class TBM_REPORT(object):
    """
    TBM_REPORT(_input_path_, _input_pic_, _out_path_)为参数绘图配置模块，该模块需要传入的参数包括
    必要参数：{原始文件存放路径（_input_path_），原始图片存放路径（_input_pic_），生成数据的保存路径（_out_path_）}
    cre_pdf(_par_name_)为参数绘图主模块，该模块需要传入的参数包括
    必要参数：{程序运行所需要的关键参数名称（_par_name_）}
    version()为展示程序版本及修改记录模块，该模块无需传入相关参数
    """
    ROCK_GRADE = {1: 'Ⅰ', 2: 'Ⅱ', 3: 'Ⅲ', 4: 'Ⅳ', 5: 'Ⅴ', 6: 'Ⅵ'}  # 定义围岩等级和与之对应的字符表达（字典类型）
    PARAMETERS = ['导向盾首里程', '日期', '推进位移']

    def __init__(self, _input_path_=None, _input_pic_=None, _out_path_=None):
        self.size_font = 8  # 页面字体大小为8
        self.type_font = 'SimSun'  # 页面字体类型
        self.page = 1  # 用于存储当前页
        self.parm = self.PARAMETERS  # 参数列（参数名称）
        self.input_path = _input_path_  # 初始化输入路径
        self.input_pic = _input_pic_  # 初始化输入路径
        self.out_path = _out_path_  # 初始化输出路径

    def create_report_Dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out_path):
            os.mkdir(self.out_path)
        else:
            shutil.rmtree(self.out_path)
            os.mkdir(self.out_path)

    def check_parm(self):
        """检查传入参数是否正常"""
        current_class = self.__class__.__name__
        if (not self.input_path) or (not self.out_path) or (not self.input_pic):  # 检查传入参数是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if (not self.parm) or (len(self.parm) != len(self.PARAMETERS)):  # 检查传入参数是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input parameters are faulty, Please check!!!\033[0m')
            print(' ->-> %s' % current_class, '\033[0;31mSuch as %s\033[0m' % self.PARAMETERS)
            sys.exit()  # 抛出异常并终止程序

    def version(self):
        """展示文件版本信息及修改记录"""
        try:
            __history__()
        except NameError:
            return self

    def add_footer_info(self, Object):
        """添加每页页脚"""
        Object.setFont(self.type_font, self.size_font)  # 设置字体类型及大小
        Object.setFillColor(colors.black)  # 设置字体颜色
        Object.drawString(105 * mm, 10 * mm, f'Page%d' % self.page)  # 页脚信息
        self.page += 1  # 页脚信息自增

    def add_text_info(self, Object, _Inf_):
        """添加正文信息"""
        format_data = []  # 用于存储页面信息
        for row in range(3):  # 对_Inf_信息转换为符合要求的形式
            format_data.append(_Inf_[2 * row][0] + _Inf_[2 * row + 1][0])
            format_data.append(_Inf_[2 * row][1] + _Inf_[2 * row + 1][1])
            format_data.append(['' for _ in range(12)])
        Cell_w = [13 * mm, 9 * mm, 12 * mm, 13 * mm, 13 * mm, 25 * mm, 13 * mm, 9 * mm, 12 * mm, 13 * mm, 13 * mm,
                  25 * mm]  # 表格列宽信息
        Cell_h = [8 * mm, 8 * mm, 68 * mm, 8 * mm, 8 * mm, 68 * mm, 8 * mm, 8 * mm, 68 * mm]  # 表格行高信息
        sheet = Table(format_data, colWidths=Cell_w, rowHeights=Cell_h,  # 创建表格并写入信息
                      style={("FONT", (0, 0), (-1, -1), self.type_font, self.size_font),  # 字体
                             ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),  # 字体颜色
                             ('SPAN', (0, 2), (5, 2)), ('SPAN', (6, 2), (-1, 2)), ('SPAN', (0, 5), (5, 5)),  # 合并单元格
                             ('SPAN', (6, 5), (-1, 5)), ('SPAN', (0, 8), (5, 8)), ('SPAN', (6, 8), (-1, 8)),  # 合并单元格
                             ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # 左右上下居中
                             ('INNERGRID', (0, 0), (-1, -1), 0.7, colors.black),  # 内部框线
                             ('BOX', (0, 0), (-1, -1), 0.7, colors.black)})  # 外部框线
        sheet.wrapOn(Object, 0, 0)  # 将sheet添加到Canvas中
        sheet.drawOn(Object, 20 * mm, 24 * mm)  # 将sheet添加到Canvas中

    def add_content_info(self, Object, _Inf_):
        """添加目录信息"""
        format_data = [['CATALOGUE']]  # 用于存储目录信息
        for row in range(50):
            if row < len(_Inf_):
                format_data.append(['%s-%s' % (_Inf_[row]['beg'], _Inf_[row]['end']),  # 每页起始-结束的循环段编号
                                    '', '%7.1f' % float(_Inf_[row]['stake']),  # 每页起始桩号
                                    '.' * 150, 'Page %d' % _Inf_[row]['page']])  # 每页页码
            else:
                format_data.append(['', '', '', '', ''])  # 不足50页时相关记录用空值代替
        Cell_w = [16 * mm, 3 * mm, 10 * mm, 95 * mm, 12 * mm]  # 表格列宽信息
        sheet = Table(format_data, colWidths=Cell_w, rowHeights=5.1 * mm, style={
            ("FONT", (0, 0), (-1, 0), self.type_font, self.size_font + 5),  # 目录标题字体
            ("FONT", (0, 1), (-1, -1), self.type_font, self.size_font),  # 目录正文字体
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),  # 字体颜色
            ('SPAN', (0, 0), (-1, 0)),  # 合并单元格
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')})  # 左右上下居中
        sheet._argH[0] = 8 * mm  # 调整目录名称行高
        sheet.wrapOn(Object, 0, 0)  # 将sheet添加到Canvas中
        sheet.drawOn(Object, 36 * mm, 25 * mm)  # 将sheet添加到Canvas中

    def add_pic_info(self, Object, _Pic_):
        """添加图片信息"""
        pic_x, pic_y = [21 * mm, 106 * mm], [193 * mm, 109 * mm, 25 * mm]  # 图片位置信息
        for row in range(3):
            for col in range(2):
                Image = _Pic_[2 * row + col]  # 读取图片
                if Image:  # 若路径有效，则添加图片
                    if Image[-3:] == 'svg':
                        drawing = svg2rlg(Image)
                        drawing.scale(0.275, 0.265)  # 缩放
                        renderPDF.draw(drawing, Object, x=pic_x[col], y=pic_y[row])  # 位置
                    if Image[-3:] == 'png':
                        Object.drawImage(image=Image, x=pic_x[col], y=pic_y[row], width=83 * mm, height=66 * mm,
                                         anchor='c')
        return self

    def cre_pdf(self, _par_name_=None):
        """读取数据，并将数据转化为可识别的类型"""
        self.parm = _par_name_  # 保存相关参数和输出路径
        self.check_parm()  # 检查参数是否正常
        self.create_report_Dir()  # 创建文件夹
        text_path = os.path.join(self.out_path, 'text.pdf')
        content_path = os.path.join(self.out_path, 'content.pdf')
        pdf_text = Canvas(filename=text_path, bottomup=1, pageCompression=1, encrypt=None)  # 创建pdf
        pdf_content = Canvas(filename=content_path, bottomup=1, pageCompression=1, encrypt=None)  # 创建pdf
        file_list = os.listdir(self.input_path)  # 获取循环段列表
        key_val, pic_val, key_content = [], [], []  # 定义关键参数(key_value)、图片参数(pic_value)列表
        for cycle, file_name in zip([i + 1 for i in range(len(file_list))], file_list):
            Data_cycle = pd.read_csv(os.path.join(self.input_path, file_name), encoding='gb2312')  # 读取文件
            Data_cycle_np = Data_cycle.loc[:, self.parm].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
            key_val.append([['Number', ('%00005d' % cycle),  # 获取循环段编号(Num)
                             'Start No', '%sm' % round(Data_cycle_np[0][0], 1),  # 获取桩号记录
                             'Start Time', Data_cycle_np[0][1]],  # 获取循环段开始时间
                            ['Rock mass', '',  # 获取围岩等级(Rock_Mass)
                             'Length', '%4.2fm' % round((Data_cycle_np[-1][2] - Data_cycle_np[0][2]) / 1000, 2),  # 掘进长度
                             'End Time', Data_cycle_np[-1][1]]])  # 获取结束时间
            pic_val.append(os.path.join(self.input_pic, file_name[:-3] + 'png'))  # 添加图片参数(pic_value)数值
            if (not cycle % 6) or (cycle == len(file_list)):  # 以6个为一组,剩余不足6个也输出
                start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                key_content.append({'beg': key_val[0][0][1], 'end': key_val[-1][0][1],
                                    'stake': key_val[0][0][3][:-1], 'page': self.page})
                if cycle == len(file_list):  # 若生成的pdf最后一页信息填充不全，可用空值进行替代
                    for fill in range(6 - len(key_val)):
                        key_val.append([['Number', '', 'Start No', '', 'Start Time', ''],
                                        ['Rock mass', '', 'Length', '', 'End Time', '']])
                        pic_val.append(None)
                self.add_text_info(pdf_text, key_val)  # 绘制表格
                self.add_pic_info(pdf_text, pic_val)  # 添加图片
                self.add_footer_info(pdf_text)  # 绘制页脚
                if cycle != len(file_list):
                    pdf_text.showPage()  # 新增一页
                if (self.page % 50 == 0) or (cycle == len(file_list)):
                    self.add_content_info(pdf_content, key_content)
                    if cycle != len(file_list):
                        pdf_content.showPage()  # 新增一页
                    key_content.clear()
                key_val.clear(), pic_val.clear()  # 对变量进行初始化， 便于进行下一次操作
                end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                visual('Create PDF', cycle=self.page-1, Sum=int(len(file_list)/6)+1, start=start, end=end, Clear=False)
        pdf_text.save(), pdf_content.save()  # pdf保存
        self.MergePDF(content=content_path, text=text_path)  # 合并目录和正文
        visual('Create PDF', cycle=-1, Clear=True)

    def MergePDF(self, **kwargs):
        """合并目录和正文成为一个PDF"""
        output = PdfFileWriter()
        outputPages = 0  # 最终pdf页数
        _Pdf_ = [open(kwargs['content'], "rb"), open(kwargs['text'], "rb")]
        for file in _Pdf_:
            Input = PdfFileReader(file)  # 读取源PDF文件
            pageCount = Input.getNumPages()
            outputPages += pageCount  # 获得源PDF文件中页面总数
            for iPage in range(pageCount):
                output.addPage(Input.getPage(iPage))  # 分别将page添加到输出output中
        outputStream = open(os.path.join(self.out_path, 'TBM-Data.pdf'), "wb")
        output.write(outputStream)  # 写入到目标PDF文件
        outputStream.close(), _Pdf_[0].close(), _Pdf_[1].close()  # 关闭读取的文件
        os.remove(kwargs['content']), os.remove(kwargs['text'])


class TBM_PLOT(object):
    """
    TBM_PLOT(_input_path_, _out_path_, _debug_)为参数绘图配置模块，该模块需要传入的参数包括
    必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）}
    data_plot(_par_name_, _Format_)为参数绘图主模块，该模块需要传入的参数包括
    必要参数：{程序运行所需要的关键参数名称（_par_name_）}，可选参数：{生成图片的格式（_Format_），位图（png）/矢量图（svg）}
    version()为展示程序版本及修改记录模块，该模块无需传入相关参数
    """
    PARAMETERS = ['刀盘转速', '刀盘给定转速', '推进速度(nn/M)', '推进给定速度', '刀盘扭矩', '总推力']

    def __init__(self, _input_path_=None, _out_path_=None):
        self.input_path = _input_path_  # 初始化输入路径
        self.out_path = _out_path_  # 初始化输出路径
        self.parm = self.PARAMETERS  # 掘进状态判定参数
        self.size = (10, 8)
        self.dpi = 120
        self.format = 'png'

    def create_pic_dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out_path):
            os.mkdir(self.out_path)  # 创建文件夹
        else:
            shutil.rmtree(self.out_path)  # 清空文件夹
            os.mkdir(self.out_path)  # 创建文件夹

    def check_parm(self):
        """检查传入参数是否正常"""
        current_class = self.__class__.__name__
        if (not self.input_path) or (not self.out_path):  # 检查输入输出路径是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if (not self.parm) or (len(self.parm) != len(self.PARAMETERS)):  # 检查传入参数是否正常
            print(' ->-> %s' % current_class, '\033[0;31mThe input parameters are faulty, Please check!!!\033[0m')
            print(' ->-> %s' % current_class, '\033[0;31mSuch as %s\033[0m' % self.parm)
            sys.exit()  # 抛出异常并终止程序

    def version(self):
        """展示文件版本信息及修改记录"""
        try:
            __history__()
        except NameError:
            return self

    def parm_plot(self, _data_, _name_, _key_):
        """完成掘进参数的绘图与保存"""
        x = [i for i in range(_data_.shape[0])]  # 'Time'
        y_n = _data_.loc[:, self.parm[0]]  # '刀盘转速'
        y_n_set = _data_.loc[:, self.parm[1]]  # '刀盘转速设定'
        y_V = _data_.loc[:, self.parm[2]]  # '推进速度'
        y_V_set = _data_.loc[:, self.parm[3]]  # '推进速度设定'
        y_T = _data_.loc[:, self.parm[4]]  # '刀盘总扭矩'
        y_F = _data_.loc[:, self.parm[5]]  # '推进总推力'
        plt.figure(figsize=self.size, dpi=self.dpi)  # 设置画布大小（10cm x 8cm）及分辨率（dpi=120）
        plt.scatter(x, y_n, label="n", color='mediumblue', marker='+')
        plt.scatter(x, y_n_set, label="n_set", color='k', marker='_')
        plt.scatter(x, y_V / 10, label="V/10", color='y', marker='.', s=100)
        plt.scatter(x, y_V_set / 10, label="V_set/10", color='saddlebrown', marker='.', s=50)
        plt.legend(bbox_to_anchor=(0.36, 1.1), loc=9, borderaxespad=-1, ncol=2, columnspacing=2, frameon=False,
                   fontsize=18, markerscale=1.5)
        plt.ylabel("刀盘转速、推进速度及其设定值", fontsize=20, labelpad=10)
        plt.xlabel("时间/s", fontsize=20)
        plt.twinx()
        plt.scatter(x, y_T, label="T", color='deeppink', marker='^', s=30)
        plt.scatter(x, y_F / 2, label="F/2", color='c', marker='v', s=30)
        plt.legend(bbox_to_anchor=(0.77, 1.1), loc=9, borderaxespad=-1.1, ncol=1, columnspacing=2, frameon=False,
                   fontsize=18, markerscale=1.5)
        plt.ylabel("刀盘推力、刀盘扭矩", fontsize=20, labelpad=10)
        if _key_:
            plt.axvline(x=_key_['rise'] - 1, c="r", ls="-.")
            plt.axvline(x=_key_['steadyS'] - 1, c="r", ls="-.")
            plt.axvline(x=_key_['steadyE'] - 1, c="r", ls="-.")
        pic_path = os.path.join(self.out_path, _name_[:-3] + self.format)
        plt.savefig(pic_path, dpi=self.dpi, format=self.format, bbox_inches='tight')
        plt.close()

    def data_plot(self, _par_name_=None, _Format_='png'):
        """掘进参数可视化"""
        self.parm, self.format = _par_name_, _Format_  # 将掘进参数和时间间隔赋值
        self.check_parm()  # 检查参数是否正常
        self.create_pic_dir()  # 创建文件夹
        try:
            Index_Path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Index-File.csv')  # 索引文件存放根目录
            data_Index = pd.read_csv(Index_Path, encoding='gb2312')  # 读取文件
            try:
                Index_value = data_Index.loc[:, ['循环段', '上升段起点', '稳定段起点', '稳定段终点']].values
            except KeyError:
                Index_value = []
        except FileNotFoundError:
            Index_value = []
        file_list = os.listdir(self.input_path)  # 获取输入文件夹下的所有文件名，并将其保存
        for index, file_name in enumerate(file_list):  # 遍历每个文件
            start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            file_num = int(file_name[:5])
            _data_ = pd.read_csv(os.path.join(self.input_path, file_name), encoding='gb2312')  # 读取文件
            if len(Index_value):
                mark = {'cycle': Index_value[file_num - 1][0], 'rise': Index_value[file_num - 1][1],
                        'steadyS': Index_value[file_num - 1][2], 'steadyE': Index_value[file_num - 1][3]}
            else:
                mark = {}
            self.parm_plot(_data_, file_name, mark)
            end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            visual('Drawing pic', cycle=index, Sum=len(file_list), start=start, end=end, Clear=False)
        visual('Drawing pic', cycle=-1, Clear=True)


class DEBUG(object):
    PARAMETERS = ['日期', '导向盾首里程', '刀盘转速', '推进速度(nn/M)', '刀盘扭矩',
                  '总推力', '刀盘给定转速', '推进给定速度', '推进位移', '刀盘贯入度']

    def __init__(self, debug=False):
        self.debug = debug
        self.parm = self.PARAMETERS
        self.file_name = ''

    def debug_start(self, _inf_):
        """第一次打印输出"""
        if self.debug:
            print('=' * 40, 'Debug', '=' * 40)
            print('\033[0;33m     ->-> %s <-<-\033[0m' % _inf_)
            self.file_name = _inf_

    def debug_print(self, _inf_):
        """语句打印输出"""
        if self.debug:
            for information in _inf_:
                print('\033[0;33m     %s\033[0m' % information, end='')
            print('')

    def debug_finish(self, _inf_):
        """最后一次打印输出"""
        if self.debug:
            print('\033[0;33m     ->-> %s <-<-\033[0m' % _inf_)
            print('=' * 40, 'Debug', '=' * 40)

    def debug_draw_N(self, _data_df_):
        """刀盘转速绘图"""
        if self.debug:
            x = [i for i in range(_data_df_.shape[0])]  # 'Time'
            y_n = _data_df_.loc[:, self.parm[2]]  # '刀盘转速'
            plt.figure(figsize=(14, 7), dpi=120)  # 设置画布大小（10cm x 8cm）及分辨率（dpi=120）
            plt.plot(x, y_n, label="n", color='b')
            plt.ylabel("刀盘转速、推进速度及其设定值", fontsize=15, labelpad=10)
            plt.xlabel("时间/s", fontsize=15)
            plt.show()
            plt.close()
            self.debug_finish(self.file_name)

    def debug_draw_V(self, _data_df_):
        """推进速度绘图"""
        if self.debug:
            x = [i for i in range(_data_df_.shape[0])]  # 'Time'
            y_n = _data_df_.loc[:, self.parm[3]]  # '推进速度'
            plt.figure(figsize=(14, 7), dpi=120)  # 设置画布大小（10cm x 8cm）及分辨率（dpi=120）
            plt.plot(x, y_n, label="n", color='b')
            plt.ylabel("刀盘转速、推进速度及其设定值", fontsize=15, labelpad=10)
            plt.xlabel("时间/s", fontsize=15)
            plt.show()
            plt.close()
            self.debug_finish(self.file_name)


def __history__():
    """展示文件版本信息和修改记录"""
    print('\r', '\n', end='')
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(__file__))
    with open(file_path, 'r', encoding="utf-8") as F:
        lines = F.readlines()
    for i in range(2, 11):
        print('\r', '\033[0;32m%s\033[0m' % lines[i], end='')
    print('\n', '\033[0;32m%s\033[0m' % HISTORY, '\n')  # 打印文件修改记录


def visual(Print, Debug=None, **kwargs):
    """可视化输出"""
    if Debug:
        return None
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
