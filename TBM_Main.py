#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_Main for python                                            *
# * Version:  1.1.1                                                          *
# * Date:     2022-10-13                                                      *
# * Last update: 2022-10-1                                                   *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import os
import shutil
import sys
import urllib.request
import zipfile
import pandas as pd
from TBM_CYCLE import plot_parameters_TBM, TBM_CYCLE, TBM_CYCLE_version
from TBM_REPORT import TBM_REPORT, TBM_REPORT_version
try:
    from TBM_SPLIT import TBM_SPLIT, TBM_SPLIT_version
except ModuleNotFoundError:
    None


def Check_Update():
    """用于检查文件更新， 请勿修改"""
    def Update_file(name, now, new, path, Type):
        if now < new:
            zipfile.ZipFile(os.path.join(path, 'main.zip'), 'r').extract('TBM-Intelligent-main/%s' % name, path)
            current_path = os.path.dirname(os.path.abspath(__file__))
            shutil.copyfile(current_path + '\\temp\\TBM-Intelligent-main\\%s' % name, os.path.join(current_path, name))
            if Type == 'minor update':
                print(' ->->', '\033[0;33mUpdate %s Successfully! Version: %s ->-> %s\033[0m' % (name, now, new))
            if Type == 'main update':
                print(' ->->', '\033[0;32mPlease restart the program!!!\033[0m')
                sys.exit()
    try:
        now_version = {'TBM_Main.py': TBM_Main_version, 'TBM_REPORT.py': TBM_REPORT_version,
                       'TBM_CYCLE.py': TBM_CYCLE_version, 'TBM_SPLIT.py': TBM_SPLIT_version}
    except NameError:
        now_version = {'TBM_Main.py': TBM_Main_version, 'TBM_REPORT.py': TBM_REPORT_version,'TBM_CYCLE.py': TBM_CYCLE_version}
    temp, network = 'temp\\', True
    URL = 'https://github.com/Moonquakes-liu/TBM-Intelligent/archive/refs/heads/'
    if not os.path.exists(temp):
        os.mkdir(temp)
    filepath = os.path.join(temp, 'main.zip')
    try:
        urllib.request.urlretrieve(URL + 'main.zip', filepath)
    except urllib.error.URLError:
        print('\033[0;31mInternet connection failed, unable to check for updates!!!\033[0m')
        network = False
    if network:
        zipfile.ZipFile(filepath, 'r').extract('TBM-Intelligent-main/version', temp)
        new_version = pd.read_csv(os.path.join(temp, 'TBM-Intelligent-main/version'), index_col=0, encoding='gb2312').values
        if new_version.shape[0] > len(now_version):
            print(' ->->', '\033[0;33mAdded %s successfully! Version: %s\033[0m' % (new_version[-1, 0], new_version[-1, 1]))
            Update_file(new_version[-1, 0], '0.0.0', new_version[-1, 1], temp, 'main update')
        elif now_version['TBM_Main.py'] < new_version[0, 1]:
            print(' ->->', '\033[0;33mUpdate %s Successfully! Version: %s ->-> %s\033[0m' % (new_version[0, 0], now_version['TBM_Main.py'], new_version[0, 1]))
            Update_file(new_version[0, 0], now_version[new_version[0, 0]], new_version[0, 1], temp, 'main update')
        else:
            for file, version in new_version[1:]:
                Update_file(file, now_version[file], version, temp, 'minor update')
    shutil.rmtree(temp)


TBM_Main_version = '1.1.1'  # 版本号，请勿修改！！！
Check_Update()  # 检查更新模块，请勿修改！！！


Root_Path = 'D:\\test'  # 文件存放根目录（可修改）
IN_Folder = ['RawData']
Out_Folder = ['AllDataSet', 'KeyDataSet', 'Class-Data', 'ML-Data', 'ML2-Data', 'A-ML2-Data', 'Pdf-Data', 'Pic']  # 生成目录
for folder in Out_Folder:
    if not os.path.exists(os.path.join(Root_Path, folder)):
        os.makedirs(os.path.join(Root_Path, folder))  # 创建文件夹
# 文件夹路径赋值
Raw_Data_Input = os.path.join(Root_Path, IN_Folder[0])  # 原始数据
Cycle_Data_Output = os.path.join(Root_Path, Out_Folder[0])  # 分割好的循环段数据
Key_Data_Output = os.path.join(Root_Path, Out_Folder[1])  # 仅保留破岩关键数据的单个循环段数据
Class_Data_Output = os.path.join(Root_Path, Out_Folder[2])  # 异常的数据
ML_Data_Output = os.path.join(Root_Path, Out_Folder[3])  # 用于机器学习的数据集
ML2_Data_Output = os.path.join(Root_Path, Out_Folder[4])  # 降噪后的数据集
A_ML2_Data_Output = os.path.join(Root_Path, Out_Folder[5])  # 内部段分割的数据集
Pdf_Data_Output = os.path.join(Root_Path, Out_Folder[6])  # 数据汇编
Pic_Data_Output = os.path.join(Root_Path, Out_Folder[7])  # 数据绘图
# 主程序调用函数
TBM_CYCLE().read_file(Raw_Data_Input, Cycle_Data_Output, 100)  # 循环段分割
#key_parameter_extraction(Cycle_Data_Output, Key_Data_Output)  # 破岩关键数据提取
TBM_SPLIT().data_Split(Cycle_Data_Output, A_ML2_Data_Output)
plot_parameters_TBM(Cycle_Data_Output, Pic_Data_Output)  # 参数绘图
TBM_REPORT().cre_pdf(Cycle_Data_Output, Pic_Data_Output, Pdf_Data_Output)  # pdf生成
