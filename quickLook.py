from bokeh.io import curdoc
from bokeh.models.widgets import RangeSlider, RadioButtonGroup, CheckboxGroup
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

TRIGTIME_MIN = -1
TRIGTIME_MAX = 1000

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
    selectable=True,
    height = 400
)


df_hgcrocData = pd.DataFrame(columns=[
    'event', 'chip', 'half', 'channel', 
    'adc', 'adcm', 'toa', 'tot', 
    'totflag', 'trigtime', 
    'corruption', 
    #'bxcounter', 'eventcounter', 'orbitcounter','trigwidth'
])


def selected_input(attr, oldIndices, newIndices):
    for idx in newIndices:
        read_root(os.path.join(dataPath,source_files.data['Path'][idx],source_files.data['Filename'][idx]))

#myTable.on_event(Event, read_root)
source_files.selected.on_change('indices', selected_input)


selected_value = 'adc'
selected_vetocorruption = True
selected_channels = []
selected_rawchannels = []
selected_chip_halfs = []
selected_trigtime_range = [TRIGTIME_MIN, TRIGTIME_MAX]


'''
select_value_dropdown = RadioButtonGroup(labels=['adc','adcm','tot','toa'], active=0)

def select_value(attr,oldIdx,newIdx):
    selected_value = select_value_dropdown.labels[newIdx]

select_value_dropdown.on_change('active',select_value)
'''



checkbox_flag_select = CheckboxGroup(
    labels=['veto corruption'], 
    active=[0]
)
def flag_select_from_checkbox(attr,oldIndices,newIndices):
    global selected_vetocorruption
    if len(newIndices)==0:
        selected_vetocorruption = False
    else:
        selected_vetocorruption = True
    update_adc_overview()
    update_adc_hist()
    update_trigadc_image()
    
        
checkbox_flag_select.on_change('active',flag_select_from_checkbox)

fig_adc_hist = figure(
    x_axis_label = 'adc',
    y_axis_label = 'counts',
    tooltips=[("adc", "@adc"),("counts", "@counts")],
    title = "Channel: all"
)
source_adc_hist = ColumnDataSource(data={'adc':[],'counts':[]})
fig_adc_hist.vbar(x='adc', top='counts', width=1.0, source=source_adc_hist)


def update_adc_hist():
    if len(selected_rawchannels)>0:
        df_selected = df_hgcrocData[(df_hgcrocData['channel']==selected_rawchannels[0]) & (df_hgcrocData['half']==selected_chip_halfs[0]) & (df_hgcrocData['trigtime']>=selected_trigtime_range[0]) & (df_hgcrocData['trigtime']<=selected_trigtime_range[1])]
        for iselect in range(1,len(selected_rawchannels)):
            df_selected = pd.concat([
                df_selected,
                df_hgcrocData[(df_hgcrocData['channel']==selected_rawchannels[iselect]) & (df_hgcrocData['half']==selected_chip_halfs[iselect]) & (df_hgcrocData['trigtime']>=selected_trigtime_range[0]) & (df_hgcrocData['trigtime']<=selected_trigtime_range[1])]
            ])
    else:
        df_selected = df_hgcrocData[(df_hgcrocData['trigtime']>=selected_trigtime_range[0]) & (df_hgcrocData['trigtime']<=selected_trigtime_range[1])]
        
    if selected_vetocorruption:
        df_selected = df_selected[(df_selected['corruption']==0)]
        
    arr_adc = df_selected['adc'].to_numpy()
        
    hist,_ = np.histogram(
        arr_adc,
        bins=np.linspace(-1.5,1023.5,1026)
    )
    adc_values = np.linspace(-1.0,1023,1025)
    source_adc_hist.data = {'adc':adc_values, 'counts':hist}
   
    if len(selected_rawchannels)>0:
        text = "%i"%(selected_channels[0])
        for idx in range(1,len(selected_rawchannels)):
            text += ", %i"%(selected_channels[idx])
        fig_adc_hist.title.text = "Channel: "+text
    else:
        fig_adc_hist.title.text = "Channel: all"
    
    selected_adc = adc_values[hist>1.5]
    if len(selected_adc)>0:
        adc_min = min(selected_adc)
        adc_max = max(selected_adc)
        if adc_min>=-1 and adc_max<=1024 and adc_max>adc_min:
            fig_adc_hist.x_range.start = adc_min
            fig_adc_hist.x_range.end = adc_max
    
    

