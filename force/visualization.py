import importlib
import json
import os
import random
from typing import Dict, List, Optional, Tuple

import cv2
import matplotlib.pyplot as plt
import numpy as np


if True:
    colors = [ (1,0,0), (0,1,0), (0,0,1), (1,1,0), (0,1,1) ] # 
else:
    colors = set()
    while len(colors)<90:
        colors.add( tuple([round(random.random(),2) for i in range(3)]) )
    colors = list(colors)


def stroke(A,L,color): # list[bool] # up, mid, down, upleft, upright, downleft, downright
    if not L:
        A[:3,:3,:] = 0,0,0
        A[-3:,-3:,:] = 0,0,0
        for i in range(10):
            A[i*2:i*2+2,10-i-1:10-i,:] = 0,0,0
    else:
        if L[0]:
            A[0:3,:,:] = 0,0,0
        if L[1]:
            A[10-1:10+1,:,:] = 0,0,0        
        if L[2]:
            A[20-3:20,:,:] = 0,0,0
        if L[3]:
            A[:10,:3,:] = 0,0,0
        if L[4]:
            A[:10,10-3:,:] = 0,0,0
        if L[5]:
            A[10:,:3,:] = 0,0,0
        if L[6]:
            A[10:,10-3:,:] = 0,0,0
    B = np.array([ [color for j in range(5+10+5)] for i in range(5+20+5) ]).astype(float)
    B[5:25,5:15,:] = A
    return B # 30,20


def getImg(n,color=(1,1,1)):
    A = np.array([ [color for j in range(10)] for i in range(20) ]).astype(float)
    D = {0:[1,0,1,1,1,1,1],
         1:[0,0,0,1,0,1,0],
         2:[1,1,1,0,1,1,0],
         3:[1,1,1,0,1,0,1],
         4:[0,1,0,1,1,0,1],
         5:[1,1,1,1,0,0,1],
         6:[1,1,1,1,0,1,1],
         7:[1,0,0,0,1,0,1],
         8:[1,1,1,1,1,1,1],
         9:[1,1,1,1,1,0,1],
         10:[], # percent
        }
    return stroke(A,D[n],color)


def getPatch(a,b,color=(1,1,1)):
    A = np.array([ [color for j in range(20+20+20)] for i in range(30) ]).astype(float)
    A[:,:20,:] = getImg(a,color)
    A[:,20:40,:] = getImg(b,color)
    A[:,40:60,:] = getImg(10,color)
    return A # 30,60


def show(
        class_list: str,
        data_dict: Dict,
        save_path: Optional[str] = None,
        box_width: int = 4,
        value_ratios: Tuple[int, int] = (1,1)
    ):
    
    img_raw = cv2.imread(data_dict["img_path"])[:,:,::-1]/255

    if 1:
        img_gt = img_raw.copy()
        boxes_gt = data_dict["gt_boxes"] 
        cids_gt = data_dict["gt_cls"]
        for (xmin, ymin, xmax, ymax), cid in zip(boxes_gt, cids_gt):
            img_gt[ymin-box_width:ymin+box_width, xmin:xmax, :] = colors[cid]
            img_gt[ymax-box_width:ymax+box_width, xmin:xmax, :] = colors[cid]
            img_gt[ymin:ymax, xmin-box_width:xmin+box_width, :] = colors[cid]
            img_gt[ymin:ymax, xmax-box_width:xmax+box_width, :] = colors[cid]
    
    if 1:
        img_pd = img_raw.copy()
        pd_probs = data_dict.get("pd_probs", [])
        pd_boxes = data_dict.get("pd_boxes", [])

        if pd_probs:
            pd_confs = np.array(pd_probs).max(axis=1)
            pd_cids = np.array(pd_probs).argmax(axis=1)
        else:
            pd_confs = []
            pd_cids = []

        for pd_conf, (xmin, ymin, xmax, ymax), pd_cid in sorted(zip(pd_confs, pd_boxes, pd_cids)): # plot least conf first
            img_pd[ymin-box_width:ymin+box_width, xmin:xmax, :] = colors[pd_cid]
            img_pd[ymax-box_width:ymax+box_width, xmin:xmax, :] = colors[pd_cid]
            img_pd[ymin:ymax, xmin-box_width:xmin+box_width, :] = colors[pd_cid]
            img_pd[ymin:ymax, xmax-box_width:xmax+box_width, :] = colors[pd_cid]
            
            # confidence patches
            ud, td = int(pd_conf*10), int(pd_conf*100)%10
            P = getPatch(ud, td, color=colors[pd_cid])
            (ph, pw, _), (rh,rw) = P.shape, value_ratios
            P = cv2.resize( P, (int(pw*rw),int(ph*rh)) )
            try:
                if ymin>=P.shape[0] and xmin+P.shape[1]<img_pd.shape[1]: # upper bar - up
                    img_pd[ymin-P.shape[0]:ymin,xmin:xmin+P.shape[1],:] = P
                elif ymax+P.shape[0]<img_pd.shape[0] and xmin+P.shape[1]<img_pd.shape[1]: # down bar - down
                    img_pd[ymax:ymax+P.shape[0],xmin:xmin+P.shape[1],:] = P
                elif ymin+P.shape[0]<img_pd.shape[0] and xmin+P.shape[1]<img_pd.shape[1]:
                    img_pd[ymin:ymin+P.shape[0],xmin:xmin+P.shape[1],:] = P # upper bar - down
                elif ymax+P.shape[0]>0 and xmin+P.shape[1]<img_pd.shape[1]: # down bar - up
                    img_pd[ymax-P.shape[0]:ymax,xmin:xmin+P.shape[1],:] = P
            except:
                pass

    # plot
    fig = plt.figure(figsize=(20,10))
    fig.set_facecolor("white")

    plt.subplot(1,2,1)
    plt.title("GT", fontsize=24)
    plt.tick_params(axis='both', which='major', labelsize=16)
    for r, g, b in colors:
        c2hex = lambda c: hex(int(c*255))[2:].zfill(2)
        plt.scatter([0], [0], c=f"#{c2hex(r)}{c2hex(g)}{c2hex(b)}")

    plt.legend(labels=class_list, fontsize=16)
    plt.imshow(img_gt)
    
    plt.subplot(1,2,2)
    plt.title("Pred", fontsize=24)
    plt.tick_params(axis='both', which='major', labelsize=16)
    plt.imshow(img_pd)
    
    plt.savefig(save_path) if save_path else plt.show()
    plt.close()


