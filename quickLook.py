from bokeh.io import curdoc
from bokeh.models.widgets import RangeSlider, RadioButtonGroup, CheckboxGroup
from bokeh.models import Spinner, TextInput
from bokeh.models.ui.menus import Menu,Action
from bokeh.models import ColumnDataSource, TableColumn, DataTable, MultiSelect, BoxSelectTool, BoxAnnotation, LinearColorMapper, HoverTool
from bokeh.events import DocumentReady, SelectionGeometry
from bokeh.plotting import figure
from bokeh.layouts import row,column
from bokeh.colors  import Color

import pandas as pd
import uproot
import numpy as np

import os
import sys
import re
import time

TRIGTIME_MIN = 0
TRIGTIME_MAX = 500

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


selected_quantity = 'adc'
selected_vetocorruption = True
selected_percentile = 60
selected_channels = []
selected_rawchannels = []
selected_chip_halfs = []
selected_chips = []
selected_trigtime_range = [TRIGTIME_MIN, TRIGTIME_MAX]



dropdown_select_quantity = RadioButtonGroup(labels=['adc','adcm','tot','toa'], active=0)

def quantity_select_from_radiobutton(attr,oldIdx,newIdx):
    global selected_quantity
    selected_quantity = dropdown_select_quantity.labels[newIdx]
    update_adc_hist()
    update_trigadc_image()

dropdown_select_quantity.on_change('active',quantity_select_from_radiobutton)




checkbox_vetocorruption_select = CheckboxGroup(
    labels=['veto corruption'], 
    active=[0],
    margin=[10,10,10,0]
)
def vetocorruption_select_from_checkbox(attr,oldIndices,newIndices):
    global selected_vetocorruption
    if len(newIndices)==0:
        selected_vetocorruption = False
    else:
        selected_vetocorruption = True
    update_adc_overview()
    update_adc_hist()
    update_trigadc_image()
    
        
checkbox_vetocorruption_select.on_change('active',vetocorruption_select_from_checkbox)

'''
textfield_channel_select = TextInput(value="all")

def channel_select_from_textfield(attr,old,new):
    if len(new)==0:
        pass
        #textfield_channel_select.value = "all"
    else:
        try:
            numbers = list(map(int,re.split(' ;|,', new)))
            print (numbers)
            textfield_channel_select.prefix = None
        except Exception as e:
            textfield_channel_select.prefix = "INVALID"
    print(old,"=>",new)
    
textfield_channel_select.on_change('value',channel_select_from_textfield)
'''
fig_adc_hist = figure(
    x_axis_label = selected_quantity,
    y_axis_label = 'counts',
    
    title = "Channel: all"
)
source_quantity_hist = ColumnDataSource(data={'quantity':[],'counts':[]})
fig_adc_hist.vbar(x='quantity', top='counts', width=1.0, source=source_quantity_hist)


def update_adc_hist():
    global selected_quantity
    fig_adc_hist.xaxis.axis_label = selected_quantity
    fig_adc_hist.select(dict(type=HoverTool)).tooltips=[("selected_quantity", "@quantity"),("counts", "@counts")]
    
    if len(selected_rawchannels)>0:
        df_selected = df_hgcrocData[(df_hgcrocData['chip']==selected_chips[0]) & (df_hgcrocData['channel']==selected_rawchannels[0]) & (df_hgcrocData['half']==selected_chip_halfs[0]) & (df_hgcrocData['trigtime']>=selected_trigtime_range[0]) & (df_hgcrocData['trigtime']<=selected_trigtime_range[1])]
        for iselect in range(1,len(selected_rawchannels)):
            df_selected = pd.concat([
                df_selected,
                df_hgcrocData[(df_hgcrocData['chip']==selected_chips[iselect]) & (df_hgcrocData['channel']==selected_rawchannels[iselect]) & (df_hgcrocData['half']==selected_chip_halfs[iselect]) & (df_hgcrocData['trigtime']>=selected_trigtime_range[0]) & (df_hgcrocData['trigtime']<=selected_trigtime_range[1])]
            ])
    else:
        df_selected = df_hgcrocData[(df_hgcrocData['trigtime']>=selected_trigtime_range[0]) & (df_hgcrocData['trigtime']<=selected_trigtime_range[1])]
        
    if selected_vetocorruption:
        df_selected = df_selected[(df_selected['corruption']==0)]
        
    arr_quantity = df_selected[selected_quantity].to_numpy()
        
    hist,_ = np.histogram(
        arr_quantity,
        bins=np.linspace(-1.5,1023.5,1026)
    )
    quantity_values = np.linspace(-1.0,1023,1025)
    source_quantity_hist.data = {'quantity':quantity_values, 'counts':hist}
   
    if len(selected_rawchannels)>0:
        text = "%i"%(selected_channels[0])
        for idx in range(1,len(selected_rawchannels)):
            text += ", %i"%(selected_channels[idx])
        fig_adc_hist.title.text = "Channel: "+text
    else:
        fig_adc_hist.title.text = "Channel: all"
    
    quantity_above_thres = quantity_values[hist>1.5]
    if len(quantity_above_thres)>0:
        quantity_min = min(quantity_above_thres)
        quantity_max = max(quantity_above_thres)
        if quantity_min>=-1 and quantity_max<=1024 and quantity_max>quantity_min:
            fig_adc_hist.x_range.start = quantity_min
            fig_adc_hist.x_range.end = quantity_max
    
    

