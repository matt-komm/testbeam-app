from bokeh.io import curdoc
from bokeh.models.widgets import RangeSlider
from bokeh.models import ColumnDataSource, TableColumn, DataTable, MultiSelect, BoxSelectTool, BoxAnnotation, LinearColorMapper
from bokeh.events import DocumentReady, SelectionGeometry
from bokeh.plotting import figure
from bokeh.layouts import row,column
from bokeh.colors  import Color

import pandas as pd
import uproot
import numpy as np

import os
import sys
import env
import time

TRIGTIME_MIN = 180
TRIGTIME_MAX = 220

dataPath = os.environ.get('QLDATA', os.getcwd())
print (dataPath)
source_files = ColumnDataSource({"Path":[],"Filename":[], "Date": []})

def discover_files(event):
    paths = []
    filenames = []
    dates = []
    timeStamps = []
    for root, dirs, files in os.walk(dataPath):
        for f in files:
            if f.endswith(".root"):
                fullPath = os.path.join(root,f)
                path,filename = os.path.relpath(fullPath,dataPath).rsplit('/',1)
                paths.append(path)
                filenames.append(filename)
                timeStamp =  os.path.getmtime(fullPath)
                timeStamps.append(timeStamp)
                date = time.ctime(timeStamp)
                dates.append(date)
                
    #df_files["Filename"] = filenames
    #print (df_files)
    #df_files = new_df_files
    source_files.data = {"Path":paths,"Filename":filenames, "Date": dates}
    #print (df_files)
    

    
curdoc().on_event(DocumentReady, discover_files)

myTable = DataTable(
    source=source_files, 
    columns=[
        TableColumn(field='Path', title='Path'),
        TableColumn(field='Filename', title='Filename'),
        TableColumn(field='Date', title='Date'),
    ],
    selectable=True
)


df_hgcrocData = pd.DataFrame(columns=[
    'event', 'chip', 'half', 'channel', 
    'adc', 'adcm', 'toa', 'tot', 
    'totflag', 'trigtime', 'trigwidth', 
    'corruption', 'bxcounter', 'eventcounter', 
    'orbitcounter'
])


def selected_input(attr, oldIndices, newIndices):
    for idx in newIndices:
        read_root(os.path.join(dataPath,source_files.data['Path'][idx],source_files.data['Filename'][idx]))

#myTable.on_event(Event, read_root)
source_files.selected.on_change('indices', selected_input)




selected_channels = []
selected_chip_halfs = []
trigtime_range = [TRIGTIME_MIN, TRIGTIME_MAX]


fig_adc_hist = figure(
    x_axis_label = 'adc',
    y_axis_label = 'counts',
    tooltips=[("adc", "@adc"),("counts", "@counts")]
)
source_adc_hist = ColumnDataSource(data={'adc':[],'counts':[]})
fig_adc_hist.vbar(x='adc', top='counts', width=1.0, source=source_adc_hist)

def update_adc_hist():
    if len(selected_channels)>0:
        df_selected = df_hgcrocData[(df_hgcrocData['channel']==selected_channels[0]) & (df_hgcrocData['half']==selected_chip_halfs[0]) & (df_hgcrocData['trigtime']>trigtime_range[0]) & (df_hgcrocData['trigtime']<trigtime_range[1])]
        for iselect in range(1,len(selected_channels)):
            df_selected = pd.concat([
                df_selected,
                df_hgcrocData[(df_hgcrocData['channel']==selected_channels[iselect]) & (df_hgcrocData['half']==selected_chip_halfs[iselect]) & (df_hgcrocData['trigtime']>trigtime_range[0]) & (df_hgcrocData['trigtime']<trigtime_range[1])]
            ])
        
        arr_adc = df_selected['adc'].to_numpy()
    else:
        df_selected = df_hgcrocData[(df_hgcrocData['trigtime']>trigtime_range[0]) & (df_hgcrocData['trigtime']<trigtime_range[1])]
        arr_adc = df_hgcrocData['adc'].to_numpy()
    hist,_ = np.histogram(
        arr_adc,
        bins=np.linspace(-0.5,1023.5,1025)
    )
    adc_values = np.linspace(0.0,1023,1024)
    source_adc_hist.data = {'adc':adc_values, 'counts':hist}
    
    selected_adc = adc_values[hist>1.5]
    if len(selected_adc)>0:
        adc_min = min(selected_adc)
        adc_max = max(selected_adc)
        if adc_min>=0 and adc_max<=1024 and adc_max>adc_min:
            fig_adc_hist.x_range.start = adc_min
            fig_adc_hist.x_range.end = adc_max
    
    

trigtime_range_slider = RangeSlider(
    value=(TRIGTIME_MIN,TRIGTIME_MAX),
    start = TRIGTIME_MIN,
    end = TRIGTIME_MAX,
    step = 1,
    title="trigtime interval",
    width_policy='max'
)
def trigtime_select_from_slider(attr,old,new):
    global trigtime_range
    trigtime_range = new
    update_adc_hist()
    
trigtime_range_slider.on_change('value_throttled',trigtime_select_from_slider)

fig_trig_adc = figure(
    x_axis_label = 'trigtime',
    y_axis_label = 'adc',
    tooltips=[("trigtime", "$x"), ("adc", "$y"), ("value", "@image")],
    title = "Channels: all"
)
source_trig_adc = ColumnDataSource(data={'image':[]})
image2d_trig_adc = fig_trig_adc.image('image',source=source_trig_adc,x=TRIGTIME_MIN,y=0,dw=TRIGTIME_MAX-TRIGTIME_MIN+1,dh=1024,palette="Spectral11")
select_trigtime_image = BoxSelectTool(dimensions='width')
fig_trig_adc.add_tools(select_trigtime_image)
fig_trig_adc.toolbar.active_drag=select_trigtime_image

