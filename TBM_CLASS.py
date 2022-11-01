#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_CLASS for python                                           *
# * Version:  3.1.0                                                          *
# * Date:     2022-10-31 20:00:00                                            *
# * Last update: 2022-10-28 20:00:00                                         *
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


HISTORY = "最后更改时间:2022-10-31  修改人:刘建国  修改内容:暂无"  # 每次修改后添加修改人、修改时间和改动的功能


warnings.filterwarnings("ignore")  # 忽略警告信息
TIME_VAL = []  # 初始化时间存储
PROJECT_COEFFICIENT = {'引松': 1/40.731, '引额-361': 1.227, '引额-362': 1.354, '引绰-667': 1.763, '引绰-668': 2.356}
PARAMETERS = ['日期', '导向盾首里程', '刀盘转速', '推进速度(nn/M)', '刀盘扭矩', '总推力', '刀盘给定转速', '推进给定速度', '推进位移', '刀盘贯入度']
class_sub_folders = ['A1class-data', 'B1class-data', 'B2class-data', 'C1class-data',
                     'C2class-data', 'D1class-data', 'E1class-data', 'Norclass-data']  # 默认子文件夹
clean_sub_folders = ['NorA1class-data', 'NorB1class-data', 'NorB2class-data', 'NorC1class-data',
                     'NorC2class-data', 'NorD1class-data', 'NorE1class-data', 'Norclass-data', ]


