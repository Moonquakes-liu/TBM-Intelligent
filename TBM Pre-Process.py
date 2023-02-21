#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ************************************************************************
# * Software:  TBM Pre-Process  for  Python                              *
# * Version:  1.0.3                                                      *
# * Date:  2023-02-20 00:00:00                                           *
# * Last  update: 2023-02-06 00:00:00                                    *
# * License:  LGPL v1.0                                                  *
# * Maintain  address:  https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A  *
# * Maintain  code:  STBM                                                *
# ************************************************************************

import configparser
import math
import copy
import datetime
import time
import tarfile
import tkinter
from tkinter.filedialog import *
import warnings
import os
import sys
import shutil
import requests
import zipfile
import tempfile
import numpy as np
import pandas as pd
import statsmodels.nonparametric.api as SMNP
import psutil
import scipy
from functools import reduce
from tkinter import messagebox
from tkinter import *
from tkinter.ttk import *
from PyPDF2 import PdfFileReader, PdfFileMerger
from numpy import ndarray, std
from pandas import Series, DataFrame
from scipy import fft
from scipy import signal
from scipy.fftpack import fft
from io import BytesIO
import webbrowser as web
from matplotlib import pyplot as plt, pyplot
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table
from reportlab.lib.utils import ImageReader


class TBM_CYCLE(object):
    """
    循环段分割模块，完成从原始数据中提取有效循环段的功能
    必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行；
            生成数据保存路径（out_path），若不传入输出路径，程序则抛出异常并终止运行；
            索引文件保存路径（index_path），若不传入输出路径，程序则抛出异常并终止运行；
            关键参数名称（par_name），若不传入参数，程序则抛出异常并终止运行；
    可选参数：循环段划分方法（division），刀盘转速'Rotate Speed'/推进速度'Advance Speed'；
            相邻循环段时间间隔（s）（interval_time），默认100s；
            推进速度下限值（mm/min）（V_min），默认1mm/min；
            掘进长度下限值（mm）（L_min），默认10mm；
            程序调试/修复选项（debug），默认为关闭状态；
            直接运行程序（Run）， 默认为开启状态；
    """
    PARAMETERS = ['桩号', '日期', '推进位移', '刀盘转速', '推进速度', '刀盘扭矩',
                  '总推力', '刀盘贯入度', '刀盘转速设定值', '推进速度设定值']  # 循环段分割模块中的参数名称和顺序示例
    INDEX_NAME = ['循环段', '桩号', '日期', '掘进时间']  # 生成索引文件中标签信息
    NEW_INDEX = pd.DataFrame(columns=INDEX_NAME)  # 保存新的索引数据

    def __init__(self, input_path=None, out_path=None, index_path=None, parameter=None,
                 division='Rotate Speed', interval_time=100, V_min=1, L_min=10, debug=False, Run=True):
        """初始化必要参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.index = index_path  # 初始化索引文件路径
        self.parm = parameter  # 掘进状态判定参数
        """初始化可选参量"""
        self.division = division  # 循环段划分依据
        self.L_min = L_min  # 掘进长度下限值
        self.V_min = V_min  # 推进速度下限值
        self.MTI = interval_time  # 初始化两个相邻掘进段的最小时间间隔为0（minimum time interval）
        self.debug = debug  # 调试/修复程序
        """初始化程序内部参量"""
        self.D_last = 0  # 初始化上一时刻的掘进状态
        self.Number = 1  # 初始化循环段编号
        self.debug_number = 1  # 初始化Debug模式下循环段编号
        self.Time_val = []  # 初始化程序运行花费时间
        self.debug_divide = []  # 初始化Debug模式下划分信息
        self.show_parm = True  # 将输入参数打印出来，便于进行核对
        self.add_temp = pd.DataFrame(None)  # 初始化dataframe类型数组，便于对连续部分数据进行存储
        None if not Run else self.main()  # 运行主程序

    def create_cycle_dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):
            os.mkdir(self.out)  # 创建相关文件夹
        else:
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数（输入路径/输入路径/索引路径/参数名称）是否正确，若正确则运行程序，如果不正确则终止程序"""
        Class = self.__class__.__name__  # 获取当前模块名称
        if (not self.input) or (not self.out) or (not self.index) or \
                (not self.parm) or (len(self.parm) < len(self.PARAMETERS)):  # 检查必要参数
            print('-> %s \033[0;31mThe input/output/index path or parameter are faulty, Please check!!!\033[0m' % Class)
            sys.exit()  # 抛出异常并终止程序

    def check_index(self, all_location: list) -> None:
        """
        判断数据中是否存在重复列名，若存在重复列名，则需要输入位置索引
        :param all_location: 原始数据的所有标签名称
        :return: 无
        """
        if reduce(lambda x, y: x * y, [type(name) == str for name in self.parm]):  # 判断是否为标签类型索引(名称)
            all_location = [name.split('.')[0] for name in all_location]  # 获取原始数据的标签名称
            mark = max([all_location.count(now_name) for now_name in self.parm])  # 检查标签名称中是否重复
            if mark == 1:  # 标签名称不重复
                self.parm = [all_location.index(now_name) for now_name in self.parm]
            else:
                maybe = [all_location.index(now_name) for now_name in self.parm]  # 可能的参数位置索引
                print('-> \033[0;31mLabel index(loc) is not available, Please enter location index(iloc)!!!\033[0m')
                print('   \033[0;31mLocation index(iloc) may be %s, You can verify that.\033[0m' % maybe)
                sys.exit()
        if self.show_parm:  # 将输入参数打印出来，便于进行核对
            self.show_parm = False
            Class = self.__class__.__name__  # 获取当前模块名称
            print('-> %s \033[0;33m参数名称: %s \033[0m' % (Class, [all_location[i] for i in self.parm]))

    def write_index(self, info: dict) -> None:  # 规定_Num_为整型(int)，info为列表(list)，返回值返回值无类型限定
        """
        向索引文件写入数据
        :param info: 待写入的信息，其中至少含有{‘name’：‘’}，name为循环段名称
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        if self.NEW_INDEX.empty:  # 若新的索引数据为空
            if os.path.isfile(self.index):  # 判断索引文件是否存在
                os.remove(self.index)  # 若索引文件存在，则删除
        Num = int(info['name'][:5])  # 获取当前循环段编号
        self.NEW_INDEX.loc[Num] = [Num] + [info[name] for name in self.INDEX_NAME[1:]]  # 新的索引记录
        self.NEW_INDEX.to_csv(self.index, index=False, encoding='gb2312')  # 保存新的索引记录

    def tunnel_determine(self, data_np: Series) -> [bool, str]:  # 规定data_np为Numpy类型数组(Series)，返回值类型为[布尔值，字符型]
        """
        对掘进状态的实时判定，结合历史数据返回掘进段开始和结束位置
        :param data_np: 当前时刻的原始数据（Numpy类型）
        :return: Tunnel是否掘进（True/False）, key掘进段开始或结束标志（Start/Finish/None）
        """
        Fx = np.int64(data_np[0:1] > 0.1)  # 判定函数 F(x) = 1(x>0), 0(x<=0)
        if self.division == 'Advance Speed':  # 获取划分方法（推进速度/刀盘转速）
            Fx = np.int64(data_np[1:2] > 0.1)  # 判定函数 F(x) = 1(x>0), 0(x<=0)
        D_now = reduce(lambda x, y: x * y, Fx)  # D(x) = F(x1)·F(x2)...F(Xn)        lambda为自定义函数
        Tunnel = False if D_now == 0 else True  # 掘进状态 D(x) = 0(downtime), 1(Tunnel)
        # 当前时刻D(x) - 上一时刻D(x‘) = Start(>0), Finish(<0), None(=0)
        key = 'None' if D_now - self.D_last == 0 else 'Start' if D_now - self.D_last > 0 else 'Finish'
        self.D_last = D_now  # 保存上一时刻状态
        return Tunnel, key  # 掘进状态判定结果Tunnel（True/False）和掘进段开始或结束标志key（Start/Finish/None）

    def cycle_splice(self, data: DataFrame) -> DataFrame:  # 规定data为DataFrame类型数组(DataFrame)，返回数组类型为DataFrame
        """
        对原始数据中相邻两天存在连续性的数据进行拼接
        :param data: 每天的原始数据（DataFrame）
        :return: 拼接后的数据（DataFrame）
        """
        state = []  # 定义一个空列表，用于存储每一时刻掘进状态（处于掘进状态：True，处于停机状态：False ）
        mark = 0  # 循环段结束位置索引
        data_np = data.iloc[:, self.parm[3:5]].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
        for col in list(data.index.values)[::-1]:  # 从后往前，对每一时刻的掘进状态进行判定
            state.append(self.tunnel_determine(data_np[int(col), :])[0])  # 将该时刻的掘进状态存储至state中
            if (len(state) > self.MTI) and (not any(state[-self.MTI:-1])):
                mark = col  # 循环段结束位置索引
                break  # 判定两个相邻掘进段的时间间隔内（self.MTI）盾构是否处于掘进状态，若未处于掘进状态，则返回该时刻的行索引值
        data_out = pd.concat([self.add_temp, data.iloc[:mark + 1, :]], ignore_index=True)  # 将两天连续部分数据进行拼接，形成一个数据集
        self.add_temp = data.iloc[mark + 1:, :]  # 将当天与后一天连续部分的数据进行单独保存，便于和后一天的数据进行拼接
        return data_out  # 返回拼接后的新数据集

    def cycle_extract(self, name: str, data: DataFrame) -> None:  # 规定data为DataFrame类型数组(DataFrame)，返回值无类型限定
        """
        对原始数据中的掘进段进行实时提取
        :param name: 循环段名称
        :param data: 每天的原始数据（DataFrame）
        :return: 无
        """
        key = {'now-S': 0, 'now-F': 0, 'last-S': 0, 'last-F': 0}  # 当前掘进段开始与结束的行索引,上一个掘进段开始与结束的行索引
        data_np = data.iloc[:, self.parm[2:5]].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
        for index, item in enumerate(data_np):  # 从前往后，对每一时刻的掘进状态进行判定（index为行索引， item为每行数据）
            _, result = self.tunnel_determine(item[1:])  # 调用掘进状态判定函数并返回掘进段开始或结束标志
            if result == 'Start':
                key['now-S'] = index  # 保存掘进段开始时的行索引
            if result == 'Finish':
                key['now-F'] = index  # 保存掘进段结束时的行索引
            if (key['now-F'] > key['now-S']) or (index == len(data_np) - 1):  # 获取到掘进段开始和结束索引是否完整
                Length = data_np[key['now-F'], 0] - data_np[key['now-S'], 0]  # 掘进长度最小值大于规定值
                if (index == len(data_np) - 1) or Length > self.L_min \
                        and max(data_np[key['now-S']:key['now-F'], 2]) > self.V_min:
                    if key['last-S'] == 0 and key['last-F'] == 0:  # 获取到下一个完整掘进段的开始和结束的行索引后才对上一个循环段进行保存，因此要对第一个掘进段进行特殊处理
                        key['last-S'], key['last-F'] = key['now-S'], key['now-F']  # 首个掘进段开始和结束的行索引进行赋值
                    if (key['now-S'] - key['last-F'] > self.MTI) or (index == len(data_np) - 1):  # 判断两个掘进段时间间隔是否满足要求
                        if key['last-S'] < key['last-F']:
                            self.cycle_save(data, Start=key['last-S'], Finish=key['last-F'])  # 两掘进段间隔满足要求，对上一掘进段进行保存
                            self.detail(name=name, key=['Start:', key['last-S'],
                                                        'Finish:', key['last-F']], debug=self.debug)  # DEBUG
                    else:
                        key['now-S'] = key['last-S']  # 两个掘进段时间间隔不满足要求，需要将上一掘进段和当前掘进段进行合并
                    key['last-S'], key['last-F'] = key['now-S'], key['now-F']  # 将当前掘进段的开始和结束的行索引信息进行保存
                key['now-S'], key['now-F'] = 0, 0  # 清空当前的索引记录

    @staticmethod  # 不强制要求传递参数
    def default_read(file_path: str) -> DataFrame:  # 规定file_path为字符型数据，返回值为（DataFrame）类型数组
        """
        调用默认文件读取模块（仅可读取csv数据类型）
        :param file_path: 文件路径
        :return: 读取的数据集（DataFrame）
        """
        try:  # 首先尝试使用'gb2312'编码进行csv文件读取
            data = pd.read_csv(file_path, encoding='gb2312')  # 读取文件
        except UnicodeDecodeError:  # 若默认方式读取csv文件失败，则更换为' utf-8 '编码后重新进行尝试
            data = pd.read_csv(file_path, encoding='utf-8')  # 读取文件
        data.drop(data.tail(1).index, inplace=True)  # 删除文件最后一行
        data = data.iloc[:, ~data.columns.str.contains('Unnamed')]  # 删除Unnamed空列
        data.fillna(0, inplace=True)  # 将NAN值替换为0
        return data

    def custom_read(self, file_path: str) -> DataFrame:  # 规定file_path为字符型数据，返回值为（DataFrame）类型数组
        """自定义文件读取模块，若定义了相关功能，则优先运行此功能，若未定义相关功能，则运行默认文件读取模块"""
        pass

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """原始数据的读取"""
        self.check_parm()  # 检查参数是否正常
        self.create_cycle_dir()  # 创建相关文件夹
        all_file = os.listdir(self.input)  # 获取输入文件夹下的所有文件名，并将其保存
        all_file.sort(key=lambda x: x)  # 对读取的文件列表进行重新排序
        for num, file in enumerate(all_file):  # 遍历每个文件
            time_S = time.time()  # 记录程序执行开始时间
            local_path = os.path.join(self.input, file)  # 当前文件路径
            data_raw = self.custom_read(local_path)  # 自定义文件读取模块
            if data_raw is None:
                data_raw = self.default_read(local_path)  # 默认文件读取模块
            self.check_index(list(data_raw))  # 检查参数是否重复
            after_process = self.cycle_splice(data_raw)  # 调用函数对相邻两天数据存在连续性的情况进行处理
            self.cycle_extract(name=file, data=after_process)  # 调用cycle_extract函数对原始数据中的循环段进行提取
            self.detail(name=file, data=after_process, Parm=[self.parm[3]], draw=True, debug=self.debug)  # DEBUG输出
            time_F = time.time()  # 记录程序执行结束时间
            self.show_info(use_time=time_F - time_S, file_num=num, file_sum=len(all_file))

    def cycle_save(self, data: DataFrame, Start: int, Finish: int) -> None:  # 规定data为(DataFrame)类型数组，返回值无类型限定
        """
        对已经划分出的循环段数据进行保存
        :param data: 每天的原始数据（DataFrame）
        :param Start: 每个循环段数据开始位置索引
        :param Finish: 每个循环段数据结束位置索引
        :return: 无
        """
        cycle_data = data.iloc[Start:Finish, :]  # 提取掘进段数据
        cycle_data = cycle_data.reset_index(drop=True)  # 重建提取数据的行索引
        Mark = round(cycle_data.iloc[0, self.parm[0]], 2)  # 获取每个掘进段的起始桩号
        Time = cycle_data.iloc[0, self.parm[1]]  # 获取每个掘进段的时间记录
        Time = pd.to_datetime(Time, format='%Y-%m-%d %H:%M:%S')  # 对时间类型记录进行转换
        year, mon, d, h, m, s = Time.year, Time.month, Time.day, Time.hour, Time.minute, Time.second  # 获取时间记录的时分秒等
        csv_name = (self.Number, Mark, int(year), int(mon), int(d), int(h), int(m), int(s))  # 文件名
        csv_path = os.path.join(self.out, '%00005d %.2f %04d年%02d月%02d日 %02d时%02d分%02d秒.csv' % csv_name)  # 循环段保存路径
        cycle_data.to_csv(csv_path, index=False, encoding='gb2312')  # 循环段保存为csv文件
        self.write_index({'name': '%5d' % self.Number, '桩号': Mark, '日期': Time, '掘进时间': (Finish - Start)})  # 索引文件记录
        self.Number += 1  # 循环段编号自增

    def show_info(self, use_time: float, file_num: int, file_sum: int) -> None:
        """
        实时输出程序运行状况
        :param use_time: 处理每个循环段数据花费的时间
        :param file_num: 当前的循环段编号
        :param file_sum: 总的循环段数量
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        cpu_percent = psutil.cpu_percent()  # CPU占用
        mem_percent = psutil.Process(os.getpid()).memory_percent()  # 内存占用
        self.Time_val.append(use_time)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(self.Time_val) / len(self.Time_val)  # 计算平均时间
        sum_time = round(sum(self.Time_val) / 3600, 3)  # 计算程序执行的总时间
        remain_time = round((mean_time * (file_sum - file_num - 1)) / 3600, 3)  # 预计剩余时间计算
        print('\r   [第%d个 / 共%d个]  ' % (file_num + 1, file_sum),
              '[所用时间%ds / 平均时间%ds]  ' % (int(use_time), int(mean_time)),
              '[CPU占用: %5.2f%% / 内存占用: %5.2f%%]  ' % (cpu_percent, mem_percent),
              '[累积运行时间: %6.3f小时 / 预计剩余时间: %6.3f小时]' % (sum_time, remain_time), end='')  # 打印输出
        if file_num + 1 >= file_sum:
            Class = self.__class__.__name__  # 获取当前模块名称
            print('\r-> %s \033[0;32mBoring-cycle extract completed, which took %6.3f hours\033[0m' % (Class, sum_time))

    def detail(self, name=None, data=None, key=None, Parm=None, draw=False, debug=False):
        """展示程序细节信息"""
        if debug:
            if draw:
                x = [i for i in range(data.shape[0])]  # 'Time'
                plt.figure(figsize=(14, 7), dpi=120)  # 设置画布大小（10cm x 8cm）及分辨率（dpi=120）
                for parm, color in zip(Parm, ['b', 'g', 'r', 'y']):
                    plt.plot(x, data.iloc[:, parm], label="%s" % list(data)[parm], color=color)
                plt.legend()
                plt.xlabel("时间/s", fontsize=15)
                for color, information in zip(['g', 'r', 'y', 'b'], Divide):
                    for index in information:
                        plt.axvline(x=index, c=color, ls="-.")
                plt.show()
                plt.close()
                print("\033[0;33m{:·^100}\033[0m".format(name))
                self.debug_number, self.debug_divide = 0, []
            else:
                if not self.debug_divide:
                    self.debug_divide = [[] for _ in range(len(key) + 2)]
                    print("\033[0;33m{:·^100}\033[0m".format(name))
                for num, information in enumerate([' Cycle:', '  %s' % Number] + Key):
                    if isinstance(information, int) and information is not None:
                        Divide[int(num / 2)].append(information)
                    print('\033[0;33m%9s\033[0m' % str(information), end='')
                print('')
            self.debug_number += 1