selected_trigtime_range_slider = RangeSlider(
    value=(TRIGTIME_MIN,TRIGTIME_MAX),
    start = TRIGTIME_MIN,
    end = TRIGTIME_MAX,
    step = 1,
    title="trigtime interval",
    width_policy='max'
)
def trigtime_select_from_slider(attr,old,new):
    global selected_trigtime_range
    selected_trigtime_range = new
    update_adc_hist()
    update_trigadc_image()
    
selected_trigtime_range_slider.on_change('value_throttled',trigtime_select_from_slider)

fig_trig_adc = figure(
    x_axis_label = 'trigtime',
    y_axis_label = 'adc',
    tooltips=[("trigtime", "$x"), ("adc", "$y"), ("value", "@image")],
    title = "Channel: all",
    height = 400
)
source_trig_adc = ColumnDataSource(data={'image':[]})
image2d_trig_adc = fig_trig_adc.image('image',source=source_trig_adc,x=TRIGTIME_MIN,y=-1,dw=TRIGTIME_MAX-TRIGTIME_MIN+1,dh=1025,palette="Spectral11")
select_trigtime_image = BoxSelectTool(dimensions='width')
fig_trig_adc.add_tools(select_trigtime_image)
fig_trig_adc.toolbar.active_drag=select_trigtime_image

def trigtime_select_from_image(selectGeom):
    global selected_trigtime_range
    if selectGeom.geometry["x0"]>0:
        selected_trigtime_range = [
            max(TRIGTIME_MIN,round(selectGeom.geometry["x0"])), 
            min(TRIGTIME_MAX,round(selectGeom.geometry["x1"]))
        ]
        selected_trigtime_range_slider.value=selected_trigtime_range
        update_adc_hist()
        update_trigadc_image()
        
fig_trig_adc.on_event(SelectionGeometry,trigtime_select_from_image)



def update_trigadc_image(adjust_trigtime=False):
    global selected_trigtime_range
    if len(selected_rawchannels)>0:
        df_selected = df_hgcrocData[(df_hgcrocData['channel']==selected_rawchannels[0]) & (df_hgcrocData['half']==selected_chip_halfs[0])]
        for iselect in range(1,len(selected_rawchannels)):
            df_selected = pd.concat([
                df_selected,
                df_hgcrocData[(df_hgcrocData['channel']==selected_rawchannels[iselect]) & (df_hgcrocData['half']==selected_chip_halfs[iselect])]
            ])
    else:
        df_selected = df_hgcrocData.copy()
        
    if selected_vetocorruption:
        df_selected = df_selected[(df_selected['corruption']==0)]
        
    arr_trigtime = df_selected['trigtime'].to_numpy()
    arr_adc = df_selected['adc'].to_numpy()
        
    image,_,_ = np.histogram2d(arr_trigtime,arr_adc,bins=[
        np.linspace(TRIGTIME_MIN-0.5, TRIGTIME_MAX+0.5, TRIGTIME_MAX-TRIGTIME_MIN+2), #np.linspace(149.5,300.5,152), 
        np.linspace(-1.5,1023.5,1026)
    ])
    source_trig_adc.data = {'image':[np.transpose(image)]} #for some reason image is rendered flipped
    
    if len(selected_rawchannels)>0:
        text = "%i"%(selected_channels[0])
        for idx in range(1,len(selected_rawchannels)):
            text += ", %i"%(selected_channels[idx])
        fig_trig_adc.title.text = "Channel: "+text
    else:
        fig_trig_adc.title.text = "Channel: all"
    
    selected_adc = np.linspace(-1.0,1023,1025)[np.sum(image,axis=0)>1.5]
    if len(selected_adc)>0:
        adc_min = min(selected_adc)
        adc_max = max(selected_adc)
        #print (adc_min, adc_max)
        if adc_min>=-1 and adc_max<=1024 and adc_max>adc_min:
            fig_trig_adc.y_range.start = adc_min
            fig_trig_adc.y_range.end = adc_max
        image2d_trig_adc.glyph.color_mapper.low= 1.5
        image2d_trig_adc.glyph.color_mapper.low_color= 'white'

        if adjust_trigtime:
            selected_trigtime = np.linspace(TRIGTIME_MIN, TRIGTIME_MAX, TRIGTIME_MAX-TRIGTIME_MIN+1)[np.sum(image,axis=1)>1.5]
            trig_min = min(selected_trigtime)
            trig_max = max(selected_trigtime)
            if trig_min>=TRIGTIME_MIN and trig_max<=TRIGTIME_MAX and trig_max>trig_min:
                
                selected_trigtime_range = [
                    max(TRIGTIME_MIN,round(trig_min)), 
                    min(TRIGTIME_MAX,round(trig_max))
                ]
                selected_trigtime_range_slider.value = selected_trigtime_range
    fig_trig_adc.x_range.start = selected_trigtime_range[0]
    fig_trig_adc.x_range.end = selected_trigtime_range[1]
                