class TBM_CLASS(object):
    def __init__(self):
        self.first_write = True  # 第一次写入索引
        self.index_exists = False  # 索引文件是否存在
        self.parameter = PARAMETERS  # 过程中用到的相关参数
        self.out_path = ''  # 初始化输出路径
        self.sub_folder = class_sub_folders  # 子文件夹
        self.line = []  # 索引数据保存
        self.project_type = '引绰-668'  # 工程类型（'引松'、'引额-361'、'引额-362'、'引绰-667'、'引绰-668'）
        self.length_threshold_value = 0.3  # 掘进长度下限值
        self.V_threshold_value = 120  # 推进速度上限值，引松取120，额河取200
        self.V_set_variation = 15  # 推进速度设定值变化幅度
        self.missing_ratio = 0.2  # 数据缺失率

    def create_class_Dir(self):
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
        index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Index-File.csv')  # 索引文件路径
        except_name = ['循环段', 'A', 'B1', 'B2', 'C1', 'C2', 'D', 'E', '正常掘进段']  # 新添加索引数据标题
        if self.first_write:  # 第一次写入索引时要写入标题
            if os.path.isfile(index_path):
                self.index_exists = True
            if self.index_exists:
                with open(index_path, 'r+', newline='', encoding='gb2312') as f:  # 只写模式打开文件
                    self.line = copy.deepcopy(f.readlines())  # 将文件内容保存
                    f.truncate(0)  # 清空文件内容，准备重新写入数据
                with open(index_path, 'a', encoding='gb2312') as fw:  # 用读写模式打开文件
                    line = self.line[0].replace('\r\n', ',' + str(','.join([str(i) for i in except_name[1:]])) + '\n')
                    fw.write(line)  # 写入标题
            else:
                with open(index_path, 'w', encoding='gb2312', newline='') as f:  # 新建索引文件
                    csv.writer(f).writerow(except_name)  # 写入标签数据
            self.first_write = False
        if self.index_exists:
            with open(index_path, 'a', encoding='gb2312') as fw:  # 用读写模式打开文件
                line = self.line[_Num_].replace('\r\n', ',' + str(','.join([str(i) for i in _inf_])) + '\n')  # 新数据
                fw.write(line)  # 写入数据
        else:
            input_csv = open(index_path, 'a', newline='')  # 打开索引文件
            _inf_.insert(0, _Num_)
            csv.writer(input_csv).writerow(_inf_)  # 写入数据记录

    def A_premature(self, _cycle_):
        """判断数据类型是不是A_premature"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parameter[1]]  # 获取桩号,导向盾首里程（self.parameter[1]）
        start_length = _cycle_.loc[0, self.parameter[8]]  # 获取循环段开始点位移,推进位移（self.parameter[8]）
        end_length = _cycle_.loc[_cycle_.shape[0] - 1, self.parameter[8]]  # 获取循环段结束点位移,推进位移（self.parameter[8]）
        length = (end_length - start_length) / 1000  # 循环段掘进长度
        if length < self.length_threshold_value:
            Anomaly_classification = 'A'  # 异常分类A
        return Anomaly_classification, stake  # 数据分类的结果(Anomaly...),桩号(stake)

    def B1_markAndModify(self, _cycle_):
        """判断数据类型是不是B1_markAndModify"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parameter[1]]  # 获取桩号，导向盾首里程（self.parameter[1]）
        data_V = _cycle_.loc[:, self.parameter[3]].values  # 获取推进速度并转化类型，推进速度（self.parameter[3]）
        data_len = len(data_V)  # 获取循环段长度
        data_mean, data_std = np.mean(data_V), np.std(data_V)  # 获取推进速度均值和标准差
        for i in range(data_len):
            if data_V[i] > self.V_threshold_value and (data_V[i] > data_mean + 3 * data_std):
                Anomaly_classification = 'B1'  # 异常分类B1
                data_V[i] = sum(data_V[i - 10:i]) / 10.0  # 采用前10个推进速度的平均值进行替换
        _cycle_[self.parameter[3]] = pd.DataFrame(data_V)  # 对异常推进速度值进行替换，推进速度（self.parameter[3]）
        return Anomaly_classification, data_V, _cycle_, stake  # 数据分类的结果(Anomaly...),修正的速度(data_V),桩号(stake)

    def B2_constant(self, _cycle_):
        """判断数据类型是不是B2_constant"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parameter[1]]  # 获取桩号，导向盾首里程（self.parameter[1]）
        data_F = _cycle_.loc[:, self.parameter[5]].values  # 获取刀盘推力并转化类型，刀盘推力（self.parameter[5]）
        for i in range(len(data_F) - 4):
            if (not np.std(data_F[i:i+5])) and (np.mean(data_F[i:i+5])):  # 判断刀盘扭矩是否连续五个数值稳定不变
                Anomaly_classification = 'B2'
                break
        return Anomaly_classification, stake  # 数据分类的结果(Anomaly...),桩号(stake)

    def C1_sine(self, _cycle_):
        """判断数据类型是不是C1_sine"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parameter[1]]  # 获取桩号，导向盾首里程（self.parameter[1]）
        data_T = _cycle_.loc[:, self.parameter[4]]  # 获取刀盘扭矩并转化类型，刀盘扭矩（self.parameter[4]）
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
        stake = _cycle_.loc[0, self.parameter[1]]  # 获取桩号，导向盾首里程（self.parameter[1]）
        N_set = _cycle_.loc[:, self.parameter[6]].values  # 获取刀盘转速设定值，刀盘转速设定值（self.parameter[6]）
        V_set = _cycle_.loc[:, self.parameter[7]].values  # 获取推进速度设定值，推进速度设定值（self.parameter[7]）
        for N_set_value, V_set_value in zip(N_set, V_set):
            if V_set_value == 0 and N_set_value > 0.1:
                Anomaly_classification = 'C2'
                break
        return Anomaly_classification, stake

    def D_adjust_setting(self, _cycle_):
        """判断数据类型是不是D_adjust_setting"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parameter[1]]  # 获取桩号，导向盾首里程（self.parameter[1]）
        data_V = _cycle_.loc[:, self.parameter[3]]  # 获取推进速度，推进速度（self.parameter[3]）
        V_mean, V_std = data_V.mean(), data_V.std()  # 获取推进速度均值和标准差
        rule = ((data_V < 0) | (data_V > self.V_threshold_value) | (data_V > V_mean + 3 * V_std))  # 满足条件的数据
        index = np.arange(data_V.shape[0])[rule]  # 满足条件的索引
        _cycle_ = _cycle_.drop(index, axis=0)  # 删除相关数据
        _cycle_.index = [i for i in range(_cycle_.shape[0])]  # 重建新数据集的行索引
        data_V_set = (_cycle_.loc[:, self.parameter[7]] * PROJECT_COEFFICIENT[self.project_type]).std()  # 获取推进速度设定值的方差
        if data_V_set > self.V_set_variation:
            Anomaly_classification = 'D'  # 异常分类D
        return Anomaly_classification, stake  # 数据分类的结果(Anomaly...),桩号(stake)

    def E_missing_ratio(self, _cycle_):
        """判断数据类型是不是E_missing_ratio"""
        Anomaly_classification = 'Normal'  # 异常分类
        stake = _cycle_.loc[0, self.parameter[1]]  # 获取桩号，导向盾首里程（self.parameter[1]）
        data_time = _cycle_.loc[:, self.parameter[0]].values  # 获取日期并转化类型，日期（self.parameter[0]）
        time_start = pd.to_datetime(data_time[0], format='%Y-%m-%d %H:%M:%S')  # 循环段开始日期
        time_end = pd.to_datetime(data_time[-1], format='%Y-%m-%d %H:%M:%S')  # 循环段结束日期
        time_diff = (time_end - time_start).seconds  # 时间差，以s为单位
        time_len = len(data_time)  # 实际时间
        missing_ratio = (time_diff - time_len) / time_diff  # 缺失率计算
        if missing_ratio > self.missing_ratio:
            Anomaly_classification = 'E'  # 异常分类E
        return Anomaly_classification, missing_ratio, stake  # 数据分类的结果(Anomaly...),缺失率(missing_ratio),桩号(stake)

    def data_class(self, _input_path_, _out_path_, _par_name_, _sub_folder_, History=False):
        """数据分类
        :param _input_path_: 文件读取路径
        :param _out_path_: 文件保存路径
        :param _par_name_: 参数名称
        :param _sub_folder_: 创建子文件夹名称
        :param History: 展示历史修改记录
        """
        if History: print('\n', '='*100, '\n', HISTORY, '\n', '='*100, '\n')  # 打印文件修改记录
        if (not _input_path_) and (not _out_path_) and (not _par_name_):  # 检查传入参数是否正常
            print('->-> %s' % os.path.basename(__file__), '\033[0;31mParameters abnormal, Please check!!!\033[0m')
            sys.exit()
        self.out_path, self.parameter, self.sub_folder = _out_path_, _par_name_, _sub_folder_  # 输出路径、所用到的参数、文件保存子路径
        self.create_class_Dir()  # 创建文件夹
        csv_list = os.listdir(_input_path_)  # 获取输入文件夹下的所有文件名，并将其保存
        for num, name in zip([i + 1 for i in range(len(csv_list))], csv_list):
            start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            local_csv_path = os.path.join(_input_path_, name)
            cycle = pd.read_csv(local_csv_path, encoding='gb2312')
            except_type = ['' for _ in range(8)]  # 创建列表用来存储异常类型
            if_Normal = 0
            if self.A_premature(cycle)[0] == 'Normal':
                RS_index = self.get_RS_index(cycle)
                this_cycle = cycle.loc[RS_index['rise']:RS_index['steadyE'], :]
                this_cycle.index = [i for i in range(this_cycle.shape[0])]  # 重建新数据集的行索引
                this_cycle_steady = cycle.loc[RS_index['steadyS']:RS_index['steadyE'], :]
                this_cycle_steady.index = [i for i in range(this_cycle_steady.shape[0])]  # 重建新数据集的行索引
            else:
                except_type[0] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(self.out_path + self.sub_folder[0], name))
                self.write_index(except_type, int(name[:5]))
                continue
            if self.B1_markAndModify(this_cycle_steady)[0] == 'B1':
                except_type[1] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(self.out_path + self.sub_folder[1], name))
            if self.B2_constant(this_cycle)[0] == 'B2':
                except_type[2] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(self.out_path + self.sub_folder[2], name))
            if self.C1_sine(this_cycle)[0] == 'C1':
                except_type[3] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(self.out_path + self.sub_folder[3], name))
            if self.C2_shutdown(this_cycle_steady)[0] == 'C2':
                except_type[4] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(self.out_path + self.sub_folder[4], name))
            if self.D_adjust_setting(this_cycle_steady)[0] == 'D':
                except_type[5] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(self.out_path + self.sub_folder[5], name))
            if self.E_missing_ratio(this_cycle)[0] == 'E':
                except_type[6] = 'True'
                if_Normal += 1
                shutil.copyfile(local_csv_path, os.path.join(self.out_path + self.sub_folder[6], name))
            if not if_Normal:
                except_type[7] = 'True'
                shutil.copyfile(local_csv_path, os.path.join(self.out_path + self.sub_folder[7], name))
            self.write_index(except_type, int(name[:5]))
            end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
            visual('Data-Class', cycle=num, Sum=len(csv_list), start=start, end=end, Clear=False)
        visual('Data-Class', cycle=-1, Clear=True)

    def get_RS_index(self, _data_):
        """获取空推、上升、稳定、下降的关键点"""
        RS_index = {'rise': 0, 'steadyS': 0, 'steadyE': 0}  # 初始化空推、上升、稳定、下降的关键点
        V_mean = int(_data_[self.parameter[3]].mean())  # 推进速度索引（self.parameter[3]）
        mid_point = 0  # 中点位置索引
        while _data_[self.parameter[3]][mid_point] < V_mean:  # 推进速度索引（self.parameter[3]）
            mid_point += 5
        steadyE = _data_.shape[0] - 1  # 稳定段结束位置索引
        while _data_[self.parameter[3]][steadyE] <= V_mean:  # 推进速度索引（self.parameter[3]）
            steadyE -= 1
        if mid_point:
            rise = mid_point  # 上升段开始位置处索引
            while _data_[self.parameter[9]][rise] > 2 and rise > 10:  # 刀盘贯入度度索引（self.parameter[9]）
                rise -= 1
            steadyS = mid_point  # 稳定段开始位置处索引
            V_set_mean = int(_data_[self.parameter[7]].mean())  # 推进速度设定值索引（self.parameter[7]）
            V_assist = _data_[self.parameter[3]] / V_set_mean  # 推进速度索引（self.parameter[3]）
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
    def __init__(self):
        self.create_dir = True  # 第一次保存文件时要创建相关文件夹
        self.parameter = PARAMETERS  # 过程中用到的相关参数
        self.out_path = ''  # 初始化输出路径
        self.sub_folder = clean_sub_folders  # 文件输出路径
        self.V_threshold_value = 120  # 推进速度上限值，引松取120，额河取200

    def create_clean_Dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if self.create_dir:
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
            self.create_dir = False

    def get_RS_index(self, _data_):
        """获取空推、上升、稳定、下降的关键点"""
        RS_index = {'rise': 0, 'steadyS': 0, 'steadyE': 0}  # 初始化空推、上升、稳定、下降的关键点
        V_mean = int(_data_[self.parameter[3]].mean())  # 推进速度索引（self.parameter[3]）
        mid_point = 0  # 中点位置索引
        while _data_[self.parameter[3]][mid_point] < V_mean:  # 推进速度索引（self.parameter[3]）
            mid_point += 5
        steadyE = _data_.shape[0] - 1  # 稳定段结束位置索引
        while _data_[self.parameter[3]][steadyE] <= V_mean:  # 推进速度索引（self.parameter[3]）
            steadyE -= 1
        if mid_point:
            rise = mid_point  # 上升段开始位置处索引
            while _data_[self.parameter[9]][rise] > 2 and rise > 10:  # 刀盘贯入度度索引（self.parameter[9]）
                rise -= 1
            steadyS = mid_point  # 稳定段开始位置处索引
            V_set_mean = int(_data_[self.parameter[7]].mean())  # 推进速度设定值索引（self.parameter[7]）
            V_assist = _data_[self.parameter[3]] / V_set_mean  # 推进速度索引（self.parameter[3]）
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
        data_V = _cycle_.loc[:, self.parameter[3]].values  # 推进速度（self.parameter[3]）
        data_mean, data_std = np.mean(data_V), np.std(data_V)  # 获取推进速度均值和标准差
        for i in range(len(data_V)):
            if data_V[i] > self.V_threshold_value or (data_V[i] > data_mean + 3 * data_std):
                replace = sum(data_V[i - 10:i]) / 10.0  # 采用前10个推进速度的平均值进行替换
                _cycle_.loc[i, self.parameter[3]] = replace  # 采用前10个推进速度的平均值进行替换
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

    def data_clean(self, _input_path_, _out_path_, _par_name_, _sub_folder_, History=False):
        """
        将数据类型进行汇总并保存
        :param _input_path_: 文件读取路径
        :param _out_path_: 文件保存路径
        :param _par_name_: 参数名称
        :param _sub_folder_: 创建子文件夹名称
        :param History: 展示历史修改记录
        """
        if History: print('\n', '='*100, '\n', HISTORY, '\n', '='*100, '\n')  # 打印文件修改记录
        if (not _input_path_) or (not _out_path_) or (not _par_name_):  # 检查传入参数是否正常
            print('->-> %s' % os.path.basename(__file__), '\033[0;31mParameters abnormal, Please check!!!\033[0m')
            sys.exit()
        self.out_path, self.parameter, self.sub_folder = _out_path_, _par_name_, _sub_folder_  # 输出路径、所用到的参数、文件保存子路径
        self.create_clean_Dir()  # 创建文件夹
        except_name = ['A', 'B1', 'B2', 'C1', 'C2', 'D', 'E', 'Normal']  # 新添加索引数据标题
        for Type, Dir in zip(except_name, os.listdir(_input_path_)):
            csv_list = os.listdir(_input_path_ + '\\' + Dir)  # 获取输入文件夹下的所有文件名，并将其保存
            for num, csv_file in zip([i + 1 for i in range(len(csv_list))], csv_list):
                start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                local_csv_path = os.path.join(_input_path_ + '\\' + Dir, csv_file)
                if Type == 'Normal':
                    shutil.copyfile(local_csv_path, os.path.join(self.out_path + self.sub_folder[-1], csv_file))
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
        

def ML_data(_input_path_,  _out_path_, History=False):
    """
    合并形成机器学习数据集
    :param _input_path_: 文件读取路径
    :param _out_path_: 文件保存路径
    :param History: 展示历史修改记录
    """
    if History: print('\n', '=' * 100, '\n', HISTORY, '\n', '=' * 100, '\n')  # 打印文件修改记录
    if (not _input_path_) or (not _out_path_):  # 检查传入参数是否正常
        print('->-> %s' % os.path.basename(__file__), '\033[0;31mParameters abnormal, Please check!!!\033[0m')
        sys.exit()
    if not os.path.exists(_out_path_):
        os.mkdir(_out_path_)
    else:
        shutil.rmtree(_out_path_)
        os.mkdir(_out_path_)
    for file in os.listdir(_input_path_):
        path = os.path.join(_input_path_, file)
        if os.path.isdir(path):
            for num, csv in zip([i + 1 for i in range(len(os.listdir(path)))], os.listdir(path)):
                start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                now_csv = os.path.join(path, csv)
                target_csv = os.path.join(_out_path_, csv)
                shutil.copyfile(now_csv, target_csv)
                end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                visual('Merge-Data extract', cycle=num, Sum=len(os.listdir(path)), start=start, end=end, Clear=False)
    visual('Merge-Data extract', cycle=-1, Clear=True)


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