class TBM_EXTRACT(object):
    """
    破岩关键数据提取配置模块，主要完成从原始数据中提取破岩关键数据的功能
    ****必选参数：破岩关键参数名称（par_name），若不传入相关参数，程序则抛出异常并终止运行
                原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                索引文件保存路径（index_path），若不传入输出路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输出路径，程序则抛出异常并终止运行
    ****可选参数：程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run）， 默认为开启状态
    """
    PARAMETERS = ['None']  # 破岩关键数据提取中的参数名称和顺序示例

    def __init__(self, input_path=None, out_path=None, index_path=None, key_parm=None, debug=False, Run=True):
        """初始化必要参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.index = index_path  # 初始化索引文件路径
        self.parm = key_parm  # 破岩关键参数
        """初始化可选参量"""
        self.debug = debug  # 调试/修复程序
        """初始化程序内部参量"""
        self.Time_val = []  # 初始化程序运行花费时间
        self.debug_number = 1  # Debug模式下循环段编号
        self.show_parm = True  # 将输入参数大音出来，便于进行核对
        None if not Run else self.main()  # 运行主程序

    def create_extract_dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):
            os.mkdir(self.out)  # 创建相关文件夹
        else:
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        Class = self.__class__.__name__  # 获取当前模块名称
        if (not self.input) or (not self.out) or (not self.parm):  # 检查必要参数
            print('-> %s \033[0;31mThe input/output/index path or parameter are faulty, Please check!!!\033[0m' % Class)
            sys.exit()  # 抛出异常并终止程序

    def check_index(self, all_location: list) -> None:
        """
        判断数据中是否存在重复列名，若存在重复列名，则需要输入位置索引
        :param all_location: 原始数据的所有标签名称
        :return: 无
        """
        if reduce(lambda x, y: x * y, [type(name) == str for name in self.parm]):  # 判断是否为标签类型索引(名称)
            all_location = [name.split('.')[0] for name in all_location]  # 获取原始数据的标签名称
            mark = max([all_location.count(now_name) for now_name in self.parm])  # 检查标签名称中是否重复
            if mark == 1:  # 标签名称不重复
                self.parm = [all_location.index(now_name) for now_name in self.parm]
            else:
                maybe = [all_location.index(now_name) for now_name in self.parm]  # 可能的参数位置索引
                print('-> \033[0;31mLabel index(loc) is not available, Please enter location index(iloc)!!!\033[0m')
                print('   \033[0;31mLocation index(iloc) may be %s, You can verify that.\033[0m' % maybe)
                sys.exit()
        if self.show_parm:  # 将输入参数打印出来，便于进行核对
            self.show_parm = False
            Class = self.__class__.__name__  # 获取当前模块名称
            print('-> %s \033[0;33m参数名称: %s \033[0m' % (Class, [all_location[i] for i in self.parm]))

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """关键破岩数据提取"""
        self.check_parm()  # 检查参数是否正常
        self.create_extract_dir()  # 创建相关文件夹
        all_file = os.listdir(self.input)  # 获取输入文件夹下的所有文件名，并将其保存
        all_file.sort(key=lambda x: int(x[:5]))  # 对读取的文件列表进行重新排序
        for num, file in enumerate(all_file):  # 遍历每个文件
            time_S = time.time()  # 记录程序执行开始时间
            local_csv_path = os.path.join(self.input, file)  # 当前文件路径
            try:
                data = pd.read_csv(local_csv_path, encoding='gb2312')
            except UnicodeDecodeError:  # 若使用'gb2312'编码读取csv文件失败，则使用 'utf-8'编码后重新进行尝试
                data = pd.read_csv(local_csv_path, encoding='utf-8')
            self.check_index(list(data))  # 检查参数是否重复
            self.detail(name='Key Extract', key=['   %s:    %d\n' % (list(data)[name], name) for name in self.parm],
                        debug=self.debug)  # DEBUG输出
            data.iloc[:, self.parm].to_csv(os.path.join(self.out, file), index=False, encoding='gb2312')  # 保存csv文件
            time_F = time.time()  # 记录程序执行结束时间
            self.show_info(use_time=time_F - time_S, file_num=num, file_sum=len(all_file))

    def show_info(self, use_time: float, file_num: int, file_sum: int) -> None:
        """
        实时输出程序运行状况
        :param use_time: 处理每个循环段数据花费的时间
        :param file_num: 当前的循环段编号
        :param file_sum: 总的循环段数量
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        cpu_percent = psutil.cpu_percent()  # CPU占用
        mem_percent = psutil.Process(os.getpid()).memory_percent()  # 内存占用
        self.Time_val.append(use_time)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(self.Time_val) / len(self.Time_val)  # 计算平均时间
        sum_time = round(sum(self.Time_val) / 3600, 3)  # 计算程序执行的总时间
        remain_time = round((mean_time * (file_sum - file_num - 1)) / 3600, 3)  # 预计剩余时间计算
        print('\r   [第%d个 / 共%d个]  ' % (file_num + 1, file_sum),
              '[所用时间%ds / 平均时间%ds]  ' % (int(use_time), int(mean_time)),
              '[CPU占用: %5.2f%% / 内存占用: %5.2f%%]  ' % (cpu_percent, mem_percent),
              '[累积运行时间: %6.3f小时 / 预计剩余时间: %6.3f小时]' % (sum_time, remain_time), end='')
        if file_num + 1 >= file_sum:
            Class = self.__class__.__name__  # 获取当前模块名称
            print('\r-> %s \033[0;32mKey-Data extract completed, which took %6.3f hours\033[0m' % (Class, sum_time))

    def detail(self, name=None, key=None, debug=False):
        """展示程序细节信息"""
        if debug:
            if self.debug_number == 1:
                print("\033[0;33m{:·^100}\033[0m".format(name))
                for num, information in enumerate(key):
                    print('\033[0;33m%9s\033[0m' % information, end='')
                print("\033[0;33m{:·^100}\033[0m".format(name))
            self.debug_number += 1


class TBM_CLASS(object):
    """
    异常分类配置模块，主要完成异常循环段识别和分类的工作
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行;
                生成数据保存路径（out_path），若不传入输入路径，程序则抛出异常并终止运行;
                索引文件保存路径（index_path），若不传入输出路径，程序则抛出异常并终止运行;
                程序运行所需要的关键参数名称（par_name），若不传入参数，程序则会终止运行;
    ****可选参数：工程类型（project_type）， 有'引松'、'引额-361'、'引额-362'、'引绰-667'、'引绰-668'几种;
                最小掘进长度（L_min），默认300mm;
                推进速度最大值（V_max），引松取 120mm/min，额河取 200mm/min;
                推进速度设定值变化幅值（V_set_var），默认15;
                数据缺失率（missing_ratio），默认0.2;
                程序调试/修复选项（debug），默认为关闭状态;
                直接运行程序（Run）， 默认为开启状态;
    """
    PROJECT_COEFFICIENT = {'引松': 1.0 / 40.731, '引额-361': 1.227, '引额-362': 1.354, '引绰-667': 1.763, '引绰-668': 2.356}
    RESULT = {'A': '', 'B1': '', 'B2': '', 'C1': '', 'C2': '', 'D': '', 'E': '', 'Normal': ''}
    SUB_FOLDERS = {'A': 'A1class-data', 'B1': 'B1class-data', 'B2': 'B2class-data',
                   'C1': 'C1class-data', 'C2': 'C2class-data', 'D': 'D1class-data',
                   'E': 'E1class-data', 'Unknown': 'Unknown-data', 'Normal': 'Norclass-data'}  # 默认子文件夹
    PARAMETERS = ['桩号', '日期', '推进位移', '刀盘转速', '推进速度', '刀盘扭矩',
                  '总推力', '刀盘贯入度', '刀盘转速设定值', '推进速度设定值']  # 默认参数示例
    INDEX_NAME = ['循环段', 'A', 'B1', 'B2', 'C1', 'C2', 'D', 'E', 'Normal']  # 生成索引文件中标签信息
    RAW_INDEX = pd.DataFrame()  # 保存原始索引数据
    NEW_INDEX = pd.DataFrame(columns=INDEX_NAME)  # 保存新的索引数据

    def __init__(self, input_path=None, out_path=None, index_path=None, parameter=None, project_type='引绰-668',
                 L_min=0.3, V_max=120, V_set_var=15, missing_ratio=0.2, debug=False, Run=True):
        """初始化必要参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.index = index_path  # 初始化索引文件路径
        self.parm = parameter  # 过程中用到的相关参数
        """初始化可选参量"""
        self.project_type = project_type  # 工程类型（'引松'、'引额-361'、'引额-362'、'引绰-667'、'引绰-668'）
        self.length_threshold_value = L_min  # 掘进长度下限值
        self.V_threshold_value = V_max  # 推进速度上限值，引松取120，额河取200
        self.V_set_variation = V_set_var  # 推进速度设定值变化幅度
        self.missing_ratio = missing_ratio  # 数据缺失率
        self.debug = debug  # 调试/修复程序
        """初始化程序内部参量"""
        self.Time_val = []  # 初始化程序运行花费时间
        self.show_parm = True  # 将输入参数大音出来，便于进行核对
        None if not Run else self.main()  # 运行主程序

    def create_class_Dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):
            os.mkdir(self.out)  # 创建相关文件夹
        else:
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹
        for index, name in enumerate(list(self.SUB_FOLDERS.keys())):  # 创建子文件夹
            self.SUB_FOLDERS[name] = '%d-' % (index + 1) + self.SUB_FOLDERS[name]  # 子文件夹前面添加编号
            sub_folder_path = os.path.join(self.out, self.SUB_FOLDERS[name])  # 子文件夹路径
            if not os.path.exists(sub_folder_path):
                os.mkdir(sub_folder_path)  # 创建子文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        Class = self.__class__.__name__  # 获取当前模块名称
        if (not self.input) or (not self.out) or (not self.index) or \
                (not self.parm) or (len(self.parm) < len(self.PARAMETERS)):  # 检查必要参数
            print('-> %s \033[0;31mThe input/output/index path or parameter are faulty, Please check!!!\033[0m' % Class)
            sys.exit()  # 抛出异常并终止程序

    def check_index(self, all_location: list) -> None:
        """
        判断数据中是否存在重复列名，若存在重复列名，则需要输入位置索引
        :param all_location: 原始数据的所有标签名称
        :return: 无
        """
        if reduce(lambda x, y: x * y, [type(name) == str for name in self.parm]):  # 判断是否为标签类型索引(名称)
            all_location = [name.split('.')[0] for name in all_location]  # 获取原始数据的标签名称
            mark = max([all_location.count(now_name) for now_name in self.parm])  # 检查标签名称中是否重复
            if mark == 1:  # 标签名称不重复
                self.parm = [all_location.index(now_name) for now_name in self.parm]
            else:
                maybe = [all_location.index(now_name) for now_name in self.parm]  # 可能的参数位置索引
                print('-> \033[0;31mLabel index(loc) is not available, Please enter location index(iloc)!!!\033[0m')
                print('   \033[0;31mLocation index(iloc) may be %s, You can verify that.\033[0m' % maybe)
                sys.exit()
        if self.show_parm:  # 将输入参数打印出来，便于进行核对
            self.show_parm = False
            Class = self.__class__.__name__  # 获取当前模块名称
            print('-> %s \033[0;33m参数名称: %s \033[0m' % (Class, [all_location[i] for i in self.parm]))

    def write_index(self, info: dict) -> None:  # 规定_Num_为整型(int)，info为列表(list)，返回值返回值无类型限定
        """
        向索引文件写入数据
        :param info: 待写入的信息，其中至少含有{‘name’：‘’}，name为循环段名称
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        if self.RAW_INDEX.empty:  # 索引文件行位置记录
            if os.path.isfile(self.index):
                self.RAW_INDEX = pd.read_csv(self.index, index_col=0, encoding='gb2312')  # 读取索引文件
                for name in self.INDEX_NAME:  # 删除已经存在的与内部段划分有关的列
                    if name in list(self.RAW_INDEX):
                        self.RAW_INDEX = self.RAW_INDEX.drop(name, axis=1)
        local_Num = int(info['name'][:5])  # 当前文件编号
        while self.NEW_INDEX.shape[0] + 1 < local_Num:  # 对中间缺失数据用空值进行处理
            index_Num = self.NEW_INDEX.shape[0] + 1  # 索引记录编号
            self.NEW_INDEX.loc[index_Num] = [str(index_Num)] + ['' for _ in self.INDEX_NAME[1:]]
        self.NEW_INDEX.loc[local_Num] = [local_Num] + [info[name] for name in self.INDEX_NAME[1:]]  # 新的索引文件记录
        after_index = self.RAW_INDEX.merge(self.NEW_INDEX, how='right', left_index=True, right_index=True)  # 合并
        ID = after_index.pop('循环段')  # 将'循环段'一列移动到最前面
        after_index.insert(0, '循环段', ID)  # 将'循环段'一列移动到最前面
        after_index.to_csv(self.index, index=False, encoding='gb2312')  # 保存索引记录

    def A_premature(self, cycle: DataFrame) -> str:  # 规定cycle为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """
        判断数据类型是不是A_premature (循环段掘进长度过短 L<0.3m)
        :param cycle: 循环段数据（DataFrame）
        :return: 异常类型（'Normal'/'A'）
        """
        start_length = cycle.iloc[0, self.parm[2]]  # 获取循环段开始点位移,推进位移（self.parm[2]）
        end_length = cycle.iloc[cycle.shape[0] - 1, self.parm[2]]  # 获取循环段结束点位移,推进位移（self.parm[2]）
        length = end_length - start_length  # 循环段掘进长度
        if length < self.length_threshold_value:
            return 'A'  # 返回数据分类的结果('A'),并退出子程序，子程序后续代码将不再执行
        return 'Normal'  # 返回数据分类的结果('Normal'),并退出子程序

    def B1_markAndModify(self, cycle: DataFrame) -> str:  # 规定cycle为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是B1_markAndModify (循环段速度值超限 V>120mm/min)
        :param cycle: 循环段数据（DataFrame）
        :return: 异常类型（'Normal'/'B1'）
        """
        data_V = cycle.iloc[:, self.parm[4]].values  # 获取推进速度并转化类型，推进速度（self.parm[4]）
        data_mean, data_std = np.mean(data_V), np.std(data_V)  # 获取推进速度均值和标准差
        for V in data_V:
            if (V > self.V_threshold_value) and (V > data_mean + 3 * data_std):
                return 'B1'  # 返回数据分类的结果('B1'),并退出子程序，子程序后续代码将不再执行
        return 'Normal'  # 返回数据分类的结果('Normal'),并退出子程序

    def B2_constant(self, cycle: DataFrame) -> str:  # 规定cycle为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是B2_constant (循环段数据传输异常 刀盘推力连续5s不发生变化)
        :param cycle: 循环段数据（DataFrame）
        :return: 异常类型（'Normal'/'B2'）
        """
        data_F = cycle.iloc[:, self.parm[6]].values  # 获取刀盘推力并转化类型，刀盘推力（self.parm[6]）
        for i in range(len(data_F) - 4):
            if (not np.std(data_F[i:i + 5])) and (np.mean(data_F[i:i + 5])):  # 判断刀盘推力是否连续五个数值稳定不变
                return 'B2'  # 返回数据分类的结果('B2'),并退出子程序，子程序后续代码将不再执行
        return 'Normal'  # 返回数据分类的结果('Normal'),并退出子程序

    def C1_sine(self, cycle: DataFrame) -> str:  # 规定cycle为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是C1_sine (循环段刀盘扭矩出现正弦波扭矩)
        :param cycle: 循环段数据（DataFrame）
        :return: 异常类型（'Normal'/'C1'）
        """
        data_T = cycle.iloc[:, self.parm[5]]  # 获取刀盘扭矩，刀盘扭矩（self.parm[5]）
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
            return 'C1'  # 返回数据分类的结果('C1'),并退出子程序，子程序后续代码将不再执行
        return 'Normal'  # 返回数据分类的结果('Normal'),并退出子程序

    def C2_shutdown(self, cycle: DataFrame) -> str:  # 规定cycle为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是C2_shutdown (循环段内机器发生短暂停机)
        :param cycle: 循环段数据（DataFrame）
        :return: 异常类型（'Normal'/'C2'）
        """
        N_set = cycle.iloc[:, self.parm[8]].values  # 获取刀盘转速设定值，刀盘转速设定值（self.parm[8]）
        V_set = cycle.iloc[:, self.parm[9]].values  # 获取推进速度设定值，推进速度设定值（self.parm[9]）
        for N_set_value, V_set_value in zip(N_set, V_set):
            if V_set_value == 0 and N_set_value > 0.1:
                return 'C2'  # 返回数据分类的结果('C2'),并退出子程序，子程序后续代码将不再执行
        return 'Normal'  # 返回数据分类的结果('Normal'),并退出子程序

    def D_adjust_setting(self, cycle: DataFrame) -> str:  # 规定cycle为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是D_adjust_setting (循环段内多次调整推进速度设定值)
        :param cycle: 循环段数据（DataFrame）
        :return: 异常类型（'Normal'/'D'）
        """
        data_V = cycle.iloc[:, self.parm[4]]  # 获取推进速度，推进速度（self.parm[4]）
        V_mean, V_std = data_V.mean(), data_V.std()  # 获取推进速度均值和标准差
        rule = ((data_V < 0) | (data_V > self.V_threshold_value) | (data_V > V_mean + 3 * V_std))  # 满足条件的数据
        index = np.arange(data_V.shape[0])[rule]  # 满足条件的索引
        cycle = cycle.drop(index, axis=0)  # 删除相关数据
        cycle.index = [i for i in range(cycle.shape[0])]  # 重建新数据集的行索引
        data_V_set = (cycle.iloc[:, self.parm[9]] * self.PROJECT_COEFFICIENT[self.project_type]).std()  # 获取推进速度设定值的方差
        if data_V_set > self.V_set_variation:
            return 'D'  # 返回数据分类的结果('D'),并退出子程序，子程序后续代码将不再执行
        return 'Normal'  # 返回数据分类的结果('Normal'),并退出子程序

    def E_missing_ratio(self, cycle: DataFrame) -> str:  # 规定cycle为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是E_missing_ratio (循环段内数据缺失过多)
        :param cycle: 循环段数据（DataFrame）
        :return: 异常类型（'Normal'/'E'）"""
        data_time = cycle.iloc[:, self.parm[1]].values  # 获取日期并转化类型，日期（self.parm[1]）
        time_start = pd.to_datetime(data_time[0], format='%Y-%m-%d %H:%M:%S')  # 循环段开始日期
        time_finish = pd.to_datetime(data_time[-1], format='%Y-%m-%d %H:%M:%S')  # 循环段结束日期
        time_diff = (time_finish - time_start).seconds  # 时间差，以s为单位
        time_len = len(data_time)  # 实际时间
        missing_ratio = (time_diff - time_len) / time_diff  # 缺失率计算
        if missing_ratio > self.missing_ratio:
            return 'E'  # 返回数据分类的结果('E'),并退出子程序，子程序后续代码将不再执行
        return 'Normal'  # 返回数据分类的结果('Normal'),并退出子程序

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """数据分类"""
        self.check_parm()  # 检查参数是否正常
        self.create_class_Dir()  # 创建相关文件夹
        all_file = os.listdir(self.input)  # 获取输入文件夹下的所有文件名，并将其保存
        all_file.sort(key=lambda x: int(x[:5]))  # 对读取的文件列表进行重新排序
        for num, file in enumerate(all_file):
            time_S = time.time()  # 记录程序执行开始时间
            local_csv_path = os.path.join(self.input, file)
            try:
                data_A = pd.read_csv(local_csv_path, encoding='gb2312')
            except UnicodeDecodeError:  # 若默认方式读取csv文件失败，则添加'gb2312'编码后重新进行尝试
                data_A = pd.read_csv(local_csv_path)
            self.check_index(list(data_A))  # 检查参数是否重复
            RS_Index = self.custom_get_RS(data_A, file)  # 调用自定义函数，获取空推、上升、稳定、下降的变化点
            if RS_Index is None:
                RS_Index = self.default_get_RS(data_A)  # 调用默认函数，获取空推、上升、稳定、下降的变化点
            result = copy.deepcopy(self.RESULT)
            result['A'] = 'True' if self.A_premature(data_A) == 'A' else ''  # 调用相关模块判断是否为A类异常
            if RS_Index['稳定段起点'] - RS_Index['上升段起点'] >= 30 and RS_Index['稳定段终点'] - RS_Index['稳定段起点'] >= 50:
                data_RS = data_A.iloc[RS_Index['上升段起点']:RS_Index['稳定段终点'], :].reset_index(drop=True)  # 上升段和稳定段数据
                data_S = data_A.iloc[RS_Index['稳定段起点']:RS_Index['稳定段终点'], :].reset_index(drop=True)  # 稳定段数据
                result['B1'] = 'True' if self.B1_markAndModify(data_A) == 'B1' else ''  # 调用相关模块判断是否为B1类异常
                result['B2'] = 'True' if self.B2_constant(data_RS) == 'B2' else ''  # 调用相关模块判断是否为B2类异常
                result['C1'] = 'True' if self.C1_sine(data_RS) == 'C1' else ''  # 调用相关模块判断是否为C1类异常
                result['C2'] = 'True' if self.C2_shutdown(data_S) == 'C2' else ''  # 调用相关模块判断是否为C2类异常
                result['D'] = 'True' if self.D_adjust_setting(data_S) == 'D' else ''  # 调用相关模块判断是否为D类异常
                result['E'] = 'True' if self.E_missing_ratio(data_RS) == 'E' else ''  # 调用相关模块判断是否为E类异常
                result['Normal'] = 'True' if 'True' not in result.values() else ''
            elif 'True' not in list(result.values()):
                for Type in list(result.keys()):
                    result[Type] = 'Unknown'  # 若循环段类型无法判断，则将其归类于Unknown文件夹
            for Key in list(result.keys()):
                target_csv_path = os.path.join(self.out, self.SUB_FOLDERS[Key], file)  # 异常数据存放位置
                if result[Key] == 'True':  # 复制文件到‘Norclass-data’文件夹
                    shutil.copyfile(local_csv_path, target_csv_path)
                if result[Key] == 'Unknown':  # 复制文件到‘Unknown’文件夹
                    shutil.copyfile(local_csv_path, os.path.join(self.out, self.SUB_FOLDERS['Unknown'], file))  # 复制文件
            self.write_index(dict(result, **{'name': file}))  # 将记录写入索引文件
            self.detail(name=file, data=data_A, Parm=self.parm[3:7], debug=self.debug,
                        key=['循环段分类:'] + ['' if result[key] not in ['True', 'Unknown'] else key
                        if result[key] != 'Unknown' else 'Unknown' for key in result.keys()])  # DEBUG
            time_F = time.time()  # 记录程序执行结束时间
            self.show_info(use_time=time_F - time_S, file_num=num, file_sum=len(all_file))  # 实时输出程序运行状况

    def default_get_RS(self, data: DataFrame) -> dict:
        """
        使用默认方式获取空推、上升、稳定、下降的关键点
        :param data: 循环段数据（DataFrame）
        :return: '上升段起点'、'稳定段起点'和'稳定段终点'位置索引
        """
        try:
            if data.shape[0] < 80:
                RS_index = {'上升段起点': 0, '稳定段起点': 0, '稳定段终点': 0}
                return RS_index
            T_mean = data.iloc[:, self.parm[5]].mean()
            mid_start_value = min(data.iloc[0:int(data.shape[0] / 3), self.parm[9]])  # 找前1/3的v_set最小值
            mid_point_start = 0  # 中点位置索引
            while data.iloc[mid_point_start, self.parm[9]] > mid_start_value:
                mid_point_start += 1
            V_set_mean = data.iloc[mid_point_start:-1, self.parm[9]].mean()  # 第一次求均值，用于索引中点
            mid_point = mid_point_start
            while data.iloc[mid_point, self.parm[9]] < V_set_mean:
                if mid_point > 0.7 * data.shape[0]:
                    mid_point = int(data.shape[0] * 0.2)
                else:
                    while data.iloc[mid_point, self.parm[9]] < V_set_mean or \
                            data.iloc[mid_point + 30, self.parm[9]] < V_set_mean:
                        mid_point += 1  # #############有修改
            steadyE = data.shape[0] - 1  # 稳定段结束位置索引
            while data.iloc[steadyE, self.parm[5]] <= T_mean:  # 判断稳定段结束点
                steadyE -= 1
            if mid_point and mid_point <= 0.7 * data.shape[0]:
                rise = mid_point  # 上升段开始位置处索引
                while abs(data.iloc[rise, self.parm[7]]) > 0 and rise > 10:  # 刀盘贯入度度索引（self.parm[7]） ########
                    rise -= 1
                steadyS = mid_point
                V_set_ = data.iloc[mid_point_start:steadyE, self.parm[9]]  # #改改改改改改改改改改改改改改改
                if steadyS + 60 < steadyE:
                    while V_set_[steadyS] - V_set_.mean() <= 0 or \
                            (max(V_set_[steadyS:steadyS + 60]) - min(V_set_[steadyS:steadyS + 60]) >= 0.02 * V_set_[
                                steadyS]):
                        steadyS += 1
                if steadyE - steadyS > 300:
                    steady_V_set_mean = V_set_.iloc[0: 300].mean()
                    steady_V_set_mean = min(0.95 * steady_V_set_mean, steady_V_set_mean - 3)
                else:
                    steady_V_set_mean = V_set_.iloc[0:steadyE - steadyS].mean()
                    steady_V_set_mean = min(0.95 * steady_V_set_mean, steady_V_set_mean - 3)
                while V_set_.iloc[steadyS - mid_point] < steady_V_set_mean:  # 稳定段开始位置处的均值是否大于整个稳定段推进速度均值
                    steadyS += 1
                RS_index = {'上升段起点': rise, '稳定段起点': steadyS, '稳定段终点': steadyE}
            else:
                RS_index = {'上升段起点': 0, '稳定段起点': 0, '稳定段终点': 0}
        except Exception:
            RS_index = {'上升段起点': 0, '稳定段起点': 0, '稳定段终点': 0}
        return RS_index

    def custom_get_RS(self, data: DataFrame, name) -> dict:
        """自定义获取空推、上升、稳定、下降的关键点模块，若定义了相关功能，则优先运行此功能，若未定义相关功能，则运行默认模块"""
        pass

    def show_info(self, use_time: float, file_num: int, file_sum: int) -> None:
        """
        实时输出程序运行状况
        :param use_time: 处理每个循环段数据花费的时间
        :param file_num: 当前的循环段编号
        :param file_sum: 总的循环段数量
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        cpu_percent = psutil.cpu_percent()  # CPU占用
        mem_percent = psutil.Process(os.getpid()).memory_percent()  # 内存占用
        self.Time_val.append(use_time)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(self.Time_val) / len(self.Time_val)  # 计算平均时间
        sum_time = round(sum(self.Time_val) / 3600, 3)  # 计算程序执行的总时间
        remain_time = round((mean_time * (file_sum - file_num - 1)) / 3600, 3)  # 预计剩余时间计算
        print('\r   [第%d个 / 共%d个]  ' % (file_num + 1, file_sum),
              '[所用时间%ds / 平均时间%ds]  ' % (int(use_time), int(mean_time)),
              '[CPU占用: %5.2f%% / 内存占用: %5.2f%%]  ' % (cpu_percent, mem_percent),
              '[累积运行时间: %6.3f小时 / 预计剩余时间: %6.3f小时]' % (sum_time, remain_time), end='')
        if file_num + 1 >= file_sum:
            Class = self.__class__.__name__  # 获取当前模块名称
            print('\r-> %s \033[0;32mData-Class completed, which took %6.3f hours\033[0m' % (Class, sum_time))

    @staticmethod  # 不强制要求传递参数
    def detail(name=None, data=None, key=None, Parm=None, debug=False):
        """展示程序细节信息"""
        if debug:
            print("\033[0;33m{:·^100}\033[0m".format(name))
            for num, information in enumerate(key):
                print('\033[0;33m%9s\033[0m' % str(information), end='')
            print('')
            x = [i for i in range(data.shape[0])]  # 'Time'
            plt.figure(figsize=(14, 7), dpi=120)  # 设置画布大小（10cm x 8cm）及分辨率（dpi=120）
            for parm, color in zip(Parm, ['b', 'g', 'r', 'y']):
                plt.plot(x, data.iloc[:, parm], label="%s" % list(data)[parm], color=color)
            plt.legend()
            plt.xlabel("时间/s", fontsize=15)
            plt.show()
            plt.close()
            print("\033[0;33m{:·^100}\033[0m".format(name))