fig_adc_overview = figure(
    x_axis_label = 'channel',
    y_axis_label = 'adc',
    tooltips=[("channel", "@channel"),("raw channel","@rawchannel"),("chip half", "@half"), ("adc median", "@y50"), ("adc 68%", "[@y15; @y85]")]
)
source_adc_overview = ColumnDataSource(data={'y15':[],'y50':[],'y85':[], 'channel':[], 'rawchannel': [], 'half':[]})
fig_adc_overview.vbar(x='channel',width=0.7,top='y15',bottom='y50',source=source_adc_overview, fill_color='royalblue')
fig_adc_overview.vbar(x='channel',width=0.7,top='y50',bottom='y85',source=source_adc_overview, fill_color='deepskyblue')
select_adc_overview = BoxSelectTool()
fig_adc_overview.add_tools(select_adc_overview)
fig_adc_overview.toolbar.active_drag=select_adc_overview


def channel_select(attrname, old, new):
    global selected_channels,selected_rawchannels, selected_chip_halfs
    selected_rawchannels = []
    selected_chip_halfs = []
    selected_channels = []
    for idx in new:
        selected_channels.append(source_adc_overview.data['channel'][idx])
        selected_rawchannels.append(source_adc_overview.data['rawchannel'][idx])
        selected_chip_halfs.append(source_adc_overview.data['half'][idx])
    update_trigadc_image()
    update_adc_hist()
        
source_adc_overview.selected.on_change('indices',channel_select)

def update_adc_overview():
    if selected_vetocorruption:
        df_selected = df_hgcrocData[(df_hgcrocData['corruption']==0)]
    else:
        df_selected = df_hgcrocData.copy()
    
    quantiles = []
    stds = []
    indices = []
    channels = []
    rawchannels = []
    halfs = []
    #print (df_hgcrocData)
    for half in [0,1]:
        for channel in range(36):
            adc_data = df_selected[(df_selected['half']==half) & (df_selected['channel']==channel)]['adc']
            quantiles.append(adc_data.quantile(q=[0.05,0.15,0.50,0.85,0.95]).to_numpy())
            channels.append(channel+36*half)
            rawchannels.append(channel)
            halfs.append(half)
    quantiles = np.stack(quantiles,axis=1)
    source_adc_overview.data = {'y15': quantiles[1], 'y50': quantiles[2], 'y85': quantiles[3], 'channel': channels, 'half': halfs, 'rawchannel': rawchannels}

def read_root(filePath):
    global df_hgcrocData
    rootFile = uproot.open(filePath,file_handler=uproot.MemmapSource)
    df_hgcrocData  = pd.DataFrame(rootFile['unpacker_data/hgcroc'].arrays([
        'event', 'chip', 'half', 'channel', 
        'adc', 'adcm', 'toa', 'tot', 
        'totflag', 'trigtime', 
        'corruption', 
        #'bxcounter', 'eventcounter', 'orbitcounter', 'trigwidth', 
    ],library='np'))
    update_trigadc_image(adjust_trigtime=True)
    update_adc_overview()
    update_adc_hist()
    '''
    triggerhgcroc = rootFile['unpacker_data/triggerhgcroc'].iterate([
        'event', 'chip', 'trigtime', 'channelsumid', 'rawsum', 'decompresssum'
    ],step_size=100, library='np')
    '''
    
    rootFile.close()
    


#curdoc().add_root(row([column([myTable,]),column(,])]))
curdoc().add_root(
    column([
        row([column([myTable,row([checkbox_flag_select])]), column([selected_trigtime_range_slider,fig_trig_adc])],height=450),
        row([fig_adc_overview,fig_adc_hist],height=550)
    ])
)