selected_trigtime_range_slider = RangeSlider(
    value=(TRIGTIME_MIN,TRIGTIME_MAX),
    start = TRIGTIME_MIN,
    end = TRIGTIME_MAX,
    step = 1,
    title="trigtime interval",
    width_policy='max',
    margin=[10,10,10,20]
)

def trigtime_select_from_slider(attr,old,new):
    global selected_trigtime_range
    selected_trigtime_range = new
    update_adc_hist()
    update_trigadc_image()
    
selected_trigtime_range_slider.on_change('value_throttled',trigtime_select_from_slider)


spinner_percentile = Spinner(
    title='percentile', 
    high=100,
    low=0,
    value=selected_percentile,
    mode='int',
    width=80
)
def percentile_on_change(attr,old,new):
    global selected_percentile
    selected_percentile = new
    update_trigadc_image()
    
spinner_percentile.on_change('value',percentile_on_change)


fig_trig_adc = figure(
    x_axis_label = 'trigtime',
    y_axis_label = 'adc',
    tooltips=[("trigtime", "$x"), (selected_quantity, "@y"), ("counts", "@image")],
    title = "Channel: all",
    height = 400
)
source_trig_quantity = ColumnDataSource(data={'image':[]})
source_trig_percentiles = ColumnDataSource(data={'percentile_x':[],'percentile_y':[]})
image2d_trig_adc = fig_trig_adc.image('image',source=source_trig_quantity,x=TRIGTIME_MIN,y=-1,dw=TRIGTIME_MAX-TRIGTIME_MIN+1,dh=1025,palette="Spectral11")

#TODO: this causes a bug in the xaxis range; unclear perhaps try new bokeh version
fig_trig_adc.line(x='percentile_x',y='percentile_y',source=source_trig_percentiles,color='#ff0000',line_width=2)
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
    global selected_trigtime_range, selected_quantity, selected_percentile, fig_trig_adc

    fig_trig_adc.yaxis.axis_label = selected_quantity
    fig_trig_adc.select(dict(type=HoverTool)).tooltips=[("trigtime", "$x"), (selected_quantity, "@y"), ("counts", "@image")]
    
    if len(selected_rawchannels)>0:
        df_selected = df_hgcrocData[(df_hgcrocData['chip']==selected_chips[0]) & (df_hgcrocData['channel']==selected_rawchannels[0]) & (df_hgcrocData['half']==selected_chip_halfs[0])]
        for iselect in range(1,len(selected_rawchannels)):
            df_selected = pd.concat([
                df_selected,
                df_hgcrocData[(df_hgcrocData['chip']==selected_chips[iselect]) & (df_hgcrocData['channel']==selected_rawchannels[iselect]) & (df_hgcrocData['half']==selected_chip_halfs[iselect])]
            ])
    else:
        df_selected = df_hgcrocData.copy()
        
    if selected_vetocorruption:
        df_selected = df_selected[(df_selected['corruption']==0)]
        
    arr_trigtime = df_selected['trigtime'].to_numpy()
    arr_quantity = df_selected[selected_quantity].to_numpy()
        
    trigtime_binning = np.linspace(TRIGTIME_MIN-0.5, TRIGTIME_MAX+0.5, TRIGTIME_MAX-TRIGTIME_MIN+2)
    adc_binning = np.linspace(-1.5,1023.5,1026)
       
    image,_,_ = np.histogram2d(arr_trigtime,arr_quantity,bins=[
        trigtime_binning, #np.linspace(149.5,300.5,152), 
        adc_binning
    ])
    
    cumsum = np.cumsum(image,axis=1)
    cumsum /= cumsum[:,-1:]+0.1
    adc_percentile_idx = np.argmin(np.square(cumsum-0.01*selected_percentile),axis=1)
    adc_percentile = adc_binning[adc_percentile_idx]
    
    source_trig_percentiles.data = {
        'percentile_x': np.linspace(TRIGTIME_MIN, TRIGTIME_MAX, TRIGTIME_MAX-TRIGTIME_MIN+1)+0.5,
        'percentile_y': adc_percentile
    }
    source_trig_quantity.data = {
        'image':[np.transpose(image)], #for some reason image is rendered flipped
    }
    
    
    if len(selected_rawchannels)>0:
        text = "%i"%(selected_channels[0])
        for idx in range(1,len(selected_rawchannels)):
            text += ", %i"%(selected_channels[idx])
        fig_trig_adc.title.text = "Channel: "+text
    else:
        fig_trig_adc.title.text = "Channel: all"
    
    quantity_over_thres = np.linspace(-1.0,1023,1025)[np.sum(image,axis=0)>1.5]
    if len(quantity_over_thres)>0:
        quantity_min = min(quantity_over_thres)
        quantity_max = max(quantity_over_thres)
        #print (adc_min, adc_max)
        if quantity_min>=-1 and quantity_max<=1024 and quantity_max>quantity_min:
            fig_trig_adc.y_range.start = quantity_min
            fig_trig_adc.y_range.end = quantity_max
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
    if fig_trig_adc.x_range.start!=selected_trigtime_range[0] or fig_trig_adc.x_range.end!=selected_trigtime_range[1]:
        fig_trig_adc.x_range.update(start = selected_trigtime_range[0], end = selected_trigtime_range[1])
                