class TBM_CLEAN(object):
    """
    异常数据清理修正模块，主要完成异常循环段修正的工作
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输入路径，程序则抛出异常并终止运行
                索引文件保存路径（index_path），若不传入输出路径，程序则抛出异常并终止运行
                程序运行所需要的关键参数名称（par_name），若不传入参数，程序则会终止运行
    ****可选参数：推进速度最大值（V_max），引松取 120mm/min，额河取 200mm/min;
                程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run）， 默认为开启状态
    """
    PARAMETERS = ['桩号', '日期', '推进位移', '刀盘转速', '推进速度', '刀盘扭矩',
                  '总推力', '刀盘贯入度', '刀盘转速设定值', '推进速度设定值']  # 默认参数示例
    SUB_FOLDERS = {'A': 'NorA1class-data', 'B1': 'NorB1class-data', 'B2': 'NorB2class-data',
                   'C1': 'NorC1class-data', 'C2': 'NorC2class-data', 'D': 'NorD1class-data',
                   'E': 'NorE1class-data', 'Unknown': 'Unknown-data', 'Normal': 'Normclass-data'}  # 默认子文件夹
    INDEX_NAME = ['循环段', 'A', 'B1', 'B2', 'C1', 'C2', 'D', 'E', 'Normal']
    RAW_INDEX = pd.DataFrame()  # 保存原始索引数据
    NEW_INDEX = pd.DataFrame()  # 保存新的索引数据

    def __init__(self, input_path=None, out_path=None, index_path=None, parameter=None, V_max=120, debug=False,
                 Run=True):
        """初始化必要参量"""
        self.input = input_path  # 初始化输入路径
        self.index = index_path  # 初始化索引文件路径
        self.out = out_path  # 初始化输出路径
        self.parm = parameter  # 过程中用到的相关参数
        """初始化可选参量"""
        self.V_threshold_value = V_max  # 推进速度上限值，引松取120，额河取200
        self.debug = debug  # 调试/修复程序
        """初始化程序内部参量"""
        self.Time_val = []  # 初始化程序运行花费时间
        self.show_parm = True  # 将输入参数大音出来，便于进行核对
        None if not Run else self.main()  # 运行主程序

    def create_clean_Dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):
            os.mkdir(self.out)  # 创建相关文件夹
        else:
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹
        for index, name in enumerate(list(self.SUB_FOLDERS.keys())):  # 创建子文件夹
            self.SUB_FOLDERS[name] = '%d-' % (index + 1) + self.SUB_FOLDERS[name]  # 子文件夹前面添加编号
            sub_folder_path = os.path.join(self.out, self.SUB_FOLDERS[name])  # 子文件夹路径
            if not os.path.exists(sub_folder_path):
                os.mkdir(sub_folder_path)  # 创建子文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        Class = self.__class__.__name__  # 获取当前模块名称
        if (not self.input) or (not self.out) or (not self.index) or \
                (not self.parm) or (len(self.parm) < len(self.PARAMETERS)):  # 检查必要参数
            print('-> %s \033[0;31mThe input/output/index path or parameter are faulty, Please check!!!\033[0m' % Class)
            sys.exit()  # 抛出异常并终止程序

    def check_index(self, all_location: list) -> None:
        """
        判断数据中是否存在重复列名，若存在重复列名，则需要输入位置索引
        :param all_location: 原始数据的所有标签名称
        :return: 无
        """
        if reduce(lambda x, y: x * y, [type(name) == str for name in self.parm]):  # 判断是否为标签类型索引(名称)
            all_location = [name.split('.')[0] for name in all_location]  # 获取原始数据的标签名称
            mark = max([all_location.count(now_name) for now_name in self.parm])  # 检查标签名称中是否重复
            if mark == 1:  # 标签名称不重复
                self.parm = [all_location.index(now_name) for now_name in self.parm]
            else:
                maybe = [all_location.index(now_name) for now_name in self.parm]  # 可能的参数位置索引
                print('-> \033[0;31mLabel index(loc) is not available, Please enter location index(iloc)!!!\033[0m')
                print('   \033[0;31mLocation index(iloc) may be %s, You can verify that.\033[0m' % maybe)
                sys.exit()
        if self.show_parm:  # 将输入参数打印出来，便于进行核对
            self.show_parm = False
            Class = self.__class__.__name__  # 获取当前模块名称
            print('-> %s \033[0;33m参数名称: %s \033[0m' % (Class, [all_location[i] for i in self.parm]))

    def write_index(self, info: dict) -> None:  # 规定_Num_为整型(int)，info为列表(list)，返回值返回值无类型限定
        """
        向索引文件写入数据
        :param info: 待写入的信息，其中至少含有{‘name’：‘’, 'Type'：‘’}，name为循环段名称, Type为异常类型
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        try:
            if self.RAW_INDEX.empty:  # 索引文件行位置记录
                Type = {'A': str, 'B1': str, 'B2': str, 'C1': str, 'C2': str, 'D': str, 'E': str, 'Normal': str}
                self.RAW_INDEX = pd.read_csv(self.index, index_col=0, encoding='gb2312', dtype=Type)  # 读取索引文件
                self.NEW_INDEX = copy.deepcopy(self.RAW_INDEX)  # 复制一份索引文件
            self.RAW_INDEX[info['Type']][int(info['name'][:5])] = ''  # 修正后去掉异常循环段标识
            if (self.RAW_INDEX.loc[int(info['name'][:5]), self.INDEX_NAME[1:-1]] == 'True').sum() <= 0:
                self.NEW_INDEX['Normal'][int(info['name'][:5])] = 'True'  # 将修正后的索引修改为True
                self.NEW_INDEX.to_csv(self.index, index=True, encoding='gb2312')  # 保存索引记录
        except (FileNotFoundError, KeyError, IndexError, TypeError):
            pass

    def A_premature_Modify(self, cycle: DataFrame) -> DataFrame:  # 规定cycle为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对A_premature (循环段掘进长度过短 L<0.3m)类异常数据进行修正
        :param cycle: 循环段数据（DataFrame）
        :return: 修正后循环段数据（DataFrame）
        """
        pass

    def B1_mark_Modify(self, cycle: DataFrame) -> DataFrame:  # 规定cycle为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对B1_markAndModify (循环段速度值超限 V>120mm/min)类异常数据进行修正
        :param cycle: 循环段数据（DataFrame）
        :return: 修正后循环段数据（DataFrame）
        """
        data_V = cycle.iloc[:, self.parm[4]].values  # 推进速度（self.parm[4]）
        data_mean, data_std = np.mean(data_V), np.std(data_V)  # 获取推进速度均值和标准差
        for i in range(len(data_V)):
            if data_V[i] > self.V_threshold_value or (data_V[i] > data_mean + 3 * data_std):
                replace = sum(data_V[i - 10:i]) / 10.0  # 采用前10个推进速度的平均值进行替换
                cycle.iloc[i, self.parm[4]] = replace  # 采用前10个推进速度的平均值进行替换
        return cycle

    def B2_constant_Modify(self, cycle: DataFrame) -> DataFrame:  # 规定cycle为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对B2_constant (循环段数据传输异常 刀盘推力连续5s不发生变化)类异常数据进行修正
        :param cycle: 循环段数据（DataFrame）
        :return: 修正后循环段数据（DataFrame）
        """
        pass

    def C1_sine_Modify(self, cycle: DataFrame) -> DataFrame:  # 规定cycle为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对C1_sine (循环段刀盘扭矩出现正弦波扭矩)类异常数据进行修正
        :param cycle: 循环段数据（DataFrame）
        :return: 修正后循环段数据（DataFrame）
        """
        pass

    def C2_shutdown_Modify(self, cycle: DataFrame) -> DataFrame:  # 规定cycle为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对C2_shutdown (循环段内机器发生短暂停机)类异常数据进行修正
        :param cycle: 循环段数据（DataFrame）
        :return: 修正后循环段数据（DataFrame）
        """
        pass

    def D_adjust_setting_Modify(self, cycle: DataFrame) -> DataFrame:  # 规定cycle为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对D_adjust_setting (循环段内多次调整推进速度设定值)类异常数据进行修正
        :param cycle: 循环段数据（DataFrame）
        :return: 修正后循环段数据（DataFrame）
        """
        pass

    def E_missing_ratio_Modify(self, cycle: DataFrame) -> DataFrame:  # 规定cycle为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对E_missing_ratio (循环段内数据缺失过多)类异常数据进行修正
        :param cycle: 循环段数据（DataFrame）
        :return: 修正后循环段数据（DataFrame）
        """
        pass

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """将数据类型进行汇总并保存"""
        self.check_parm()  # 检查参数是否正常
        self.create_clean_Dir()  # 创建相关文件夹
        all_dir = os.listdir(self.input)  # 获取输入文件夹下的所有文件夹名称，并将其保存
        for dir_num, (Key, Dir) in enumerate(zip(list(self.SUB_FOLDERS.keys()), all_dir)):
            all_file = os.listdir(os.path.join(self.input, Dir))  # 获取输入文件夹下的所有文件名称，并将其保存
            all_file.sort(key=lambda x: int(x[:5]))  # 对读取的文件列表进行重新排序
            for file_num, file in enumerate(all_file):  # 遍历输入文件夹下的所有子文件夹
                time_S = time.time()  # 记录程序执行开始时间
                local_csv_path = os.path.join(self.input, Dir, file)  # 当前文件路径
                target_csv_path = os.path.join(self.out, self.SUB_FOLDERS[Key], file)  # 目标文件路径
                try:
                    data = pd.read_csv(local_csv_path, encoding='gb2312')  # 读取异常循环段数据，编码为'gb2312'
                except UnicodeDecodeError:
                    data = pd.read_csv(local_csv_path)  # 读取异常循环段数据，编码为默认
                self.check_index(list(data))  # 检查参数是否重复
                function = {'A': self.A_premature_Modify(data), 'B1': self.B1_mark_Modify(data),
                            'B2': self.B2_constant_Modify(data), 'C1': self.C1_sine_Modify(data),
                            'C2': self.C2_shutdown_Modify(data), 'D': self.D_adjust_setting_Modify(data),
                            'E': self.E_missing_ratio_Modify(data), 'Unknown': None, 'Normal': None}  # 保存修正后循环段数据
                if function[Key] is not None:  # 调用相对应的修正函数对异常数据进行修正
                    function[Key].to_csv(target_csv_path, index=False, encoding='gb2312')  # 保存修正后'A'类循环段数据
                    self.write_index({'name': file, 'Type': Key})  # 修正索引文件
                    self.detail(name=file, data=data, key=['循环段修正：'] + ['%s  ->  修正为  ->  Normal' % Key],
                                Parm=self.parm[3:7], debug=self.debug)  # 显示细节信息
                if Key == 'Normal':
                    shutil.copyfile(local_csv_path, target_csv_path)  # 将正常循环段数据复制到'Normclass-data'文件夹
                time_F = time.time()  # 记录程序执行结束时间
                self.show_info(Use_time=time_F - time_S, Num=[dir_num, file_num], Sum=[len(all_dir), len(all_file)])

    def show_info(self, Use_time: float, Num: list, Sum: list) -> None:
        """
        实时输出程序运行状况
        :param Use_time: 处理每个循环段数据花费的时间
        :param Num: 当前的循环段编号
        :param Sum: 总的循环段数量
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        cpu_percent = psutil.cpu_percent()  # CPU占用
        mem_percent = psutil.Process(os.getpid()).memory_percent()  # 内存占用
        self.Time_val.append(Use_time)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(self.Time_val) / len(self.Time_val)  # 计算平均时间
        sum_time = round(sum(self.Time_val) / 3600, 3)  # 计算程序执行的总时间
        remain_time = round((mean_time * (Sum[1] - Num[1] - 1)) / 3600, 3)  # 预计剩余时间计算
        print('\r   [第%d个 / 共%d个]  ' % (Num[1] + 1, Sum[1]),
              '[所用时间%ds / 平均时间%ds]  ' % (int(Use_time), int(mean_time)),
              '[CPU占用: %5.2f%% / 内存占用: %5.2f%%]  ' % (cpu_percent, mem_percent),
              '[累积运行时间: %6.3f小时 / 预计剩余时间: %6.3f小时]' % (sum_time, remain_time), end='')
        if Num[0] + 1 >= Sum[0] and Num[1] + 1 >= Sum[1]:
            Class = self.__class__.__name__  # 获取当前模块名称
            print('\r-> %s \033[0;32mData-Clean completed, which took %6.3f hours\033[0m' % (Class, sum_time))

    @staticmethod  # 不强制要求传递参数
    def detail(name=None, data=None, key=None, Parm=None, debug=False):
        """展示程序细节信息"""
        if debug:
            print("\033[0;33m{:·^100}\033[0m".format(name))
            for num, information in enumerate(key):
                print('\033[0;33m%9s\033[0m' % str(information), end='')
            print('')
            x = [i for i in range(data.shape[0])]  # 'Time'
            plt.figure(figsize=(14, 7), dpi=120)  # 设置画布大小（10cm x 8cm）及分辨率（dpi=120）
            for parm, color in zip(Parm, ['b', 'g', 'r', 'y']):
                plt.plot(x, data.iloc[:, parm], label="%s" % list(data)[parm], color=color)
            plt.legend()
            plt.xlabel("时间/s", fontsize=15)
            plt.show()
            plt.close()
            print("\033[0;33m{:·^100}\033[0m".format(name))


class TBM_MERGE(object):
    """
    修正后数据合并模块，主要完成将修正后的数据集合并的工作
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输入路径，程序则抛出异常并终止运行
                索引文件保存路径（index_path），若不传入输出路径，程序则抛出异常并终止运行
                程序运行所需要的关键参数名称（par_name），若不传入参数，程序则会终止运行
    ****可选参数：程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run）， 默认为开启状态
    """
    PARAMETERS = ['None']  # 默认参数示例
    RAW_INDEX = pd.DataFrame()  # 保存原始索引数据

    def __init__(self, input_path=None, out_path=None, index_path=None, parameter=None, debug=False, Run=True):
        """初始化必要参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.index = index_path  # 初始化索引文件路径
        self.parm = parameter  # 过程中用到的相关参数
        """初始化可选参量"""
        self.debug = debug  # 调试/修复程序
        """初始化程序内部参量"""
        self.Time_val = []  # 初始化程序运行花费时间
        self.show_parm = True  # 将输入参数大音出来，便于进行核对
        None if not Run else self.main()  # 运行主程序

    def create_merge_Dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):
            os.mkdir(self.out)  # 创建相关文件夹
        else:
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        Class = self.__class__.__name__  # 获取当前模块名称
        if (not self.input) or (not self.out) or (not self.index):  # 检查必要参数
            print('-> %s \033[0;31mThe input/output/index path or parameter are faulty, Please check!!!\033[0m' % Class)
            sys.exit()  # 抛出异常并终止程序

    def check_index(self, all_location: list) -> None:
        """
        判断数据中是否存在重复列名，若存在重复列名，则需要输入位置索引
        :param all_location: 原始数据的所有标签名称
        :return: 无
        """
        if reduce(lambda x, y: x * y, [type(name) == str for name in self.parm]):  # 判断是否为标签类型索引(名称)
            all_location = [name.split('.')[0] for name in all_location]  # 获取原始数据的标签名称
            mark = max([all_location.count(now_name) for now_name in self.parm])  # 检查标签名称中是否重复
            if mark == 1:  # 标签名称不重复
                self.parm = [all_location.index(now_name) for now_name in self.parm]
            else:
                maybe = [all_location.index(now_name) for now_name in self.parm]  # 可能的参数位置索引
                print('-> \033[0;31mLabel index(loc) is not available, Please enter location index(iloc)!!!\033[0m')
                print('   \033[0;31mLocation index(iloc) may be %s, You can verify that.\033[0m' % maybe)
                sys.exit()
        if self.show_parm:  # 将输入参数打印出来，便于进行核对
            self.show_parm = False
            Class = self.__class__.__name__  # 获取当前模块名称
            print('-> %s \033[0;33m参数名称: %s \033[0m' % (Class, [all_location[i] for i in self.parm]))

    def get_index(self, info: dict) -> dict:
        """获取索引文件记录  info中至少含有{‘name’：‘’}"""
        try:  # 尝试读取索引文件，若索引文件存在，则将['循环段', '上升段起点', '稳定段起点', '稳定段终点']保存至Index_value中
            if self.RAW_INDEX.empty:  # 索引文件行位置记录
                self.RAW_INDEX = pd.read_csv(self.index, index_col=0, encoding='gb2312', dtype={'Normal': str})  # 获取索引
                self.RAW_INDEX = self.RAW_INDEX.loc[:, 'Normal']  # 将关键点保存至Index_value
            mark = '' if self.RAW_INDEX is None else self.RAW_INDEX[int(info['name'][:5])]
        except (FileNotFoundError, KeyError, IndexError, TypeError):  # 若索引文件存在，则令Index_value为空[]
            mark = 'True'
        return mark

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """合并形成机器学习数据集"""
        self.check_parm()  # 检查参数是否正常
        self.create_merge_Dir()  # 创建相关文件夹
        self.check_index(self.parm)  # 检查参数是否重复
        all_dir = os.listdir(self.input)  # 获取输入路径下的所有子文件夹
        for dir_num, Dir in enumerate(all_dir):  # 遍历输入路径下的所有子文件夹
            Dir_path = os.path.join(self.input, Dir)  # 子文件夹路径
            all_file = os.listdir(Dir_path)
            for file_num, file in enumerate(all_file):
                time_S = time.time()  # 记录程序执行开始时间
                local_csv_path = os.path.join(self.input, Dir, file)  # 当前文件路径
                target_csv_path = os.path.join(self.out, file)  # 目标文件路径
                if self.get_index({'name': file}) == 'True':
                    shutil.copyfile(local_csv_path, target_csv_path)  # 复制文件值目标路径
                time_F = time.time()  # 记录程序执行结束时间
                self.show_info(Use_time=time_F - time_S, Num=[dir_num, file_num], Sum=[len(all_dir), len(all_file)])

    def show_info(self, Use_time: float, Num: list, Sum: list) -> None:
        """
        实时输出程序运行状况
        :param Use_time: 处理每个循环段数据花费的时间
        :param Num: 当前的循环段编号
        :param Sum: 总的循环段数量
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        cpu_percent = psutil.cpu_percent()  # CPU占用
        mem_percent = psutil.Process(os.getpid()).memory_percent()  # 内存占用
        self.Time_val.append(Use_time)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(self.Time_val) / len(self.Time_val)  # 计算平均时间
        sum_time = round(sum(self.Time_val) / 3600, 3)  # 计算程序执行的总时间
        remain_time = round((mean_time * (Sum[1] - Num[1] - 1)) / 3600, 3)  # 预计剩余时间计算
        print('\r   [第%d个 / 共%d个]  ' % (Num[1] + 1, Sum[1]),
              '[所用时间%ds / 平均时间%ds]  ' % (int(Use_time), int(mean_time)),
              '[CPU占用: %5.2f%% / 内存占用: %5.2f%%]  ' % (cpu_percent, mem_percent),
              '[累积运行时间: %6.3f小时 / 预计剩余时间: %6.3f小时]' % (sum_time, remain_time), end='')
        if Num[0] + 1 >= Sum[0] and Num[1] + 1 >= Sum[1]:
            Class = self.__class__.__name__  # 获取当前模块名称
            print('\r-> %s \033[0;32mData-Merge completed, which took %6.3f hours\033[0m' % (Class, sum_time))


class TBM_SPLIT(object):
    """
    内部段分割模块，完成从循环段提取上升段稳定段和下降段的功能
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行；
                生成数据保存路径（out_path），若不传入输出路径，程序则抛出异常并终止运行；
                索引文件保存路径（index_path），若不传入输出路径，程序则抛出异常并终止运行；
                关键参数名称（par_name），若不传入参数，程序则抛出异常并终止运行；
    ****可选参数：内部段划分方法（partition）， 统计平均值'Average'， 核密度估计'kernel density'；
                时间记录下限值（单位：s）（min_time），默认为200s；
                程序调试/修复选项（debug），默认为关闭状态；
                直接运行程序（Run）， 默认为开启状态；
    """
    SUB_FOLDERS = {'空推段': 'Free running', '上升段': 'Loading', '稳定段': 'Boring',
                   '上升和稳定段': 'Loading and Boring', '循环段': 'Boring cycle'}  # 默认子文件夹
    PARAMETERS = ['桩号', '日期', '推进位移', '刀盘转速', '推进速度', '刀盘扭矩',
                  '总推力', '刀盘贯入度', '刀盘转速设定值', '推进速度设定值']  # 默认参数示例
    INDEX_NAME = ['循环段', '上升段起点', '稳定段起点', '稳定段终点']  # 生成索引文件中标签信息
    RAW_INDEX = pd.DataFrame()  # 保存原始索引数据
    NEW_INDEX = pd.DataFrame(columns=INDEX_NAME)  # 保存新的索引数据

    def __init__(self, input_path=None, out_path=None, index_path=None, parameter=None,
                 partition='kernel density', min_time=200, debug=False, Run=True):
        """初始化必要参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.index = index_path  # 初始化索引文件路径
        self.parm = parameter  # 初始化程序处理过程中需要用到的参数
        """初始化可选参量"""
        self.partition = partition  # 内部段划分方法
        self.min_time = min_time  # 最小掘进时长(s)
        self.debug = debug  # 调试/修复程序
        """初始化程序内部参量"""
        self.Time_val = []  # 初始化程序运行花费时间
        self.show_parm = True  # 将输入参数大音出来，便于进行核对
        None if not Run else self.main()  # 运行主程序

    def create_split_Dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):  # 若保存内部段分割后数据的文件夹不存在
            os.mkdir(self.out)  # 创建相关文件夹
        else:  # 若保存内部段分割后数据的文件夹存在
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹
        for index, name in enumerate(list(self.SUB_FOLDERS.keys())):  # 创建子文件夹
            self.SUB_FOLDERS[name] = '%d-' % (index + 1) + self.SUB_FOLDERS[name]  # 子文件夹前面添加编号
            sub_folder_path = os.path.join(self.out, self.SUB_FOLDERS[name])  # 子文件夹路径
            if not os.path.exists(sub_folder_path):
                os.mkdir(sub_folder_path)  # 创建子文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        Class = self.__class__.__name__  # 获取当前模块名称
        if (not self.input) or (not self.out) or (not self.index) or (not self.parm) \
                or (len(self.parm) < len(self.PARAMETERS)):  # 检查必要参数
            print('-> %s \033[0;31mThe input/output/index path or parameter are faulty, Please check!!!\033[0m' % Class)
            sys.exit()  # 抛出异常并终止程序

    def check_index(self, all_location: list) -> None:
        """
        判断数据中是否存在重复列名，若存在重复列名，则需要输入位置索引
        :param all_location: 原始数据的所有标签名称
        :return: 无
        """
        if reduce(lambda x, y: x * y, [type(name) == str for name in self.parm]):  # 判断是否为标签类型索引(名称)
            all_location = [name.split('.')[0] for name in all_location]  # 获取原始数据的标签名称
            mark = max([all_location.count(now_name) for now_name in self.parm])  # 检查标签名称中是否重复
            if mark == 1:  # 标签名称不重复
                self.parm = [all_location.index(now_name) for now_name in self.parm]
            else:
                maybe = [all_location.index(now_name) for now_name in self.parm]  # 可能的参数位置索引
                print('-> \033[0;31mLabel index(loc) is not available, Please enter location index(iloc)!!!\033[0m')
                print('   \033[0;31mLocation index(iloc) may be %s, You can verify that.\033[0m' % maybe)
                sys.exit()
        if self.show_parm:  # 将输入参数打印出来，便于进行核对
            self.show_parm = False
            Class = self.__class__.__name__  # 获取当前模块名称
            print('-> %s \033[0;33m参数名称: %s \033[0m' % (Class, [all_location[i] for i in self.parm]))

    def write_index(self, info: dict) -> None:  # 规定_Num_为整型(int)，info为列表(list)，返回值返回值无类型限定
        """
        向索引文件写入数据
        :param info: 待写入的信息，其中至少含有{‘name’：‘’}，name为循环段名称
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        if self.RAW_INDEX.empty:  # 索引文件行位置记录
            if os.path.isfile(self.index):
                self.RAW_INDEX = pd.read_csv(self.index, index_col=0, encoding='gb2312')  # 读取索引文件
                for name in self.INDEX_NAME:  # 删除已经存在的与内部段划分有关的列
                    if name in list(self.RAW_INDEX):
                        self.RAW_INDEX = self.RAW_INDEX.drop(name, axis=1)
        local_Num = int(info['name'][:5])  # 当前文件编号
        while self.NEW_INDEX.shape[0] + 1 < local_Num:  # 对中间缺失数据用空值进行处理
            index_Num = self.NEW_INDEX.shape[0] + 1  # 索引记录编号
            self.NEW_INDEX.loc[index_Num] = [str(index_Num)] + ['' for _ in self.INDEX_NAME[1:]]
        self.NEW_INDEX.loc[local_Num] = [local_Num] + [info[name] for name in self.INDEX_NAME[1:]]  # 新的索引文件记录
        after_index = self.RAW_INDEX.merge(self.NEW_INDEX, how='right', left_index=True, right_index=True)  # 合并
        ID = after_index.pop('循环段')  # 将'循环段'一列移动到最前面
        after_index.insert(0, '循环段', ID)  # 将'循环段'一列移动到最前面
        after_index.to_csv(self.index, index=False, encoding='gb2312')  # 保存索引记录

    def segment_save(self, data: DataFrame, _key_: dict) -> None:  # 规定_name_为字符型（str），_key_为字典类型（dict）
        """
        对已经分割好的循环段文件进行保存
        :param data: 循环段数据（DataFrame）
        :param _key_: 内部段划分信息， 示例：_key_：{‘name’：‘’，‘rise’：‘’，‘steadyS’：‘’，‘steadyE’：‘’}
        :return: 无
        """
        save_data = {'空推段': data.iloc[:_key_['上升段起点'], :],  # 空推段数据
                     '上升段': data.iloc[_key_['上升段起点']:_key_['稳定段起点'], :],  # 上升段数据
                     '稳定段': data.iloc[_key_['稳定段起点']:_key_['稳定段终点'], :],  # 稳定段数据
                     '上升和稳定段': data.iloc[_key_['上升段起点']:_key_['稳定段终点'], :],  # 上升段和稳定段数据
                     '循环段': data}  # 整个循环段数据
        for Key in list(self.SUB_FOLDERS.keys()):
            save_path = os.path.join(self.out, self.SUB_FOLDERS[Key], _key_['name'])  # 数据保存路径
            save_data[Key].to_csv(save_path, index=False, encoding='gb2312')  # 保存各阶段的数据

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """对数据进行整体和细部分割"""
        self.check_parm()  # 检查参数是否正常
        self.create_split_Dir()  # 创建相关文件夹
        all_file = os.listdir(self.input)  # 获取输入文件夹下的所有文件名，并将其保存
        all_file.sort(key=lambda x: int(x[:5]))  # 对读取的文件列表进行重新排序
        for num, file in enumerate(all_file):  # 遍历每个文件
            time_S = time.time()  # 记录程序执行开始时间
            local_csv_path = os.path.join(self.input, file)  # 当前数据文件路径
            try:  # 尝试采用编码'gb2312'读取数据
                data = pd.read_csv(local_csv_path, encoding='gb2312')  # 读取循环段文件
            except UnicodeDecodeError:  # 尝试采用默认编码' UTF-8 '读取数据
                data = pd.read_csv(local_csv_path)  # 读取循环段文件
            self.check_index(list(data))  # 检查参数是否重复
            RS_Index = self.custom_get_RS(data, file)  # 调用自定义函数，获取空推、上升、稳定、下降的变化点
            if RS_Index is None:  # 优先调用自定义模块，若自定义模块未定义，则调用默认模块
                if self.partition == 'Average':  # 使用统计平均值模块进行划分
                    RS_Index = self.get_RS_index_average(data)  # 调用函数，获取空推、上升、稳定、下降的变化点
                if self.partition == 'Kernel Density':  # 使用核密度估计模块进行划分
                    RS_Index = self.get_RS_index_kernel(data)  # 调用函数，获取空推、上升、稳定、下降的变化点
            if RS_Index['稳定段起点'] - RS_Index['上升段起点'] >= 30 and RS_Index['稳定段终点'] - RS_Index['稳定段起点'] >= 50:
                RS_Index.update({'name': file})
                self.segment_save(data, RS_Index)  # 数据保存
            else:  # 若上升段和稳定段最小持续时长不满足要求，则将其归类为Unknown类型
                RS_Index = {'name': file, '上升段起点': 'Unknown', '稳定段起点': 'Unknown', '稳定段终点': 'Unknown'}
            self.write_index(RS_Index)  # 索引文件中内容写入
            self.detail(name=file, data=data, debug=self.debug, Parm=[self.parm[4]],
                        key=['上升段起点:', int(RS_Index['上升段起点']), '稳定段起点:', int(RS_Index['稳定段起点']),
                             '稳定段终点:', int(RS_Index['稳定段终点'])])  # DEBUG
            time_F = time.time()  # 记录程序执行结束时间
            self.show_info(use_time=time_F - time_S, file_num=num, file_sum=len(all_file))

    def get_RS_index_average(self, data: DataFrame) -> dict:
        """
        获取空推、上升、稳定、下降的关键点--(统计平均值)
        :param data: 循环段数据（DataFrame）
        :return: 内部段划分信息， 示例：_key_：{‘rise’：‘’，‘steadyS’：‘’，‘steadyE’：‘’}
        """
        try:
            if data.shape[0] < self.min_time:
                RS_index = {'上升段起点': 0, '稳定段起点': 0, '稳定段终点': 0}
                return RS_index
            T_mean = data.iloc[:, self.parm[5]].mean()
            mid_start_value = min(data.iloc[0:int(data.shape[0] / 3), self.parm[9]])  # 找前1/3的v_set最小值
            mid_point_start = 0  # 中点位置索引
            while data.iloc[mid_point_start, self.parm[9]] > mid_start_value:
                mid_point_start += 1
            V_set_mean = data.iloc[mid_point_start:-1, self.parm[9]].mean()  # 第一次求均值，用于索引中点
            mid_point = mid_point_start
            while data.iloc[mid_point, self.parm[9]] < V_set_mean:
                if mid_point > 0.7 * data.shape[0]:
                    mid_point = int(data.shape[0] * 0.2)
                else:
                    while data.iloc[mid_point, self.parm[9]] < V_set_mean or \
                            data.iloc[mid_point + 30, self.parm[9]] < V_set_mean:
                        mid_point += 1  # #############有修改
            steadyE = data.shape[0] - 1  # 稳定段结束位置索引
            while data.iloc[steadyE, self.parm[5]] <= T_mean:  # 判断稳定段结束点
                steadyE -= 1
            if mid_point and mid_point <= 0.7 * data.shape[0]:
                rise = mid_point  # 上升段开始位置处索引
                while abs(data.iloc[rise, self.parm[7]]) > 0 and rise > 10:  # 刀盘贯入度度索引（self.parm[7]） ########
                    rise -= 1
                steadyS = mid_point
                V_set_ = data.iloc[mid_point_start:steadyE, self.parm[9]]  # #改改改改改改改改改改改改改改改
                if steadyS + 60 < steadyE:
                    while V_set_[steadyS] - V_set_.mean() <= 0 or \
                            (max(V_set_[steadyS:steadyS + 60]) - min(V_set_[steadyS:steadyS + 60]) >= 0.02 * V_set_[
                                steadyS]):
                        steadyS += 1
                if steadyE - steadyS > 300:
                    steady_V_set_mean = V_set_.iloc[steadyS:steadyS + 300].mean()
                    steady_V_set_mean = min(0.95 * steady_V_set_mean, steady_V_set_mean - 3)
                else:
                    steady_V_set_mean = V_set_.iloc[steadyS:steadyE].mean()
                    steady_V_set_mean = min(0.95 * steady_V_set_mean, steady_V_set_mean - 3)
                while V_set_.iloc[steadyS] < steady_V_set_mean:  # 稳定段开始位置处的均值是否大于整个稳定段推进速度均值
                    steadyS += 1
                RS_index = {'上升段起点': rise, '稳定段起点': steadyS, '稳定段终点': steadyE}
            else:
                RS_index = {'上升段起点': 0, '稳定段起点': 0, '稳定段终点': 0}
        except Exception:
            RS_index = {'上升段起点': 0, '稳定段起点': 0, '稳定段终点': 0}
        return RS_index

    def get_RS_index_kernel(self, data: DataFrame) -> dict:
        """
        获取空推、上升、稳定、下降的关键点--(核密度估计)
        :param data: 循环段数据（DataFrame）
        :return: 内部段划分信息， 示例：_key_：{‘rise’：‘’，‘steadyS’：‘’，‘steadyE’：‘’}
        """

        def get_index(Data, ratio, Type='head'):
            raw_V, filter_V = copy.deepcopy(Data).values, scipy.signal.savgol_filter(Data, 19, 2)
            start, finish, Rise, Steady = 0, 0, 0, 0
            for row in range(3, len(raw_V) - 3):
                if max(raw_V[row - 3:row - 1]) <= 0.1 and raw_V[row] > 0.1:
                    Rise = start = row
                if raw_V[row] > 0.1 and max(raw_V[row + 1:row + 3]) <= 0.1 or row == len(raw_V) - 4:
                    Steady = finish = row
                if finish - start > ratio * len(raw_V) and finish - start >= 200:
                    kde = SMNP.KDEUnivariate(filter_V[Rise:Steady])  # 核密度估计
                    kde.fit(kernel='gau', bw="scott", fft=True, gridsize=200, cut=3)  # 核密度估计
                    new_KDE_mean_before = KDE_mean = float(kde.support[np.where(kde.density == np.max(kde.density))])
                    if Type == 'head':
                        while 0.8 * new_KDE_mean_before <= KDE_mean:
                            new_KDE_mean_before, Steady_before = KDE_mean, Steady
                            value = np.int64(filter_V > 0.95 * KDE_mean)
                            for i in range(Rise, len(value) - 50):
                                if filter_V[i] >= KDE_mean and sum(value[i:i + 50]) > 20 and 1.0 / 1.2 * max(
                                        filter_V[i:i + 50]) < KDE_mean < 1.0 / 0.8 * min(filter_V[i:i + 50]):
                                    Steady = i
                                    break
                            if Steady - Rise >= 200:
                                kde_new = SMNP.KDEUnivariate(filter_V[Rise:Steady])  # 核密度估计
                                kde_new.fit(kernel='gau', bw="scott", fft=True, gridsize=200, cut=3)  # 核密度估计
                                KDE_mean = float(kde_new.support[np.where(kde_new.density == np.max(kde_new.density))])
                            if Steady >= Steady_before or new_KDE_mean_before == KDE_mean:
                                break
                        return Rise, Steady
                    if Type == 'final':
                        for index, value in enumerate(filter_V[:Steady]):
                            if value >= 0.5 * KDE_mean:
                                return 0, index
            return 0, 0

        rise, steadyS = get_index(data.iloc[:, self.parm[4]], ratio=0.1, Type='head')
        _, steadyE = get_index(data.iloc[::-1, self.parm[4]], ratio=0.05, Type='final')
        return {'上升段起点': rise, '稳定段起点': steadyS, '稳定段终点': data.shape[0] - steadyE}

    def custom_get_RS(self, data: DataFrame, name) -> dict:
        """自定义获取空推、上升、稳定、下降的关键点模块，若定义了相关功能，则优先运行此功能，若未定义相关功能，则运行默认模块"""
        pass

    def show_info(self, use_time: float, file_num: int, file_sum: int) -> None:
        """
        实时输出程序运行状况
        :param use_time: 处理每个循环段数据花费的时间
        :param file_num: 当前的循环段编号
        :param file_sum: 总的循环段数量
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        cpu_percent = psutil.cpu_percent()  # CPU占用
        mem_percent = psutil.Process(os.getpid()).memory_percent()  # 内存占用
        self.Time_val.append(use_time)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(self.Time_val) / len(self.Time_val)  # 计算平均时间
        sum_time = round(sum(self.Time_val) / 3600, 3)  # 计算程序执行的总时间
        remain_time = round((mean_time * (file_sum - file_num - 1)) / 3600, 3)  # 预计剩余时间计算
        print('\r   [第%d个 / 共%d个]  ' % (file_num + 1, file_sum),
              '[所用时间%ds / 平均时间%ds]  ' % (int(use_time), int(mean_time)),
              '[CPU占用: %5.2f%% / 内存占用: %5.2f%%]  ' % (cpu_percent, mem_percent),
              '[累积运行时间: %6.3f小时 / 预计剩余时间: %6.3f小时]' % (sum_time, remain_time), end='')
        if file_num + 1 >= file_sum:
            Class = self.__class__.__name__  # 获取当前模块名称
            print('\r-> %s \033[0;32mData_Split completed, which took %6.3f hours\033[0m' % (Class, sum_time))

    @staticmethod  # 不强制要求传递参数
    def detail(name=None, data=None, key=None, Parm=None, debug=False):
        """展示程序细节信息"""
        if debug:
            Divide = []
            print("\033[0;33m{:·^100}\033[0m".format(name))
            for num, information in enumerate(key):
                if isinstance(information, int):
                    Divide.append(information)
                print('\033[0;33m%9s\033[0m' % information, end='')
            print('')
            x = [i for i in range(data.shape[0])]  # 'Time'
            plt.figure(figsize=(14, 7), dpi=120)  # 设置画布大小（10cm x 8cm）及分辨率（dpi=120）
            for parm, color in zip(Parm, ['b', 'g', 'r', 'y']):
                plt.plot(x, data.iloc[:, parm], label="%s" % list(data)[parm], color=color)
            plt.legend()
            plt.xlabel("时间/s", fontsize=15)
            for color, information in zip(['g', 'r', 'y', 'b'], Divide):
                plt.axvline(x=information, c=color, ls="-.")
            plt.show()
            plt.close()
            print("\033[0;33m{:·^100}\033[0m".format(name))


