#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_Main for python                                            *
# * Version:  4.0.0                                                          *
# * Date:     2022-10-31 20:00:00                                            *
# * Last update: 2022-10-28 20:00:00                                         *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import os
import sys
import shutil
import time
import urllib.request
import zipfile
from TBM import TBM_SPLIT, TBM_FILTER, TBM_REPORT, TBM_PLOT, TBM_CYCLE, \
                TBM_EXTRACT, TBM_CLASS, TBM_CLEAN, TBM_MERGE


def Check_Update():
    """用于检查文件更新， 请勿修改"""
    Temp_path, Network, update = '__temp__\\', True, False  # 临时文件存放位置，是否连接到网络
    New_File_URL = 'https://github.com/Moonquakes-liu/TBM-Intelligent/archive/refs/heads/'
    if not os.path.exists(Temp_path):
        os.mkdir(Temp_path)
    filepath = os.path.join(Temp_path, 'main.zip')
    try:
        urllib.request.urlretrieve(New_File_URL + 'main.zip', filepath)
    except urllib.error.URLError:
        print('\033[0;31mInternet connection failed, unable to check for updates!!!\033[0m')
        Network = False
    if Network:
        zipfile.ZipFile(filepath, 'r').extract('TBM-Intelligent-main/Update.py', Temp_path)
        current_path = os.path.dirname(os.path.abspath(__file__))  # 当前文件夹路径
        new_file_name = current_path + '\\__temp__\\TBM-Intelligent-main\\Update.py'  # 下载的新文件名称
        shutil.copyfile(new_file_name, os.path.join(current_path + '\\__temp__', 'Update.py'))  # 更新新文件
        from __temp__.Update import Update


# 在检查更新前建议先备份之前的py文件
if int(input(' ->-> 是否检查更新 (是:1/否:0):')):
    Check_Update()  # 检查更新模块，请勿修改！！！


Type = input(' ->-> 0程序运行模式 (Normal:1/Debug:0):')
if Type == 'Normal' or int(Type) == 1:
    Debug = False
elif Type == 'Debug' or int(Type) == 0:
    Debug = True
else:
    sys.exit()


start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
Root_Path = os.path.dirname(os.path.abspath(__file__))  # 文件存放根目录（可修改）


# ->->模块1：循环段分割<-<-
"""
TBM_CYCLE(_input_path_, _out_path_, _debug_)为循环段分割配置模块，该模块需要传入的参数包括 
必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）} 可选参数：{程序调试/修复选项（_debug_）}
read_file(_par_name_, _interval_time_)为循环段分割主模块，该模块需要传入的参数包括 
必要参数：{程序运行所需要的关键参数名称（_par_name_）} 可选参数：{相邻循环段时间间隔（s）（_interval_time_）默认100s}
version()为展示程序版本及修改记录模块，该模块无需传入相关参数
"""
Raw_Data_path = os.path.join(Root_Path, 'RawDataSet')  # 原始数据存放路径
Cycle_Data_path = os.path.join(Root_Path, '[ TBM_CYCLE ]-AllDataSet')  # 分割好的循环段数据存放路径
Par_name = ['导向盾首里程', '日期', '推进给定速度', '刀盘转速']  # (桩号、日期、刀盘转速、推进速度设定值)请勿修改顺序
TBM_CYCLE = TBM_CYCLE(_input_path_=Raw_Data_path, _out_path_=Cycle_Data_path, _debug_=Debug)
TBM_CYCLE.version()
TBM_CYCLE.read_file(_par_name_=Par_name, _interval_time_=100)  # 循环段分割


# ->->模块2：提取破岩关键数据<-<-
"""
TBM_EXTRACT(_input_path_, _out_path_, _debug_)为破岩关键数据提取配置模块，该模块需要传入的参数包括 
必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）} 可选参数：{程序调试/修复选项（_debug_）}
key_extract(_key_name_)为破岩关键数据提取主模块，该模块需要传入的参数包括 
必要参数：{程序运行所需要的关键参数名称（_par_name_）}
version()为展示程序版本及修改记录模块，该模块无需传入相关参数
"""
Cycle_Data_path = os.path.join(Root_Path, '[ TBM_CYCLE ]-AllDataSet')  # 分割好的循环段数据存放路径
Key_Data_path = os.path.join(Root_Path, '[ TBM_EXTRACT ]-KeyDataSet')  # 仅保留破岩关键数据的单个循环段数据
key_name = ['导向盾首里程', '日期', '刀盘扭矩', '刀盘贯入度', '刀盘给定转速', '刀盘转速', '推进给定速度', '推进速度(nn/M)', '总推力',
            '推进压力', '冷水泵压力', '控制泵压力', '撑紧压力', '左撑靴位移', '右撑靴位移', '主机皮带机速度', '顶护盾压力', '左侧护盾压力',
            '右侧护盾压力', '顶护盾位移', '左侧护盾位移', '右侧护盾位移', '推进泵电机电流', '推进位移']  # 待提取的关键参数