def show_general(img_name: str, ant_path: str, save_path: Optional[str] = None):
    """
    Show an image with its ground truth (and prediction if it exists) in general format.
    Hint: Convert coco / voc / yolo to general first by `coco2general` / `voc2general` / `yolo2general`
    Args:
        img_name (str): name of target image to be shown
        ant_path (str): path to the general format
        save_path (Optional[str]): path to save the visualized result
    """
    with open(ant_path, "r", encoding="utf-8") as f:
        general = json.load(f)
        class_list = general["categories"]
    data_dict = next(data_dict for data_dict in general["data"] if os.path.basename(data_dict["img_path"])==img_name)
    show(class_list, data_dict, save_path)


def show_coco(
        img_name: str,
        img_folder: str,
        ant_path: str,
        save_folder: Optional[str] = None,
        use_cache: bool = True,
    ):
    """
    Show an image with its ground truth in coco format.
    This func will convert coco format data into `general` format.
    Args:
        img_name (str): name of target image to be shown
        img_folder (str): path to the image folder
        ant_path (str): path to the coco label
        save_folder (Optional[str], optional): folder saves the conversion result and visualized output
        use_cache (bool, optional): if true, the conversion execute once only.
    """
    from . import coco2general
    no_save_final = save_folder is None
    if no_save_final:
        save_folder = os.path.abspath("example/output/visualization_gt_and_pd/coco")
    
    general_path = os.path.join(save_folder, ".tmp_general.json")
    if not use_cache or not os.path.exists(general_path):
        coco2general(img_folder, ant_path, general_path)
    
    save_path = None if no_save_final else os.path.join(save_folder, img_name)
    show_general(img_name, general_path, save_path)


def show_voc(
        img_name: str,
        img_path_list: List[str],
        ant_path_list: List[str],
        class_list: List[str],
        save_folder: Optional[str] = None,
        use_cache: bool = True,
    ):
    """
    Show an image with its ground truth in voc format.
    This func will convert voc format data into `general` format.
    Args:
        img_name (str): name of target image to be shown
        img_path_list (List[str]): list of image path of the dataset
        ant_path_list (List[str]): list of annotation path of the dataset
        class_list (List[str]): list of class name
        save_folder (Optional[str], optional): folder saves the conversion result and visualized output
        use_cache (bool, optional): if true, the conversion execute once only.
    """
    from . import voc2general
    no_save_final = save_folder is None
    if no_save_final:
        save_folder = os.path.abspath("example/output/visualization_gt_and_pd/voc")
    
    general_path = os.path.join(save_folder, ".tmp_general.json")
    if not use_cache or not os.path.exists(general_path):
        voc2general(img_path_list, ant_path_list, class_list, general_path)
    
    save_path = None if no_save_final else os.path.join(save_folder, img_name)
    show_general(img_name, general_path, save_path)


def show_yolo(
        img_name: str,
        img_path_list: List[str],
        ant_path_list: List[str],
        class_list: List[str],
        save_folder: Optional[str] = None,
        use_cache: bool = True,
    ):
    """
    Show an image with its ground truth in yolo format.
    This func will convert yolo format data into `general` format.
    Args:
        img_name (str): name of target image to be shown
        img_path_list (List[str]): list of image path of the dataset
        ant_path_list (List[str]): list of annotation path of the dataset
        class_list (List[str]): list of class name
        save_folder (Optional[str], optional): folder saves the conversion result and visualized output
        use_cache (bool, optional): if true, the conversion execute once only.
    """
    from . import yolo2general
    no_save_final = save_folder is None
    if no_save_final:
        save_folder = os.path.abspath("example/output/visualization_gt_and_pd/yolo")
    
    general_path = os.path.join(save_folder, ".tmp_general.json")
    if not use_cache or not os.path.exists(general_path):
        yolo2general(img_path_list, ant_path_list, class_list, general_path)
    
    save_path = None if no_save_final else os.path.join(save_folder, img_name)
    show_general(img_name, general_path, save_path)