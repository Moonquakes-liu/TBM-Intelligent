#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_CYCLE for python                                           *
# * Version:  1.5.0                                                          *
# * Date:     2023-1-1 00:00:00                                              *
# * Last update: 2022-12-2 00:00:00                                          *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import configparser
import math
import sys
import copy
import csv
import datetime
import time
import tkinter
import tkinter.filedialog
import tkinter.ttk
import warnings
import os
import shutil
from tkinter import ttk

import requests
import zipfile
import tempfile
import numpy as np
import pandas as pd
import statsmodels.nonparametric.api as SMNP
import psutil
import scipy
from functools import reduce
from tkinter import *
from PyPDF2 import PdfFileWriter, PdfFileReader
from matplotlib import pyplot as plt, pyplot
from numpy import ndarray
from pandas import Series, DataFrame
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table
from scipy import fft
from scipy import signal
from scipy.fftpack import fft
from svglib.svglib import svg2rlg

HISTORY = """
更改时间:2022-11-13  修改人:刘建国  修改位置：TBM_CYCLE()模块中cycle_extract()子程序  修改内容:修复循环段丢失问题。
更改时间:2022-11-14  修改人:董子开  修改位置：TBM_SPLIT()模块中get_RS_index()子程序   修改内容:循环段内部划分准确度优化。
更改时间:2022-12-31  修改人:刘建国  修改位置：TBM_CYCLE()模块中新增custom_read_model()子程序   新增内容:可自定义读取除CSV以外的其他类型文件。
更改时间:2022-12-31  修改人:刘建国  修改位置：TBM_CLASS()模块中新增custom_get_RS_index_model()子程序   新增内容:可自定义上升段、稳定段关键点获取子程序。
更改时间:2022-12-31  修改人:刘建国  修改位置：TBM_SPLIT()模块中新增custom_get_RS_index_model()子程序   新增内容:可自定义上升段、稳定段关键点获取子程序。
更改时间:2022-12-31  修改人:刘建国  修改位置：TBM_SPLIT()模块中新增get_RS_index_1()子程序   新增内容:新增通过核密度估计获取上升段、稳定段关键点子程序，保留原来子程序，可根据需要自行选择。
更改时间:2022-12-31  修改人:刘建国  修改位置：TBM_FILTER()模块中新增custom_filter_model()子程序   新增内容:可自定义数据滤波子程序。
更改时间:2022-12-31  修改人:刘建国  修改位置：TBM_PLOT()模块中新增custom_plot_model()子程序   新增内容:可自定义数据绘图子程序。
更改时间:2022-12-31  修改人:刘建国  修改位置：所有程序代码   修改内容:优化程序调用接口。
更改时间:2023-1-1  修改人:刘建国  修改位置：message()模块中添加高级设置功能   新增内容:添加高级设置功能。
          """

warnings.filterwarnings("ignore")  # 忽略警告信息
index_path = ''


class TBM_CYCLE(object):
    """
    循环段分割模块，完成从原始数据中提取有效循环段的功能
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输出路径，程序则抛出异常并终止运行
                关键参数名称（par_name），若不传入参数，程序则抛出异常并终止运行
    ****可选参数：相邻循环段时间间隔（s）（interval_time），若不传入参数，则采用默认100s
                程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run）， 默认为开启状态
    """
    PARAMETERS = ['桩号,', '日期,', '推进速度,', '刀盘转速']  # 循环段分割模块中的参数名称和顺序示例

    def __init__(self, input_path=None, out_path=None, parameter=None, interval_time=100, debug=False, Run=True):
        """初始化各参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.parm = parameter  # 掘进状态判定参数
        self.index_exists = False  # 将索引文件是否存在
        self.add_temp = pd.DataFrame(None)  # 初始化dataframe类型数组，便于对连续部分数据进行存储
        self.Number = 1  # 初始化循环段编号
        self.D_last = 0  # 初始化上一时刻的掘进状态
        self.MTI = interval_time  # 初始化两个相邻掘进段的最小时间间隔为0（minimum time interval）
        self.debug = DEBUG(debug)  # 调试/修复程序
        """运行各模块"""
        if Run:
            self.check_parm()  # 检查参数是否正常
            self.write_index(-1, {})  # 检查索引文件是否正常
            self.create_cycle_dir()  # 创建相关文件夹
            self.main()  # 读取文件

    def create_cycle_dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):
            os.mkdir(self.out)  # 创建相关文件夹
        else:
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正确，若正确则运行程序，如果不正确则终止程序"""
        curt_class = self.__class__.__name__  # 获取当前模块名称
        if (not self.input) or (not self.out):  # 检查输入输出路径是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if (not self.parm) or (len(self.parm) < len(self.PARAMETERS)):  # 检查传入参数是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input parameters are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序

    def write_index(self, _Num_: int, _info_: dict) -> None:  # 规定_Num_为整型（int），_info_为字典类型（dict）,返回值无类型限定
        """创建索引文件并写入索引"""
        if self.debug.debug:
            return None
        global index_path
        if _Num_ == -1:
            if os.path.isfile(index_path):
                self.index_exists = True  # 判断索引文件是否存在
            if self.index_exists:  # 索引文件存在
                os.remove(index_path)  # 若索引文件存在，则删除
            with open(index_path, 'w', encoding='gb2312', newline='') as f:  # 创建索引文件
                csv.writer(f).writerow(['循环段', '桩号', '日期', '掘进时间'])  # 写入标签数据
        else:
            index_csv = open(index_path, 'a', newline='')  # 打开索引文件
            csv.writer(index_csv).writerow([_Num_, _info_['stake'], _info_['date'], _info_['time']])  # 写入索引数据记录

    def tunnel_determine(self, _data_np_: Series) -> [bool, str]:  # 规定_data_np_为Numpy类型数组(Series)，返回值类型为[布尔值，字符型]
        """对掘进状态的实时判定，结合历史数据返回掘进段开始和结束位置"""
        Fx = np.int64(_data_np_ > 0.1)  # 判定函数 F(x) = 1(x>0), 0(x<=0)
        D_now = reduce(lambda x, y: x * y, Fx)  # D(x) = F(x1)·F(x2)...F(Xn)        lambda为自定义函数
        Tunnel = False if D_now == 0 else True  # 掘进状态 D(x) = 0(downtime), 1(Tunnel)
        # 当前时刻D(x) - 上一时刻D(x‘) = Start(>0), Finish(<0), None(=0)
        key = 'None' if D_now - self.D_last == 0 else 'Start' if D_now - self.D_last > 0 else 'Finish'
        self.D_last = D_now  # 保存上一时刻状态
        return Tunnel, key  # 掘进状态判定结果Tunnel（True/False）和掘进段开始或结束标志key（Start/Finish/None）

    def cycle_splice(self, _data_: DataFrame) -> DataFrame:  # 规定_data_为DataFrame类型数组(DataFrame)，返回数组类型为DataFrame
        """对原始数据中相邻两天存在连续性的数据进行拼接"""
        state = []  # 定义一个空列表，用于存储每一时刻掘进状态（处于掘进状态：True，处于停机状态：False ）
        _data_np_ = _data_.loc[:, self.parm[3:]].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
        mark = 0
        for col in list(_data_.index.values)[::-1]:  # 从后往前，对每一时刻的掘进状态进行判定
            state.append(self.tunnel_determine(_data_np_[int(col), :])[0])  # 将该时刻的掘进状态存储至state中
            if (len(state) > self.MTI) and (not any(state[-self.MTI:-1])):
                mark = col
                break  # 判定两个相邻掘进段的时间间隔内（self.MTI）盾构是否处于掘进状态，若未处于掘进状态，则返回该时刻的行索引值
        _out_data_ = pd.concat([self.add_temp, _data_.loc[:mark + 1, :]], ignore_index=True)  # 将两天连续部分数据进行拼接，形成一个数据集
        self.add_temp = _data_.loc[mark + 1:, :]  # 将当天与后一天连续部分的数据进行单独保存，便于和后一天的数据进行拼接
        return _out_data_  # 返回拼接后的新数据集

    def cycle_extract(self, _data_: DataFrame) -> None:  # 规定_data_为DataFrame类型数组(DataFrame)，返回值无类型限定
        """对原始数据中的掘进段进行实时提取"""
        key = {'now-S': 0, 'now-F': 0, 'last-S': 0, 'last-F': 0}  # 当前掘进段开始与结束的行索引,上一个掘进段开始与结束的行索引
        cycle_num = -1  # 每天数据所划分出的掘进段编号
        data_np = _data_.loc[:, self.parm[2:]].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
        for index, item in enumerate(data_np):  # 从前往后，对每一时刻的掘进状态进行判定（index为行索引， item为每行数据）
            _, result = self.tunnel_determine(item[1:])  # 调用掘进状态判定函数并返回掘进段开始或结束标志
            if result == 'Start':
                key['now-S'] = index  # 保存掘进段开始时的行索引
            if result == 'Finish':
                key['now-F'] = index  # 保存掘进段结束时的行索引
            if (key['now-F'] > key['now-S']) or (index == len(data_np) - 1):  # 获取到掘进段开始和结束索引是否完整
                if (index == len(data_np) - 1) or (max(data_np[key['now-S']:key['now-F'], 0]) > 0):
                    if cycle_num == -1:  # 由于在获取到下一个完整掘进段的开始和结束的行索引后才对上一个循环段进行保存，因此要对第一个掘进段进行特殊处理
                        key['last-S'], key['last-F'] = key['now-S'], key['now-F']  # 首个掘进段开始和结束的行索引进行赋值
                        cycle_num = 1  # 每天数据所划分出的掘进段编号
                    if (key['now-S'] - key['last-F'] > self.MTI) or (index == len(data_np) - 1):  # 判断两个掘进段时间间隔是否满足要求
                        if key['last-S'] < key['last-F']:
                            self.debug.debug_print([cycle_num, 'Cycle:', key['last-S'], key['last-F']])  # 用于调试程序
                            self.cycle_save(_data_, Start=key['last-S'], Finish=key['last-F'])  # 两掘进段间隔满足要求，对上一掘进段进行保存
                            cycle_num += 1  # 每天数据所划分出的掘进段编号
                    else:
                        key['now-S'] = key['last-S']  # 两个掘进段时间间隔不满足要求，需要将上一掘进段和当前掘进段进行合并
                    key['last-S'], key['last-F'] = key['now-S'], key['now-F']  # 将当前掘进段的开始和结束的行索引信息进行保存
                key['now-S'], key['now-F'] = 0, 0  # 清空当前的索引记录

    @staticmethod  # 不强制要求传递参数
    def data_read(file_path: str) -> DataFrame:  # 规定file_path为字符型数据，返回值为（DataFrame）类型数组
        """调用文件读取模块（仅可读取csv数据类型）"""
        try:  # 首先尝试使用'gb2312'编码进行csv文件读取
            data = pd.read_csv(file_path, encoding='gb2312')  # 读取文件
        except UnicodeDecodeError:  # 若默认方式读取csv文件失败，则更换为' utf-8 '编码后重新进行尝试
            data = pd.read_csv(file_path, encoding='utf-8')  # 读取文件
        data.drop(data.tail(1).index, inplace=True)  # 删除文件最后一行
        data = data.loc[:, ~data.columns.str.contains('Unnamed')]  # 删除Unnamed空列
        data.fillna(0, inplace=True)
        return data

    @staticmethod  # 不强制要求传递参数
    def custom_read_model(file_path: str) -> DataFrame:  # 规定file_path为字符型数据，返回值为（DataFrame）类型数组
        """自定义文件读取模块，若定义了相关功能，则优先运行此功能，若未定义相关功能，则运行默认文件读取模块"""
        pass

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """原始数据的读取"""
        file_list = os.listdir(self.input)  # 获取输入文件夹下的所有文件名，并将其保存
        file_list.sort(key=lambda x: x)  # 对读取的文件列表进行重新排序
        visual = VISUAL(Sum=len(file_list), Out='Boring-cycle extract', Debug=self.debug)  # 可视化
        for num, file in enumerate(file_list):  # 遍历每个文件
            self.debug.debug_start(file)  # 用于调试程序
            data_raw = self.custom_read_model(os.path.join(self.input, file))  # 调用自定义文件读取模块读取文件
            if data_raw is None:  # 优先调用自定义模块，若自定义模块未定义，则调用默认模块
                data_raw = self.data_read(os.path.join(self.input, file))  # 调用文件读取模块读取文件
            after_process = self.cycle_splice(data_raw)  # 调用associated_data_process函数对相邻两天数据存在连续性的情况进行处理
            self.cycle_extract(after_process)  # 调用cycle_extract函数对原始数据中的循环段进行提取
            self.debug.debug_draw_N(after_process, self.parm[3])  # 用于调试程序
            visual.Print_info()  # 可视化

    def cycle_save(self, _data_: DataFrame, Start: int, Finish: int) -> None:  # 规定_data_为(DataFrame)类型数组，返回值无类型限定
        """对已经划分出的循环段数据进行保存"""
        cycle_data = _data_.iloc[Start:Finish, :]  # 提取掘进段数据
        cycle_data = cycle_data.reset_index(drop=True)  # 重建提取数据的行索引
        Mark = round(cycle_data.loc[0, self.parm[0]], 2)  # 获取每个掘进段的起始桩号
        Time = cycle_data.loc[0, self.parm[1]]  # 获取每个掘进段的时间记录
        Time = pd.to_datetime(Time, format='%Y-%m-%d %H:%M:%S')  # 对时间类型记录进行转换
        year, mon, d, h, m, s = Time.year, Time.month, Time.day, Time.hour, Time.minute, Time.second  # 获取时间记录的时分秒等
        csv_name = (self.Number, Mark, year, mon, d, h, m, s)  # 文件名
        csv_path = os.path.join(self.out, '%00005d %.2f-%s年%s月%s日 %s时%s分%s秒.csv' % csv_name)  # 循环段保存路径
        cycle_data.to_csv(csv_path, index=False, encoding='gb2312')  # 保存csv文件
        self.write_index(self.Number, {'stake': Mark, 'date': Time, 'time': (Finish - Start)})  # 索引文件记录
        self.Number += 1  # 循环段编号自增