TBM_EXTRACT = TBM_EXTRACT(_input_path_=Cycle_Data_path, _out_path_=Key_Data_path, _debug_=False)
TBM_EXTRACT.key_extract(_key_name_=key_name)

# ->->模块3：数据分类<-<-
"""
TBM_CLASS(_input_path_, _out_path_)为异常分类配置模块，该模块需要传入的参数包括 
必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）}
data_class(_par_name_, _sub_folder_)为异常分类主模块，该模块需要传入的参数包括 
必要参数：{程序运行所需要的关键参数名称（_par_name_）} 可选参数：{程序运行需要创建的子目录（_sub_folder_）若不传入参数则采用默认子目录名称}
version()为展示程序版本及修改记录模块，该模块无需传入相关参数
"""
if not Debug:
    Key_Data_path = os.path.join(Root_Path, '[ TBM_EXTRACT ]-KeyDataSet')  # 仅保留破岩关键数据的单个循环段数据
    Class_Data_path = os.path.join(Root_Path, '[ TBM_CLASS ]-Class-Data')  # 异常分类的数据
    par_name = ['日期', '导向盾首里程', '刀盘转速', '推进速度(nn/M)', '刀盘扭矩',
                '总推力', '刀盘给定转速', '推进给定速度', '推进位移', '刀盘贯入度']
    Out_dir = ['A1class-data', 'B1class-data', 'B2class-data', 'C1class-data',
               'C2class-data', 'D1class-data', 'E1class-data', 'Norclass-data']
    TBM_CLASS = TBM_CLASS(_input_path_=Key_Data_path, _out_path_=Class_Data_path)
    TBM_CLASS.data_class(_par_name_=par_name, _sub_folder_=Out_dir)


# ->->模块4、5：异常1数据清理、异常2数据清理<-<-
"""
TBM_CLEAN(_input_path_, _out_path_)为异常数据清理修正配置模块，该模块需要传入的参数包括 
必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）}
data_clean(_par_name_, _sub_folder_)为异常数据清理修正主模块，该模块需要传入的参数包括 
必要参数：{程序运行所需要的关键参数名称（_par_name_）} 可选参数：{程序运行需要创建的子目录（_sub_folder_）若不传入参数则采用默认子目录名称}
version()为展示程序版本及修改记录模块，该模块无需传入相关参数
"""
if not Debug:
    Class_Data_path = os.path.join(Root_Path, '[ TBM_CLASS ]-Class-Data')  # 异常分类的数据
    Clean_Data_path = os.path.join(Root_Path, '[ TBM_CLEAN ]-Clean-Data')  # 异常数据清理修正
    par_name = ['日期', '导向盾首里程', '刀盘转速', '推进速度(nn/M)', '刀盘扭矩',
                '总推力', '刀盘给定转速', '推进给定速度', '推进位移', '刀盘贯入度']
    Out_dir = ['NorA1class-data', 'NorB1class-data', 'NorB2class-data', 'NorC1class-data',
               'NorC2class-data', 'NorD1class-data', 'NorE1class-data', 'Norclass-data', ]
    TBM_CLEAN = TBM_CLEAN(_input_path_=Class_Data_path, _out_path_=Clean_Data_path)
    TBM_CLEAN.data_clean(_par_name_=par_name, _sub_folder_=Out_dir)


# ->->模块6：合并形成机器学习数据集<-<-
"""
TBM_MERGE(_input_path_, _out_path_)为数据集合并配置模块，该模块需要传入的参数包括 
必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）}
data_merge()为数据集合并主模块，该模块无需传入相关参数
version()为展示程序版本及修改记录模块，该模块无需传入相关参数
"""
if not Debug:
    Clean_Data_path = os.path.join(Root_Path, '[ TBM_CLEAN ]-Clean-Data')  # 异常数据清理修正
    ML_Data_path = os.path.join(Root_Path, '[ TBM_MERGE ]-ML-Data')  # 合并形成机器学习数据集
    TBM_MERGE = TBM_MERGE(_input_path_=Clean_Data_path, _out_path_=ML_Data_path)
    TBM_MERGE.data_merge()


# ->->模块7：数据降噪<-<-
"""
TBM_FILTER(_input_path_, _out_path_)为数据降噪配置模块，该模块需要传入的参数包括 
必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）}
data_filter(_par_name_)为数据降噪主模块，该模块需要传入的参数包括 
可选参数：{程序运行所需要的关键参数名称（_par_name_），若传入参数，则仅对传入的参数进行降噪，若不传入参数，则对所有参数进行降噪}
version()为展示程序版本及修改记录模块，该模块无需传入相关参数
"""
if not Debug:
    ML_Data_path = os.path.join(Root_Path, '[ TBM_MERGE ]-ML-Data')  # 合并形成机器学习数据集
    ML2_Data_path = os.path.join(Root_Path, '[ TBM_FILTER ]-ML2-Data')  # 降噪后数据保存路径
    par_name = ['总推力']  # 待降噪参数
    TBM_FILTER = TBM_FILTER(_input_path_=ML_Data_path, _out_path_=ML2_Data_path)
    TBM_FILTER.data_filter()