class TBM_FILTER(object):
    """
    数据降噪模块，完成对循环段数据滤波的功能
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输出路径，程序则抛出异常并终止运行
                索引文件保存路径（index_path），若不传入输出路径，程序则抛出异常并终止运行
    ****可选参数：关键参数名称（par_name），若传入参数，则仅对传入的参数进行降噪，若不传入参数，则对所有参数进行降噪
                程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run）， 默认为开启状态
    """
    PARAMETERS = ['None']  # 默认参数示例

    def __init__(self, input_path=None, out_path=None, index_path=None, parameter=None, debug=False, Run=True):
        """初始化必要参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.index = index_path  # 初始化索引文件路径
        self.parm = parameter  # 初始化待滤波参数名称
        """初始化可选参量"""
        self.debug = debug  # 调试/修复程序
        """初始化程序内部参量"""
        self.Time_val = []  # 初始化程序运行花费时间
        self.debug_number = 1  # Debug模式下循环段编号
        self.show_parm = True  # 将输入参数大音出来，便于进行核对
        None if not Run else self.main()  # 运行主程序

    def create_filter_dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):  # 保存滤波后数据的文件夹不存在
            os.mkdir(self.out)  # 创建相关文件夹
        else:  # 保存滤波后数据的文件夹存在
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        Class = self.__class__.__name__  # 获取当前模块名称
        if (not self.input) or (not self.out) or (not self.parm):  # 检查必要参数
            print('-> %s \033[0;31mThe input/output/index path or parameter are faulty, Please check!!!\033[0m' % Class)
            sys.exit()  # 抛出异常并终止程序

    def check_index(self, all_location: list) -> None:
        """
        判断数据中是否存在重复列名，若存在重复列名，则需要输入位置索引
        :param all_location: 原始数据的所有标签名称
        :return: 无
        """
        if reduce(lambda x, y: x * y, [type(name) == str for name in self.parm]):  # 判断是否为标签类型索引(名称)
            all_location = [name.split('.')[0] for name in all_location]  # 获取原始数据的标签名称
            mark = max([all_location.count(now_name) for now_name in self.parm])  # 检查标签名称中是否重复
            if mark == 1:  # 标签名称不重复
                self.parm = [all_location.index(now_name) for now_name in self.parm]
            else:
                maybe = [all_location.index(now_name) for now_name in self.parm]  # 可能的参数位置索引
                print('-> \033[0;31mLabel index(loc) is not available, Please enter location index(iloc)!!!\033[0m')
                print('   \033[0;31mLocation index(iloc) may be %s, You can verify that.\033[0m' % maybe)
                sys.exit()
        if self.show_parm:  # 将输入参数打印出来，便于进行核对
            self.show_parm = False
            Class = self.__class__.__name__  # 获取当前模块名称
            print('-> %s \033[0;33m参数名称: %s \033[0m' % (Class, [all_location[i] for i in self.parm]))

    @staticmethod  # 不强制要求传递参数
    def default_filter(data: DataFrame) -> ndarray:  # 规定data为DataFrame类型，返回值为 array 类型
        """
        巴特沃斯滤波器
        :param data: 循环段数据（DataFrame）
        :return: 滤波后的循环段数据（DataFrame）
        """
        return scipy.signal.savgol_filter(data, 19, 4)  # 巴特沃斯滤波器，滑动窗口长度为19，滤波阶数为4

    @staticmethod  # 不强制要求传递参数
    def custom_filter(data: DataFrame) -> ndarray:  # 规定data为DataFrame类型
        """自定义滤波器模块，若定义了相关功能，则优先运行此功能，若未定义相关功能，则运行默认滤波器模块"""
        pass

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """依次读取每个循环段数据"""
        self.check_parm()  # 检查参数是否正常
        self.create_filter_dir()  # 创建相关文件夹
        all_file = os.listdir(self.input)  # 获取输入文件夹下的所有循环段名称，并将其保存
        for num, file in enumerate(all_file):  # 遍历每个文件
            time_S = time.time()  # 记录程序执行开始时间
            local_csv_path = os.path.join(self.input, file)  # 当前循环段数据存放路径
            try:  # 尝试采用编码'gb2312'读取数据
                data = pd.read_csv(local_csv_path, encoding='gb2312')  # 读取循环段数据，编码'gb2312'
            except UnicodeDecodeError:  # 若采用编码'gb2312'读取数据失败，则尝试采用默认编码读取数据
                data = pd.read_csv(local_csv_path)  # 读取循环段数据，编码使用默认值
            if self.parm == ['']:  # 若传入待滤波参数名称，则仅对所传入的参数数据进行滤波
                self.parm = list(data)
            self.check_index(list(data))  # 检查参数是否重复
            if data.shape[0] > 50:  # 检查数据量是否满足滤波的最低要求
                for col in self.parm:
                    if not isinstance(data.iloc[0, col], str):  # 对非字符型的数据进行滤波
                        after_filter = self.custom_filter(data.iloc[:, col])  # 自定义参数滤波模块
                        if after_filter is None:
                            after_filter = self.default_filter(data.iloc[:, col])  # 默认参数滤波模块
                        data.iloc[:, col] = after_filter
            data.to_csv(os.path.join(self.out, file), index=False, encoding='gb2312')  # 保存滤波后的循环段数据
            filter_parm = ([list(data)[i] for i in self.parm] if len(self.parm) != len(list(data)) else ['全部参数'])
            self.detail(name=file, debug=self.debug, key=['滤波参数: '] + filter_parm)
            time_F = time.time()  # 记录程序执行结束时间
            self.show_info(use_time=time_F - time_S, file_num=num, file_sum=len(all_file))

    def show_info(self, use_time: float, file_num: int, file_sum: int) -> None:
        """
        实时输出程序运行状况
        :param use_time: 处理每个循环段数据花费的时间
        :param file_num: 当前的循环段编号
        :param file_sum: 总的循环段数量
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        cpu_percent = psutil.cpu_percent()  # CPU占用
        mem_percent = psutil.Process(os.getpid()).memory_percent()  # 内存占用
        self.Time_val.append(use_time)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(self.Time_val) / len(self.Time_val)  # 计算平均时间
        sum_time = round(sum(self.Time_val) / 3600, 3)  # 计算程序执行的总时间
        remain_time = round((mean_time * (file_sum - file_num - 1)) / 3600, 3)  # 预计剩余时间计算
        print('\r   [第%d个 / 共%d个]  ' % (file_num + 1, file_sum),
              '[所用时间%ds / 平均时间%ds]  ' % (int(use_time), int(mean_time)),
              '[CPU占用: %5.2f%% / 内存占用: %5.2f%%]  ' % (cpu_percent, mem_percent),
              '[累积运行时间: %6.3f小时 / 预计剩余时间: %6.3f小时]' % (sum_time, remain_time), end='')
        if file_num + 1 >= file_sum:
            Class = self.__class__.__name__  # 获取当前模块名称
            print('\r-> %s \033[0;32mData filter completed, which took %6.3f hours\033[0m' % (Class, sum_time))

    def detail(self, name=None, key=None, debug=False):
        """展示程序细节信息"""
        if debug:
            if self.debug_number == 1:
                print("\033[0;33m{:·^100}\033[0m".format(name))
                for num, information in enumerate(key):
                    print('\033[0;33m%9s\033[0m' % information, end='')
                print('')
                print("\033[0;33m{:·^100}\033[0m".format(name))
            self.debug_number += 1