class TBM_EXTRACT(object):
    """
    破岩关键数据提取配置模块，主要完成从原始数据中提取破岩关键数据的功能
    ****必选参数：破岩关键参数名称（par_name），若不传入相关参数，程序则抛出异常并终止运行
                原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输出路径，程序则抛出异常并终止运行
    ****可选参数：程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run）， 默认为开启状态
    """
    PARAMETERS = ['None']  # 破岩关键数据提取中的参数名称和顺序示例

    def __init__(self, input_path=None, out_path=None, key_parm=None, debug=False, Run=True):
        """初始化各参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.parm = key_parm  # 破岩关键参数
        self.debug = DEBUG(debug)  # 调试/修复程序
        """运行各模块"""
        if Run:
            self.check_parm()  # 检查参数是否正常
            self.create_extract_dir()  # 创建相关文件夹
            self.main()  # 读取文件

    def create_extract_dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):
            os.mkdir(self.out)  # 创建相关文件夹
        else:
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        curt_class = self.__class__.__name__
        if (not self.input) or (not self.out):  # 检查输入输出路径是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if not self.parm:  # 检查传入参数是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input parameters are null, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """关键破岩数据提取"""
        file_name_list = os.listdir(self.input)  # 获取输入文件夹下的所有文件名，并将其保存
        file_name_list.sort(key=lambda x: int(x[:5]))  # 对读取的文件列表进行重新排序
        visual = VISUAL(Sum=len(file_name_list), Out='Key-Data extract', Debug=self.debug)  # 可视化
        for num, file_name in enumerate(file_name_list):  # 遍历每个文件
            local_csv_path = os.path.join(self.input, file_name)  # 当前文件路径
            try:
                data = pd.read_csv(local_csv_path, encoding='gb2312')
            except UnicodeDecodeError:  # 若使用'gb2312'编码读取csv文件失败，则使用 'utf-8'编码后重新进行尝试
                data = pd.read_csv(local_csv_path, encoding='utf-8')
            col_name = list(data)  # 获取所有列名
            self.debug.debug_start(file_name)  # 用于调试程序
            for col in self.parm:
                self.debug.debug_print([col, col_name.index(col)])  # 用于调试程序
            self.debug.debug_finish(file_name)  # 用于调试程序
            data.loc[:, self.parm].to_csv(os.path.join(self.out, file_name), index=False, encoding='gb2312')  # 保存csv文件
            visual.Print_info()  # 可视化


class TBM_CLASS(object):
    """
    异常分类配置模块，主要完成异常循环段识别和分类的工作
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输入路径，程序则抛出异常并终止运行
                程序运行所需要的关键参数名称（par_name），若不传入参数，程序则会终止运行
    ****可选参数：程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run）， 默认为开启状态
    """
    PROJECT_COEFFICIENT = {'引松': 1 / 40.731, '引额-361': 1.227, '引额-362': 1.354, '引绰-667': 1.763, '引绰-668': 2.356}
    PARAMETERS = ['日期,', '桩号,', '刀盘转速,', '推进速度,', '刀盘扭矩,',
                  '总推力,', '刀盘转速设定值,', '推进速度设定值,', '推进位移,', '刀盘贯入度']
    SUB_FOLDERS = ['A1class-data', 'B1class-data', 'B2class-data', 'C1class-data',
                   'C2class-data', 'D1class-data', 'E1class-data', 'Norclass-data']  # 默认子文件夹

    def __init__(self, input_path=None, out_path=None, parameter=None, project_type='引绰-668',
                 L_min=0.3, V_max=120, V_set_var=15, missing_ratio=0.2, debug=False, Run=True):
        """初始化各参量"""
        self.index_exists = False  # 索引文件是否存在
        self.index_content = []  # 索引数据保存
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.sub_folder = self.SUB_FOLDERS  # 子文件夹
        self.parm = parameter  # 过程中用到的相关参数
        self.project_type = project_type  # 工程类型（'引松'、'引额-361'、'引额-362'、'引绰-667'、'引绰-668'）
        self.length_threshold_value = L_min  # 掘进长度下限值
        self.V_threshold_value = V_max  # 推进速度上限值，引松取120，额河取200
        self.V_set_variation = V_set_var  # 推进速度设定值变化幅度
        self.missing_ratio = missing_ratio  # 数据缺失率
        self.debug = DEBUG(debug)  # 调试/修复程序
        """运行各模块"""
        if Run:
            self.check_parm()  # 检查参数是否正常
            self.write_index(-1, {})  # 检查索引文件是否正常
            self.create_class_Dir()  # 创建相关文件夹
            self.main()

    def create_class_Dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):
            os.mkdir(self.out)  # 创建相关文件夹
        else:
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹
        for index, Dir in enumerate(self.sub_folder):  # 创建子文件夹
            self.sub_folder[index] = '%d-' % (index + 1) + Dir  # 子文件夹前面添加编号
            sub_folder_path = os.path.join(self.out, self.sub_folder[index])  # 子文件夹路径
            if not os.path.exists(sub_folder_path):
                os.mkdir(sub_folder_path)  # 创建子文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        curt_class = self.__class__.__name__
        if (not self.input) or (not self.out):  # 检查输入输出路径是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if (not self.parm) or (len(self.parm) != len(self.PARAMETERS)):  # 检查传入参数是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input parameters are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序

    def write_index(self, _Num_: int, _info_: dict) -> None:  # 规定_Num_为整型(int)，_info_为列表(list)，返回值返回值无类型限定
        """索引文件写入数据"""
        if self.debug.debug:
            return None
        global index_path  # 索引文件路径
        index_name = ['循环段', 'A', 'B1', 'B2', 'C1', 'C2', 'D', 'E', 'Normal']  # 索引文件中的标题
        index_data = list(_info_.values())  # 索引文件中的数据内容
        old_index = ['桩号', '日期', '掘进时间']
        if _Num_ == -1:  # 对索引文件内容进行配置
            if os.path.isfile(index_path):
                self.index_exists = True  # 判断索引文件是否存在
            if self.index_exists:  # 索引文件存在
                with open(index_path, 'r+', newline='', encoding='gb2312') as f:  # 只写模式打开索引文件
                    self.index_content = copy.deepcopy(f.readlines())  # 将原始索引文件内容进行保存
                for name in old_index:
                    if name not in self.index_content[0]:  # 判断索引文件中是否包含关键参数
                        self.index_exists = False
            if self.index_exists:  # 索引文件存在
                with open(index_path, 'w+', encoding='gb2312', newline='') as f:  # 打开索引文件
                    title = self.index_content[0].replace('\r\n', '').split(',')[:len(old_index) + 1] + index_name[1:]
                    csv.writer(f).writerow(title)  # 向索引文件写入标题
            else:  # 索引文件不存在
                with open(index_path, 'w+', encoding='gb2312', newline='') as f:  # 创建新的索引文件
                    csv.writer(f).writerow(index_name)  # 写入标题内容
        else:
            if self.index_exists:  # 索引文件存在
                try:
                    data = self.index_content[_Num_].replace('\r\n', '').split(',')[:len(old_index) + 1] + index_data
                except IndexError:
                    data = [str(_Num_)] + ['-' for _ in range(3)] + index_data  # 数据内容
            else:
                data = [_Num_] + index_data  # 数据内容
            with open(index_path, 'a', encoding='gb2312', newline='') as f:  # 打开索引文件
                csv.writer(f).writerow(data)  # 写入数据

    def A_premature(self, _cycle_: DataFrame) -> str:  # 规定_cycle_为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是A_premature (循环段掘进长度过短 L<0.3m)"""
        Anomaly_classification = 'Normal'  # 异常分类
        start_length = _cycle_.loc[0, self.parm[8]]  # 获取循环段开始点位移,推进位移（self.parm[8]）
        end_length = _cycle_.loc[_cycle_.shape[0] - 1, self.parm[8]]  # 获取循环段结束点位移,推进位移（self.parm[8]）
        length = (end_length - start_length) / 1000  # 循环段掘进长度
        if length < self.length_threshold_value:
            Anomaly_classification = 'A'  # 异常分类A
        return Anomaly_classification  # 数据分类的结果(Anomaly_classification)

    def B1_markAndModify(self, _cycle_: DataFrame) -> str:  # 规定_cycle_为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是B1_markAndModify (循环段速度值超限 V>120mm/min)"""
        Anomaly_classification = 'Normal'  # 异常分类
        data_V = _cycle_.loc[:, self.parm[3]].values  # 获取推进速度并转化类型，推进速度（self.parm[3]）
        data_mean, data_std = np.mean(data_V), np.std(data_V)  # 获取推进速度均值和标准差
        for V in data_V:
            if (V > self.V_threshold_value) and (V > data_mean + 3 * data_std):
                Anomaly_classification = 'B1'  # 异常分类B1
                break
        return Anomaly_classification  # 数据分类的结果(Anomaly_classification)

    def B2_constant(self, _cycle_: DataFrame) -> str:  # 规定_cycle_为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是B2_constant (循环段数据传输异常 刀盘推力连续5s不发生变化)"""
        Anomaly_classification = 'Normal'  # 异常分类
        data_F = _cycle_.loc[:, self.parm[5]].values  # 获取刀盘推力并转化类型，刀盘推力（self.parm[5]）
        for i in range(len(data_F) - 4):
            if (not np.std(data_F[i:i + 5])) and (np.mean(data_F[i:i + 5])):  # 判断刀盘推力是否连续五个数值稳定不变
                Anomaly_classification = 'B2'
                break
        return Anomaly_classification  # 数据分类的结果(Anomaly_classification)

    def C1_sine(self, _cycle_: DataFrame) -> str:  # 规定_cycle_为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是C1_sine (循环段刀盘扭矩出现正弦波扭矩)"""
        Anomaly_classification = 'Normal'  # 异常分类
        data_T = _cycle_.loc[:, self.parm[4]]  # 获取刀盘扭矩，刀盘扭矩（self.parm[4]）
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
        return Anomaly_classification  # 数据分类的结果(Anomaly_classification)

    def C2_shutdown(self, _cycle_: DataFrame) -> str:  # 规定_cycle_为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是C2_shutdown (循环段内机器发生短暂停机)"""
        Anomaly_classification = 'Normal'  # 异常分类
        N_set = _cycle_.loc[:, self.parm[6]].values  # 获取刀盘转速设定值，刀盘转速设定值（self.parm[6]）
        V_set = _cycle_.loc[:, self.parm[7]].values  # 获取推进速度设定值，推进速度设定值（self.parm[7]）
        for N_set_value, V_set_value in zip(N_set, V_set):
            if V_set_value == 0 and N_set_value > 0.1:
                Anomaly_classification = 'C2'
                break
        return Anomaly_classification  # 数据分类的结果(Anomaly_classification)

    def D_adjust_setting(self, _cycle_: DataFrame) -> str:  # 规定_cycle_为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是D_adjust_setting (循环段内多次调整推进速度设定值)"""
        Anomaly_classification = 'Normal'  # 异常分类
        data_V = _cycle_.loc[:, self.parm[3]]  # 获取推进速度，推进速度（self.parm[3]）
        V_mean, V_std = data_V.mean(), data_V.std()  # 获取推进速度均值和标准差
        rule = ((data_V < 0) | (data_V > self.V_threshold_value) | (data_V > V_mean + 3 * V_std))  # 满足条件的数据
        index = np.arange(data_V.shape[0])[rule]  # 满足条件的索引
        _cycle_ = _cycle_.drop(index, axis=0)  # 删除相关数据
        _cycle_.index = [i for i in range(_cycle_.shape[0])]  # 重建新数据集的行索引
        data_V_set = (_cycle_.loc[:, self.parm[7]] * self.PROJECT_COEFFICIENT[self.project_type]).std()  # 获取推进速度设定值的方差
        if data_V_set > self.V_set_variation:
            Anomaly_classification = 'D'  # 异常分类D
        return Anomaly_classification  # 数据分类的结果(Anomaly_classification)

    def E_missing_ratio(self, _cycle_: DataFrame) -> str:  # 规定_cycle_为DataFrame类型数组(DataFrame)，返回值类型为字符型(str)
        """判断数据类型是不是E_missing_ratio (循环段内数据缺失过多)"""
        Anomaly_classification = 'Normal'  # 异常分类
        data_time = _cycle_.loc[:, self.parm[0]].values  # 获取日期并转化类型，日期（self.parm[0]）
        time_start = pd.to_datetime(data_time[0], format='%Y-%m-%d %H:%M:%S')  # 循环段开始日期
        time_finish = pd.to_datetime(data_time[-1], format='%Y-%m-%d %H:%M:%S')  # 循环段结束日期
        time_diff = (time_finish - time_start).seconds  # 时间差，以s为单位
        time_len = len(data_time)  # 实际时间
        missing_ratio = (time_diff - time_len) / time_diff  # 缺失率计算
        if missing_ratio > self.missing_ratio:
            Anomaly_classification = 'E'  # 异常分类E
        return Anomaly_classification  # 数据分类的结果(Anomaly_classification)

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """数据分类"""
        csv_list = os.listdir(self.input)  # 获取输入文件夹下的所有文件名，并将其保存
        csv_list.sort(key=lambda x: int(x[:5]))  # 对读取的文件列表进行重新排序
        visual = VISUAL(Sum=len(csv_list), Out='Data-Class', Debug=self.debug)  # 可视化
        for cycle, name in enumerate(csv_list):
            local_csv_path = os.path.join(self.input, name)
            try:
                data = pd.read_csv(local_csv_path, encoding='gb2312')
            except UnicodeDecodeError:  # 若默认方式读取csv文件失败，则添加'gb2312'编码后重新进行尝试
                data = pd.read_csv(local_csv_path)
            if self.A_premature(data) == 'Normal':
                RS_Index = self.custom_get_RS_index_model(data)  # 调用自定义函数，获取空推、上升、稳定、下降的变化点
                if RS_Index is None:  # 优先调用自定义模块，若自定义模块未定义，则调用默认模块
                    RS_Index = self.get_RS_index(data)  # 调用函数，获取空推、上升、稳定、下降的变化点
                this_data = data.loc[RS_Index['rise']:RS_Index['steadyE'], :]  # 提取出上升段和稳定段数据
                this_data = this_data.reset_index(drop=True)  # 重建提取数据的行索引
                this_data_steady = data.loc[RS_Index['steadyS']:RS_Index['steadyE'], :]  # 提取出稳定段数据
                this_data_steady = this_data_steady.reset_index(drop=True)  # 重建新数据集的行索引
                func = {'A': self.A_premature(data),  # 调用相关模块判断是否为A类异常
                        'B1': self.B1_markAndModify(this_data),  # 调用相关模块判断是否为B1类异常
                        'B2': self.B2_constant(this_data),  # 调用相关模块判断是否为B2类异常
                        'C1': self.C1_sine(this_data),  # 调用相关模块判断是否为C1类异常
                        'C2': self.C2_shutdown(this_data_steady),  # 调用相关模块判断是否为C2类异常
                        'D': self.D_adjust_setting(this_data_steady),  # 调用相关模块判断是否为D类异常
                        'E': self.E_missing_ratio(this_data),  # 调用相关模块判断是否为E类异常
                        'Normal': ''}
            else:
                func = {'A': 'A', 'B1': '', 'B2': '', 'C1': '', 'C2': '', 'D': '', 'E': '', 'Normal': ''}
            normal = True  # 定义循环段初始为正常循环段类型
            for num, abnormal, result in zip([i for i in range(len(func))], list(func.keys()), list(func.values())):
                target_csv_path = os.path.join(os.path.join(self.out, self.sub_folder[num]), name)  # 异常数据存放位置
                if abnormal == result:  # 判断循环段是否是该类型异常
                    func[abnormal] = 'True'  # 循环段判断为该类型异常，将异常类型替换为True（例：{'A': 'A'} -> 'True'{'A': 'True'}）
                    normal = False  # 将循环段类型更改为异常循环段
                    shutil.copyfile(local_csv_path, target_csv_path)  # 复制文件到指定位置
                else:
                    func[abnormal] = ''  # 循环段判断不属于该类型异常，将异常类型替换为空（例：{'A': 'A'} -> 'True'{'A': ''}）
            if normal:
                target_csv_path = os.path.join(os.path.join(self.out, self.sub_folder[-1]), name)  # 异常数据存放位置
                func['Normal'] = 'True'  # 循环段不属于上述异常，将其判断为正常循环段（例：{'Normal': ''} -> {'Normal': 'True'}）
                shutil.copyfile(local_csv_path, target_csv_path)  # 复制文件到指定位置
            self.write_index(int(name[:5]), func)  # 将记录写入索引文件
            visual.Print_info()  # 可视化

    def get_RS_index(self, _data_):
        """获取空推、上升、稳定、下降的关键点"""
        def get_index(data, ratio, limit, short=False):
            raw_V = copy.deepcopy(data).values
            start, finish, Rise, Steady, count, First = 0, 0, 0, 0, 1, True
            for row in range(3, len(raw_V) - 3):
                if max(raw_V[row - 3:row - 1]) <= 0.1 and raw_V[row] > 0.1:
                    Rise = start = row
                if raw_V[row] > 0.1 and max(raw_V[row + 1:row + 3]) <= 0.1 or row == len(raw_V) - 1:
                    Steady = finish = row
                if finish - start > ratio * len(raw_V):
                    while First or (Steady - Rise >= limit * len(raw_V)):
                        First, backdate = False, 1
                        kde = SMNP.KDEUnivariate(abs(np.diff(raw_V[Rise:Steady])))  # 核密度估计
                        kde.fit(kernel='gau', bw="scott", fft=True, gridsize=200, cut=3)  # 核密度估计
                        KDE_Diff_mean = float(kde.support[np.where(kde.density == np.max(kde.density))])  # 推进速度差值的均值
                        kde = SMNP.KDEUnivariate(raw_V[Rise:Steady])  # 核密度估计
                        kde.fit(kernel='gau', bw="scott", fft=True, gridsize=200, cut=3)  # 核密度估计
                        KDE_mean = float(kde.support[np.where(kde.density == np.max(kde.density))])  # 稳定段推进速度的均值
                        for index, value in enumerate(raw_V[Rise:Steady]):
                            value_diff = count * KDE_Diff_mean * (math.log(backdate + 3, 1.3))
                            if short or (value > 0.1 and abs(value-raw_V[Rise+index-backdate]) <= value_diff):
                                backdate = 1
                                if value >= KDE_mean:
                                    Steady = Rise + index
                                    break
                            else:
                                backdate += 1
                        count += 0.5
                    return Rise, Steady

        rise, steadyS = get_index(_data_.loc[:, self.parm[3]], ratio=0.1, limit=0.3)
        _, steadyE = get_index(_data_.loc[::-1, self.parm[3]], ratio=0.05, limit=0.01, short=True)
        RS_index = {'rise': rise, 'steadyS': steadyS, 'steadyE': _data_.shape[0] - steadyE}
        return RS_index

    def custom_get_RS_index_model(self, _data_: DataFrame) -> dict:
        """自定义获取空推、上升、稳定、下降的关键点模块，若定义了相关功能，则优先运行此功能，若未定义相关功能，则运行默认模块"""
        pass


