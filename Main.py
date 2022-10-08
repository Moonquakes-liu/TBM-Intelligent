# -*- coding: utf-8 -*-
import os
from TBM智能建造.EX_CYCLE import plot_parameters_TBM
from TBM智能建造.EX_CYCLE import TBM_CYCLE
from TBM智能建造.TBM_REPORT import TBM_REPORT

print(' ->-> If program is missing, please visit:')
print(' ->-> URl= https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A  password= STBM <-<-')

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
plot_parameters_TBM(Cycle_Data_Output, Pic_Data_Output)  # 参数绘图
TBM_REPORT().cre_pdf(Cycle_Data_Output, Pic_Data_Output, Pdf_Data_Output)  # pdf生成