class TBM_REPORT(object):
    """
    参数绘图模块，完成对循环段数据生成PDF的功能
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行;
                生成数据保存路径（out_path），若不传入输出路径，程序则抛出异常并终止运行;
                索引文件保存路径（index_path），若不传入输出路径，程序则抛出异常并终止运行;
                关键参数名称（par_name），若不传入参数，程序则抛出异常并终止运行;
    ****可选参数：添加封面（cover），可选选项为（True/False），默认为开启状态;
                添加目录（content），可选选项为（True/False），默认为开启状态;
                添加页眉（header），可选选项为（True/False），默认为开启状态;
                添加页脚（footer），可选选项为（True/False），默认为开启状态;
                添加水印（watermark），可选选项为（True/False），默认为开启状态;
                水印名称（watermark_info）;
                使用外部图片资源（pic_outer），可选选项为（True/False），默认为关闭状态;
                外部图片存放路径（input_pic）;
                程序调试/修复选项（debug），默认为关闭状态;
                直接运行程序（Run）， 默认为开启状态;
    """
    if os.path.exists('Resource/fonts/STSONG.TTF'):  # 判断字体文件是否存在
        pdfmetrics.registerFont(TTFont('SimSun', 'Resource/fonts/STSONG.TTF'))  # 读取所需要的字体文件
    else:
        print('->\033[0;31mFont file(STSONG.TTF) not found!!!\033[0m')
        sys.exit()  # 抛出异常并终止程序
    warnings.filterwarnings("ignore")  # 忽略警告信息
    ROCK_GRADE = {1: 'Ⅰ', 2: 'Ⅱ', 3: 'Ⅲ', 4: 'Ⅳ', 5: 'Ⅴ', 6: 'Ⅵ'}  # 定义围岩等级和与之对应的字符表达（字典类型）
    PARAMETERS = ['桩号', '日期', '推进位移', '刀盘转速', '推进速度', '刀盘扭矩',
                  '总推力', '刀盘贯入度', '刀盘转速设定值', '推进速度设定值']  # 默认参数示例
    INDEX_NAME = ['循环段', '上升段起点', '稳定段起点', '稳定段终点']  # 生成索引文件中标签信息
    RAW_INDEX = pd.DataFrame()  # 保存原始索引数据

    def __init__(self, input_path=None, out_path=None, index_path=None, parameter=None, input_pic=None,
                 cover=True, content=True, header=True, footer=True, watermark=True, pic_outer=False,
                 watermark_info=None, debug=False, Run=True):
        """初始化必要参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.index = index_path  # 初始化索引文件路径
        self.parm = parameter  # 参数列（参数名称）
        """初始化可选参量"""
        self.switch_cover = cover  # 初始化封面开关
        self.switch_content = content  # 初始化目录开关
        self.switch_footer = footer  # 初始化页脚开关
        self.switch_header = header  # 初始化页眉开关
        self.switch_watermark = watermark  # 初始化水印开关
        self.watermark_context = watermark_info  # 水印名称
        self.pic_outer = pic_outer  # 使用内部绘图模块添加图片资源
        self.input_pic = input_pic  # 初始化输入路径
        self.debug = debug  # 调试/修复程序
        """初始化程序内部参量"""
        self.size_font = 8  # 页面字体大小为8
        self.type_font = 'SimSun'  # 页面字体类型
        self.page = 1  # 用于存储当前页
        self.content_value = {}  # 用于存储目录信息
        self.cover_path = 'Resource\\images\\cover.png'  # 初始化封面图片路径
        self.local_time = [time.time(), time.time()]  # 记录当前时间
        self.Time_val = []  # 初始化程序运行花费时间
        self.show_parm = True  # 将输入参数大音出来，便于进行核对
        self.debug_number = 1  # Debug模式下页面编号
        None if not Run else self.main()  # 运行主程序

    def create_report_Dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):
            os.mkdir(self.out)  # 创建相关文件夹
        else:
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        Class = self.__class__.__name__  # 获取当前模块名称
        if (not self.input) or (not self.out) or (not sself.index) or \
                (not self.parm) or (len(self.parm) < len(self.PARAMETERS)):  # 检查必要参数
            print('-> %s \033[0;31mThe input/output/index path or parameter are faulty, Please check!!!\033[0m' % Class)
            sys.exit()  # 抛出异常并终止程序

    def check_index(self, all_location: list) -> None:
        """
        判断数据中是否存在重复列名，若存在重复列名，则需要输入位置索引
        :param all_location: 原始数据的所有标签名称
        :return: 无
        """
        if reduce(lambda x, y: x * y, [type(name) == str for name in self.parm]):  # 判断是否为标签类型索引(名称)
            all_location = [name.split('.')[0] for name in all_location]  # 获取原始数据的标签名称
            mark = max([all_location.count(now_name) for now_name in self.parm])  # 检查标签名称中是否重复
            if mark == 1:  # 标签名称不重复
                self.parm = [all_location.index(now_name) for now_name in self.parm]
            else:
                maybe = [all_location.index(now_name) for now_name in self.parm]  # 可能的参数位置索引
                print('-> \033[0;31mLabel index(loc) is not available, Please enter location index(iloc)!!!\033[0m')
                print('   \033[0;31mLocation index(iloc) may be %s, You can verify that.\033[0m' % maybe)
                sys.exit()
        if self.show_parm:  # 将输入参数打印出来，便于进行核对
            self.show_parm = False
            Class = self.__class__.__name__  # 获取当前模块名称
            print('-> %s \033[0;33m参数名称: %s \033[0m' % (Class, [all_location[i] for i in self.parm]))

    def add_footer_info(self, Obj) -> None:  # 规定返回值无类型限定/无返回值:
        """
        添加页脚信息
        :param Obj: Canvas容器
        :return: 无
        """
        sheet = Table([['Page%d' % self.page]], colWidths=[15 * mm], rowHeights=[5 * mm],  # 绘制页码框
                      style={("FONT", (0, 0), (-1, -1), self.type_font, self.size_font),  # 设置页码字体类型和大小
                             ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')})  # 页码居中
        sheet.wrapOn(Obj, 0, 0)  # 将页码框添加到Canvas中
        sheet.drawOn(Obj, 97.5 * mm, 12 * mm)  # 将页码框添加到Canvas中

    def add_header_info(self, Obj) -> None:
        """
        添加页眉信息
        :param Obj: Canvas容器
        :return: 无
        """
        Obj.setStrokeColor(colors.royalblue)  # 指定边缘颜色
        Obj.setFillColor(colors.royalblue)  # 指定填充颜色
        Obj.line(20 * mm, 277 * mm, 190 * mm, 277 * mm)  # 绘制一条线
        Obj.rect(25 * mm, 280 * mm, 7 * mm, 7 * mm, fill=1)  # 绘制一个矩形
        Obj.drawString(35 * mm, 282 * mm, 'REPORT')  # 添加页眉信息
        current_date = datetime.datetime.now().strftime('%Y.%m')
        sheet = Table([['%s  <数据预处理>  |  %d' % (current_date, self.page)]], colWidths=[50 * mm], rowHeights=[4 * mm],
                      style={("FONT", (0, 0), (-1, -1), self.type_font, self.size_font + 1),  # 设置字体类型和大小
                             ("TEXTCOLOR", (0, 0), (0, 0), colors.royalblue),  # 设置字体颜色
                             ('ALIGN', (0, 0), (-1, -1), 'RIGHT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')})  # 字体右对齐
        sheet.wrapOn(Obj, 0, 0)  # 将页码框添加到Canvas中
        sheet.drawOn(Obj, 140 * mm, 281 * mm)  # 将页码框添加到Canvas中

    def add_watermark_info(self, Obj) -> None:
        """
        添加水印信息
        :param Obj: Canvas容器
        :return: 无
        """
        Obj.setFont(self.type_font, self.size_font + 17)  # 设置字体类型及大小
        Obj.rotate(40)  # 旋转45度，坐标系被旋转
        Obj.setFillColorRGB(0, 0, 0.6)  # 指定填充颜色
        Obj.setFillAlpha(0.2)  # 设置透明度，0为透明，1为不透明
        Obj.drawString(55 * mm, 4 * mm, self.watermark_context)  # 添加水印名称1
        Obj.drawString(185 * mm, 4 * mm, self.watermark_context)  # 添加水印名称2
        Obj.drawString(123 * mm, 85 * mm, self.watermark_context)  # 添加水印名称3
        Obj.drawString(250 * mm, 85 * mm, self.watermark_context)  # 添加水印名称4

    def add_cover_info(self, Obj) -> None:
        """
        添加封面信息
        :param Obj: Canvas容器
        :return: 无
        """
        Obj.setStrokeColor(colors.skyblue)  # 指定边缘颜色
        Obj.setFillColor(colors.skyblue)  # 指定填充颜色
        Obj.roundRect(64 * mm, 53 * mm, 80 * mm, 10 * mm, fill=1, radius=10)  # 绘制一个矩形
        current_year = datetime.datetime.now().strftime('%Y')
        sheet = Table(data=[['%s' % current_year], ['TBM数据预处理报告书'], ['TBM DATA PREPROCESSING REPORT'], ['**机构信息**']],
                      colWidths=[150 * mm], rowHeights=[17 * mm, 17 * mm, 17 * mm, 17 * mm],  # 创建表格并写入信息
                      style={("FONT", (0, 0), (0, 0), self.type_font, 37),  # 字体类型
                             ("FONT", (0, 1), (0, 1), self.type_font, 30),  # 字体类型
                             ("FONT", (0, 2), (0, 2), self.type_font, 20),  # 字体类型
                             ("FONT", (0, 3), (0, 3), self.type_font, 15),  # 字体类型
                             ("TEXTCOLOR", (0, 0), (0, 0), colors.skyblue),  # 字体颜色为黑色
                             ("TEXTCOLOR", (0, 1), (0, 1), colors.black),  # 字体颜色为黑色
                             ("TEXTCOLOR", (0, 2), (0, 2), colors.gray),  # 字体颜色为黑色
                             ("TEXTCOLOR", (0, 3), (0, 3), colors.black),  # 字体颜色为黑色
                             ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')})  # 左右上下居中
        sheet.wrapOn(Obj, 0, 0)  # 将页码框添加到Canvas中
        sheet.drawOn(Obj, 30 * mm, 50 * mm)  # 将页码框添加到Canvas中
        if os.path.exists(self.cover_path):  # 若路径有效，则添加封面图片
            Obj.drawImage(image=self.cover_path, x=20 * mm, y=120 * mm, width=170 * mm, height=120 * mm, anchor='c')

    def add_content_info(self, Obj, value: dict, loc: int) -> None:  # 规定返回值无类型限定/无返回值
        """
        添加目录信息
        :param Obj:  Canvas容器
        :param value: 所要添加的单条目录信息，示例{'beg': '', 'end': '', 'stake': '', 'page': ''}
        :param loc: 所要添加的单条目录的放置位置（范围 1 ~ 50）
        :return: 无
        """
        table_w = [[136 * mm], [16 * mm, 3 * mm, 10 * mm, 95 * mm, 12 * mm]]  # 表格列宽信息
        table_h = [[8 * mm], [5.1 * mm]]  # 表格行高信息
        table_y = [280 * mm] + [(274.9 - 5.1 * i) * mm for i in range(50)]  # 表格位置信息
        inf = [['CATALOGUE'], ['%s-%s' % (value['beg'], value['end']), '',
                               value['stake'], '.' * 150, 'Page%s' % value['page']]]  # 表格内容信息
        if loc == 1:
            sheet = Table([inf[0]], colWidths=table_w[0], rowHeights=table_h[0],
                          style={("FONT", (0, 0), (-1, -1), self.type_font, self.size_font),  # 目录正文字体
                                 ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),  # 字体颜色
                                 ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')})  # 内容居中
            sheet.wrapOn(Obj, 0, 0)  # 将表格添加到Canvas中
            sheet.drawOn(Obj, 36 * mm, table_y[0])  # 将表格添加到Canvas中
        sheet = Table([inf[1]], colWidths=table_w[1], rowHeights=table_h[1],
                      style={("FONT", (0, 0), (-1, -1), self.type_font, self.size_font),  # 目录正文字体
                             ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),  # 字体颜色
                             ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')})  # 内容居中
        sheet.wrapOn(Obj, 0, 0)  # 将表格添加到Canvas中
        sheet.drawOn(Obj, 36 * mm, table_y[loc])  # 将表格添加到Canvas中

    def add_text_info(self, Obj, value: list, loc: int) -> None:  # 规定返回值无类型限定/无返回值
        """
        添加正文信息
        :param Obj:  Canvas容器
        :param value: 所要添加的单条正文信息
        :param loc: 所要添加的单条正文的放置位置（范围 1 ~ 6）
        :return: 无
        """
        table_x = [20 * mm, 105 * mm, 20 * mm, 105 * mm, 20 * mm, 105 * mm]  # 表格x位置信息
        table_y = [189 * mm, 189 * mm, 105 * mm, 105 * mm, 21 * mm, 21 * mm]  # 表格y位置信息
        value.append(['' for _ in range(6)])  #
        sheet = Table(data=value,
                      colWidths=[13 * mm, 9 * mm, 12 * mm, 13 * mm, 13 * mm, 25 * mm],  # 表格列宽信息
                      rowHeights=[8 * mm, 8 * mm, 68 * mm],  # 表格行高信息
                      style={("FONT", (0, 0), (-1, -1), self.type_font, self.size_font),  # 字体类型
                             ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),  # 字体颜色为黑色
                             ('SPAN', (0, 2), (5, 2)),  # 合并单元格
                             ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # 左右上下居中
                             ('INNERGRID', (0, 0), (-1, -1), 0.7, colors.black),  # 显示内部框线
                             ('BOX', (0, 0), (-1, -1), 0.7, colors.black)})  # 显示外部框线
        sheet.wrapOn(Obj, 0, 0)  # 将表格添加到Canvas中
        sheet.drawOn(Obj, table_x[loc], table_y[loc])  # 将表格添加到Canvas中

    def add_pic_info(self, Obj, name: str, value: 'list | DataFrame', loc: int) -> None:  # 规定返回值无类型限定/无返回值
        """
        添加图片信息
        :param Obj: Canvas容器
        :param name: 循环段名称
        :param value: 循环段数据/循环段对于的图片路径
        :param loc: 所要添加的图片的放置位置（范围 1 ~ 6）
        :return: 无
        """
        pic_x = [21 * mm, 107 * mm, 21 * mm, 107 * mm, 21 * mm, 107 * mm]  # 图片x位置信息
        pic_y = [190 * mm, 190 * mm, 106 * mm, 106 * mm, 22 * mm, 22 * mm]  # 图片y位置信息
        if isinstance(value, pd.DataFrame):
            img = self.draw_pic(name, value)  # 使用内置绘图模块进行绘图
            Obj.drawImage(image=img, x=pic_x[loc], y=pic_y[loc], width=82 * mm, height=66 * mm, anchor='c')
        elif isinstance(value, str):
            img = value  # 添加外部图片资源
            if os.path.exists(img):  # 若路径有效，则添加图片
                Obj.drawImage(image=img, x=pic_x[loc], y=pic_y[loc], width=82 * mm, height=66 * mm, anchor='c')

    def draw_Canvas(self, pdf_text, pdf_content, data: DataFrame, cycle: int, name: str, All: list, end: bool) -> None:
        """
        调用各模块
        :param pdf_text: 存放正文pdf的Canvas
        :param pdf_content: 存放目录pdf的Canvas
        :param data: 循环段数据
        :param cycle: 循环段编号
        :param name: 循环段名称
        :param All: 所有循环段名称组成的列表
        :param end: 程序结束标志
        :return: 无
        """
        data_np = data.iloc[:, self.parm[:3]].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
        text_value = [['Number', ('%00005d' % (cycle + 1)),  # 获取循环段编号(Num)
                       'Start No', '%sm' % round(data_np[0][0], 1),  # 获取桩号记录
                       'Start Time', data_np[0][1]],  # 获取循环段开始时间
                      ['Rock mass', '---',  # 获取围岩等级(Rock_Mass)
                       'Length', '%4.2fm' % round((data_np[-1][2] - data_np[0][2]) / 1000, 2),  # 掘进长度
                       'End Time', data_np[-1][1]]]  # 获取结束时间
        self.add_text_info(pdf_text, text_value, (cycle + 1) % 6 - 1)  # 添加正文信息
        pic_val = os.path.join(self.input_pic, name[:-3] + 'png') if self.pic_outer else data  # 添加图片变量信息（数据/路径）
        self.add_pic_info(pdf_text, name, pic_val, (cycle + 1) % 6 - 1)  # 添加图片信息
        if (cycle + 1) % 6 == 1:
            self.local_time[0] = time.time()  # 记录程序执行开始时间
            self.content_value.update({'beg': text_value[0][1], 'stake': text_value[0][3][:-1], 'page': self.page})
        if (cycle + 1) % 6 == 0 or end:
            inf = ['第%d页' % self.page, '\n图片来源:', '外部图片' if self.pic_outer else '内部图片', '\n文件列表:'] + \
                  ['\n' + name for name in All[6 * (self.page - 1): ((6 * self.page) if not end else len(All))]]
            self.detail(name='Create PDF', debug=self.debug, end=end, key=inf)  # 展示细节
            self.content_value.update({'end': text_value[0][1]})  # 目录信息添加
            if self.switch_content:
                self.add_content_info(pdf_content, self.content_value, self.page % 50)  # 添加目录信息
            None if not self.switch_header else self.add_header_info(pdf_text)  # 添加页眉信息
            None if not self.switch_footer else self.add_footer_info(pdf_text)  # 添加页脚信息
            None if not self.switch_watermark else self.add_watermark_info(pdf_text)  # 添加水印信息
            pdf_text.showPage()  # 正文新增一页
            self.local_time[1] = time.time()  # 记录程序执行结束时间
            self.show_info(use_time=self.local_time[1] - self.local_time[0], file_num=self.page,
                           file_sum=math.ceil(len(All) / 6))
            self.page += 1  # 页脚页码自增
        if (cycle + 1) % 300 == 0 or end:
            pdf_content.showPage()  # 目录新增一页

    def draw_pic(self, name: str, data: DataFrame) -> ImageReader:
        """
        内部绘图模块
        :param name: 循环段名称
        :param data: 循环段数据
        :return: 绘制好的图片
        """
        Mark = self.get_index({'name': name})
        Plt = self.custom_plot(data, Mark)  # 自定义参数绘图模块
        if Plt is None:
            Plt = self.default_plot(data, Mark)  # 默认参数绘图模块
        Image_data = BytesIO()  # 将绘制的画布临时保存至内存中
        Plt.savefig(Image_data, bbox_inches='tight', format='png')
        Plt.close()  # 关闭画布
        Image_data.seek(0)  # rewind the data
        return ImageReader(Image_data)

    def get_index(self, info: dict) -> dict:
        """
        获取索引文件记录
        :param info: 包含循环段名称的dict，其中至少含有{‘name’：‘’}
        :return: 所有的上升段稳定段变化点索引值
        """
        try:  # 尝试读取索引文件，若索引文件存在，则将['循环段', '上升段起点', '稳定段起点', '稳定段终点']保存至Index_value中
            if self.RAW_INDEX.empty:  # 索引文件行位置记录
                self.RAW_INDEX = pd.read_csv(self.index, index_col=0, encoding='gb2312')  # 读取索引文件
                self.RAW_INDEX = self.RAW_INDEX.loc[:, self.INDEX_NAME[1:]]  # 将关键点保存至Index_value
            mark = {} if self.RAW_INDEX is None else {'上升段起点': self.RAW_INDEX['上升段起点'][int(info['name'][:5])],
                                                      '稳定段起点': self.RAW_INDEX['稳定段起点'][int(info['name'][:5])],
                                                      '稳定段终点': self.RAW_INDEX['稳定段终点'][int(info['name'][:5])]}
        except (FileNotFoundError, KeyError, IndexError, TypeError):  # 若索引文件存在，则令Index_value为空[]
            mark = {}
        return mark

    def default_plot(self, data: DataFrame, _key_: dict) -> pyplot:  # 规定_key_为字典类型（dict）,返回值为绘制好的plt
        """
        完成掘进参数的绘图与保存
        :param data: 循环段数据
        :param _key_: 循环段对应的关键点索引值
        :return: 绘制好的图片
        """
        x = [i for i in range(data.shape[0])]  # 'Time'
        y_n = data.iloc[:, self.parm[3]]  # '刀盘转速'
        y_n_set = data.iloc[:, self.parm[8]]  # '刀盘转速设定'
        y_V = data.iloc[:, self.parm[4]]  # '推进速度'
        y_V_set = data.iloc[:, self.parm[9]]  # '推进速度设定'
        y_T = data.iloc[:, self.parm[5]]  # '刀盘总扭矩'
        y_F = data.iloc[:, self.parm[6]]  # '推进总推力'
        plt.figure(figsize=(10, 8), dpi=120)  # 设置画布大小（10cm x 8cm）及分辨率（dpi=120）
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
        if _key_:  # 如果索引文件中空推段、上升段和稳定段的变化点存在，则在图中绘出
            for name, value in zip(_key_.keys(), _key_.values()):
                if value != 'Unknown':
                    plt.axvline(x=int(value), c="r", ls="-.")
        return plt

    def custom_plot(self, data: DataFrame, _key_: dict) -> pyplot:  # 规定_key_为字典类型（dict）,返回值为绘制好的plt
        """自定义绘图模块，若定义了相关功能，则优先运行此功能，若未定义相关功能，则运行默认绘图模块"""
        pass

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """读取数据，并将数据转化为可识别的类型"""
        self.check_parm()  # 检查参数是否正常
        self.create_report_Dir()  # 创建相关文件夹
        pdf = {'cover': Canvas(filename=os.path.join(self.out, 'cover.pdf'), bottomup=1, pageCompression=1),  # 创建封面
               'content': Canvas(filename=os.path.join(self.out, 'content.pdf'), bottomup=1, pageCompression=1),  # 创建目录
               'text': Canvas(filename=os.path.join(self.out, 'text.pdf'), bottomup=1, pageCompression=1)}  # 创建正文
        all_file = os.listdir(self.input)  # 获取循环段列表
        all_file.sort(key=lambda x: int(x[:5]))  # 对读取的文件列表进行重新排序
        for num, file in enumerate(all_file):
            finish = False if num != len(all_file) - 1 else True  # 程序结束标志
            try:  # 尝试采用编码'gb2312'读取数据
                data = pd.read_csv(os.path.join(self.input, file), encoding='gb2312')  # 读取循环段数据，编码'gb2312'
            except UnicodeDecodeError:  # 若采用编码'gb2312'读取数据失败，则尝试采用默认编码读取数据
                data = pd.read_csv(os.path.join(self.input, file))  # 读取循环段数据，编码使用默认值
            self.check_index(list(data))  # 检查参数是否重复
            self.draw_Canvas(pdf['text'], pdf['content'], data, num, file, all_file, finish)
        None if not self.switch_cover else self.add_cover_info(pdf['cover'])  # 添加目录信息
        pdf['text'].save(), pdf['content'].save(), pdf['cover'].save()  # pdf保存
        self.MergePDF([os.path.join(self.out, 'cover.pdf'), os.path.join(self.out, 'content.pdf'),
                       os.path.join(self.out, 'text.pdf')])  # 合并目录和正文

    def MergePDF(self, pdf_path: list) -> None:  # 规定返回值无类型限定/无返回值
        """
        合并目录和正文成为一个PDF
        :param pdf_path: 带合并的 pdf路径，以列表形式存放
        :return: 无
        """
        merger = PdfFileMerger()  # 调用PDF编辑的类
        for file in pdf_path:
            merger.append(PdfFileReader(file))  # 合并pdf文件
            os.remove(file)  # 删除合并后的pdf文件
        merger.write(os.path.join(self.out, 'TBM-Data.pdf'))  # 将合并后的pdf写入到新文件
        merger.close()  # 关闭文件

    def show_info(self, use_time: float, file_num: int, file_sum: int) -> None:
        """
        实时输出程序运行状况
        :param use_time: 处理每个循环段数据花费的时间
        :param file_num: 当前的循环段编号
        :param file_sum: 总的循环段数量
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        cpu_percent = psutil.cpu_percent()  # CPU占用
        mem_percent = psutil.Process(os.getpid()).memory_percent()  # 内存占用
        self.Time_val.append(use_time)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(self.Time_val) / len(self.Time_val)  # 计算平均时间
        sum_time = round(sum(self.Time_val) / 3600, 3)  # 计算程序执行的总时间
        remain_time = round((mean_time * (file_sum - file_num - 1)) / 3600, 3)  # 预计剩余时间计算
        print('\r   [第%d个 / 共%d个]  ' % (file_num + 1, file_sum),
              '[所用时间%ds / 平均时间%ds]  ' % (int(use_time), int(mean_time)),
              '[CPU占用: %5.2f%% / 内存占用: %5.2f%%]  ' % (cpu_percent, mem_percent),
              '[累积运行时间: %6.3f小时 / 预计剩余时间: %6.3f小时]' % (sum_time, remain_time), end='')
        if file_num >= file_sum:
            Class = self.__class__.__name__  # 获取当前模块名称
            print('\r-> %s \033[0;32mCreate PDF completed, which took %6.3f hours\033[0m' % (Class, sum_time))

    def detail(self, name=None, key=None, end=False, debug=False):
        """展示程序细节信息"""
        if debug:
            if self.debug_number == 1:
                print("\033[0;33m{:·^100}\033[0m".format(name))
            for num, information in enumerate(key):
                print('\033[0;33m%-9s\033[0m' % str(information), end='')
            print('')
            if end:
                print("\033[0;33m{:·^100}\033[0m".format(name))
            self.debug_number += 1


