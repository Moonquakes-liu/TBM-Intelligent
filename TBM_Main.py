#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_Main for python                                            *
# * Version:  1.1.2                                                          *
# * Date:     2022-10-13                                                      *
# * Last update: 2022-10-1                                                   *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import os
import shutil
import sys
import time
import urllib.request
import zipfile
import pandas as pd
from TBM_CYCLE import TBM_CYCLE, key_parameter_extraction, TBM_CYCLE_version
from TBM_REPORT import TBM_REPORT, plot_parameters_TBM, TBM_REPORT_version
try:
    from TBM_SPLIT import TBM_SPLIT, butter_worth_filter, TBM_SPLIT_version
except ModuleNotFoundError:
    None


def Check_Update():
    """用于检查文件更新， 请勿修改"""
    def Update_file(name, now, new, path, Type):
        if now < new:
            zipfile.ZipFile(os.path.join(path, 'main.zip'), 'r').extract('TBM-Intelligent-main/%s' % name, path)
            current_path = os.path.dirname(os.path.abspath(__file__))
            old_program = current_path + '\\Old Programs'
            if not os.path.exists(old_program):
                os.makedirs(old_program)
            shutil.copyfile(os.path.join(current_path, name), os.path.join(current_path, '%s version%s.py' % (name[:,-3], now)))
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


TBM_Main_version = '1.1.2'  # 版本号，请勿修改！！！
Check_Update()  # 检查更新模块，请勿修改！！！
start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
print('\033[0;33m请将本程序及其附属模块均放置在要提取的文件夹上一级目录下，如要提取数据的文件夹在{···/RawData}，则程序文件放置在{···/}下！！！\033[0m')
Root_Path = os.path.dirname(os.path.abspath(__file__))  # 文件存放根目录（可修改）
IN_Folder = ['RawData']
Out_Folder = ['TBM_CYCLE-AllDataSet', 'TBM_CYCLE-KeyDataSet', 'Class-Data', 'ML-Data', 'TBM_SPLIT-ML2-Data',
              'TBM_SPLIT-A-ML2-Data', 'TBM_REPORT-Pdf-Data', 'TBM_REPORT-Pic']  # 生成目录
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


"""写一段文字，程序的使用说明：1.plot_parameters_TBM，TBM_REPORT调用的时候应该根据自己的目标选择相应的Output"""
# ->->模块1：循环段分割<-<-
TBM_CYCLE().read_file(Raw_Data_Input, Cycle_Data_Output, 100)  # 循环段分割

# ->->模块2：提取破岩关键数据<-<-
key_name = ['导向盾首里程', '日期', '刀盘扭矩', '刀盘贯入度', '刀盘给定转速', '刀盘转速', '推进给定速度', '推进速度(nn/M)', '总推力',
            '推进压力', '冷水泵压力', '控制泵压力', '撑紧压力', '左撑靴位移', '右撑靴位移', '主机皮带机速度', '顶护盾压力', '左侧护盾压力',
            '右侧护盾压力', '顶护盾位移', '左侧护盾位移', '右侧护盾位移', '推进泵电机电流', '推进位移']  # 待提取的关键参数
key_parameter_extraction(Cycle_Data_Output, Key_Data_Output, key_name)  # 破岩关键数据提取

# ->->模块3：数据分类<-<-

# ->->模块4：异常1数据清理<-<-

# ->->模块5：异常2数据清理<-<-

# ->->模块6：合并形成机器学习数据集<-<-

# ->->模块7：数据降噪<-<-
butter_worth_filter(Key_Data_Output, ML2_Data_Output)

# ->->模块8：内部段分割<-<-
TBM_SPLIT().data_Split(Key_Data_Output, A_ML2_Data_Output)

# ->->模块10：数据绘图<-<-
Par_name = ['刀盘转速', '刀盘给定转速', '推进速度(nn/M)', '推进给定速度', '刀盘扭矩', '总推力']  # 要绘制的掘进参数
plot_parameters_TBM(Key_Data_Output, Pic_Data_Output, Par_name)

# ->->模块9：数据汇编<-<-
TBM_REPORT().cre_pdf(Cycle_Data_Output, Pic_Data_Output, Pdf_Data_Output)
end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
print(end-start)