class TBM_CLEAN(object):
    """
    异常数据清理修正模块，主要完成异常循环段修正的工作
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输入路径，程序则抛出异常并终止运行
                程序运行所需要的关键参数名称（par_name），若不传入参数，程序则会终止运行
    ****可选参数：程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run）， 默认为开启状态
    """
    PARAMETERS = ['日期,', '桩号,', '刀盘转速,', '推进速度,', '刀盘扭矩,',
                  '总推力,', '刀盘转速设定值,', '推进速度设定值,', '推进位移,', '刀盘贯入度']
    SUB_FOLDERS = ['NorA1class-data', 'NorB1class-data', 'NorB2class-data', 'NorC1class-data',
                   'NorC2class-data', 'NorD1class-data', 'NorE1class-data', 'Norclass-data', ]

    def __init__(self, input_path=None, out_path=None, parameter=None, V_max=120, debug=False, Run=True):
        """初始化各参量"""
        self.parm = parameter  # 过程中用到的相关参数
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.sub_folder = self.SUB_FOLDERS  # 文件输出路径
        self.V_threshold_value = V_max  # 推进速度上限值，引松取120，额河取200
        self.debug = DEBUG(debug)  # 调试/修复程序
        """运行各模块"""
        if Run:
            self.check_parm()  # 检查参数是否正常
            self.create_clean_Dir()  # 创建相关文件夹
            self.main()

    def create_clean_Dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):
            os.mkdir(self.out)  # 创建相关文件夹
        else:
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹
        for index, Dir in enumerate(self.sub_folder):  # 创建子文件夹
            self.sub_folder[index] = '%d-' % (index + 1) + Dir  # 子文件夹前面添加编号
            sub_folder_path = os.path.join(self.out, self.sub_folder[index])  # 子文件夹路径
            if not os.path.exists(sub_folder_path):
                os.mkdir(sub_folder_path)  # 创建子文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        curt_class = self.__class__.__name__
        if (not self.input) or (not self.out):  # 检查输入输出路径是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if (not self.parm) or (len(self.parm) != len(self.PARAMETERS)):  # 检查传入参数是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input parameters are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if len(self.sub_folder) != len(self.SUB_FOLDERS):  # 检查传入子文件夹数量是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input sub_folders are faulty, Please check!!!\033[0m')
            print(' ->-> %s' % curt_class, '\033[0;31mSuch as %s\033[0m' % self.SUB_FOLDERS)
            sys.exit()  # 抛出异常并终止程序

    def A_premature_Modify(self, _cycle_: DataFrame) -> DataFrame:  # 规定_cycle_为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对A_premature (循环段掘进长度过短 L<0.3m)类异常数据进行修正"""
        pass

    def B1_mark_Modify(self, _cycle_: DataFrame) -> DataFrame:  # 规定_cycle_为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对B1_markAndModify (循环段速度值超限 V>120mm/min)类异常数据进行修正"""
        data_V = _cycle_.loc[:, self.parm[3]].values  # 推进速度（self.parm[3]）
        data_mean, data_std = np.mean(data_V), np.std(data_V)  # 获取推进速度均值和标准差
        for i in range(len(data_V)):
            if data_V[i] > self.V_threshold_value or (data_V[i] > data_mean + 3 * data_std):
                replace = sum(data_V[i - 10:i]) / 10.0  # 采用前10个推进速度的平均值进行替换
                _cycle_.loc[i, self.parm[3]] = replace  # 采用前10个推进速度的平均值进行替换
        return _cycle_

    def B2_constant_Modify(self, _cycle_: DataFrame) -> DataFrame:  # 规定_cycle_为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对B2_constant (循环段数据传输异常 刀盘推力连续5s不发生变化)类异常数据进行修正"""
        pass

    def C1_sine_Modify(self, _cycle_: DataFrame) -> DataFrame:  # 规定_cycle_为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对C1_sine (循环段刀盘扭矩出现正弦波扭矩)类异常数据进行修正"""
        pass

    def C2_shutdown_Modify(self, _cycle_: DataFrame) -> DataFrame:  # 规定_cycle_为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对C2_shutdown (循环段内机器发生短暂停机)类异常数据进行修正"""
        pass

    def D_adjust_setting_Modify(self, _cycle_: DataFrame) -> DataFrame:  # 规定_cycle_为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对D_adjust_setting (循环段内多次调整推进速度设定值)类异常数据进行修正"""
        pass

    def E_missing_ratio_Modify(self, _cycle_: DataFrame) -> DataFrame:  # 规定_cycle_为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对E_missing_ratio (循环段内数据缺失过多)类异常数据进行修正"""
        pass

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """将数据类型进行汇总并保存"""
        except_name = ['A', 'B1', 'B2', 'C1', 'C2', 'D', 'E', 'Normal']  # 新添加索引数据标题
        for Type, Dir in zip(except_name, os.listdir(self.input)):
            csv_list = os.listdir(os.path.join(self.input, Dir))  # 获取输入文件夹下的所有文件夹名称，并将其保存
            csv_list.sort(key=lambda x: int(x[:5]))  # 对读取的文件列表进行重新排序
            visual = VISUAL(Sum=len(csv_list), Out='Data-Clean', Debug=self.debug)  # 可视化
            for cycle, name in enumerate(csv_list):  # 遍历输入文件夹下的所有子文件夹
                local_csv_path = os.path.join(self.input, Dir, name)  # 当前文件路径
                target_csv_path = os.path.join(self.out, self.sub_folder[except_name.index(Type)], name)  # 目标文件路径
                if Type == 'Normal':
                    shutil.copyfile(local_csv_path, target_csv_path)  # 将正常循环段数据复制到目标位置
                    if Dir == os.listdir(self.input)[-1]:
                        visual.Print_info(Clean=True)  # 可视化
                        continue
                    visual.Print_info(Clean=False)  # 可视化
                    continue  # 本循环段操作结束
                else:
                    try:
                        data = pd.read_csv(local_csv_path, encoding='gb2312')  # 读取异常循环段数据，编码为'gb2312'
                    except UnicodeDecodeError:
                        data = pd.read_csv(local_csv_path)  # 读取异常循环段数据，编码为默认
                if (Type == 'A') and (self.A_premature_Modify(data) is not None):
                    data.to_csv(target_csv_path, index=False, encoding='gb2312')  # 保存修正后'A'类循环段数据
                if (Type == 'B1') and (self.B1_mark_Modify(data) is not None):
                    data.to_csv(target_csv_path, index=False, encoding='gb2312')  # 保存修正后'B1'类循环段数据
                if (Type == 'B2') and (self.B2_constant_Modify(data) is not None):
                    data.to_csv(target_csv_path, index=False, encoding='gb2312')  # 保存修正后'B2'类循环段数据
                if (Type == 'C1') and (self.C1_sine_Modify(data) is not None):
                    data.to_csv(target_csv_path, index=False, encoding='gb2312')  # 保存修正后'C1'类循环段数据
                if (Type == 'C2') and (self.C2_shutdown_Modify(data) is not None):
                    data.to_csv(target_csv_path, index=False, encoding='gb2312')  # 保存修正后'C2'类循环段数据
                if (Type == 'D') and (self.D_adjust_setting_Modify(data) is not None):
                    data.to_csv(target_csv_path, index=False, encoding='gb2312')  # 保存修正后'D'类循环段数据
                if (Type == 'E') and (self.E_missing_ratio_Modify(data) is not None):
                    data.to_csv(target_csv_path, index=False, encoding='gb2312')  # 保存修正后'E'类循环段数据
                if Dir == os.listdir(self.input)[-1]:
                    visual.Print_info(Clean=True)  # 可视化
                    continue
                visual.Print_info(Clean=False)  # 可视化


class TBM_MERGE(object):
    """
    修正后数据合并模块，主要完成将修正后的数据集合并的工作
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输入路径，程序则抛出异常并终止运行
                程序运行所需要的关键参数名称（par_name），若不传入参数，程序则会终止运行
    ****可选参数：程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run）， 默认为开启状态
    """
    PARAMETERS = ['None']

    def __init__(self, input_path=None, out_path=None, debug=False, Run=True):
        """初始化各参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.debug = DEBUG(debug)  # 调试/修复程序
        """运行各模块"""
        if Run:
            self.check_parm()  # 检查参数是否正常
            self.create_merge_Dir()  # 创建相关文件夹
            self.main()

    def create_merge_Dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):
            os.mkdir(self.out)  # 创建相关文件夹
        else:
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        curt_class = self.__class__.__name__
        if (not self.input) or (not self.out):  # 检查输入输出路径是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """合并形成机器学习数据集"""
        for Dir in os.listdir(self.input):  # 遍历输入路径下的所有子文件夹
            Dir_path = os.path.join(self.input, Dir)  # 子文件夹路径
            if os.path.isdir(Dir_path):
                visual = VISUAL(Sum=len(os.listdir(Dir_path)), Out='Data-Merge', Debug=self.debug)  # 可视化
                for num, name in enumerate(os.listdir(Dir_path)):
                    local_csv_path = os.path.join(self.input, Dir, name)  # 当前文件路径
                    target_csv_path = os.path.join(self.out, name)  # 目标文件路径
                    shutil.copyfile(local_csv_path, target_csv_path)  # 复制文件值目标路径
                    if Dir == os.listdir(self.input)[-1]:
                        visual.Print_info(Clean=True)  # 可视化
                        continue
                    visual.Print_info(Clean=False)  # 可视化


class TBM_SPLIT(object):
    """
    内部段分割模块，完成从循环段提取上升段稳定段和下降段的功能
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输出路径，程序则抛出异常并终止运行
                关键参数名称（par_name），若不传入参数，程序则抛出异常并终止运行
    ****可选参数：程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run）， 默认为开启状态
    """
    SUB_FOLDERS = ['Free running', 'Loading', 'Boring', 'Loading and Boring', 'Boring cycle']
    PARAMETERS = ['推进位移', '推进速度', '贯入度', '推进速度设定值', '刀盘扭矩']

    def __init__(self, input_path=None, out_path=None, parameter=None, min_time=200,
                 min_length=0.1, debug=False, Run=True):
        """初始化各参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.sub_folder = self.SUB_FOLDERS  # 初始化子文件夹
        self.parm = parameter  # 初始化程序处理过程中需要用到的参数
        self.index_exists = False  # 索引文件是否存在
        self.index_content = []  # 索引数据保存
        self.index_number = 1  # 索引文件行位置记录
        self.min_time = min_time  # 最小掘进时长(s)
        self.min_length = min_length  # 最小掘进距离(m)
        self.debug = DEBUG(debug)  # 调试/修复程序
        """运行各模块"""
        if Run:
            self.check_parm()  # 检查参数是否正常
            self.write_index(-1, {})  # 检查索引文件是否正常
            self.create_split_Dir()  # 创建相关文件夹
            self.main()

    def create_split_Dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):  # 若保存内部段分割后数据的文件夹不存在
            os.mkdir(self.out)  # 创建相关文件夹
        else:  # 若保存内部段分割后数据的文件夹存在
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹
        for index, Dir in enumerate(self.sub_folder):  # 创建子文件夹
            self.sub_folder[index] = '%d-' % (index + 1) + Dir  # 子文件夹前面添加编号
            sub_folder_path = os.path.join(self.out, self.sub_folder[index])  # 子文件夹路径
            if not os.path.exists(sub_folder_path):
                os.mkdir(sub_folder_path)  # 创建子文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        curt_class = self.__class__.__name__  # 获取当前模块（class）的名称
        if (not self.input) or (not self.out):  # 检查输入输出路径是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if (not self.parm) or (len(self.parm) != len(self.PARAMETERS)):  # 检查传入参数是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input parameters are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if len(self.sub_folder) != len(self.SUB_FOLDERS):  # 检查传入子文件夹数量是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input sub_folders are faulty, Please check!!!\033[0m')
            print(' ->-> %s' % curt_class, '\033[0;31mSuch as %s\033[0m' % self.SUB_FOLDERS)
            sys.exit()  # 抛出异常并终止程序

    def write_index(self, _Num_: int, _info_: dict) -> None:  # 规定_Num_为整型(int)，_info_为列表(list)，返回值返回值无类型限定
        """索引文件写入数据"""
        if self.debug.debug:
            return None
        global index_path  # 索引文件路径
        index_name = ['循环段', '上升段起点', '稳定段起点', '稳定段终点']  # 索引文件中的标题
        index_data = list(_info_.values())  # 索引文件中的数据内容
        old_index = ['桩号', '日期', '掘进时间', 'A', 'B1', 'B2', 'C1', 'C2', 'D', 'E', 'Normal']
        if _Num_ == -1:  # 对索引文件内容进行配置
            if os.path.isfile(index_path):
                self.index_exists = True  # 判断索引文件是否存在
            if self.index_exists:  # 索引文件存在
                with open(index_path, 'r+', newline='', encoding='gb2312') as f:  # 只写模式打开索引文件
                    self.index_content = copy.deepcopy(f.readlines())  # 将原始索引文件内容进行保存
                for name in old_index:
                    if name not in self.index_content[0]:  # 判断索引文件中是否包含关键参数
                        self.index_exists = False
            if self.index_exists:  # 索引文件存在
                with open(index_path, 'w+', encoding='gb2312', newline='') as f:  # 打开索引文件，并清空内容
                    title = self.index_content[0].replace('\r\n', '').split(',')[:len(old_index) + 1] + index_name[1:]
                    csv.writer(f).writerow(title)  # 向索引文件写入标题
            else:  # 索引文件不存在
                with open(index_path, 'w+', encoding='gb2312', newline='') as f:  # 创建新的索引文件
                    csv.writer(f).writerow(index_name)  # 写入标题内容
        elif _Num_ == -2:
            _Num_ = len(self.index_content)
            while self.index_number < _Num_:  # 对中间空行数据进行处理
                if self.index_exists:  # 索引文件存在
                    try:
                        data = self.index_content[self.index_number].replace('\r\n', '').split(',')[:len(old_index) + 1]
                    except IndexError:
                        data = [str(self.index_number)] + ['-' for _ in range(len(old_index))]  # 历史数据内容不足，则用'-'代替
                else:  # 索引文件不存在
                    data = [str(self.index_number)]  # 索引编号
                with open(index_path, 'a', encoding='gb2312', newline='') as f:  # 打开索引文件
                    csv.writer(f).writerow(data + ['' for _ in range(len(index_name) - 1)])  # 写入数据内容为''
                self.index_number += 1
        else:
            while self.index_number < _Num_:  # 对中间空行数据进行处理
                if self.index_exists:  # 索引文件存在
                    try:
                        data = self.index_content[self.index_number].replace('\r\n', '').split(',')[:len(old_index) + 1]
                    except IndexError:
                        data = [str(self.index_number)] + ['-' for _ in range(len(old_index))]  # 历史数据内容不足，则用'-'代替
                else:  # 索引文件不存在
                    data = [str(self.index_number)]  # 索引编号
                with open(index_path, 'a', encoding='gb2312', newline='') as f:  # 打开索引文件
                    csv.writer(f).writerow(data + ['' for _ in range(len(index_name) - 1)])  # 写入数据内容为''
                self.index_number += 1
            if self.index_exists:  # 索引文件存在
                try:
                    data = self.index_content[_Num_].replace('\r\n', '').split(',')[:len(old_index) + 1]  # 历史数据内容
                except IndexError:
                    data = [str(self.index_number)] + ['-' for _ in range(len(old_index))]  # 历史数据内容不足，则用'-'代替
            else:  # 索引文件不存在
                data = [str(self.index_number)]  # 索引编号
            with open(index_path, 'a', encoding='gb2312', newline='') as f:  # 打开索引文件
                csv.writer(f).writerow(data + index_data)  # 写入数据内容
            self.index_number += 1

    def segment_save(self, _data_, _name_: str, _key_: dict) -> None:  # 规定_name_为字符型（str），_key_为字典类型（dict）
        """对已经分割好的循环段文件进行保存"""
        save_data = [_data_.iloc[:_key_['rise'], :],  # 空推段数据
                     _data_.iloc[_key_['rise']:_key_['steadyS'], :],  # 上升段数据
                     _data_.iloc[_key_['steadyS']:_key_['steadyE'], :],  # 稳定段数据
                     _data_.iloc[_key_['rise']:_key_['steadyE'], :],  # 上升段和稳定段数据
                     _data_]  # 整个循环段数据
        for num, data in enumerate(save_data):
            save_path = os.path.join(self.out, self.sub_folder[num], _name_)
            data.to_csv(save_path, index=False, encoding='gb2312')  # 保存数据

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """对数据进行整体和细部分割"""
        file_name_list = os.listdir(self.input)  # 获取输入文件夹下的所有文件名，并将其保存
        file_name_list.sort(key=lambda x: int(x[:5]))  # 对读取的文件列表进行重新排序
        visual = VISUAL(Sum=len(file_name_list), Out='Data_Split', Debug=self.debug)  # 可视化
        for num, file in enumerate(file_name_list):  # 遍历每个文件
            local_csv_path = os.path.join(self.input, file)  # 当前数据文件路径
            try:  # 尝试采用编码'gb2312'读取数据
                data = pd.read_csv(local_csv_path, encoding='gb2312')  # 读取循环段文件
            except UnicodeDecodeError:  # 尝试采用默认编码' UTF-8 '读取数据
                data = pd.read_csv(local_csv_path)  # 读取循环段文件
            if data.shape[0] >= self.min_time:  # 判断是否为有效循环段(掘进时间>100s)
                length = (data.loc[data.shape[0] - 1, self.parm[0]] - data.loc[0, self.parm[0]]) / 1000  # 循环段掘进长度
                if length > self.min_length:  # 推进位移要大于0.1m,实际上推进位移有正有负
                    self.debug.debug_start(file)  # 用于调试程序
                    RS_Index = self.custom_get_RS_index_model(data)  # 调用自定义函数，获取空推、上升、稳定、下降的变化点
                    if RS_Index is None:  # 优先调用自定义模块，若自定义模块未定义，则调用默认模块
                        RS_Index = self.get_RS_index(data)  # 调用函数，获取空推、上升、稳定、下降的变化点
                    self.debug.debug_print(list(RS_Index.values()))  # 用于调试程序
                    self.segment_save(data, file, RS_Index)  # 数据保存
                    self.write_index(int(file[:5]), RS_Index)  # 索引文件中内容写入
                    self.debug.debug_draw_V(data, self.parm[1], RS_Index)  # 用于调试程序
            visual.Print_info()  # 可视化
        self.write_index(-2, {})  # 索引文件中内容写入

    def get_RS_index_1(self, _data_: DataFrame) -> dict:
        """获取空推、上升、稳定、下降的关键点--(类别1)"""
        def data_filter(_data_: DataFrame, par_name=None) -> DataFrame:  # 规定_data_为(DataFrame)类型数组，返回数组类型为DataFrame
            """参数滤波"""
            out_data = copy.deepcopy(_data_)  # 复制一个_data_，并对其进行滤波（复制是为了防止原始的_data_发生改变）
            if par_name:  # 对所选参数进行滤波
                for col in par_name:
                    out_data.loc[:, col] = scipy.signal.savgol_filter(out_data.loc[:, col], 19, 4)  # 用巴特沃斯滤波器进行滤波
            return out_data
        
        _data_ = data_filter(_data_, self.parm[2:])  # 数据滤波
        T_mean = _data_[self.parm[4]].mean()
        V_set_mean = _data_[self.parm[3]].mean()  # 推进速度设定值索引（self.parameter[3]）    第一次求均值，用于索引中点
        mid_start_value = min(_data_[self.parm[3]][0:int(_data_[self.parm[3]].shape[0] / 3)])
        mid_point_start = 0  # 中点位置索引
        while _data_[self.parm[3]][mid_point_start] > mid_start_value:
            mid_point_start += 1
        mid_point = mid_point_start
        while _data_[self.parm[3]][mid_point] < V_set_mean:
            if mid_point > 0.7 * _data_[self.parm[3]].shape[0]:
                mid_point = int(_data_[self.parm[3]].shape[0] * 0.2)
            else:
                while _data_[self.parm[3]][mid_point] < V_set_mean or _data_[self.parm[3]][mid_point + 30] < V_set_mean:
                    mid_point += 1  # #############有修改
        steadyE = _data_.shape[0] - 1  # 稳定段结束位置索引
        while _data_[self.parm[4]][steadyE] <= T_mean:  # 判断稳定段结束点
            steadyE -= 1
        if mid_point and mid_point <= 0.7 * _data_[self.parm[3]].shape[0]:
            rise = mid_point  # 上升段开始位置处索引
            while abs(_data_[self.parm[2]][rise]) > 0 and rise > 10:  # 刀盘贯入度度索引（self.parameter[2]） ########
                rise -= 1
            steadyS = mid_point
            V_set_ = _data_[self.parm[3]]  # #改改改改改改改改改改改改改改改[mid_point_start:int(_data_[self.parameter[3]].shape[0]/2)]
            # while V_set_[steadyS] - V_set_.mean() <= 0 or V_set_[steadyS+60]>=1.01*V_set_[steadyS]:
            while V_set_[steadyS] - V_set_.mean() <= 0 or (
                    max(V_set_[steadyS:steadyS + 60]) - min(V_set_[steadyS:steadyS + 60]) >= 0.02 * V_set_[steadyS]):
                steadyS += 1
            if steadyE - steadyS > 300:
                steady_Vsetmean = V_set_.iloc[steadyS:steadyS + 300].mean()
                steady_Vset_mean = min(0.95 * steady_Vsetmean, steady_Vsetmean - 3)
            else:
                steady_Vsetmean = V_set_.iloc[steadyS:steadyE].mean()
                steady_Vset_mean = min(0.95 * steady_Vsetmean, steady_Vsetmean - 3)
            while V_set_.iloc[steadyS] < steady_Vset_mean:  # 稳定段开始位置处的均值是否大于整个稳定段推进速度均值
                steadyS += 1
            RS_index = {'rise': rise, 'steadyS': steadyS, 'steadyE': steadyE}
        else:
            RS_index = {'rise': 0, 'steadyS': 0, 'steadyE': 0}
        return RS_index

    def get_RS_index(self, _data_: DataFrame) -> dict:
        """获取空推、上升、稳定、下降的关键点--(类别2)"""
        def get_index(data, ratio, limit, short=False):
            raw_V = copy.deepcopy(data).values
            start, finish, Rise, Steady, count, First = 0, 0, 0, 0, 1, True
            for row in range(3, len(raw_V) - 3):
                if max(raw_V[row - 3:row - 1]) <= 0.1 and raw_V[row] > 0.1:
                    Rise = start = row
                if raw_V[row] > 0.1 and max(raw_V[row + 1:row + 3]) <= 0.1 or row == len(raw_V) - 1:
                    Steady = finish = row
                if finish - start > ratio * len(raw_V):
                    while First or (Steady - Rise >= limit * len(raw_V)):
                        First, backdate = False, 1
                        kde = SMNP.KDEUnivariate(abs(np.diff(raw_V[Rise:Steady])))  # 核密度估计
                        kde.fit(kernel='gau', bw="scott", fft=True, gridsize=200, cut=3)  # 核密度估计
                        KDE_Diff_mean = float(kde.support[np.where(kde.density == np.max(kde.density))])  # 推进速度差值的均值
                        kde = SMNP.KDEUnivariate(raw_V[Rise:Steady])  # 核密度估计
                        kde.fit(kernel='gau', bw="scott", fft=True, gridsize=200, cut=3)  # 核密度估计
                        KDE_mean = float(kde.support[np.where(kde.density == np.max(kde.density))])  # 稳定段推进速度的均值
                        for index, value in enumerate(raw_V[Rise:Steady]):
                            value_diff = count * KDE_Diff_mean * (math.log(backdate + 3, 1.3))
                            if short or (value > 0.1 and abs(value-raw_V[Rise+index-backdate]) <= value_diff):
                                backdate = 1
                                if value >= KDE_mean:
                                    Steady = Rise + index
                                    break
                            else:
                                backdate += 1
                        count += 0.5
                    return Rise, Steady

        rise, steadyS = get_index(_data_.loc[:, self.parm[1]], ratio=0.1, limit=0.4)
        _, steadyE = get_index(_data_.loc[::-1, self.parm[1]], ratio=0.05, limit=0.01, short=True)
        RS_index = {'rise': rise, 'steadyS': steadyS, 'steadyE': _data_.shape[0] - steadyE}
        return RS_index

    def custom_get_RS_index_model(self, _data_: DataFrame) -> dict:
        """自定义获取空推、上升、稳定、下降的关键点模块，若定义了相关功能，则优先运行此功能，若未定义相关功能，则运行默认模块"""
        pass