fig_adc_overview = figure(
    x_axis_label = 'channel',
    y_axis_label = 'adc',
    tooltips=[("channel", "@channel"),("raw channel","@rawchannel"), ("chip", "@chip"), ("half", "@half"), ("adc median", "@y50"), ("adc 68%", "[@y15; @y85]")]
)
source_adc_overview = ColumnDataSource(data={'y15':[],'y50':[],'y85':[], 'channel':[], 'rawchannel': [], 'half':[], "chip": []})
fig_adc_overview.vbar(x='channel',width=0.7,top='y15',bottom='y50',source=source_adc_overview, fill_color='royalblue')
fig_adc_overview.vbar(x='channel',width=0.7,top='y50',bottom='y85',source=source_adc_overview, fill_color='deepskyblue')
select_adc_overview = BoxSelectTool()
fig_adc_overview.add_tools(select_adc_overview)
fig_adc_overview.toolbar.active_drag=select_adc_overview


def channel_select(attrname, old, new):
    global selected_channels,selected_rawchannels, selected_chip_halfs, selected_chips
    selected_rawchannels = []
    selected_chip_halfs = []
    selected_channels = []
    selected_chips = []
    for idx in new:
        selected_channels.append(source_adc_overview.data['channel'][idx])
        selected_rawchannels.append(source_adc_overview.data['rawchannel'][idx])
        selected_chip_halfs.append(source_adc_overview.data['half'][idx])
        selected_chips.append(source_adc_overview.data['chip'][idx])
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
    chips = []
    rawchannels = []
    halfs = []
    nchips = df_hgcrocData["chip"].max()+1
    for chip in range(nchips):
        for half in [0,1]:
            for channel in range(36):
                adc_data = df_selected[(df_selected['chip']==chip) & (df_selected['half']==half) & (df_selected['channel']==channel)]['adc']
                quantiles.append(adc_data.quantile(q=[0.05,0.15,0.50,0.85,0.95]).to_numpy())
                channels.append(100*chip+channel+36*half)
                rawchannels.append(channel)
                halfs.append(half)
                chips.append(chip)
    quantiles = np.stack(quantiles,axis=1)
    source_adc_overview.data = {'y15': quantiles[1], 'y50': quantiles[2], 'y85': quantiles[3], 'channel': channels, 'half': halfs, 'chip': chips, 'rawchannel': rawchannels}

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
        row([
            column([
                myTable,
                row([checkbox_vetocorruption_select,dropdown_select_quantity]) #,textfield_channel_select])
            ],spacing=10), 
            column([
                row([spinner_percentile,selected_trigtime_range_slider],sizing_mode="stretch_width"),
                fig_trig_adc
            ],spacing=10)
        ],height=470,spacing=10),
        row([
            fig_adc_overview,
            fig_adc_hist
        ],height=550,spacing=20)
    ],margin=10)
)