class TBM_PLOT(object):
    """
    参数绘图模块，完成对循环段数据进行绘图的功能
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输出路径，程序则抛出异常并终止运行
                索引文件保存路径（index_path），若不传入输出路径，程序则抛出异常并终止运行
                关键参数名称（par_name），若不传入参数，程序则抛出异常并终止运行（可对部分参数进行绘图）
    ****可选参数：生成图片的高度（单位：mm）（height），默认10cm；
                生成图片的宽度（单位：mm）（weight），默认8cm；
                生成图片的分辨率（单位：dpi）（dpi），默认120dpi；
                生成图片的格式（Format），默认png；
                展示生成的图片（show）， 默认不展示生成图片；
                程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run），默认为开启状态
    """
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置字体
    plt.rcParams['axes.unicode_minus'] = False  # 坐标轴的负号正常显示
    plt.rcParams.update({'font.size': 17})  # 设置字体大小
    warnings.filterwarnings("ignore")  # 忽略警告信息
    PARAMETERS = ['桩号', '日期', '推进位移', '刀盘转速', '推进速度', '刀盘扭矩',
                  '总推力', '刀盘贯入度', '刀盘转速设定值', '推进速度设定值']  # 默认参数示例
    INDEX_NAME = ['循环段', '上升段起点', '稳定段起点', '稳定段终点']  # 生成索引文件中标签信息
    RAW_INDEX = pd.DataFrame()  # 保存原始索引数据

    def __init__(self, input_path=None, out_path=None, index_path=None, parameter=None, height=10,
                 weight=8, dpi=120, Format='png', show=False, debug=False, Run=True):
        """初始化必要参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.index = index_path  # 初始化索引文件路径
        self.parm = parameter  # 掘进状态判定参数
        """初始化可选参量"""
        self.size = (height, weight)  # 图片大小（10*cm，8*cm）
        self.dpi = dpi  # 像素dpi=120
        self.format = Format  # 输出图片的格式
        self.show = show  # 是否展示图片
        self.debug = debug  # 调试/修复程序
        """初始化程序内部参量"""
        self.Time_val = []  # 初始化程序运行花费时间
        self.show_parm = True  # 将输入参数大音出来，便于进行核对
        None if not Run else self.main()  # 运行主程序

    def create_pic_dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):  # 保存图片的文件夹不存在
            os.mkdir(self.out)  # 创建相关文件夹
        else:  # 保存图片的文件夹存在
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        Class = self.__class__.__name__  # 获取当前模块名称
        if (not self.input) or (not self.out) or (not self.index) or \
                (not self.parm) or (len(self.parm) < len(self.PARAMETERS)):  # 检查必要参数
            print('-> %s \033[0;31mThe input/output/index path or parameter are faulty, Please check!!!\033[0m' % Class)
            sys.exit()  # 抛出异常并终止程序

    def check_index(self, all_location: list) -> None:
        """
        判断数据中是否存在重复列名，若存在重复列名，则需要输入位置索引
        :param all_location: 原始数据的所有标签名称
        :return: 无
        """
        if reduce(lambda x, y: x * y, [type(name) == str for name in self.parm]):  # 判断是否为标签类型索引(名称)
            all_location = [name.split('.')[0] for name in all_location]  # 获取原始数据的标签名称
            mark = max([all_location.count(now_name) for now_name in self.parm])  # 检查标签名称中是否重复
            if mark == 1:  # 标签名称不重复
                self.parm = [all_location.index(now_name) for now_name in self.parm]
            else:
                maybe = [all_location.index(now_name) for now_name in self.parm]  # 可能的参数位置索引
                print('-> \033[0;31mLabel index(loc) is not available, Please enter location index(iloc)!!!\033[0m')
                print('   \033[0;31mLocation index(iloc) may be %s, You can verify that.\033[0m' % maybe)
                sys.exit()
        if self.show_parm:  # 将输入参数打印出来，便于进行核对
            self.show_parm = False
            Class = self.__class__.__name__  # 获取当前模块名称
            print('-> %s \033[0;33m参数名称: %s \033[0m' % (Class, [all_location[i] for i in self.parm]))

    def default_plot(self, data: DataFrame, _key_: dict) -> pyplot:  # 规定_key_为字典类型（dict）,返回值为绘制好的plt
        """
        完成掘进参数的绘图
        :param data: 循环段数据（DataFrame）
        :param _key_: 内部段划分信息
        :return: 绘制好的图片
        """
        x = [i for i in range(data.shape[0])]  # 'Time'
        y_n = data.iloc[:, self.parm[3]]  # '刀盘转速'
        y_n_set = data.iloc[:, self.parm[8]]  # '刀盘转速设定'
        y_V = data.iloc[:, self.parm[4]]  # '推进速度'
        y_V_set = data.iloc[:, self.parm[9]]  # '推进速度设定'
        y_T = data.iloc[:, self.parm[5]]  # '刀盘总扭矩'
        y_F = data.iloc[:, self.parm[6]]  # '推进总推力'
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
        if _key_:  # 如果索引文件中空推段、上升段和稳定段的变化点存在，则在图中绘出
            for name, value in zip(_key_.keys(), _key_.values()):
                if value != 'Unknown':
                    plt.axvline(x=int(value), c="r", ls="-.")
        return plt

    def custom_plot(self, data: DataFrame, _key_: dict) -> pyplot:  # 规定_key_为字典类型（dict）,返回值为绘制好的plt
        """自定义绘图模块，若定义了相关功能，则优先运行此功能，若未定义相关功能，则运行默认绘图模块"""
        pass

    def get_index(self, info: dict) -> dict:
        """
        获取索引文件记录
        :param info: 循环段信息，info中至少含有{‘name’：‘’}
        :return: 内部段划分的所有信息
        """
        try:  # 尝试读取索引文件，若索引文件存在，则将['循环段', '上升段起点', '稳定段起点', '稳定段终点']保存至Index_value中
            if self.RAW_INDEX.empty:  # 索引文件行位置记录
                self.RAW_INDEX = pd.read_csv(self.index, index_col=0, encoding='gb2312')  # 读取索引文件
                self.RAW_INDEX = self.RAW_INDEX.loc[:, self.INDEX_NAME[1:]]  # 将关键点保存至Index_value
            mark = {} if self.RAW_INDEX is None else {'上升段起点': self.RAW_INDEX['上升段起点'][int(info['name'][:5])],
                                                      '稳定段起点': self.RAW_INDEX['稳定段起点'][int(info['name'][:5])],
                                                      '稳定段终点': self.RAW_INDEX['稳定段终点'][int(info['name'][:5])]}
        except (FileNotFoundError, KeyError, IndexError, TypeError):  # 若索引文件存在，则令Index_value为空[]
            mark = {}
        return mark

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """掘进参数可视化"""
        self.check_parm()  # 检查参数是否正常
        self.create_pic_dir()  # 创建相关文件夹
        all_file = os.listdir(self.input)  # 获取输入文件夹下的所有文件名称，并将其保存
        all_file.sort(key=lambda x: int(x[:5]))  # 对读取的文件列表进行重新排序
        for num, file in enumerate(all_file):  # 遍历每个文件
            time_S = time.time()  # 记录程序执行开始时间
            local_csv_path = os.path.join(self.input, file)  # 当前循环段数据存放路径
            try:  # 尝试采用编码'gb2312'读取数据
                data = pd.read_csv(local_csv_path, encoding='gb2312')  # 读取循环段数据，编码'gb2312'
            except UnicodeDecodeError:  # 若采用编码'gb2312'读取数据失败，则尝试采用默认编码读取数据
                data = pd.read_csv(local_csv_path)  # 读取循环段数据，编码使用默认值
            self.check_index(list(data))  # 检查参数是否重复
            Mark = self.get_index({'name': file})
            Plt = self.custom_plot(data, Mark)  # 自定义参数绘图模块
            if Plt is None:
                Plt = self.default_plot(data, Mark)  # 默认参数绘图模块
            pic_save_path = os.path.join(self.out, file[:-3] + self.format)  # 图片保存路径
            Plt.savefig(pic_save_path, dpi=self.dpi, format=self.format, bbox_inches='tight')  # 图片保存
            None if not self.show else Plt.show()  # 展示绘图
            Plt.close()  # 关闭画布，以释放内存
            time_F = time.time()  # 记录程序执行结束时间
            self.show_info(use_time=time_F - time_S, file_num=num, file_sum=len(all_file))

    def show_info(self, use_time: float, file_num: int, file_sum: int) -> None:
        """
        实时输出程序运行状况
        :param use_time: 处理每个循环段数据花费的时间
        :param file_num: 当前的循环段编号
        :param file_sum: 总的循环段数量
        :return: 无
        """
        if self.debug:  # 若为调试模式，则不向索引文件写入内容
            return None
        cpu_percent = psutil.cpu_percent()  # CPU占用
        mem_percent = psutil.Process(os.getpid()).memory_percent()  # 内存占用
        self.Time_val.append(use_time)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(self.Time_val) / len(self.Time_val)  # 计算平均时间
        sum_time = round(sum(self.Time_val) / 3600, 3)  # 计算程序执行的总时间
        remain_time = round((mean_time * (file_sum - file_num - 1)) / 3600, 3)  # 预计剩余时间计算
        print('\r   [第%d个 / 共%d个]  ' % (file_num + 1, file_sum),
              '[所用时间%ds / 平均时间%ds]  ' % (int(use_time), int(mean_time)),
              '[CPU占用: %5.2f%% / 内存占用: %5.2f%%]  ' % (cpu_percent, mem_percent),
              '[累积运行时间: %6.3f小时 / 预计剩余时间: %6.3f小时]' % (sum_time, remain_time), end='')
        if file_num + 1 >= file_sum:
            Class = self.__class__.__name__  # 获取当前模块名称
            print('\r-> %s \033[0;32mDrawing pic completed, which took %6.3f hours\033[0m' % (Class, sum_time))


class MESSAGE(object):
    """TK图像用户界面"""
    window_weight, window_height, window_x, window_y = 700, 760, 500, 10  # 窗口大小与位置
    Text = ('宋体', 11)  # 界面字体大小
    Program_description = {'Cycle': "1、两循环段间时间间隔建议设置在 (1 - 100)s\n"
                                    "2、掘进长度下限值建议设置在 (0 - 100)mm\n"
                                    "3、掘进速度下限值下限值建议设置在 (0 - 100)mm/min\n"
                                    "4、自定义文件读取模块 custom_read()",
                           'EXTRACT': "无",
                           'CLASS': "1、工程类型可设置为：引松 / 引额-361 / 引额-362 / 引绰-667 / 引绰-668\n"
                                    "2、最小掘进长度可设置为：(1 - 300)mm\n"
                                    "3、推进速度上限值可设置为：引松取 120mm/min / 额河取 200mm/min\n"
                                    "4、推进速度设定变化幅可设置为：(1 - 20)\n"
                                    "5、数据缺失率设置为：(1 - 20)%\n"
                                    "6、自定义获取空推、上升、稳定、下降的关键点模块 custom_get_RS()",
                           'CLEAN': "1、推进速度上限值可设置为：引松取 120mm/min / 额河取 200mm/min",
                           'MERGE': "1、若索引文件存在，则根据索引文件合并文件",
                           'SPLIT': "1、最小掘进长度可设置为：(1 - 300)mm\n"
                                    "2、最小时间记录可设置为：(50 - 500)s\n"
                                    "3、自定义获取空推、上升、稳定、下降的关键点模块 custom_get_RS()",
                           'FILTER': "1、自定义滤波器模块 custom_filter()",
                           'PLOT': "1、图片高度可设置为：(10 - 90)mm\n"
                                   "2、图片宽度可设置为：(10 - 160)mm\n"
                                   "3、图片分辨率可设置为：(60 - 200)dpi\n"
                                   "4、图片类型可设置为：eps,jpeg,jpg,pdf,pgf,png,ps,raw,svg,tif\n"
                                   "5、自定义绘图模块custom_plot()",
                           'REPORT': "1、若使用外部图片资源，则需保证图片名称和循环段名称一致\n"
                                     "2、内部自定义绘图模块 custom_plot()"}

    def __init__(self):
        self.root = Tk()
        self.Dir = {'Cycle': ['', '[ TBM_CYCLE ]-AllDataSet'],
                    'Extract': ['[ TBM_CYCLE ]-AllDataSet', '[ TBM_EXTRACT ]-KeyDataSet'],
                    'Class': ['[ TBM_EXTRACT ]-KeyDataSet', '[ TBM_CLASS ]-Class-Data'],
                    'Clean': ['[ TBM_CLASS ]-Class-Data', '[ TBM_CLEAN ]-Clean-Data'],
                    'Merge': ['[ TBM_CLEAN ]-Clean-Data', '[ TBM_MERGE ]-ML-Data'],
                    'Filter': ['[ TBM_MERGE ]-ML-Data', '[ TBM_FILTER ]-ML2-Data'],
                    'Split': ['[ TBM_MERGE ]-ML-Data', '[ TBM_SPLIT ]-A-ML2-Data'],
                    'Plot': ['[ TBM_MERGE ]-ML-Data', '[ TBM_PLOT ]-Pic'],
                    'Report': ['[ TBM_MERGE ]-ML-Data', '[ TBM_REPORT ]-Pdf-Data']}  # 输入输出文件夹路径
        self.example = {'Cycle': 'None', 'Extract': 'None',
                        'Class': 'None', 'Clean': 'None',
                        'Merge': 'None', 'Filter': 'None',
                        'Split': 'None', 'Plot': 'None',
                        'Report': 'None'}  # 参数示例
        self.Var_state = {'Cycle': BooleanVar(), 'Extract': BooleanVar(), 'Class': BooleanVar(),
                          'Clean': BooleanVar(), 'Merge': BooleanVar(), 'Filter': BooleanVar(),
                          'Split': BooleanVar(), 'Plot': BooleanVar(), 'Report': BooleanVar()}  # 模块开关
        self.Var_debug = {'Cycle': BooleanVar(), 'Extract': BooleanVar(), 'Class': BooleanVar(),
                          'Clean': BooleanVar(), 'Merge': BooleanVar(), 'Filter': BooleanVar(),
                          'Split': BooleanVar(), 'Plot': BooleanVar(), 'Report': BooleanVar()}  # DEBUG开关
        self.Var_input = {'Cycle': StringVar(), 'Extract': StringVar(), 'Class': StringVar(),
                          'Clean': StringVar(), 'Merge': StringVar(), 'Filter': StringVar(),
                          'Split': StringVar(), 'Plot': StringVar(), 'Report': StringVar()}  # 输入路径变量
        self.Var_output = {'Cycle': StringVar(), 'Extract': StringVar(), 'Class': StringVar(),
                           'Clean': StringVar(), 'Merge': StringVar(), 'Filter': StringVar(),
                           'Split': StringVar(), 'Plot': StringVar(), 'Report': StringVar()}  # 输出路径变量
        self.Var_parm = {'Cycle': StringVar(), 'Extract': StringVar(), 'Class': StringVar(),
                         'Clean': StringVar(), 'Merge': StringVar(), 'Filter': StringVar(),
                         'Split': StringVar(), 'Plot': StringVar(), 'Report': StringVar()}  # 参数变量
        self.Var_other = {'DIVISION-WAY': StringVar(), 'INTERVAL-TIME': IntVar(), 'VELOCITY-MIN': IntVar(),
                          'LENGTH-MIN1': IntVar(), 'PROJECT': StringVar(), 'LENGTH-MIN2': IntVar(),
                          'VELOCITY-MAX1': IntVar(), 'VELOCITY-SET': IntVar(), 'MISSING_RATIO': IntVar(),
                          'VELOCITY-MAX2': IntVar(), 'PARTITION-METHOD': StringVar(), 'TIME-MIN': IntVar(),
                          'WEIGHT': IntVar(), 'HEIGHT': IntVar(), 'DPI': IntVar(), 'FORMAT': StringVar(),
                          'SHOW': BooleanVar(), 'COVER': BooleanVar(), 'CONTENT': BooleanVar(), 'HEADER': BooleanVar(),
                          'FOOTER': BooleanVar(), 'WATERMARK': BooleanVar(), 'WATERMARK-INFO': StringVar(),
                          'OUTER': BooleanVar(), 'PLOT-PATH': StringVar()}  # 其他变量
        self.Var_text = {}  # 临时变量
        self.update = {'backup': StringVar(), 'recovery': StringVar(), 'update': StringVar()}
        self.Var_index = StringVar()  # 索引路径变量
        self.config = []  # 配置文件
        self.Main()  # 运行主程序

    def Input_Event(self, var, fuc=None, Type='Dir', file_type=None):
        """获取输入路径"""
        if Type == 'Dir':
            newDir = askdirectory(initialdir='D:\\', title='打开目录').replace('/', '\\')
            if not newDir:
                return
            Dir = newDir.replace(newDir.split('\\')[-1], '')
            if fuc is None:
                self.Var_input[var].set(newDir)
                self.Var_output[var].set(os.path.join(Dir, self.Dir[var][1]))
                self.Var_index.set(os.path.join(Dir, 'Index-File.csv'))
            else:
                fuc[var].set(newDir)
            if var == 'Cycle':
                for model, Var in zip(list(self.Dir.keys())[1:], list(self.Dir.values())[1:]):
                    self.Var_input[model].set(os.path.join(Dir, Var[0]))
                    self.Var_output[model].set(os.path.join(Dir, Var[1]))
                self.Var_other['PLOT-PATH'].set(os.path.join(Dir, self.Dir['Plot'][1]))
        if Type == 'File':
            newDir = askopenfilename(initialdir='D:\\', title='选择文件', filetypes=file_type).replace('/', '\\')
            if not newDir:
                return
            fuc[var].set(newDir)

    def Output_Event(self, var, fuc=None, Type='Dir', file_type=None):
        """获取输出路径"""
        if Type == 'Dir':
            newDir = askdirectory(initialdir='D:\\', title='另存目录').replace('/', '\\')
            if not newDir:
                return
            self.Var_output[var].set(newDir)
            self.Var_index.set(os.path.join(newDir.replace(newDir.split('\\')[-1], ''), 'Index-File.csv'))
        if Type == 'File':
            name = 'backup TBM PreProcess %s.tar.gz' % datetime.date.today()
            newDir = asksaveasfilename(initialfile=name, initialdir='D:\\', title='选择文件', filetypes=file_type).replace(
                '/', '\\')
            if not newDir:
                return
            fuc[var].set(newDir)

    def Text_Event(self, var):
        """获取文本变量"""

        def Get_Info():
            information = name_input.get('0.0', 'end')[:-1]
            self.Var_parm[var].set(information)
            window.destroy()

        window = Tk()
        window.geometry('730x270')
        window.resizable(0, 0)  # 防止用户调整尺寸
        window.title('输入参数')
        Label(window, text='多个参数间用逗号隔开(位置索引/标签索引)', font=self.Text).pack(pady=7)
        Label(window, text='参数示例：%s' % self.example[var]).pack(pady=7)
        name_input = tkinter.Text(window, font=self.Text)
        name_input.place(x=13, y=70, width=705, height=150)  # width宽 height高
        tkinter.Button(window, text='清  空', font=self.Text, command=None).place(x=13, y=230, width=80, height=30)
        tkinter.Button(window, text='确  认', font=self.Text, command=Get_Info).place(x=639, y=230, width=80, height=30)

    @staticmethod  # 不强制要求传递参数
    def Help_Event():
        """打开帮助文件"""
        try:
            os.startfile('Resource\\helps\\程序说明.pdf')
        except FileNotFoundError:
            messagebox.showwarning(title='提 示', message='帮助文件不存在！')  # 消息提醒弹

    def Reset_Event(self):
        """重置所有设置"""
        if messagebox.askyesno(title='提 示', message='将会清空所有设置，是否继续？'):
            self.config = self.Default_Setting()
            self.Setting_Var()

    @staticmethod  # 不强制要求传递参数
    def Version_Event():
        """展示版本信息"""
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(__file__))
        with open(file_path, 'r', encoding="utf-8") as F:
            Info = ''.join(F.readlines()[3:10]).replace('# *', '').replace(' *', '')
        messagebox.showinfo(title='版本信息', message=Info)  # 消息提醒弹

    def Ok_Event(self):
        """确定"""
        self.Apply_Event()
        self.root.destroy()
        self.Getting_Var()
        self.Creative_Config()
        for num, model in enumerate(list(self.Var_parm.keys())):
            try:
                self.config[num + 1]['PARAMETER'] = [int(x) for x in self.config[num + 1]['PARAMETER'].split(',')]
            except ValueError:
                self.config[num + 1]['PARAMETER'] = [x for x in self.config[num + 1]['PARAMETER'].split(',')]

    def Cancel_Event(self):
        """取消"""
        self.root.destroy()
        sys.exit()

    def Apply_Event(self):
        """应用"""
        for name, var in zip(list(self.Var_text.keys()), list(self.Var_text.values())):
            self.Var_other[name].set(var.get())

    def Model_Explain(self, framework, info, y, height=40):
        group = tkinter.LabelFrame(framework, text="模块说明", labelanchor=N, font=self.Text)
        group.place(x=10, y=y, width=570, height=130)
        Label(group, text=info, font=('宋体', 11)).place(x=10, y=0, width=550, height=height)

    def Get_Entry(self, framework, y, title, var, unit=None, state='normal'):
        Label(framework, text=title, font=self.Text).place(x=14, y=y, width=140, height=25)
        vessel = Entry(framework, textvariable=self.Var_other[var], font=self.Text, state=state)  # width宽 height高
        vessel.place(x=160, y=y, width=310, height=25)
        Label(framework, text=unit, font=self.Text).place(x=475, y=y, width=70, height=25)
        self.Var_text.update({var: vessel})

    def Basic_Settings(self, Framework, var):
        Group = tkinter.LabelFrame(Framework, text="基本设置", labelanchor=N, font=self.Text)
        Group.place(x=10, y=15, width=570, height=180)
        Radiobutton(Group, text="启 用", variable=self.Var_state[var], value=True).place(x=150, y=15, width=60, height=25)
        Radiobutton(Group, text="禁 用", variable=self.Var_state[var],
                    value=False).place(x=350, y=15, width=60, height=25)
        Checkbutton(Group, text="调 试", variable=self.Var_debug[var], onvalue=True,
                    offvalue=False).place(x=490, y=15, width=70, height=25)
        Label(Group, text='源文件:', font=self.Text, foreground='black').place(x=15, y=50, width=60, height=25)
        Entry(Group, textvariable=self.Var_input[var], font=self.Text).place(x=75, y=50, width=400, height=25)
        tkinter.Button(Group, text='打开目录', command=lambda: self.Input_Event(var),
                       font=self.Text).place(x=480, y=50, width=70, height=25)
        Label(Group, text='输  出:', font=self.Text, foreground='black').place(x=15, y=85, width=60, height=25)
        Entry(Group, textvariable=self.Var_output[var], font=self.Text).place(x=75, y=85, width=400, height=25)
        tkinter.Button(Group, text='另存目录', command=lambda: self.Output_Event(var),
                       font=self.Text).place(x=480, y=85, width=70, height=25)
        Label(Group, text='参  数:', font=self.Text).place(x=15, y=120, width=60, height=25)
        Entry(Group, textvariable=self.Var_parm[var], font=self.Text).place(x=75, y=120, width=400, height=25)
        tkinter.Button(Group, text='更   改', command=lambda: self.Text_Event(var),
                       font=self.Text).place(x=480, y=120, width=70, height=25)

    def Backup_Recovery(self, Framework, var):
        Group_1 = tkinter.LabelFrame(Framework, text="备份/恢复", labelanchor=N, font=self.Text)
        Group_1.place(x=10, y=15, width=570, height=190)
        Label(Group_1, text='备份配置:', font=self.Text, foreground='black').place(x=15, y=15, width=75, height=25)
        Entry(Group_1, textvariable=self.update['backup'], font=self.Text).place(x=95, y=15, width=375, height=25)
        tkinter.Button(Group_1, text='选择路径',
                       command=lambda: self.Output_Event(var='backup', fuc=self.update, Type='File',
                                                         file_type=[("压缩文件", ".tar.gz")]),
                       font=self.Text).place(x=480, y=15, width=70, height=25)
        tkinter.Button(Group_1, text='  生成备份  ', command=lambda: self.BRU_file(), background="#24BDDC",
                       foreground="white",
                       font=self.Text, bd=1).place(x=250, y=50, width=70, height=25)

        Label(Group_1, text='还原配置:', font=self.Text, foreground='black').place(x=15, y=95, width=75, height=25)
        Entry(Group_1, textvariable=self.update['recovery'], font=self.Text).place(x=95, y=95, width=375, height=25)
        tkinter.Button(Group_1, text='选择文件', font=self.Text,
                       command=lambda: self.Input_Event(var='recovery', fuc=self.update, Type='File',
                                                        file_type=[("压缩文件", ".tar.gz")])).place(x=480, y=95, width=70,
                                                                                                height=25)
        tkinter.Button(Group_1, text='  上传备份  ', command=lambda: self.BRU_file(Type='recovery'), background="#24BDDC",
                       foreground="white", font=self.Text, bd=1).place(x=250, y=130, width=70, height=25)

        Group_2 = tkinter.LabelFrame(Framework, text="重  置", labelanchor=N, font=self.Text)
        Group_2.place(x=10, y=230, width=570, height=70)
        tkinter.Button(Group_2, text='  执行重置  ', command=lambda: self.Reset_Event(), background="#E0AD1E",
                       foreground="white", font=self.Text, bd=1).place(x=250, y=15, width=70, height=25)

        Group_3 = tkinter.LabelFrame(Framework, text="升  级", labelanchor=N, font=self.Text)
        Group_3.place(x=10, y=330, width=570, height=110)
        Label(Group_3, text='固件文件:', font=self.Text, foreground='black').place(x=15, y=15, width=75, height=25)
        Entry(Group_3, textvariable=self.update['update'], font=self.Text).place(x=95, y=15, width=375, height=25)
        tkinter.Button(Group_3, text='选择路径', font=self.Text,
                       command=lambda: self.Input_Event(var='update', fuc=self.update, Type='File',
                                                        file_type=[("压缩文件", ".zip")])).place(x=480, y=15, width=70,
                                                                                             height=25)
        tkinter.Button(Group_3, text='  本地更新  ', command=lambda: self.BRU_file(Type='update'), background="#24BDDC",
                       foreground="white", font=self.Text, bd=1).place(x=150, y=50, width=70, height=25)
        tkinter.Button(Group_3, text='  联网更新  ', command=lambda: Check_Update(), background="#24BDDC",
                       foreground="white", font=self.Text, bd=1).place(x=350, y=50, width=70, height=25)

    def BRU_file(self, Type='backup'):
        root_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '__Update__')  # 当前文件夹路径
        if not os.path.exists(root_path):
            os.mkdir(root_path)  # 创建相关文件夹
        if Type == 'backup':
            self.Apply_Event()
            self.Getting_Var()
            self.Creative_Config(path=os.path.join(root_path, 'config.ini'))
            with tarfile.open(self.update['backup'].get(), "w:") as tar:
                tar.add(os.path.join(root_path, 'config.ini'),
                        arcname=os.path.basename(os.path.join(root_path, 'config.ini')))
            messagebox.showinfo(title='提示', message='备份配置成功')  # 消息提醒弹
        if Type == 'recovery':
            tarfile.open(self.update['recovery'].get()).extractall(root_path)
            self.Get_Config(path=os.path.join(root_path, 'config.ini'))
            messagebox.showinfo(title='提示', message='还原配置成功')  # 消息提醒弹
        if Type == 'update':
            try:
                zipfile.ZipFile(self.update['update'].get(), mode='r').extractall(root_path)
                from __Update__.Update import Update
                messagebox.showinfo(title='提示', message='更新程序成功')  # 消息提醒弹
            except (zipfile.BadZipFile, ModuleNotFoundError):
                messagebox.showinfo(title='提示', message='未选择更新文件或更新文件非法！')  # 消息提醒弹
        if os.path.exists(root_path):
            shutil.rmtree(root_path)

    def Select_Button(self, framework, title, var, y, value=None):
        if value is None:
            value = [["是", "否"], [True, False]]
        Label(framework, text=title, font=self.Text).place(x=5, y=y, width=130, height=25)
        Radiobutton(framework, text=value[0][0], variable=self.Var_other[var],
                    value=value[1][0]).place(x=185, y=y, width=100, height=25)
        Radiobutton(framework, text=value[0][1], variable=self.Var_other[var],
                    value=value[1][1]).place(x=385, y=y, width=100, height=25)

    def Bottom_Button(self, Framework):
        url = 'https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A?pwd=STBM'
        tkinter.Button(Framework, text='相关资源下载', command=lambda: web.open(url),
                       font=self.Text, bd=0, fg='blue').place(x=15, y=710, width=100, height=25)
        tkinter.Button(Framework, text='确 定', command=lambda: self.Ok_Event(),
                       font=self.Text).place(x=309, y=710, width=70, height=25)
        tkinter.Button(Framework, text='取 消', command=lambda: self.Cancel_Event(),
                       font=self.Text).place(x=409, y=710, width=70, height=25)
        tkinter.Button(Framework, text='应 用', command=lambda: self.Apply_Event(),
                       font=self.Text).place(x=509, y=710, width=70, height=25)

    def Setting_Var(self):
        for num, model in enumerate(list(self.Var_state.keys())):
            self.Var_state[model].set(self.config[num + 1]['USING-MODEL'])
        for num, model in enumerate(list(self.Var_debug.keys())):
            self.Var_debug[model].set(self.config[num + 1]['DEBUG'])
        for num, model in enumerate(list(self.Var_input.keys())):
            self.Var_input[model].set(self.config[num + 1]['INPUT-PATH'])
        for num, model in enumerate(list(self.Var_output.keys())):
            self.Var_output[model].set(self.config[num + 1]['OUTPUT-PATH'])
        for num, model in enumerate(list(self.Var_parm.keys())):
            self.Var_parm[model].set(self.config[num + 1]['PARAMETER'])
        for key in list(self.Var_other.keys()):
            for num, model in enumerate(self.config):
                if key in model.keys():
                    self.Var_other[key].set(self.config[num][key])
        self.Var_index.set(self.config[0]['INDEX-PATH'])
        for num, model in enumerate(list(self.update.keys())):
            self.update[model].set(self.config[-1][model])

    def Getting_Var(self):
        for num, model in enumerate(list(self.Var_state.keys())):
            self.config[num + 1]['USING-MODEL'] = self.Var_state[model].get()
        for num, model in enumerate(list(self.Var_debug.keys())):
            self.config[num + 1]['DEBUG'] = self.Var_debug[model].get()
        for num, model in enumerate(list(self.Var_input.keys())):
            self.config[num + 1]['INPUT-PATH'] = self.Var_input[model].get()
        for num, model in enumerate(list(self.Var_output.keys())):
            self.config[num + 1]['OUTPUT-PATH'] = self.Var_output[model].get()
        for num, model in enumerate(list(self.Var_parm.keys())):
            self.config[num + 1]['PARAMETER'] = self.Var_parm[model].get()
        for key in list(self.Var_other.keys()):
            for num, model in enumerate(self.config):
                if key in model.keys():
                    self.config[num][key] = self.Var_other[key].get()
        self.config[0]['INDEX-PATH'] = self.Var_index.get()

    @staticmethod  # 不强制要求传递参数
    def Default_Setting():
        Index_path = {'INDEX-PATH': '--请选择--'}
        Cycle = {'USING-MODEL': False, 'DEBUG': False, 'INPUT-PATH': '--请选择--',
                 'OUTPUT-PATH': '--请选择--', 'PARAMETER': '--请选择--', 'DIVISION-WAY': 'Rotate Speed',
                 'INTERVAL-TIME': '100', 'VELOCITY-MIN': '1', 'LENGTH-MIN1': '10'}
        Extract = {'USING-MODEL': False, 'DEBUG': False, 'INPUT-PATH': '--请选择--',
                   'OUTPUT-PATH': '--请选择--', 'PARAMETER': '--请选择--'}
        Class = {'USING-MODEL': False, 'DEBUG': False, 'INPUT-PATH': '--请选择--', 'OUTPUT-PATH': '--请选择--',
                 'PARAMETER': '--请选择--', 'PROJECT': '引绰-668', 'LENGTH-MIN2': '300',
                 'VELOCITY-MAX1': '120', 'VELOCITY-SET': '15', 'MISSING_RATIO': '20'}
        Clean = {'USING-MODEL': False, 'DEBUG': False, 'INPUT-PATH': '--请选择--',
                 'OUTPUT-PATH': '--请选择--', 'PARAMETER': '--请选择--', 'VELOCITY-MAX2': '120'}
        Merge = {'USING-MODEL': False, 'DEBUG': False, 'INPUT-PATH': '--请选择--',
                 'OUTPUT-PATH': '--请选择--', 'PARAMETER': '--请选择--'}
        Filter = {'USING-MODEL': False, 'DEBUG': False, 'INPUT-PATH': '--请选择--',
                  'OUTPUT-PATH': '--请选择--', 'PARAMETER': '--请选择--'}
        Split = {'USING-MODEL': False, 'DEBUG': False, 'INPUT-PATH': '--请选择--', 'OUTPUT-PATH': '--请选择--',
                 'PARAMETER': '--请选择--', 'PARTITION-METHOD': 'Average', 'TIME-MIN': '200'}
        Plot = {'USING-MODEL': False, 'DEBUG': False, 'INPUT-PATH': '--请选择--',
                'OUTPUT-PATH': '--请选择--', 'PARAMETER': '--请选择--', 'WEIGHT': '80',
                'HEIGHT': '100', 'DPI': '120', 'FORMAT': 'png', 'SHOW': False}
        Report = {'USING-MODEL': False, 'DEBUG': False, 'INPUT-PATH': '--请选择--',
                  'OUTPUT-PATH': '--请选择--', 'PARAMETER': '--请选择--', 'PLOT-PATH': '--请选择--',
                  'COVER': False, 'CONTENT': True, 'HEADER': False, 'FOOTER': True,
                  'WATERMARK': False, 'OUTER': False, 'WATERMARK-INFO': 'TBM掘进参数'}
        update = {'backup': '--未选择任何文件--', 'recovery': '--未选择任何文件--', 'update': '--未选择任何文件--'}
        return Index_path, Cycle, Extract, Class, Clean, Merge, Filter, Split, Plot, Report, update

    def Creative_Config(self, path='Resource/config/config.ini'):
        now = datetime.datetime.now()
        Time = now.strftime("%Y-%m-%d %H:%M:%S")
        Config = configparser.ConfigParser()
        Config['Program'] = {'Time': str(Time), 'Name': os.path.basename(__file__)}
        Config['Index-file'] = self.config[0]
        Config['Cycle-model'] = self.config[1]
        Config['Extract-model'] = self.config[2]
        Config['Class-model'] = self.config[3]
        Config['Clean-model'] = self.config[4]
        Config['Merge-model'] = self.config[5]
        Config['Filter-model'] = self.config[6]
        Config['Split-model'] = self.config[7]
        Config['Plot-model'] = self.config[8]
        Config['Report-model'] = self.config[9]
        with open(path, 'w+', encoding='GBK') as cfg:
            Config.write(cfg)
        return Config

    def Get_Config(self, path='Resource\\config\\config.ini'):
        """定义读取配置文件函数，分别读取各个分栏的配置参数，包含ints、floats、strings"""
        parser = configparser.ConfigParser()
        try:
            parser.read(path, encoding='GBK')  # 读取文件
            Index_path = dict([(str.upper(key), value) for key, value in parser.items('Index-file')])
            Cycle = dict([(str.upper(key), value) for key, value in parser.items('Cycle-model')])
            Extract = dict([(str.upper(key), value) for key, value in parser.items('Extract-model')])
            Class = dict([(str.upper(key), value) for key, value in parser.items('Class-model')])
            Clean = dict([(str.upper(key), value) for key, value in parser.items('Clean-model')])
            Merge = dict([(str.upper(key), value) for key, value in parser.items('Merge-model')])
            Filter = dict([(str.upper(key), value) for key, value in parser.items('Filter-model')])
            Split = dict([(str.upper(key), value) for key, value in parser.items('Split-model')])
            Plot = dict([(str.upper(key), value) for key, value in parser.items('Plot-model')])
            Report = dict([(str.upper(key), value) for key, value in parser.items('Report-model')])
            update = {'backup': '--未选择任何文件--', 'recovery': '--未选择任何文件--', 'update': '--未选择任何文件--'}
        except configparser.NoSectionError:
            Index_path, Cycle, Extract, Class, Clean, Merge, Filter, Split, Plot, Report, update = self.Default_Setting()
        self.config = [Index_path, Cycle, Extract, Class, Clean, Merge, Filter, Split, Plot, Report, update]
        self.Setting_Var()

    def Module_Entry(self, framework, state='normal'):
        Label(framework, text='  图片文件  ', font=self.Text).place(x=12, y=260, width=100, height=25)
        Entry(framework, textvariable=self.Var_other['PLOT-PATH'], font=self.Text,
              state=state).place(x=150, y=260, width=325, height=25)
        tkinter.Button(framework, text='打开目录', font=self.Text,
                       command=lambda: self.Input_Event('PLOT-PATH', self.Var_other),
                       state=state).place(x=480, y=260, width=70, height=25)

    def Main(self):
        self.root.geometry('%dx%d+%d+%d' % (self.window_weight, self.window_height, self.window_x, self.window_y))
        self.root.title('数据预处理')
        self.root.resizable(0, 0)  # 防止用户调整尺寸
        style = Style()
        style.configure('my.TNotebook', tabposition='wn')  # 'se'再改nw,ne,sw,se,w,e,wn,ws,en,es,n,s试试
        style.configure('TNotebook.Tab', background='black', font=('宋体', 13))
        notebook = Notebook(self.root, style='my.TNotebook')  # 1 创建Notebook组件
        notebook.pack(padx=10, pady=5, fill=BOTH, expand=True)
        self.Get_Config()
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.Cancel_Event())
        tkinter.Button(self.root, text='版本信息', command=lambda: self.Version_Event(),
                       font=self.Text, bd=1).place(x=17, y=645, width=70, height=25)
        tkinter.Button(self.root, text='恢复默认', command=lambda: self.Reset_Event(),
                       font=self.Text, bd=1).place(x=17, y=680, width=70, height=25)
        tkinter.Button(self.root, text=' 帮 助 ', command=lambda: self.Help_Event(),
                       font=self.Text, bd=1).place(x=17, y=715, width=70, height=25)

        fr1 = Frame(self.root)  # 2 创建选项卡1的容器框架
        notebook.add(fr1, text='\n CYCLE  \n')  # 3 装入框架1到选项卡1
        self.Basic_Settings(fr1, 'Cycle')
        group1_2 = tkinter.LabelFrame(fr1, text="高级设置", labelanchor=N, font=self.Text)
        group1_2.place(x=10, y=220, width=570, height=185)
        self.Select_Button(group1_2, '  循环段划分依据  ', 'DIVISION-WAY',
                           15, value=[["刀盘转速", "推进速度"], ['Rotate Speed', 'Advance Speed']])
        self.Get_Entry(group1_2, 50, '两循环段间时间间隔', 'INTERVAL-TIME', ' s')
        self.Get_Entry(group1_2, 85, ' 掘进长度下限值  ', 'LENGTH-MIN1', ' mm')
        self.Get_Entry(group1_2, 120, ' 掘进速度下限值  ', 'VELOCITY-MIN', ' mm/min')
        self.Model_Explain(fr1, self.Program_description['Cycle'], 430, 80)
        self.Bottom_Button(fr1)

        fr2 = Frame(self.root)  # 2 创建选项卡1的容器框架
        notebook.add(fr2, text='\nEXTRACT \n')  # 3 装入框架1到选项卡1
        self.Basic_Settings(fr2, 'Extract')
        self.Model_Explain(fr2, self.Program_description['EXTRACT'], 220, 40)
        self.Bottom_Button(fr2)

        fr3 = Frame(self.root)  # 2 创建选项卡1的容器框架
        notebook.add(fr3, text='\n CLASS  \n')  # 3 装入框架1到选项卡1
        self.Basic_Settings(fr3, 'Class')
        group3_2 = tkinter.LabelFrame(fr3, text="高级设置", labelanchor=N, font=self.Text)
        group3_2.place(x=10, y=220, width=570, height=220)
        self.Get_Entry(group3_2, 15, '     工程类型     ', 'PROJECT')
        self.Get_Entry(group3_2, 50, '  掘进长度下限值  ', 'LENGTH-MIN2', ' mm')
        self.Get_Entry(group3_2, 85, '  推进速度上限值  ', 'VELOCITY-MAX1', ' mm/min')
        self.Get_Entry(group3_2, 120, '推进速度设定变化幅', 'VELOCITY-SET')
        self.Get_Entry(group3_2, 155, '    数据缺失率    ', 'MISSING_RATIO', ' %')
        self.Model_Explain(fr3, self.Program_description['CLASS'], 465, 110)
        self.Bottom_Button(fr3)

        fr4 = Frame(self.root)  # 2 创建选项卡1的容器框架
        notebook.add(fr4, text='\n CLEAN  \n')  # 3 装入框架1到选项卡1
        self.Basic_Settings(fr4, 'Clean')
        group4_2 = tkinter.LabelFrame(fr4, text="高级设置", labelanchor=N, font=self.Text)
        group4_2.place(x=10, y=220, width=570, height=80)
        self.Get_Entry(group4_2, 15, ' 推进速度上限值', 'VELOCITY-MAX2', ' mm/min')
        self.Model_Explain(fr4, self.Program_description['CLEAN'], 325, 40)
        self.Bottom_Button(fr4)

        fr5 = Frame(self.root)  # 2 创建选项卡1的容器框架
        notebook.add(fr5, text='\n MERGE  \n')  # 3 装入框架1到选项卡1
        self.Basic_Settings(fr5, 'Merge')
        self.Model_Explain(fr5, self.Program_description['MERGE'], 220, 40)
        self.Bottom_Button(fr5)

        fr6 = Frame(self.root)  # 2 创建选项卡1的容器框架
        notebook.add(fr6, text='\n SPLIT  \n')  # 3 装入框架1到选项卡1
        self.Basic_Settings(fr6, 'Split')
        group6_2 = tkinter.LabelFrame(fr6, text="高级设置", labelanchor=N, font=self.Text)
        group6_2.place(x=10, y=220, width=570, height=115)
        self.Select_Button(group6_2, '  内部段划分方法  ', 'PARTITION-METHOD',
                           15, value=[["平均值  ", "核密度估计"], ['Average', 'Kernel Density']])
        self.Get_Entry(group6_2, 50, ' 时间记录下限值', 'TIME-MIN', ' s')
        self.Model_Explain(fr6, self.Program_description['SPLIT'], 360, 70)
        self.Bottom_Button(fr6)

        fr7 = Frame(self.root)  # 2 创建选项卡1的容器框架
        notebook.add(fr7, text='\n FILTER \n')  # 3 装入框架1到选项卡1
        self.Basic_Settings(fr7, 'Filter')
        self.Model_Explain(fr7, self.Program_description['FILTER'], 220, 40)
        self.Bottom_Button(fr7)

        fr8 = Frame(self.root)  # 2 创建选项卡1的容器框架
        notebook.add(fr8, text='\n  PLOT  \n')  # 3 装入框架1到选项卡1
        self.Basic_Settings(fr8, 'Plot')
        group8_2 = tkinter.LabelFrame(fr8, text="高级设置", labelanchor=N, font=self.Text)
        group8_2.place(x=10, y=220, width=570, height=220)
        self.Get_Entry(group8_2, 15, '  图片高度  ', 'HEIGHT', ' mm')
        self.Get_Entry(group8_2, 50, '  图片宽度  ', 'WEIGHT', ' mm')
        self.Get_Entry(group8_2, 85, ' 图片分辨率 ', 'DPI', ' dpi')
        self.Get_Entry(group8_2, 120, '  图片类型  ', 'FORMAT')
        self.Select_Button(group8_2, '  展示图片  ', 'SHOW', 155)
        self.Model_Explain(fr8, self.Program_description['PLOT'], 465, 100)
        self.Bottom_Button(fr8)

        fr9 = Frame(self.root)  # 2 创建选项卡1的容器框架
        notebook.add(fr9, text='\n REPORT \n')  # 3 装入框架1到选项卡1
        self.Basic_Settings(fr9, 'Report')
        group9_2 = tkinter.LabelFrame(fr9, text="高级设置", labelanchor=N, font=self.Text)
        group9_2.place(x=10, y=220, width=570, height=320)
        self.Select_Button(group9_2, '  添加封面  ', 'COVER', 15)
        self.Select_Button(group9_2, '  添加目录  ', 'CONTENT', 50)
        self.Select_Button(group9_2, '  添加页眉  ', 'HEADER', 85)
        self.Select_Button(group9_2, '  添加页脚  ', 'FOOTER', 120)
        use_watermark = 'normal' if self.Var_other['WATERMARK'].get() else 'disabled'
        self.Get_Entry(group9_2, 190, '  水印名称  ', 'WATERMARK-INFO', state=use_watermark)
        Label(group9_2, text='  添加水印  ', font=self.Text).place(x=14, y=155, width=100, height=25)
        Radiobutton(group9_2, text="是", variable=self.Var_other['WATERMARK'],
                    command=lambda: self.Get_Entry(group9_2, 190, '  水印名称  ', 'WATERMARK-INFO', state='normal'),
                    value=True).place(x=200, y=155, width=100, height=25)
        Radiobutton(group9_2, text="否", variable=self.Var_other['WATERMARK'],
                    command=lambda: self.Get_Entry(group9_2, 190, '  水印名称  ', 'WATERMARK-INFO',
                                                   state='disabled'),
                    value=False).place(x=400, y=155, width=100, height=25)
        use_outer = 'normal' if self.Var_other['OUTER'].get() else 'disabled'
        self.Module_Entry(group9_2, use_outer)
        Label(group9_2, text='使用外部图片', font=self.Text).place(x=14, y=225, width=100, height=25)
        Radiobutton(group9_2, text="是", variable=self.Var_other['OUTER'],
                    command=lambda: self.Module_Entry(group9_2, 'normal'),
                    value=True).place(x=200, y=225, width=100, height=25)
        Radiobutton(group9_2, text="否", variable=self.Var_other['OUTER'],
                    command=lambda: self.Module_Entry(group9_2, 'disabled'),
                    value=False).place(x=400, y=225, width=100, height=25)
        self.Model_Explain(fr9, self.Program_description['REPORT'], 565, 50)
        self.Bottom_Button(fr9)

        fr10 = Frame(self.root)  # 2 创建选项卡1的容器框架
        notebook.add(fr10, text='\n备份/升级\n')  # 3 装入框架1到选项卡1
        self.Backup_Recovery(fr10, 'Report')
        self.Bottom_Button(fr10)

        self.root.mainloop()


def Check_Update():
    """检查更新模块"""
    root_path = os.path.dirname(os.path.abspath(__file__))  # 当前文件夹路径
    URL = "https://github.com/Moonquakes-liu/TBM-Intelligent/archive/refs/heads/main.zip"
    try:
        response = requests.get(URL)
        _tmp_file = tempfile.TemporaryFile()  # 创建临时文件
        _tmp_file.write(response.content)  # byte字节数据写入临时文件
        ZF = zipfile.ZipFile(_tmp_file, mode='r')
        for num, name in enumerate(ZF.namelist()):
            F = ZF.extract(name, './__Update__')  # 解压到zip目录文件下
            current_path = os.path.join(root_path, F)  # 下载的新文件名称
            target_path = os.path.join(root_path, '__Update__', F.split('\\')[-1])  # 下载的新文件名称
            if current_path != target_path:
                shutil.copyfile(current_path, target_path)  # 更新新文件
        from __Update__.Update import Update
        shutil.rmtree(os.path.join(root_path, '__Update__')), ZF.close()  # 更新完成，删除相关文件记录
    except requests.exceptions.ConnectionError:
        return


if __name__ == "__main__":
    # Check_Update()  # 检查程序是否存在新版本
    print('-> \033[0;32mOperating System: %s  Current Program: %s\033[0m' % (sys.platform, os.path.basename(__file__)))
    CONF = MESSAGE().config  # 调用窗口获取输入输出路径及相关参数，完成对程序的配置
    if CONF[1]['USING-MODEL']:
        TBM_CYCLE(input_path=CONF[1]['INPUT-PATH'], out_path=CONF[1]['OUTPUT-PATH'], parameter=CONF[1]['PARAMETER'],
                  division=CONF[1]['DIVISION-WAY'], interval_time=CONF[1]['INTERVAL-TIME'],
                  index_path=CONF[0]['INDEX-PATH'],
                  V_min=CONF[1]['VELOCITY-MIN'], L_min=CONF[1]['LENGTH-MIN1'], debug=CONF[1]['DEBUG'])
    if CONF[2]['USING-MODEL']:
        TBM_EXTRACT(input_path=CONF[2]['INPUT-PATH'], out_path=CONF[2]['OUTPUT-PATH'], key_parm=CONF[2]['PARAMETER'],
                    index_path=CONF[0]['INDEX-PATH'], debug=CONF[2]['DEBUG'])
    if CONF[3]['USING-MODEL']:
        TBM_CLASS(input_path=CONF[3]['INPUT-PATH'], project_type=CONF[3]['PROJECT'], L_min=CONF[3]['LENGTH-MIN2'],
                  debug=CONF[3]['DEBUG'], out_path=CONF[3]['OUTPUT-PATH'], missing_ratio=CONF[3]['MISSING_RATIO'] / 100,
                  V_max=CONF[3]['VELOCITY-MAX1'], V_set_var=CONF[3]['VELOCITY-SET'], parameter=CONF[3]['PARAMETER'],
                  index_path=CONF[0]['INDEX-PATH'])
    if CONF[4]['USING-MODEL']:
        TBM_CLEAN(input_path=CONF[4]['INPUT-PATH'], out_path=CONF[4]['OUTPUT-PATH'], debug=CONF[4]['DEBUG'],
                  parameter=CONF[4]['PARAMETER'], V_max=CONF[4]['VELOCITY-MAX2'], index_path=CONF[0]['INDEX-PATH'])
    if CONF[5]['USING-MODEL']:
        TBM_MERGE(input_path=CONF[5]['INPUT-PATH'], out_path=CONF[5]['OUTPUT-PATH'], parameter=CONF[5]['PARAMETER'],
                  debug=CONF[5]['DEBUG'], index_path=CONF[0]['INDEX-PATH'])
    if CONF[6]['USING-MODEL']:
        TBM_FILTER(input_path=CONF[6]['INPUT-PATH'], out_path=CONF[6]['OUTPUT-PATH'], parameter=CONF[6]['PARAMETER'],
                   debug=CONF[6]['DEBUG'], index_path=CONF[0]['INDEX-PATH'])
    if CONF[7]['USING-MODEL']:
        TBM_SPLIT(input_path=CONF[7]['INPUT-PATH'], out_path=CONF[7]['OUTPUT-PATH'], debug=CONF[7]['DEBUG'],
                  parameter=CONF[7]['PARAMETER'], partition=CONF[7]['PARTITION-METHOD'], min_time=CONF[7]['TIME-MIN'],
                  index_path=CONF[0]['INDEX-PATH'])
    if CONF[8]['USING-MODEL']:
        TBM_PLOT(input_path=CONF[8]['INPUT-PATH'], out_path=CONF[8]['OUTPUT-PATH'], parameter=CONF[8]['PARAMETER'],
                 height=int(CONF[8]['HEIGHT'] / 10), weight=int(CONF[8]['WEIGHT'] / 10), dpi=CONF[8]['DPI'],
                 Format=CONF[8]['FORMAT'], show=CONF[8]['SHOW'], debug=CONF[8]['DEBUG'],
                 index_path=CONF[0]['INDEX-PATH'])
    if CONF[9]['USING-MODEL']:
        TBM_REPORT(input_path=CONF[9]['INPUT-PATH'], out_path=CONF[9]['OUTPUT-PATH'], parameter=CONF[9]['PARAMETER'],
                   input_pic=CONF[9]['PLOT-PATH'], cover=CONF[9]['COVER'], content=CONF[9]['CONTENT'],
                   header=CONF[9]['HEADER'], footer=CONF[9]['FOOTER'], watermark=CONF[9]['WATERMARK'],
                   pic_outer=CONF[9]['OUTER'], watermark_info=CONF[9]['WATERMARK-INFO'], debug=CONF[9]['DEBUG'],
                   index_path=CONF[0]['INDEX-PATH'])