class TBM_FILTER(object):
    """
    数据降噪模块，完成对循环段数据滤波的功能
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输出路径，程序则抛出异常并终止运行
    ****可选参数：关键参数名称（par_name），若传入参数，则仅对传入的参数进行降噪，若不传入参数，则对所有参数进行降噪
                程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run）， 默认为开启状态
    """
    PARAMETERS = ['None']

    def __init__(self, input_path=None, out_path=None, parameter=None, debug=False, Run=True):
        """初始化各参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.parm = parameter  # 初始化待滤波参数名称
        self.debug = DEBUG(debug)  # 调试/修复程序
        """运行各模块"""
        if Run:
            self.check_parm()  # 检查参数是否正常
            self.create_filter_dir()  # 创建相关文件夹
            self.main()

    def create_filter_dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):  # 保存滤波后数据的文件夹不存在
            os.mkdir(self.out)  # 创建相关文件夹
        else:  # 保存滤波后数据的文件夹存在
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        curt_class = self.__class__.__name__  # 获取当前模块（class）的名称
        if (not self.input) or (not self.out):  # 检查输入输出路径是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序

    @staticmethod  # 不强制要求传递参数
    def ButterWorthFilter(_data_: DataFrame) -> ndarray:  # 规定_data_为DataFrame类型，返回值为 array 类型
        """巴特沃斯滤波器"""
        return scipy.signal.savgol_filter(_data_, 19, 4)  # 巴特沃斯滤波器，滑动窗口长度为19，滤波阶数为4

    @staticmethod  # 不强制要求传递参数
    def custom_filter_model(_data_: DataFrame) -> ndarray:  # 规定_data_为DataFrame类型
        """自定义滤波器模块，若定义了相关功能，则优先运行此功能，若未定义相关功能，则运行默认滤波器模块"""
        pass

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """依次读取每个循环段数据"""
        file_name_list = os.listdir(self.input)  # 获取输入文件夹下的所有循环段名称，并将其保存
        visual = VISUAL(Sum=len(file_name_list), Out='Data filter', Debug=self.debug)  # 可视化
        for num, file_name in enumerate(file_name_list):  # 遍历每个文件
            local_csv_path = os.path.join(self.input, file_name)  # 当前循环段数据存放路径
            try:  # 尝试采用编码'gb2312'读取数据
                data = pd.read_csv(local_csv_path, encoding='gb2312')  # 读取循环段数据，编码'gb2312'
            except UnicodeDecodeError:  # 若采用编码'gb2312'读取数据失败，则尝试采用默认编码读取数据
                data = pd.read_csv(local_csv_path)  # 读取循环段数据，编码使用默认值
            if self.parm != ['']:  # 若传入待滤波参数名称，则仅对所传入的参数数据进行滤波
                for col in self.parm:
                    after_filter = self.custom_filter_model(data.iloc[:, col])  # 调用自定义数据绘图模块进行绘图并保存
                    if after_filter is None:  # 优先调用自定义模块，若自定义模块未定义，则调用默认模块
                        after_filter = self.ButterWorthFilter(data.iloc[:, col])  # 调用默认数据绘图模块进行绘图并保存
                    data.iloc[:, col] = after_filter
            else:  # 若未传入待滤波的参数名称，则采用默认方式，即对所有数值型数据进行滤波
                for col in range(data.shape[1]):
                    if type(data.iloc[0, col]) != type('str'):
                        after_filter = self.custom_filter_model(data.iloc[:, col])  # 调用自定义数据绘图模块进行绘图并保存
                        if after_filter is None:  # 优先调用自定义模块，若自定义模块未定义，则调用默认模块
                            after_filter = self.ButterWorthFilter(data.iloc[:, col])  # 调用默认数据绘图模块进行绘图并保存
                        data.iloc[:, col] = after_filter
            data.to_csv(os.path.join(self.out, file_name), index=False, encoding='gb2312')  # 保存滤波后的循环段数据
            visual.Print_info()  # 可视化


class TBM_REPORT(object):
    """
    参数绘图模块，完成对循环段数据生成PDF的功能
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输出路径，程序则抛出异常并终止运行
                关键参数名称（par_name），若不传入参数，程序则抛出异常并终止运行
    ****可选参数：程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run）， 默认为开启状态
    """
    pdfmetrics.registerFont(TTFont('SimSun', 'STSONG.TTF'))
    ROCK_GRADE = {1: 'Ⅰ', 2: 'Ⅱ', 3: 'Ⅲ', 4: 'Ⅳ', 5: 'Ⅴ', 6: 'Ⅵ'}  # 定义围岩等级和与之对应的字符表达（字典类型）
    PARAMETERS = ['桩号', '日期', '推进位移']

    def __init__(self, input_path=None, _input_pic_=None, out_path=None, parameter=None, debug=False, Run=True):
        """初始化各参量"""
        self.size_font = 8  # 页面字体大小为8
        self.type_font = 'SimSun'  # 页面字体类型
        self.page = 1  # 用于存储当前页
        self.parm = parameter  # 参数列（参数名称）
        self.input = input_path  # 初始化输入路径
        self.input_pic = _input_pic_  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.debug = DEBUG(debug)  # 调试/修复程序
        if Run:
            self.check_parm()  # 检查参数是否正常
            self.create_report_Dir()  # 创建相关文件夹
            self.main()

    def create_report_Dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):
            os.mkdir(self.out)  # 创建相关文件夹
        else:
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        curt_class = self.__class__.__name__  # 获取当前模块（class）的名称
        if (not self.input) or (not self.out):  # 检查输入输出路径是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if (not self.parm) or (len(self.parm) != len(self.PARAMETERS)):  # 检查传入参数是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input parameters are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序

    def add_footer_info(self, Object) -> None:  # 规定返回值无类型限定/无返回值:
        """添加每页页脚"""
        Object.setFont(self.type_font, self.size_font)  # 设置字体类型及大小
        Object.setFillColor(colors.black)  # 设置字体颜色为黑色
        Object.drawString(105 * mm, 10 * mm, f'Page%d' % self.page)  # 添加页脚信息
        self.page += 1  # 页脚页码自增

    def add_text_info(self, Object, _info_: list) -> None:  # 规定返回值无类型限定/无返回值
        """添加正文信息"""
        format_data = []  # 用于存储页面信息
        for row in range(3):  # 将_info_信息转换为符合要求的形式
            format_data.append(_info_[2 * row][0] + _info_[2 * row + 1][0])
            format_data.append(_info_[2 * row][1] + _info_[2 * row + 1][1])
            format_data.append(['' for _ in range(12)])
        Cell_w = [13 * mm, 9 * mm, 12 * mm, 13 * mm, 13 * mm, 25 * mm, 13 * mm, 9 * mm, 12 * mm, 13 * mm, 13 * mm,
                  25 * mm]  # 表格列宽信息
        Cell_h = [8 * mm, 8 * mm, 68 * mm, 8 * mm, 8 * mm, 68 * mm, 8 * mm, 8 * mm, 68 * mm]  # 表格行高信息
        sheet = Table(format_data, colWidths=Cell_w, rowHeights=Cell_h,  # 创建表格并写入信息
                      style={("FONT", (0, 0), (-1, -1), self.type_font, self.size_font),  # 字体类型
                             ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),  # 字体颜色为黑色
                             ('SPAN', (0, 2), (5, 2)), ('SPAN', (6, 2), (-1, 2)), ('SPAN', (0, 5), (5, 5)),  # 合并单元格
                             ('SPAN', (6, 5), (-1, 5)), ('SPAN', (0, 8), (5, 8)), ('SPAN', (6, 8), (-1, 8)),  # 合并单元格
                             ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # 左右上下居中
                             ('INNERGRID', (0, 0), (-1, -1), 0.7, colors.black),  # 显示内部框线
                             ('BOX', (0, 0), (-1, -1), 0.7, colors.black)})  # 显示外部框线
        sheet.wrapOn(Object, 0, 0)  # 将sheet添加到Canvas中
        sheet.drawOn(Object, 20 * mm, 24 * mm)  # 将sheet添加到Canvas中

    def add_content_info(self, Object, _info_: list) -> None:  # 规定返回值无类型限定/无返回值
        """添加目录信息"""
        format_data = [['CATALOGUE']]  # 用于存储目录信息
        for row in range(50):
            if row < len(_info_):
                format_data.append(['%s-%s' % (_info_[row]['beg'], _info_[row]['end']),  # 每页起始-结束的循环段编号
                                    '', '%7.1f' % float(_info_[row]['stake']),  # 每页起始桩号
                                    '.' * 150, 'Page %d' % _info_[row]['page']])  # 每页页码
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

    @staticmethod  # 不强制要求传递参数
    def add_pic_info(Object, _Pic_: list) -> None:  # 规定返回值无类型限定/无返回值
        """添加图片信息"""
        pic_x, pic_y = [21 * mm, 106 * mm], [193 * mm, 109 * mm, 25 * mm]  # 图片位置信息
        for row in range(3):
            for col in range(2):
                _Image = _Pic_[2 * row + col]  # 读取图片
                if _Image:  # 若路径有效，则添加图片
                    if _Image[-3:] == 'svg':
                        drawing = svg2rlg(_Image)
                        drawing.scale(0.275, 0.265)  # 缩放
                        renderPDF.draw(drawing, Object, x=pic_x[col], y=pic_y[row])  # 位置
                    if _Image[-3:] == 'png':
                        Object.drawImage(image=_Image, x=pic_x[col], y=pic_y[row], width=83 * mm, height=66 * mm,
                                         anchor='c')

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """读取数据，并将数据转化为可识别的类型"""
        text_path = os.path.join(self.out, 'text.pdf')  # 正文pdf存储路径
        content_path = os.path.join(self.out, 'content.pdf')  # 目录pdf存储路径
        pdf_text = Canvas(filename=text_path, bottomup=1, pageCompression=1, encrypt=None)  # 创建正文pdf
        pdf_content = Canvas(filename=content_path, bottomup=1, pageCompression=1, encrypt=None)  # 创建目录pdf
        file_list = os.listdir(self.input)  # 获取循环段列表
        file_list.sort(key=lambda x: int(x[:5]))  # 对读取的文件列表进行重新排序
        key_val, pic_val, key_content = [], [], []  # 定义关键参数(key_value)、图片参数(pic_value)、目录参数（key_content）列表
        visual = VISUAL(Sum=int(len(file_list) / 6) + 1, Out='Create PDF', Debug=self.debug)  # 可视化
        for cycle, file_name in zip([i + 1 for i in range(len(file_list))], file_list):
            data = pd.read_csv(os.path.join(self.input, file_name), encoding='gb2312')  # 读取文件
            data_np = data.loc[:, self.parm].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
            key_val.append([['Number', ('%00005d' % cycle),  # 获取循环段编号(Num)
                             'Start No', '%sm' % round(data_np[0][0], 1),  # 获取桩号记录
                             'Start Time', data_np[0][1]],  # 获取循环段开始时间
                            ['Rock mass', '',  # 获取围岩等级(Rock_Mass)
                             'Length', '%4.2fm' % round((data_np[-1][2] - data_np[0][2]) / 1000, 2),  # 掘进长度
                             'End Time', data_np[-1][1]]])  # 获取结束时间
            pic_val.append(os.path.join(self.input_pic, file_name[:-3] + 'png'))  # 添加图片参数(pic_value)数值
            if (not cycle % 6) or (cycle == len(file_list)):  # 以6个为一组,剩余不足6个也输出
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
                if ((self.page + 1) % 50 == 0) or (cycle == len(file_list)):
                    self.add_content_info(pdf_content, key_content)
                    if cycle != len(file_list):
                        pdf_content.showPage()  # 新增一页
                    key_content.clear()
                key_val.clear(), pic_val.clear()  # 对变量进行初始化， 便于进行下一次操作
                visual.Print_info()  # 可视化
        pdf_text.save(), pdf_content.save()  # pdf保存
        self.MergePDF(content=content_path, text=text_path)  # 合并目录和正文

    def MergePDF(self, **kwargs) -> None:  # 规定返回值无类型限定/无返回值
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
        outputStream = open(os.path.join(self.out, 'TBM-Data.pdf'), "wb")
        output.write(outputStream)  # 写入到目标PDF文件
        outputStream.close(), _Pdf_[0].close(), _Pdf_[1].close()  # 关闭读取的文件
        os.remove(kwargs['content']), os.remove(kwargs['text'])


class TBM_PLOT(object):
    """
    参数绘图模块，完成对循环段数据进行绘图的功能
    ****必选参数：原始数据存放路径（input_path），若不传入输入路径，程序则抛出异常并终止运行
                生成数据保存路径（out_path），若不传入输出路径，程序则抛出异常并终止运行
                关键参数名称（par_name），若不传入参数，程序则抛出异常并终止运行（可对部分参数进行绘图）
    ****可选参数：程序调试/修复选项（debug），默认为关闭状态
                直接运行程序（Run），默认为开启状态
    """
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置字体
    plt.rcParams['axes.unicode_minus'] = False  # 坐标轴的负号正常显示
    plt.rcParams.update({'font.size': 17})  # 设置字体大小
    PARAMETERS = ['刀盘转速,', '刀盘转速设定值,', '推进速度,', '推进速度设定值,', '刀盘扭矩,', '总推力']

    def __init__(self, input_path=None, out_path=None, parameter=None, height=10,
                 weight=8, dpi=120, Format='png', show=False, debug=False, Run=True):
        """初始化各参量"""
        self.input = input_path  # 初始化输入路径
        self.out = out_path  # 初始化输出路径
        self.parm = parameter  # 掘进状态判定参数
        self.size = (height, weight)  # 图片大小（10*cm，8*cm）
        self.dpi = dpi  # 像素dpi=120
        self.format = Format  # 输出图片的格式
        self.show = show  # 是否展示图片
        self.debug = DEBUG(debug)  # 调试/修复程序
        """运行各模块"""
        if Run:
            self.check_parm()  # 检查参数是否正常
            self.create_pic_dir()  # 创建相关文件夹
            self.main()

    def create_pic_dir(self) -> None:  # 规定返回值无类型限定/无返回值
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out):  # 保存图片的文件夹不存在
            os.mkdir(self.out)  # 创建相关文件夹
        else:  # 保存图片的文件夹存在
            shutil.rmtree(self.out)  # 清空文件夹
            os.mkdir(self.out)  # 创建相关文件夹

    def check_parm(self) -> None:  # 规定返回值无类型限定/无返回值
        """检查传入参数是否正常"""
        curt_class = self.__class__.__name__  # 获取当前模块（class）的名称
        if (not self.input) or (not self.out):  # 检查输入输出路径是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input or output path are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序
        if (not self.parm) or (len(self.parm) != len(self.PARAMETERS)):  # 检查传入参数是否正常
            print(' ->-> %s' % curt_class, '\033[0;31mThe input parameters are faulty, Please check!!!\033[0m')
            sys.exit()  # 抛出异常并终止程序

    def default_parm_plot(self, _data_: DataFrame, _key_: dict) -> pyplot:  # 规定_key_为字典类型（dict）,返回值为绘制好的plt
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
        if _key_:  # 如果索引文件中空推段、上升段和稳定段的变化点存在，则在图中绘出
            plt.axvline(x=_key_['rise'] - 1, c="r", ls="-.")
            plt.axvline(x=_key_['steadyS'] - 1, c="r", ls="-.")
            plt.axvline(x=_key_['steadyE'] - 1, c="r", ls="-.")
        return plt

    def custom_plot_model(self, _data_: DataFrame, _key_: dict) -> pyplot:  # 规定_key_为字典类型（dict）,返回值为绘制好的plt
        """自定义绘图模块，若定义了相关功能，则优先运行此功能，若未定义相关功能，则运行默认绘图模块"""
        pass

    def main(self) -> None:  # 规定返回值无类型限定/无返回值
        """掘进参数可视化"""
        try:  # 尝试读取索引文件，若索引文件存在，则将['循环段', '上升段起点', '稳定段起点', '稳定段终点']保存至Index_value中
            global index_path  # 索引文件路径
            data_Index = pd.read_csv(index_path, index_col=False, encoding='gb2312')  # 读取索引文件
            try:  # 若索引文件中存在['循环段', '上升段起点', '稳定段起点', '稳定段终点']，则将其保存至Index_value中
                Index_value = data_Index.loc[:, ['循环段', '上升段起点', '稳定段起点', '稳定段终点']].values  # 将关键点保存至Index_value
            except KeyError:  # 若索引文件中不存在['循环段', '上升段起点', '稳定段起点', '稳定段终点']，则令Index_value为空[]
                Index_value = None  # 令Index_value为空[]
        except FileNotFoundError:  # 若索引文件存在，则令Index_value为空[]
            Index_value = None  # 令Index_value为空[]
        file_list = os.listdir(self.input)  # 获取输入文件夹下的所有文件名称，并将其保存
        file_list.sort(key=lambda x: int(x[:5]))  # 对读取的文件列表进行重新排序
        visual = VISUAL(Sum=len(file_list), Out='Drawing pic', Debug=self.debug)  # 可视化
        for index, file_name in enumerate(file_list):  # 遍历每个文件
            file_num = int(file_name[:5]) - 1  # 循环段编号(由于循环段是从1开始的)
            local_csv_path = os.path.join(self.input, file_name)  # 当前循环段数据存放路径
            try:  # 尝试采用编码'gb2312'读取数据
                data = pd.read_csv(local_csv_path, encoding='gb2312')  # 读取循环段数据，编码'gb2312'
            except UnicodeDecodeError:  # 若采用编码'gb2312'读取数据失败，则尝试采用默认编码读取数据
                data = pd.read_csv(local_csv_path)  # 读取循环段数据，编码使用默认值
            if Index_value is not None:  # 如果可以从索引文件中获取到['上升段起点', '稳定段起点', '稳定段终点']
                mark = {'rise': Index_value[file_num][1], 'steadyS': Index_value[file_num][2],
                        'steadyE': Index_value[file_num][3]}
            else:
                mark = {}
            Plt = self.custom_plot_model(data, mark)  # 调用自定义数据绘图模块进行绘图并保存
            if Plt is None:  # 优先调用自定义模块，若自定义模块未定义，则调用默认模块
                Plt = self.default_parm_plot(data, mark)  # 调用默认数据绘图模块进行绘图并保存
            pic_save_path = os.path.join(self.out, file_name[:-3] + self.format)  # 图片保存路径
            Plt.savefig(pic_save_path, dpi=self.dpi, format=self.format, bbox_inches='tight')  # 图片保存
            if self.show:
                Plt.show()
            Plt.close()  # 关闭画布
            visual.Print_info()  # 可视化


class VISUAL(object):
    """可视化输出"""
    def __init__(self, Sum, Out, Debug):
        self.Time_val = []
        self.Print = Out
        self.Sum = Sum
        self.Count = 1
        self.Debug = Debug
        self.time = time.time()

    def Print_info(self, Clean=True):
        if self.Debug.debug:
            return
        cpu_percent = psutil.cpu_percent()  # CPU占用
        mem_percent = psutil.Process(os.getpid()).memory_percent()  # 内存占用
        time_diff = time.time() - self.time  # 执行一个文件所需的时间
        self.Time_val.append(time_diff)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(self.Time_val) / len(self.Time_val)  # 计算平均时间
        sum_time = round(sum(self.Time_val) / 3600, 3)  # 计算程序执行的总时间
        print('\r', '->->', '[第%d个 / 共%d个]  ' % (self.Count, self.Sum), '[所用时间%ds / 平均时间%ds]'
              % (int(time_diff), int(mean_time)), ' ', '[CPU占用: %5.2f%% / 内存占用: %5.2f%%]'
              % (cpu_percent, mem_percent), '  ', '\033[0;33m累积时间:%6.3f小时\033[0m' % sum_time, end='')
        if self.Count >= self.Sum and Clean:
            sum_time = round(sum(self.Time_val) / 3600, 3)  # 计算程序执行的总时间
            print('\r', '->->', '\033[0;32m%s completed, which took %6.3f hours\033[0m' % (self.Print, sum_time))
        self.Count += 1
        self.time = time.time()


class message(object):
    window_width = 1000
    window_heigth = 500

    def __init__(self):

        self.path_input, self.path_output, self.parm, self.cycle, self.Class, self.clean, self.split, self.plot = self.get_config()
        self.Var_select = {'TBM_CYCLE': 0, 'TBM_EXTRACT': 0, 'TBM_CLASS': 0, 'TBM_CLEAN': 0, 'TBM_MERGE': 0,
                           'TBM_SPLIT': 0, 'TBM_FILTER': 0, 'TBM_REPORT': 0, 'TBM_PLOT': 0}
        self.Var_model = 'Normal'

        self.root_window = tkinter.Tk()
        self.frame_1 = Frame(self.root_window, width=self.window_width, height=self.window_heigth)
        self.frame_1.grid(column=0, row=0, padx=20, pady=5, sticky=(tkinter.W, tkinter.N, tkinter.E))

        self.frame_2 = Frame(self.root_window, width=self.window_width, height=self.window_heigth)
        self.frame_2.grid(column=0, row=0, padx=20, pady=5, sticky=(tkinter.W, tkinter.N, tkinter.E))

        self.frame_3 = Frame(self.root_window, width=self.window_width, height=self.window_heigth)
        self.frame_3.grid(column=0, row=0, padx=20, pady=5, sticky=(tkinter.W, tkinter.N, tkinter.E))

        self.input_path = 'D:\\'
        self.path_num = 0

        self.Var_cycle_parm = StringVar()
        self.Var_cycle_inpath = StringVar()
        self.Var_cycle_outpath = StringVar()
        self.Var_cycle_interval = StringVar()
        self.Var_cycle_selt = IntVar()

        self.Var_extract_parm = StringVar()
        self.Var_extract_inpath = StringVar()
        self.Var_extract_outpath = StringVar()
        self.Var_extract_selt = IntVar()

        self.Var_class_parm = StringVar()
        self.Var_class_inpath = StringVar()
        self.Var_class_outpath = StringVar()
        self.Var_class_selt = IntVar()
        self.Var_class_project = StringVar()
        self.Var_class_L_min = StringVar()
        self.Var_class_V_max = StringVar()
        self.Var_class_V_set_var = StringVar()
        self.Var_class_missing_ratio = StringVar()

        self.Var_clean_parm = StringVar()
        self.Var_clean_inpath = StringVar()
        self.Var_clean_outpath = StringVar()
        self.Var_clean_selt = IntVar()
        self.Var_clean_V_max = StringVar()

        self.Var_merge_parm = StringVar()
        self.Var_merge_inpath = StringVar()
        self.Var_merge_outpath = StringVar()
        self.Var_merge_selt = IntVar()

        self.Var_split_parm = StringVar()
        self.Var_split_inpath = StringVar()
        self.Var_split_outpath = StringVar()
        self.Var_split_selt = IntVar()
        self.Var_split_min_time = StringVar()
        self.Var_split_min_length = StringVar()

        self.Var_filter_parm = StringVar()
        self.Var_filter_inpath = StringVar()
        self.Var_filter_outpath = StringVar()
        self.Var_filter_selt = IntVar()

        self.Var_report_parm = StringVar()
        self.Var_report_inpath = StringVar()
        self.Var_report_outpath = StringVar()
        self.Var_report_selt = IntVar()

        self.Var_plot_parm = StringVar()
        self.Var_plot_inpath = StringVar()
        self.Var_plot_outpath = StringVar()
        self.Var_plot_selt = IntVar()
        self.Var_plot_weight = StringVar()
        self.Var_plot_height = StringVar()
        self.Var_plot_dpi = StringVar()
        self.Var_plot_type = StringVar()
        self.Var_plot_show = BooleanVar()

        self.model = StringVar()

        self.create_widgets_in_frame_3()
        self.create_widgets_in_frame_2()
        self.create_widgets_in_frame_1()

        self.frame_3.grid_forget()
        self.frame_2.grid_forget()

        self.root_window.mainloop()

        self.creative_conf()

    def cycle_model(self, index, model_name, Type):
        if Type == 'PARM':
            example = TBM_CYCLE(Run=False).PARAMETERS
            Label(self.frame_3, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_3, text=['示例:'] + example).grid(row=1 + 3 * index, column=1)
            Label(self.frame_3, text='参数:').grid(row=2 + 3 * index, column=0)
            self.Var_cycle_parm.set(self.parm['TBM_CYCLE'])
            Entry(self.frame_3, textvariable=self.Var_cycle_parm, width=100).grid(row=2 + 3 * index, column=1)
            Button(self.frame_3, text='更改', command=self.textEvent_cycle).grid(row=2 + 3 * index, column=2)
        if Type == 'PATH':
            Label(self.frame_2, text=model_name).grid(row=0 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='高级设置', command=self.settle_Event_cycle).grid(row=0 + 3 * index, column=2)
            Label(self.frame_2, text='源文件:').grid(row=1 + 3 * index, column=0)
            self.Var_cycle_inpath.set(self.path_input['TBM_CYCLE'])
            Entry(self.frame_2, textvariable=self.Var_cycle_inpath, width=100).grid(row=1 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='打开目录', command=self.openDirEvent_cycle).grid(row=1 + 3 * index, column=2)
            Label(self.frame_2, text='输   出:').grid(row=2 + 3 * index, column=0)
            self.Var_cycle_outpath.set(self.path_output['TBM_CYCLE'])
            Entry(self.frame_2, textvariable=self.Var_cycle_outpath, width=100).grid(row=2 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='另存目录', command=self.OutPathEvent_cycle).grid(row=2 + 3 * index, column=2)

    def settle_Event_cycle(self):
        window = Tk()
        window.geometry('700x200')
        window.title('TBM_CYCLE高级设置')
        Label(window, text='当两个循环段间时间间隔小于').grid(row=0, column=0)
        name_input = Text(window, width=10, height=1)  # width宽 height高
        name_input.insert('0.0', self.cycle['INTERVAL_TIME'])
        Label(window, text='s 可视为同一个循环段。').grid(row=0, column=2)
        name_input.grid(row=0, column=1)

        def get_inf():
            information = name_input.get('0.0', 'end')
            self.Var_cycle_interval.set(information)
            self.cycle['INTERVAL_TIME'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).grid(row=1, column=1)

    def textEvent_cycle(self):
        window = Tk()
        window.geometry('700x200')
        window.title('输入参数')
        name_input = Label(window, text='多个参数间用逗号隔开').pack()
        name_input = Text(window, width='100', height='3')  # width宽 height高
        name_input.pack()

        def get_inf():
            information = name_input.get('0.0', 'end')
            self.Var_cycle_parm.set(information)
            self.parm['TBM_CYCLE'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).pack()

    def openDirEvent_cycle(self):
        global index_path
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='打开目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_cycle_inpath.set(newDir)
        self.path_input['TBM_CYCLE'] = newDir
        output = newDir.replace(newDir.split('\\')[-1], '')
        index_path = os.path.join(output, 'Index-File.csv')  # 索引文件路径及名称
        self.Var_cycle_outpath.set(os.path.join(output, '[ TBM_CYCLE ]-AllDataSet'))
        self.path_output['TBM_CYCLE'] = os.path.join(output, '[ TBM_CYCLE ]-AllDataSet')
        self.Var_extract_inpath.set(os.path.join(output, '[ TBM_CYCLE ]-AllDataSet'))
        self.Var_extract_outpath.set(os.path.join(output, '[ TBM_EXTRACT ]-KeyDataSet'))
        self.path_input['TBM_EXTRACT'] = os.path.join(output, '[ TBM_CYCLE ]-AllDataSet')
        self.path_output['TBM_EXTRACT'] = os.path.join(output, '[ TBM_EXTRACT ]-KeyDataSet')
        self.Var_class_inpath.set(os.path.join(output, '[ TBM_EXTRACT ]-KeyDataSet'))
        self.Var_class_outpath.set(os.path.join(output, '[ TBM_CLASS ]-Class-Data'))
        self.path_input['TBM_CLASS'] = os.path.join(output, '[ TBM_EXTRACT ]-KeyDataSet')
        self.path_output['TBM_CLASS'] = os.path.join(output, '[ TBM_CLASS ]-Class-Data')
        self.Var_clean_inpath.set(os.path.join(output, '[ TBM_CLASS ]-Class-Data'))
        self.Var_clean_outpath.set(os.path.join(output, '[ TBM_CLEAN ]-Clean-Data'))
        self.path_input['TBM_CLEAN'] = os.path.join(output, '[ TBM_CLASS ]-Class-Data')
        self.path_output['TBM_CLEAN'] = os.path.join(output, '[ TBM_CLEAN ]-Clean-Data')
        self.Var_merge_inpath.set(os.path.join(output, '[ TBM_CLEAN ]-Clean-Data'))
        self.Var_merge_outpath.set(os.path.join(output, '[ TBM_MERGE ]-ML-Data'))
        self.path_input['TBM_MERGE'] = os.path.join(output, '[ TBM_CLEAN ]-Clean-Data')
        self.path_output['TBM_MERGE'] = os.path.join(output, '[ TBM_MERGE ]-ML-Data')
        self.Var_split_inpath.set(os.path.join(output, '[ TBM_MERGE ]-ML-Data'))
        self.Var_split_outpath.set(os.path.join(output, '[ TBM_SPLIT ]-A-ML2-Data'))
        self.path_input['TBM_SPLIT'] = os.path.join(output, '[ TBM_MERGE ]-ML-Data')
        self.path_output['TBM_SPLIT'] = os.path.join(output, '[ TBM_SPLIT ]-A-ML2-Data')
        self.Var_filter_inpath.set(os.path.join(output, '[ TBM_MERGE ]-ML-Data'))
        self.Var_filter_outpath.set(os.path.join(output, '[ TBM_FILTER ]-ML2-Data'))
        self.path_input['TBM_FILTER'] = os.path.join(output, '[ TBM_MERGE ]-ML-Data')
        self.path_output['TBM_FILTER'] = os.path.join(output, '[ TBM_FILTER ]-ML2-Data')
        self.Var_report_inpath.set(os.path.join(output, '[ TBM_MERGE ]-ML-Data'))
        self.Var_report_outpath.set(os.path.join(output, '[ TBM_REPORT ]-Pdf-Data'))
        self.path_input['TBM_REPORT'] = os.path.join(output, '[ TBM_MERGE ]-ML-Data')
        self.path_output['TBM_REPORT'] = os.path.join(output, '[ TBM_REPORT ]-Pdf-Data')
        self.Var_plot_inpath.set(os.path.join(output, '[ TBM_MERGE ]-ML-Data'))
        self.Var_plot_outpath.set(os.path.join(output, '[ TBM_PLOT ]-Pic'))
        self.path_input['TBM_PLOT'] = os.path.join(output, '[ TBM_MERGE ]-ML-Data')
        self.path_output['TBM_PLOT'] = os.path.join(output, '[ TBM_PLOT ]-Pic')

    def OutPathEvent_cycle(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='另存目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_cycle_outpath.set(newDir)
        self.path_output['TBM_CYCLE'] = newDir

    def extract_model(self, index, model_name, Type):
        if Type == 'PARM':
            example = TBM_EXTRACT(Run=False).PARAMETERS
            Label(self.frame_3, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_3, text=['示例:'] + example).grid(row=1 + 3 * index, column=1)
            Label(self.frame_3, text='参数:').grid(row=2 + 3 * index, column=0)
            self.Var_extract_parm.set(self.parm['TBM_EXTRACT'])
            Entry(self.frame_3, textvariable=self.Var_extract_parm, width=100).grid(row=2 + 3 * index, column=1)
            Button(self.frame_3, text='更改', command=self.textEvent_extract).grid(row=2 + 3 * index, column=2)
        if Type == 'PATH':
            Label(self.frame_2, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_2, text='源文件:').grid(row=1 + 3 * index, column=0, )
            self.Var_extract_inpath.set(self.path_input['TBM_EXTRACT'])
            Entry(self.frame_2, textvariable=self.Var_extract_inpath, width=100).grid(row=1 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='打开目录', command=self.openDirEvent_extract).grid(row=1 + 3 * index,
                                                                                              column=2)
            Label(self.frame_2, text='输   出:').grid(row=2 + 3 * index, column=0)
            self.Var_extract_outpath.set(self.path_output['TBM_EXTRACT'])
            Entry(self.frame_2, textvariable=self.Var_extract_outpath, width=100).grid(row=2 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='另存目录', command=self.OutPathEvent_extract).grid(row=2 + 3 * index,
                                                                                              column=2)

    def textEvent_extract(self):
        window = Tk()
        window.geometry('700x200')
        window.title('输入参数')
        name_input = Label(window, text='多个参数间用逗号隔开').pack()
        name_input = Text(window, width='100', height='3')  # width宽 height高
        name_input.pack()

        def get_inf():
            information = name_input.get('0.0', 'end')
            self.Var_extract_parm.set(information)
            self.parm['TBM_EXTRACT'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).pack()

    def openDirEvent_extract(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='打开目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_extract_inpath.set(newDir)
        self.path_input['TBM_EXTRACT'] = newDir

    def OutPathEvent_extract(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='另存目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_extract_outpath.set(newDir)
        self.path_output['TBM_EXTRACT'] = newDir

    def class_model(self, index, model_name, Type):
        if Type == 'PARM':
            example = TBM_CLASS(Run=False).PARAMETERS
            Label(self.frame_3, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_3, text=['示例:'] + example).grid(row=1 + 3 * index, column=1)
            Label(self.frame_3, text='参数:').grid(row=2 + 3 * index, column=0)
            self.Var_class_parm.set(self.parm['TBM_CLASS'])
            Entry(self.frame_3, textvariable=self.Var_class_parm, width=100).grid(row=2 + 3 * index, column=1)
            Button(self.frame_3, text='更改', command=self.textEvent_class).grid(row=2 + 3 * index, column=2)
        if Type == 'PATH':
            Label(self.frame_2, text=model_name).grid(row=0 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='高级设置', command=self.settle_Event_class).grid(row=0 + 3 * index, column=2)
            Label(self.frame_2, text='源文件:').grid(row=1 + 3 * index, column=0, )
            self.Var_class_inpath.set(self.path_input['TBM_CLASS'])
            Entry(self.frame_2, textvariable=self.Var_class_inpath, width=100).grid(row=1 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='打开目录', command=self.openDirEvent_class).grid(row=1 + 3 * index, column=2)
            Label(self.frame_2, text='输   出:').grid(row=2 + 3 * index, column=0)
            self.Var_class_outpath.set(self.path_output['TBM_CLASS'])
            Entry(self.frame_2, textvariable=self.Var_class_outpath, width=100).grid(row=2 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='另存目录', command=self.OutPathEvent_class).grid(row=2 + 3 * index, column=2)

    def settle_Event_class(self):
        window = Tk()
        window.geometry('700x200')
        window.title('TBM_CLASS高级设置')
        Label(window, text='工程类型').grid(row=0, column=0)
        Label(window, text='PROJECT:').grid(row=0, column=1)
        name_project = Text(window, width=8, height=1)  # width宽 height高
        name_project.insert('0.0', self.Class['PROJECT_TYPE'])
        Label(window, text='（引松, 引额-361, 引额-362, 引绰-667, 引绰-668）').grid(row=0, column=4)
        name_project.grid(row=0, column=2)

        Label(window, text='最小掘进长度（单位:m）').grid(row=1, column=0)
        Label(window, text='L-MIN:').grid(row=1, column=1)
        name_L_min = Text(window, width=8, height=1)  # width宽 height高
        name_L_min.insert('0.0', self.Class['LENGTH_MIN'])
        name_L_min.grid(row=1, column=2)

        Label(window, text='推进速度上限值（单位: mm/min）').grid(row=2, column=0)
        Label(window, text='V-MAX:').grid(row=2, column=1)
        name_V_max = Text(window, width=8, height=1)  # width宽 height高
        name_V_max.insert('0.0', self.Class['VELOCITY_MAX'])
        Label(window, text='（引松取120，额河取200）').grid(row=2, column=4)
        name_V_max.grid(row=2, column=2)

        Label(window, text='推进速度设定值变化幅度').grid(row=3, column=0)
        Label(window, text='V-set-VAR:').grid(row=3, column=1)
        name_V_set_var = Text(window, width=8, height=1)  # width宽 height高
        name_V_set_var.insert('0.0', self.Class['VELOCITY_SET_VARIATION'])
        name_V_set_var.grid(row=3, column=2)

        Label(window, text='数据缺失率（单位: %）').grid(row=4, column=0)
        Label(window, text='V-MAX:').grid(row=4, column=1)
        name_missing_ratio = Text(window, width=8, height=1)  # width宽 height高
        name_missing_ratio.insert('0.0', self.Class['MISSING_RATIO'])
        name_missing_ratio.grid(row=4, column=2)

        def get_inf():
            information = name_project.get('0.0', 'end')
            self.Var_class_project.set(information)
            self.Class['PROJECT_TYPE'] = information[:-1]

            information = name_L_min.get('0.0', 'end')
            self.Var_class_L_min.set(information)
            self.Class['LENGTH_MIN'] = information[:-1]

            information = name_V_max.get('0.0', 'end')
            self.Var_class_V_max.set(information)
            self.Class['VELOCITY_MAX'] = information[:-1]

            information = name_V_set_var.get('0.0', 'end')
            self.Var_class_V_set_var.set(information)
            self.Class['VELOCITY_SET_VARIATION'] = information[:-1]

            information = name_missing_ratio.get('0.0', 'end')
            self.Var_class_missing_ratio.set(information)
            self.Class['MISSING_RATIO'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).grid(row=5, column=2)

    def textEvent_class(self):
        window = Tk()
        window.geometry('700x200')
        window.title('输入参数')
        name_input = Label(window, text='多个参数间用逗号隔开').pack()
        name_input = Text(window, width='100', height='3')  # width宽 height高
        name_input.pack()

        def get_inf():
            information = name_input.get('0.0', 'end')
            self.Var_class_parm.set(information)
            self.parm['TBM_CLASS'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).pack()

    def openDirEvent_class(self):
        global index_path
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='打开目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_class_inpath.set(newDir)
        self.path_input['TBM_CLASS'] = newDir
        output = newDir.replace(newDir.split('\\')[-1], '')
        index_path = os.path.join(output, 'Index-File.csv')  # 索引文件路径及名称

    def OutPathEvent_class(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='另存目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_class_outpath.set(newDir)
        self.path_output['TBM_CLASS'] = newDir

    def clean_model(self, index, model_name, Type):
        if Type == 'PARM':
            example = TBM_CLEAN(Run=False).PARAMETERS
            Label(self.frame_3, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_3, text=['示例:'] + example).grid(row=1 + 3 * index, column=1)
            Label(self.frame_3, text='参数:').grid(row=2 + 3 * index, column=0)
            self.Var_clean_parm.set(self.parm['TBM_CLEAN'])
            Entry(self.frame_3, textvariable=self.Var_clean_parm, width=100).grid(row=2 + 3 * index, column=1)
            Button(self.frame_3, text='更改', command=self.textEvent_clean).grid(row=2 + 3 * index, column=2)
        if Type == 'PATH':
            Label(self.frame_2, text=model_name).grid(row=0 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='高级设置', command=self.settle_Event_clean).grid(row=0 + 3 * index, column=2)
            Label(self.frame_2, text='源文件:').grid(row=1 + 3 * index, column=0, )
            self.Var_clean_inpath.set(self.path_input['TBM_CLEAN'])
            Entry(self.frame_2, textvariable=self.Var_clean_inpath, width=100).grid(row=1 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='打开目录', command=self.openDirEvent_clean).grid(row=1 + 3 * index, column=2)
            Label(self.frame_2, text='输   出:').grid(row=2 + 3 * index, column=0)
            self.Var_clean_outpath.set(self.path_output['TBM_CLEAN'])
            Entry(self.frame_2, textvariable=self.Var_clean_outpath, width=100).grid(row=2 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='另存目录', command=self.OutPathEvent_clean).grid(row=2 + 3 * index, column=2)

    def settle_Event_clean(self):
        window = Tk()
        window.geometry('700x200')
        window.title('TBM_CLEAN高级设置')
        Label(window, text='推进速度上限值（单位: mm/min）').grid(row=0, column=0)
        Label(window, text='V-MAX:').grid(row=0, column=1)
        name_min_time = Text(window, width=8, height=1)  # width宽 height高
        name_min_time.insert('0.0', self.clean['VELOCITY_MAX'])
        Label(window, text='（引松取120，额河取200）').grid(row=0, column=4)
        name_min_time.grid(row=0, column=2)

        def get_inf():
            information = name_min_time.get('0.0', 'end')
            self.Var_clean_V_max.set(information)
            self.clean['VELOCITY_MAX'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).grid(row=1, column=2)

    def textEvent_clean(self):
        window = Tk()
        window.geometry('700x200')
        window.title('输入参数')
        name_input = Label(window, text='多个参数间用逗号隔开').pack()
        name_input = Text(window, width='100', height='3')  # width宽 height高
        name_input.pack()

        def get_inf():
            information = name_input.get('0.0', 'end')
            self.Var_clean_parm.set(information)
            self.parm['TBM_CLEAN'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).pack()

    def openDirEvent_clean(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='打开目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_clean_inpath.set(newDir)
        self.path_input['TBM_CLEAN'] = newDir

    def OutPathEvent_clean(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='另存目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_clean_outpath.set(newDir)
        self.path_output['TBM_CLEAN'] = newDir

    def merge_model(self, index, model_name, Type):
        if Type == 'PARM':
            example = TBM_MERGE(Run=False).PARAMETERS
            Label(self.frame_3, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_3, text=['示例:'] + example).grid(row=1 + 3 * index, column=1)
            Label(self.frame_3, text='参数:').grid(row=2 + 3 * index, column=0)
            self.Var_merge_parm.set(self.parm['TBM_MERGE'])
            Entry(self.frame_3, textvariable=self.Var_merge_parm, width=100).grid(row=2 + 3 * index, column=1)
            Button(self.frame_3, text='更改', command=self.textEvent_merge).grid(row=2 + 3 * index, column=2)
        if Type == 'PATH':
            Label(self.frame_2, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_2, text='源文件:').grid(row=1 + 3 * index, column=0, )
            self.Var_merge_inpath.set(self.path_input['TBM_MERGE'])
            Entry(self.frame_2, textvariable=self.Var_merge_inpath, width=100).grid(row=1 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='打开目录', command=self.openDirEvent_merge).grid(row=1 + 3 * index, column=2)
            Label(self.frame_2, text='输   出:').grid(row=2 + 3 * index, column=0)
            self.Var_merge_outpath.set(self.path_output['TBM_MERGE'])
            Entry(self.frame_2, textvariable=self.Var_merge_outpath, width=100).grid(row=2 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='另存目录', command=self.OutPathEvent_merge).grid(row=2 + 3 * index, column=2)

    def textEvent_merge(self):
        window = Tk()
        window.geometry('700x200')
        window.title('输入参数')
        name_input = Label(window, text='多个参数间用逗号隔开').pack()
        name_input = Text(window, width='100', height='3')  # width宽 height高
        name_input.pack()

        def get_inf():
            information = name_input.get('0.0', 'end')
            self.Var_merge_parm.set(information)
            self.parm['TBM_MERGE'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).pack()

    def openDirEvent_merge(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='打开目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_merge_inpath.set(newDir)
        self.path_input['TBM_MERGE'] = newDir

    def OutPathEvent_merge(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='另存目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_merge_outpath.set(newDir)
        self.path_output['TBM_MERGE'] = newDir

    def split_model(self, index, model_name, Type):
        if Type == 'PARM':
            example = TBM_SPLIT(Run=False).PARAMETERS
            Label(self.frame_3, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_3, text=['示例:'] + example).grid(row=1 + 3 * index, column=1)
            Label(self.frame_3, text='参数:').grid(row=2 + 3 * index, column=0)
            self.Var_split_parm.set(self.parm['TBM_SPLIT'])
            Entry(self.frame_3, textvariable=self.Var_split_parm, width=100).grid(row=2 + 3 * index, column=1)
            Button(self.frame_3, text='更改', command=self.textEvent_split).grid(row=2 + 3 * index, column=2)
        if Type == 'PATH':
            Label(self.frame_2, text=model_name).grid(row=0 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='高级设置', command=self.settle_Event_split).grid(row=0 + 3 * index, column=2)
            Label(self.frame_2, text='源文件:').grid(row=1 + 3 * index, column=0, )
            self.Var_split_inpath.set(self.path_input['TBM_SPLIT'])
            Entry(self.frame_2, textvariable=self.Var_split_inpath, width=100).grid(row=1 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='打开目录', command=self.openDirEvent_split).grid(row=1 + 3 * index, column=2)
            Label(self.frame_2, text='输   出:').grid(row=2 + 3 * index, column=0)
            self.Var_split_outpath.set(self.path_output['TBM_SPLIT'])
            Entry(self.frame_2, textvariable=self.Var_split_outpath, width=100).grid(row=2 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='另存目录', command=self.OutPathEvent_split).grid(row=2 + 3 * index, column=2)

    def settle_Event_split(self):
        window = Tk()
        window.geometry('700x200')
        window.title('TBM_SPLIT高级设置')
        Label(window, text='最小时间记录长度').grid(row=0, column=0)
        Label(window, text='MIN_TIME:').grid(row=0, column=1)
        name_min_time = Text(window, width=8, height=1)  # width宽 height高
        name_min_time.insert('0.0', self.split['MIN_TIME'])
        Label(window, text='（单位: s）').grid(row=0, column=4)
        name_min_time.grid(row=0, column=2)

        Label(window, text='最小掘进长度').grid(row=1, column=0)
        Label(window, text='MIN_LENGTH:').grid(row=1, column=1)
        name_min_length = Text(window, width=8, height=1)  # width宽 height高
        name_min_length.insert('0.0', self.split['MIN_LENGTH'])
        Label(window, text='（单位: m）').grid(row=1, column=4)
        name_min_length.grid(row=1, column=2)

        def get_inf():
            information = name_min_time.get('0.0', 'end')
            self.Var_split_min_time.set(information)
            self.split['MIN-TIME'] = information[:-1]
            information = name_min_length.get('0.0', 'end')
            self.Var_split_min_length.set(information)
            self.split['MIN-LENGTH'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).grid(row=2, column=2)

    def textEvent_split(self):
        window = Tk()
        window.geometry('700x200')
        window.title('输入参数')
        name_input = Label(window, text='多个参数间用逗号隔开').pack()
        name_input = Text(window, width='100', height='3')  # width宽 height高
        name_input.pack()

        def get_inf():
            information = name_input.get('0.0', 'end')
            self.Var_split_parm.set(information)
            self.parm['TBM_SPLIT'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).pack()

    def openDirEvent_split(self):
        global index_path
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='打开目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_split_inpath.set(newDir)
        self.path_input['TBM_SPLIT'] = newDir
        output = newDir.replace(newDir.split('\\')[-1], '')
        index_path = os.path.join(output, 'Index-File.csv')  # 索引文件路径及名称

    def OutPathEvent_split(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='另存目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_split_outpath.set(newDir)
        self.path_output['TBM_SPLIT'] = newDir

    def filter_model(self, index, model_name, Type):
        if Type == 'PARM':
            example = TBM_FILTER(Run=False).PARAMETERS
            Label(self.frame_3, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_3, text=['示例:'] + example).grid(row=1 + 3 * index, column=1)
            Label(self.frame_3, text='参数:').grid(row=2 + 3 * index, column=0)
            self.Var_filter_parm.set(self.parm['TBM_FILTER'])
            Entry(self.frame_3, textvariable=self.Var_filter_parm, width=100).grid(row=2 + 3 * index, column=1)
            Button(self.frame_3, text='更改', command=self.textEvent_filter).grid(row=2 + 3 * index, column=2)
        if Type == 'PATH':
            Label(self.frame_2, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_2, text='源文件:').grid(row=1 + 3 * index, column=0, )
            self.Var_filter_inpath.set(self.path_input['TBM_FILTER'])
            Entry(self.frame_2, textvariable=self.Var_filter_inpath, width=100).grid(row=1 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='打开目录', command=self.openDirEvent_filter).grid(row=1 + 3 * index,
                                                                                             column=2)
            Label(self.frame_2, text='输   出:').grid(row=2 + 3 * index, column=0)
            self.Var_filter_outpath.set(self.path_output['TBM_FILTER'])
            Entry(self.frame_2, textvariable=self.Var_filter_outpath, width=100).grid(row=2 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='另存目录', command=self.OutPathEvent_filter).grid(row=2 + 3 * index,
                                                                                             column=2)

    def textEvent_filter(self):
        window = Tk()
        window.geometry('700x200')
        window.title('输入参数')
        name_input = Label(window, text='多个参数间用逗号隔开').pack()
        name_input = Text(window, width='100', height='3')  # width宽 height高
        name_input.pack()

        def get_inf():
            information = name_input.get('0.0', 'end')
            self.Var_filter_parm.set(information)
            self.parm['TBM_FILTER'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).pack()

    def openDirEvent_filter(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='打开目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_filter_inpath.set(newDir)
        self.path_input['TBM_FILTER'] = newDir

    def OutPathEvent_filter(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='另存目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_filter_outpath.set(newDir)
        self.path_output['TBM_FILTER'] = newDir

    def report_model(self, index, model_name, Type):
        if Type == 'PARM':
            example = TBM_REPORT(Run=False).PARAMETERS
            Label(self.frame_3, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_3, text=['示例:'] + example).grid(row=1 + 3 * index, column=1)
            Label(self.frame_3, text='参数:').grid(row=2 + 3 * index, column=0)
            self.Var_report_parm.set(self.parm['TBM_REPORT'])
            Entry(self.frame_3, textvariable=self.Var_report_parm, width=100).grid(row=2 + 3 * index, column=1)
            Button(self.frame_3, text='更改', command=self.textEvent_report).grid(row=2 + 3 * index, column=2)
        if Type == 'PATH':
            Label(self.frame_2, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_2, text='源文件:').grid(row=1 + 3 * index, column=0, )
            self.Var_report_inpath.set(self.path_input['TBM_REPORT'])
            Entry(self.frame_2, textvariable=self.Var_report_inpath, width=100).grid(row=1 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='打开目录', command=self.openDirEvent_report).grid(row=1 + 3 * index,
                                                                                             column=2)
            Label(self.frame_2, text='输   出:').grid(row=2 + 3 * index, column=0)
            self.Var_report_outpath.set(self.path_output['TBM_REPORT'])
            Entry(self.frame_2, textvariable=self.Var_report_outpath, width=100).grid(row=2 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='另存目录', command=self.OutPathEvent_report).grid(row=2 + 3 * index,
                                                                                             column=2)

    def textEvent_report(self):
        window = Tk()
        window.geometry('700x200')
        window.title('输入参数')
        name_input = Label(window, text='多个参数间用逗号隔开').pack()
        name_input = Text(window, width='100', height='3')  # width宽 height高
        name_input.pack()

        def get_inf():
            information = name_input.get('0.0', 'end')
            self.Var_report_parm.set(information)
            self.parm['TBM_REPORT'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).pack()

    def openDirEvent_report(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='打开目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_report_inpath.set(newDir)
        self.path_input['TBM_REPORT'] = newDir

    def OutPathEvent_report(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='另存目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_report_outpath.set(newDir)
        self.path_output['TBM_REPORT'] = newDir

    def plot_model(self, index, model_name, Type):
        if Type == 'PARM':
            example = TBM_PLOT(Run=False).PARAMETERS
            Label(self.frame_3, text=model_name).grid(row=0 + 3 * index, column=1)
            Label(self.frame_3, text=['示例:'] + example).grid(row=1 + 3 * index, column=1)
            Label(self.frame_3, text='参数:').grid(row=2 + 3 * index, column=0)
            self.Var_plot_parm.set(self.parm['TBM_PLOT'])
            Entry(self.frame_3, textvariable=self.Var_plot_parm, width=100).grid(row=2 + 3 * index, column=1)
            Button(self.frame_3, text='更改', command=self.textEvent_plot).grid(row=2 + 3 * index, column=2)
        if Type == 'PATH':
            Label(self.frame_2, text=model_name).grid(row=0 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='高级设置', command=self.settle_Event_plot).grid(row=0 + 3 * index, column=2)
            Label(self.frame_2, text='源文件:').grid(row=1 + 3 * index, column=0)
            self.Var_plot_inpath.set(self.path_input['TBM_PLOT'])
            Entry(self.frame_2, textvariable=self.Var_plot_inpath, width=100).grid(row=1 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='打开目录', command=self.openDirEvent_plot).grid(row=1 + 3 * index, column=2)
            Label(self.frame_2, text='输   出:').grid(row=2 + 3 * index, column=0)
            self.Var_plot_outpath.set(self.path_output['TBM_PLOT'])
            Entry(self.frame_2, textvariable=self.Var_plot_outpath, width=100).grid(row=2 + 3 * index, column=1)
            tkinter.Button(self.frame_2, text='另存目录', command=self.OutPathEvent_plot).grid(row=2 + 3 * index, column=2)

    def settle_Event_plot(self):
        def true_inf():
            self.Var_plot_show.set(True)

        def false_inf():
            self.Var_plot_show.set(False)

        def get_inf():
            information = name_weight.get('0.0', 'end')
            self.Var_plot_weight.set(information)
            self.plot['WEIGHT'] = information[:-1]
            information = name_height.get('0.0', 'end')
            self.Var_plot_weight.set(information)
            self.plot['HEIGHT'] = information[:-1]
            information = name_dpi.get('0.0', 'end')
            self.Var_plot_dpi.set(information)
            self.plot['DPI'] = information[:-1]
            information = name_type.get('0.0', 'end')
            self.Var_plot_type.set(information)
            self.plot['FORMAT'] = information[:-1]
            self.plot['SHOW'] = self.Var_plot_show.get()
            window.destroy()

        window = Tk()
        window.geometry('700x200')
        window.title('TBM_PLOT高级设置')
        Label(window, text='生成图片高度').grid(row=0, column=0)
        Label(window, text='     H:').grid(row=0, column=1)
        name_height = Text(window, width=8, height=1)  # width宽 height高
        name_height.insert('0.0', self.plot['HEIGHT'])
        Label(window, text='（单位: cm）').grid(row=0, column=4)
        name_height.grid(row=0, column=2)

        Label(window, text='生成图片宽度').grid(row=1, column=0)
        Label(window, text='     W:').grid(row=1, column=1)
        name_weight = Text(window, width=8, height=1)  # width宽 height高
        name_weight.insert('0.0', self.plot['WEIGHT'])
        Label(window, text='（单位: cm）').grid(row=1, column=4)
        name_weight.grid(row=1, column=2)

        Label(window, text='生成图片的分辨率').grid(row=2, column=0)
        Label(window, text='   DPI:').grid(row=2, column=1)
        name_dpi = Text(window, width=8, height=1)  # width宽 height高
        name_dpi.insert('0.0', self.plot['DPI'])
        Label(window, text='（DPI应设置为50~200范围内）').grid(row=2, column=4)
        name_dpi.grid(row=2, column=2)

        Label(window, text='生成图片的类型').grid(row=3, column=0)
        Label(window, text='FORMAT:').grid(row=3, column=1)
        name_type = Text(window, width=8, height=1)  # width宽 height高
        name_type.insert('0.0', self.plot['FORMAT'])
        Label(window, text='（图片格式可为eps, jpeg, jpg, pdf, pgf, png, ps, raw, svg, svgz, tif, tiff）').grid(row=3, column=4)
        name_type.grid(row=3, column=2)

        Label(window, text='展示绘制的图片').grid(row=4, column=0)
        self.Var_plot_show.set(self.plot['SHOW'])
        Radiobutton(window, text="是", variable=self.Var_plot_show, value=True, command=true_inf).grid(row=4, column=1)
        Radiobutton(window, text="否", variable=self.Var_plot_show, value=False, command=false_inf).grid(row=4, column=2)
        Button(window, text='  OK  ', command=get_inf).grid(row=5, column=2)

    def textEvent_plot(self):
        window = Tk()
        window.geometry('700x200')
        window.title('输入参数')
        name_input = Label(window, text='多个参数间用逗号隔开').pack()
        name_input = Text(window, width='100', height='3')  # width宽 height高
        name_input.pack()

        def get_inf():
            information = name_input.get('0.0', 'end')
            self.Var_plot_parm.set(information)
            self.parm['TBM_PLOT'] = information[:-1]
            window.destroy()

        Button(window, text='  OK  ', command=get_inf).pack()

    def openDirEvent_plot(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='打开目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_plot_inpath.set(newDir)
        self.path_input['TBM_PLOT'] = newDir

    def OutPathEvent_plot(self):
        newDir = tkinter.filedialog.askdirectory(initialdir=self.input_path, title='另存目录').replace('/', '\\')
        if len(newDir) == 0:
            return
        self.Var_plot_outpath.set(newDir)
        self.path_output['TBM_PLOT'] = newDir

    def select(self):
        a = list(self.parm.keys())
        Label(self.frame_1, text='程序运行方式').grid(row=0, column=2, pady=20)
        Radiobutton(self.frame_1, text="Normal", variable=self.model, value="Normal").grid(row=1, column=0)
        Radiobutton(self.frame_1, text="Debug", variable=self.model, value="Debug").grid(row=1, column=4)
        Label(self.frame_1, text='需要运行模块').grid(row=3, column=2, pady=20)
        Checkbutton(self.frame_1, text=a[0], variable=self.Var_cycle_selt, onvalue=1, offvalue=0).grid(row=4, column=0)
        Checkbutton(self.frame_1, text=a[1], variable=self.Var_extract_selt, onvalue=1, offvalue=0).grid(row=4,
                                                                                                         column=1)
        Checkbutton(self.frame_1, text=a[2], variable=self.Var_class_selt, onvalue=1, offvalue=0).grid(row=4, column=2)
        Checkbutton(self.frame_1, text=a[3], variable=self.Var_clean_selt, onvalue=1, offvalue=0).grid(row=4, column=3)
        Checkbutton(self.frame_1, text=a[4], variable=self.Var_merge_selt, onvalue=1, offvalue=0).grid(row=4, column=4)
        Checkbutton(self.frame_1, text=a[5], variable=self.Var_split_selt, onvalue=1, offvalue=0).grid(row=5, column=0)
        Checkbutton(self.frame_1, text=a[6], variable=self.Var_filter_selt, onvalue=1, offvalue=0).grid(row=5, column=1)
        Checkbutton(self.frame_1, text=a[7], variable=self.Var_report_selt, onvalue=1, offvalue=0).grid(row=5, column=2)
        Checkbutton(self.frame_1, text=a[8], variable=self.Var_plot_selt, onvalue=1, offvalue=0).grid(row=5, column=3)

    def get_select(self):
        self.Var_model = self.model.get()
        a = list(self.parm.keys())
        self.Var_select['TBM_CYCLE'] = self.Var_cycle_selt.get()
        self.Var_select['TBM_EXTRACT'] = self.Var_extract_selt.get()
        self.Var_select['TBM_CLASS'] = self.Var_class_selt.get()
        self.Var_select['TBM_CLEAN'] = self.Var_clean_selt.get()
        self.Var_select['TBM_MERGE'] = self.Var_merge_selt.get()
        self.Var_select['TBM_SPLIT'] = self.Var_split_selt.get()
        self.Var_select['TBM_FILTER'] = self.Var_filter_selt.get()
        self.Var_select['TBM_REPORT'] = self.Var_report_selt.get()
        self.Var_select['TBM_PLOT'] = self.Var_plot_selt.get()
        self.frame_2 = Frame(self.root_window, width=self.window_width, height=self.window_heigth)
        self.frame_2.grid(column=0, row=0, padx=20, pady=5, sticky=(tkinter.W, tkinter.N, tkinter.E))
        self.frame_3 = Frame(self.root_window, width=self.window_width, height=self.window_heigth)
        self.frame_3.grid(column=0, row=0, padx=20, pady=5, sticky=(tkinter.W, tkinter.N, tkinter.E))
        if self.Var_select['TBM_CYCLE'] == 1:
            self.cycle_model(self.path_num, a[0], 'PATH')
            self.cycle_model(self.path_num, a[0], 'PARM')
            self.path_num += 1
        if self.Var_select['TBM_EXTRACT'] == 1:
            self.extract_model(self.path_num, a[1], 'PATH')
            self.extract_model(self.path_num, a[1], 'PARM')
            self.path_num += 1
        if self.Var_select['TBM_CLASS'] == 1:
            self.class_model(self.path_num, a[2], 'PATH')
            self.class_model(self.path_num, a[2], 'PARM')
            self.path_num += 1
        if self.Var_select['TBM_CLEAN'] == 1:
            self.clean_model(self.path_num, a[3], 'PATH')
            self.clean_model(self.path_num, a[3], 'PARM')
            self.path_num += 1
        if self.Var_select['TBM_MERGE'] == 1:
            self.merge_model(self.path_num, a[4], 'PATH')
            self.merge_model(self.path_num, a[4], 'PARM')
            self.path_num += 1
        if self.Var_select['TBM_SPLIT'] == 1:
            self.split_model(self.path_num, a[5], 'PATH')
            self.split_model(self.path_num, a[5], 'PARM')
            self.path_num += 1
        if self.Var_select['TBM_FILTER'] == 1:
            self.filter_model(self.path_num, a[6], 'PATH')
            self.filter_model(self.path_num, a[6], 'PARM')
            self.path_num += 1
        if self.Var_select['TBM_REPORT'] == 1:
            self.report_model(self.path_num, a[7], 'PATH')
            self.report_model(self.path_num, a[7], 'PARM')
            self.path_num += 1
        if self.Var_select['TBM_PLOT'] == 1:
            self.plot_model(self.path_num, a[8], 'PATH')
            self.plot_model(self.path_num, a[8], 'PARM')
            self.path_num += 1
        Button(self.frame_2, text="Back", command=self.call_frame_1_on_top).grid(row=3 * self.path_num + 1, column=0)
        Button(self.frame_2, text="Next", command=self.call_frame_3_on_top).grid(row=3 * self.path_num + 1, column=2)
        Button(self.frame_3, text="Back", command=self.call_frame_2_on_top).grid(row=3 * self.path_num + 1, column=0)
        Button(self.frame_3, text="Next", command=self.quit_program).grid(row=3 * self.path_num + 1, column=2)
        self.call_frame_2_on_top()

    def create_widgets_in_frame_1(self):
        self.select()
        first_window_quit_button = tkinter.Button(self.frame_1, text="Quit", command=self.quit_program)
        first_window_quit_button.grid(column=0, row=6, pady=10)
        first_window_next_button = tkinter.Button(self.frame_1, text="Next", command=self.get_select)
        first_window_next_button.grid(column=4, row=6, pady=10)

    def create_widgets_in_frame_2(self):
        Button(self.frame_2, text="Back", command=self.call_frame_1_on_top).grid(row=3 * self.path_num + 1, column=0)
        Button(self.frame_2, text="Next", command=self.call_frame_3_on_top).grid(row=3 * self.path_num + 1, column=2)

    def create_widgets_in_frame_3(self):
        Button(self.frame_3, text="Back", command=self.call_frame_2_on_top).grid(row=3 * self.path_num + 1, column=0)
        Button(self.frame_3, text="Next", command=self.quit_program).grid(row=3 * self.path_num + 1, column=2)

    def call_frame_1_on_top(self):
        self.frame_2.grid_forget()
        self.frame_1.grid(column=0, row=0, padx=20, pady=5, sticky=(tkinter.W, tkinter.N, tkinter.E))

    def call_frame_2_on_top(self):
        self.frame_1.grid_forget()
        self.frame_3.grid_forget()
        self.frame_2.grid(column=0, row=0, padx=20, pady=5, sticky=(tkinter.W, tkinter.N, tkinter.E))

    def call_frame_3_on_top(self):
        self.frame_2.grid_forget()
        self.frame_3.grid(column=0, row=0, padx=20, pady=5, sticky=(tkinter.W, tkinter.N, tkinter.E))

    def quit_program(self):
        self.root_window.destroy()

    def creative_conf(self):
        global index_path
        now = datetime.datetime.now()
        Time = now.strftime("%Y-%m-%d %H:%M:%S")
        Config = configparser.ConfigParser()
        Config['program'] = {'time': str(Time),
                             'name': os.path.basename(__file__)}
        Config['index-path'] = {'path': index_path}
        Config['input-path'] = self.path_input
        Config['output-path'] = self.path_output
        Config['parameters'] = self.parm
        Config['cycle_model'] = self.cycle
        Config['class_model'] = self.Class
        Config['clean_model'] = self.clean
        Config['split_model'] = self.split
        Config['plot_model'] = self.plot
        with open('config.ini', 'w+') as cfg:
            Config.write(cfg)

    def get_config(self):
        """定义读取配置文件函数，分别读取各个分栏的配置参数，包含ints、floats、strings"""
        global index_path
        parser = configparser.ConfigParser()
        try:
            parser.read('config.ini')  # 读取文件
            input_path = dict([(str.upper(key), value) for key, value in parser.items('input-path')])
            output_path = dict([(str.upper(key), value) for key, value in parser.items('output-path')])
            parameters = dict([(str.upper(key), value) for key, value in parser.items('parameters')])
            index_path = dict([(str.upper(key), value) for key, value in parser.items('index-path')])['PATH']
            cycle_model = dict([(str.upper(key), value) for key, value in parser.items('cycle_model')])
            class_model = dict([(str.upper(key), value) for key, value in parser.items('class_model')])
            clean_model = dict([(str.upper(key), value) for key, value in parser.items('clean_model')])
            split_model = dict([(str.upper(key), value) for key, value in parser.items('split_model')])
            plot_model = dict([(str.upper(key), value) for key, value in parser.items('plot_model')])
        except configparser.NoSectionError:
            input_path = {'TBM_CYCLE': '--请选择--', 'TBM_EXTRACT': '--请选择--', 'TBM_CLASS': '--请选择--',
                          'TBM_CLEAN': '--请选择--', 'TBM_MERGE': '--请选择--', 'TBM_SPLIT': '--请选择--',
                          'TBM_FILTER': '--请选择--', 'TBM_REPORT': '--请选择--', 'TBM_PLOT': '--请选择--'}
            output_path = {'TBM_CYCLE': '--请选择--', 'TBM_EXTRACT': '--请选择--', 'TBM_CLASS': '--请选择--',
                           'TBM_CLEAN': '--请选择--', 'TBM_MERGE': '--请选择--', 'TBM_SPLIT': '--请选择--',
                           'TBM_FILTER': '--请选择--', 'TBM_REPORT': '--请选择--', 'TBM_PLOT': '--请选择--'}
            parameters = {'TBM_CYCLE': '--请选择--', 'TBM_EXTRACT': '--请选择--', 'TBM_CLASS': '--请选择--',
                          'TBM_CLEAN': '--请选择--', 'TBM_MERGE': '--请选择--', 'TBM_SPLIT': '--请选择--',
                          'TBM_FILTER': '--请选择--', 'TBM_REPORT': '--请选择--', 'TBM_PLOT': '--请选择--'}
            index_path = ''
            cycle_model = {'INTERVAL_TIME': '100'}
            class_model = {'PROJECT_TYPE': '引绰-668', 'LENGTH_MIN': '0.3', 'VELOCITY_MAX': '120',
                           'VELOCITY_SET_VARIATION': '15', 'MISSING_RATIO': '20'}
            clean_model = {'VELOCITY_MAX': '120'}
            split_model = {'MIN_TIME': '200', 'MIN_LENGTH': '0.1'}
            plot_model = {'WEIGHT': '8', 'HEIGHT': '10', 'DPI': '120', 'FORMAT': 'png', 'SHOW': False}
        return input_path, output_path, parameters, cycle_model, class_model, clean_model, split_model, plot_model


class DEBUG(object):
    PARAMETERS = ['日期', '导向盾首里程', '刀盘转速', '推进速度(nn/M)', '刀盘扭矩',
                  '总推力', '刀盘给定转速', '推进给定速度', '推进位移', '刀盘贯入度']

    def __init__(self, debug=False):
        self.debug = debug
        self.parm = self.PARAMETERS
        self.file_name = ''

    def debug_start(self, _info_):
        """第一次打印输出"""
        if self.debug:
            print('=' * 40, 'Debug', '=' * 40)
            print('\033[0;33m     ->-> %s <-<-\033[0m' % _info_)
            self.file_name = _info_

    def debug_print(self, _info_):
        """语句打印输出"""
        if self.debug:
            for information in _info_:
                print('\033[0;33m     %s\033[0m' % information, end='')
            print('')

    def debug_finish(self, _info_):
        """最后一次打印输出"""
        if self.debug:
            print('\033[0;33m     ->-> %s <-<-\033[0m' % _info_)
            print('=' * 40, 'Debug', '=' * 40)

    def debug_draw_N(self, _data_df_, parm):
        """刀盘转速绘图"""
        if self.debug:
            x = [i for i in range(_data_df_.shape[0])]  # 'Time'
            y_n = _data_df_.loc[:, parm]  # '刀盘转速'
            plt.figure(figsize=(14, 7), dpi=120)  # 设置画布大小（10cm x 8cm）及分辨率（dpi=120）
            plt.plot(x, y_n, label="n", color='b')
            # plt.ylim(0, 10)
            plt.ylabel("刀盘转速、推进速度及其设定值", fontsize=15, labelpad=10)
            plt.xlabel("时间/s", fontsize=15)
            plt.show()
            plt.close()
            self.debug_finish(self.file_name)

    def debug_draw_V(self, _data_df_, parm, _key_):
        """推进速度绘图"""
        if self.debug:
            _data_df_ = self.B1_mark_Modify(_data_df_, parm)
            x = [i for i in range(_data_df_.shape[0])]  # 'Time'
            y_n = _data_df_.loc[:, parm]  # '推进速度'
            plt.figure(figsize=(14, 7), dpi=120)  # 设置画布大小（10cm x 8cm）及分辨率（dpi=120）
            plt.plot(x, y_n, label="n", color='b')
            if _key_:
                plt.axvline(x=_key_['rise'] - 1, c="r", ls="-.")
                plt.axvline(x=_key_['steadyS'] - 1, c="g", ls="-.")
                plt.axvline(x=_key_['steadyE'] - 1, c="y", ls="-.")
            plt.ylabel("刀盘转速、推进速度及其设定值", fontsize=15, labelpad=10)
            plt.xlabel("时间/s", fontsize=15)
            plt.ylim(0, 120)
            plt.show()
            plt.close()
            self.debug_finish(self.file_name)

    def B1_mark_Modify(self, _cycle_: DataFrame, parm) -> DataFrame:  # 规定_cycle_为(DataFrame)类型数组，返回值为(DataFrame)类型数组
        """对B1_markAndModify (循环段速度值超限 V>120mm/min)类异常数据进行修正"""
        data_V = _cycle_.loc[:, parm].values  # 推进速度（self.parm[3]）
        data_mean, data_std = np.mean(data_V), np.std(data_V)  # 获取推进速度均值和标准差
        for i in range(len(data_V)):
            if data_V[i] > 120 or (data_V[i] > data_mean + 3 * data_std):
                replace = sum(data_V[i - 10:i]) / 10.0  # 采用前10个推进速度的平均值进行替换
                _cycle_.loc[i, self.parm[3]] = replace  # 采用前10个推进速度的平均值进行替换
        return _cycle_


def __history__():
    """展示文件版本信息和修改记录"""
    print('\r', '\n', end='')
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(__file__))
    with open(file_path, 'r', encoding="utf-8") as F:
        lines = F.readlines()
    for i in range(2, 11):
        print('\r', '\033[0;32m%s\033[0m' % lines[i], end='')
    print('\033[0;32m%s\033[0m' % HISTORY, '\n')  # 打印文件修改记录


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
        shutil.rmtree(os.path.join(root_path, '__Update__', 'TBM-Intelligent-main')), ZF.close()
        from __Update__.Update import Update
        shutil.rmtree(os.path.join(root_path, '__Update__'))  # 更新完成，删除相关文件记录
    except requests.exceptions.ConnectionError:
        return


__history__()

if __name__ == "__main__":
    Check_Update()  # 检查程序是否存在新版本
    main = message()  # 调用窗口获取输入输出路径及相关参数，完成对程序的配置
    print(' ->->', '\033[0;32m程序配置完成，准备运行...\033[0m')
    run = False
    if main.Var_model == 'Debug':
        run = True
    start_all = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
    if main.Var_select['TBM_CYCLE']:
        Input_path = main.path_input['TBM_CYCLE']  # 原始数据存放路径
        Output_path = main.path_output['TBM_CYCLE']  # 分割好的循环段数据存放路径
        Par_name = list(main.parm['TBM_CYCLE'].split(','))  # (桩号、运行时间、刀盘转速、推进速度设定值)请勿修改顺序
        Interval_Time = int(main.cycle['INTERVAL_TIME'])  # 相邻两个循环段时间间隔
        TBM_CYCLE = TBM_CYCLE(input_path=Input_path, out_path=Output_path, parameter=Par_name,
                              interval_time=Interval_Time, debug=run)
    if main.Var_select['TBM_EXTRACT']:
        Input_path = main.path_input['TBM_EXTRACT']  # 原始数据存放路径
        Output_path = main.path_output['TBM_EXTRACT']  # 分割好的循环段数据存放路径
        Par_name = list(main.parm['TBM_EXTRACT'].split(','))  # (桩号、运行时间、刀盘转速、推进速度设定值)请勿修改顺序
        TBM_EXTRACT = TBM_EXTRACT(input_path=Input_path, out_path=Output_path, key_parm=Par_name, debug=run)
    if main.Var_select['TBM_CLASS']:
        Input_path = main.path_input['TBM_CLASS']  # 原始数据存放路径
        Output_path = main.path_output['TBM_CLASS']  # 分割好的循环段数据存放路径
        Par_name = list(main.parm['TBM_CLASS'].split(','))  # (桩号、运行时间、刀盘转速、推进速度设定值)请勿修改顺序
        Project_type = str(main.Class['PROJECT_TYPE'])  # 工程项目
        L_Min = float(main.Class['LENGTH_MIN'])  # 最小掘进长度
        V_Max = int(main.Class['VELOCITY_MAX'])  # 最大掘进速度
        V_Set_var = int(main.Class['VELOCITY_SET_VARIATION'])
        Missing_Ratio = float(main.Class['MISSING_RATIO'])/100  # 缺失率
        TBM_CLASS = TBM_CLASS(input_path=Input_path, out_path=Output_path, parameter=Par_name, project_type=Project_type,
                              L_min=L_Min, V_max=V_Max, V_set_var=V_Set_var, missing_ratio=Missing_Ratio, debug=run)
    if main.Var_select['TBM_CLEAN']:
        Input_path = main.path_input['TBM_CLEAN']  # 原始数据存放路径
        Output_path = main.path_output['TBM_CLEAN']  # 分割好的循环段数据存放路径
        Par_name = list(main.parm['TBM_CLEAN'].split(','))  # (桩号、运行时间、刀盘转速、推进速度设定值)请勿修改顺序
        V_Max = int(main.clean['VELOCITY_MAX'])  # 最大掘进速度
        TBM_CLEAN = TBM_CLEAN(input_path=Input_path, out_path=Output_path, parameter=Par_name, V_max=V_Max, debug=run)
    if main.Var_select['TBM_MERGE']:
        Input_path = main.path_input['TBM_MERGE']  # 原始数据存放路径
        Output_path = main.path_output['TBM_MERGE']  # 分割好的循环段数据存放路径
        Par_name = list(main.parm['TBM_MERGE'].split(','))  # (桩号、运行时间、刀盘转速、推进速度设定值)请勿修改顺序
        TBM_MERGE = TBM_MERGE(input_path=Input_path, out_path=Output_path, debug=run)
    if main.Var_select['TBM_FILTER']:
        Input_path = main.path_input['TBM_FILTER']  # 原始数据存放路径
        Output_path = main.path_output['TBM_FILTER']  # 分割好的循环段数据存放路径
        Par_name = list(main.parm['TBM_FILTER'].split(','))  # (桩号、运行时间、刀盘转速、推进速度设定值)请勿修改顺序
        TBM_FILTER = TBM_FILTER(input_path=Input_path, out_path=Output_path, parameter=Par_name, debug=run)
    if main.Var_select['TBM_SPLIT']:
        Input_path = main.path_input['TBM_SPLIT']  # 原始数据存放路径
        Output_path = main.path_output['TBM_SPLIT']  # 分割好的循环段数据存放路径
        Par_name = list(main.parm['TBM_SPLIT'].split(','))  # (桩号、运行时间、刀盘转速、推进速度设定值)请勿修改顺序
        Min_time = int(main.split['MIN_TIME'])  # 最小掘进时间
        Min_length = float(main.split['MIN_LENGTH'])  # 最小掘进长度
        TBM_SPLIT = TBM_SPLIT(input_path=Input_path, out_path=Output_path, parameter=Par_name,
                              min_time=Min_time, min_length=Min_length, debug=run)
    if main.Var_select['TBM_PLOT']:
        Input_path = main.path_input['TBM_PLOT']  # 原始数据存放路径
        Output_path = main.path_output['TBM_PLOT']  # 分割好的循环段数据存放路径
        Par_name = list(main.parm['TBM_PLOT'].split(','))  # (桩号、运行时间、刀盘转速、推进速度设定值)请勿修改顺序
        Height = int(main.plot['HEIGHT'])  # 图片高度
        Weight = int(main.plot['WEIGHT'])  # 图片宽度
        Dpi = int(main.plot['DPI'])  # 图片dpi
        Format = str(main.plot['FORMAT'])  # 图片格式
        Show = bool(main.plot['SHOW'])  # 展示图片
        TBM_PLOT = TBM_PLOT(input_path=Input_path, out_path=Output_path, parameter=Par_name, height=Height,
                            weight=Weight, dpi=Dpi, Format=Format, show=Show, debug=run)
    if main.Var_select['TBM_REPORT']:
        Input_path = main.path_input['TBM_REPORT']  # 原始数据存放路径
        Input_pic = main.path_output['TBM_PLOT']  # 原始数据存放路径
        Output_path = main.path_output['TBM_REPORT']  # 分割好的循环段数据存放路径
        Par_name = list(main.parm['TBM_REPORT'].split(','))  # (桩号、运行时间、刀盘转速、推进速度设定值)请勿修改顺序
        TBM_REPORT = TBM_REPORT(input_path=Input_path, _input_pic_=Input_pic, out_path=Output_path,
                                parameter=Par_name, debug=run)
    end_all = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
    time = end_all - start_all
    if time < 3600:
        if time < 60:
            print(' ->->', '花费时间：%5.2f s' % round(time, 2))
        else:
            print(' ->->', '花费时间：%5.2f min' % round(time / 60, 2))
    else:
        print(' ->->', '花费时间：%5.2f h' % round(time / 3600, 2))