def trigtime_select_from_image(selectGeom):
    global trigtime_range
    if selectGeom.geometry["x0"]>0:
        trigtime_range = [
            max(TRIGTIME_MIN,round(selectGeom.geometry["x0"])), 
            min(TRIGTIME_MAX,round(selectGeom.geometry["x1"]))
        ]
        trigtime_range_slider.value=trigtime_range
        update_adc_hist()
        
fig_trig_adc.on_event(SelectionGeometry,trigtime_select_from_image)



def update_trigadc_image():
    if len(selected_channels)>0:
        df_selected = df_hgcrocData[(df_hgcrocData['channel']==selected_channels[0]) & (df_hgcrocData['half']==selected_chip_halfs[0])]
        for iselect in range(1,len(selected_channels)):
            df_selected = pd.concat([
                df_selected,
                df_hgcrocData[(df_hgcrocData['channel']==selected_channels[iselect]) & (df_hgcrocData['half']==selected_chip_halfs[iselect])]
            ])
        
        arr_trigtime = df_selected['trigtime'].to_numpy()
        arr_adc = df_selected['adc'].to_numpy()
    else:
        arr_trigtime = df_hgcrocData['trigtime'].to_numpy()
        arr_adc = df_hgcrocData['adc'].to_numpy()
    image,_,_ = np.histogram2d(arr_trigtime,arr_adc,bins=[
        np.linspace(TRIGTIME_MIN-0.5, TRIGTIME_MAX+0.5, TRIGTIME_MAX-TRIGTIME_MIN+2), #np.linspace(149.5,300.5,152), 
        np.linspace(-0.5,1023.5,1025)
    ])
    source_trig_adc.data = {'image':[np.transpose(image)]} #for some reason image is rendered flipped
    
    if len(selected_channels)>0:
        fig_trig_adc.title.text = "Channels: "+str(selected_channels)
    
    selected_adc = np.linspace(0.0,1023,1024)[np.sum(image,axis=0)>1.5]
    if len(selected_adc)>0:
        adc_min = min(selected_adc)
        adc_max = max(selected_adc)
        #print (adc_min, adc_max)
        if adc_min>=0 and adc_max<=1024 and adc_max>adc_min:
            fig_trig_adc.y_range.start = adc_min
            fig_trig_adc.y_range.end = adc_max
        image2d_trig_adc.glyph.color_mapper.low= 1.5
        image2d_trig_adc.glyph.color_mapper.low_color= 'white'


fig_adc_overview = figure(
    x_axis_label = 'channel',
    y_axis_label = 'mean adc',
    tooltips=[("channel", "@channel"),("chip half", "@half"), ("adc", "$y")]
)
source_adc_overview = ColumnDataSource(data={'x':[],'y1':[],'y2':[], 'channel':[], 'half':[]})
fig_adc_overview.vbar(x='x',width=0.7,top='y1',bottom='y2',source=source_adc_overview)
select_adc_overview = BoxSelectTool()
fig_adc_overview.add_tools(select_adc_overview)
fig_adc_overview.toolbar.active_drag=select_adc_overview


def channel_select(attrname, old, new):
    global selected_channels, selected_chip_halfs
    selected_channels = []
    selected_chip_halfs = []
    for idx in new:
        selected_channels.append(source_adc_overview.data['channel'][idx])
        selected_chip_halfs.append(source_adc_overview.data['half'][idx])
    update_trigadc_image()
    update_adc_hist()
        
source_adc_overview.selected.on_change('indices',channel_select)

def update_adc_overview():
    arr_trigtime = df_hgcrocData['trigtime'].to_numpy()
    arr_adc = df_hgcrocData['adc'].to_numpy()
    means = []
    stds = []
    indices = []
    channels = []
    halfs = []
    idx = 0
    #print (df_hgcrocData)
    for half in [0,1]:
        for channel in range(39):
            adc_data = df_hgcrocData[(df_hgcrocData['half']==half) & (df_hgcrocData['channel']==channel)]['adc']
            means.append(adc_data.mean())
            stds.append(adc_data.std())
            indices.append(idx)
            channels.append(channel)
            halfs.append(half)
            idx+=1
    means = np.array(means,dtype=np.float32)
    stds = np.array(stds,dtype=np.float32)
    source_adc_overview.data = {'x':indices, 'y1': means+stds, 'y2': means-stds, 'channel': channels, 'half': halfs}
    #source_image.data = {'image':[image]}

def read_root(filePath):
    global df_hgcrocData
    rootFile = uproot.open(filePath)
    df_hgcrocData  = pd.DataFrame(rootFile['unpacker_data/hgcroc'].arrays([
        'event', 'chip', 'half', 'channel', 
        'adc', 'adcm', 'toa', 'tot', 
        'totflag', 'trigtime', 'trigwidth', 
        'corruption', 'bxcounter', 'eventcounter', 
        'orbitcounter'
    ],library='np'))
    update_trigadc_image()
    update_adc_overview()
    update_adc_hist()
    '''
    triggerhgcroc = rootFile['unpacker_data/triggerhgcroc'].iterate([
        'event', 'chip', 'trigtime', 'channelsumid', 'rawsum', 'decompresssum'
    ],step_size=100, library='np')
    '''
    
    rootFile.close()
    


curdoc().add_root(row([column([myTable,fig_adc_overview]),column([trigtime_range_slider,fig_trig_adc,fig_adc_hist])]))