# ->->模块8：内部段分割<-<-
"""
TBM_SPLIT(_input_path_, _out_path_, _debug_)为内部段分割配置模块，该模块需要传入的参数包括 
必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）} 可选参数：{程序调试/修复选项（_debug_）}
data_clean(_par_name_, _sub_folder_)为内部段分割主模块，该模块需要传入的参数包括 
必要参数：{程序运行所需要的关键参数名称（_par_name_）} 可选参数：{程序运行需要创建的子目录（_sub_folder_）若不传入参数则采用默认子目录名称}
version()为展示程序版本及修改记录模块，该模块无需传入相关参数
"""
if Debug:
    ML_Data_path = os.path.join(Root_Path, '[ TBM_EXTRACT ]-KeyDataSet')  # 合并形成机器学习数据集
else:
    ML_Data_path = os.path.join(Root_Path, '[ TBM_MERGE ]-ML-Data')  # 合并形成机器学习数据集
A_ML2_Data_path = os.path.join(Root_Path, '[ TBM_SPLIT ]-A-ML2-Data')  # 内部段分割后的数据集
Par_name = ['推进位移', '推进速度(nn/M)', '刀盘贯入度', '推进给定速度']  # (推进位移、推进速度、刀盘贯入度、推进速度设定值)请勿修改顺序
Out_dir = ['Free running', 'Loading', 'Boring', 'Loading and Boring', 'Boring cycle']
TBM_SPLIT = TBM_SPLIT(_input_path_=ML_Data_path, _out_path_=A_ML2_Data_path, _debug_=Debug)
TBM_SPLIT.data_split(_par_name_=Par_name, _sub_folder_=Out_dir)

# ->->模块10：数据绘图<-<-
"""
TBM_PLOT(_input_path_, _out_path_, _debug_)为参数绘图配置模块，该模块需要传入的参数包括
必要参数：{原始文件存放路径（_input_path_），生成数据的保存路径（_out_path_）}
data_plot(_par_name_, _Format_)为参数绘图主模块，该模块需要传入的参数包括
必要参数：{程序运行所需要的关键参数名称（_par_name_）}，可选参数：{生成图片的格式（_Format_），位图（png）/矢量图（svg）}
version()为展示程序版本及修改记录模块，该模块无需传入相关参数
"""
if Debug:
    ML_Data_path = os.path.join(Root_Path, '[ TBM_EXTRACT ]-KeyDataSet')  # 合并形成机器学习数据集
else:
    ML_Data_path = os.path.join(Root_Path, '[ TBM_MERGE ]-ML-Data')  # 合并形成机器学习数据集
Pic_Data_path = os.path.join(Root_Path, '[ TBM_PLOT ]-Pic')  # 绘制完成的图片保存位置
Par_name = ['刀盘转速', '刀盘给定转速', '推进速度(nn/M)', '推进给定速度', '刀盘扭矩', '总推力']  # （要绘制的掘进参数）请勿修改顺序
TBM_PLOT = TBM_PLOT(_input_path_=ML_Data_path, _out_path_=Pic_Data_path)
TBM_PLOT.data_plot(_par_name_=Par_name)

# ->->模块9：数据汇编<-<-
"""
TBM_REPORT(_input_path_, _input_pic_, _out_path_)为参数绘图配置模块，该模块需要传入的参数包括 
必要参数：{原始文件存放路径（_input_path_），原始图片存放路径（_input_pic_），生成数据的保存路径（_out_path_）}
cre_pdf(_par_name_)为参数绘图主模块，该模块需要传入的参数包括 
必要参数：{程序运行所需要的关键参数名称（_par_name_）}
version()为展示程序版本及修改记录模块，该模块无需传入相关参数
"""
if Debug:
    ML_Data_path = os.path.join(Root_Path, '[ TBM_EXTRACT ]-KeyDataSet')  # 合并形成机器学习数据集
else:
    ML_Data_path = os.path.join(Root_Path, '[ TBM_MERGE ]-ML-Data')  # 合并形成机器学习数据集
Pic_Data_path = os.path.join(Root_Path, '[ TBM_PLOT ]-Pic')  # 绘制完成的图片保存位置
Pdf_Data_path = os.path.join(Root_Path, '[ TBM_REPORT ]-Pdf-Data')  # 绘制完成的图片保存位置
Par_name = ['导向盾首里程', '日期', '推进位移']  # （桩号、日期、推进位移）请勿修改顺序
TBM_REPORT = TBM_REPORT(_input_path_=ML_Data_path, _input_pic_=Pic_Data_path, _out_path_=Pdf_Data_path)
TBM_REPORT.cre_pdf(_par_name_=Par_name)


end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
time = end - start


if time < 3600:
    if time < 60:
        print(' ->->', '花费时间：%5.2f s' % round(time, 2))
    else:
        print(' ->->', '花费时间：%5.2f min' % round(time/60, 2))
else:
    print(' ->->', '花费时间：%5.2f h' % round(time / 3600, 2))
